"""Pokemon 3D - Point d'entree principal.
Carte OSM + Pokemon sauvages + combat + Pokedex + Gestion d'equipe.
Menu Start + Capture 3D par drag de pokeball.
"""
import os
import sys
import json
import urllib.request

GAME_DIR = os.path.dirname(os.path.abspath(__file__))
if GAME_DIR not in sys.path:
    sys.path.insert(0, GAME_DIR)


from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    Filename, getModelPath, Point3, Vec4,
    Texture, TransparencyAttrib, CardMaker,
    PNMImage, NodePath, Shader,
)
from engine.state_manager import GameState, StateManager
from gui.main_menu import MainMenu
from core.save_manager import SaveManager
from core.sound_manager import SoundManager

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

NUM_WILD_POKEMON = 5
ENCOUNTER_DISTANCE = 12.0

# Sword/Shield starters
STARTERS = [
    (810, 10, False),  # Grookey
    (813, 10, False),  # Scorbunny
    (816, 10, False),  # Sobble
]


def detect_gps():
    try:
        data = json.loads(urllib.request.urlopen(
            'http://ip-api.com/json/', timeout=5).read())
        lat, lon = data['lat'], data['lon']
        print(f"[GPS] Position: {data.get('city', '?')} ({lat}, {lon})")
        return lat, lon
    except Exception:
        return 43.3104, 5.37335


class MyApp(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)
        getModelPath().prependDirectory(Filename.fromOsSpecific(PROJECT_ROOT))

        # Etat du jeu -- demarre en MENU
        self.state_mgr = StateManager()

        # Ciel (toujours visible)
        self._setup_sky()

        # Attributs initialises plus tard par _start_game
        self.pokedex = None
        self.encounter_sys = None
        self.battle_scene = None
        self.player = None
        self.player_team = []
        self.wild_pokemon = []
        self.hud = None
        self.map_floor = None
        self._nearby_pokemon = None
        self._swap_slot_index = None
        self._capture_3d = None
        self.current_slot = None

        # Audio
        self.sound_manager = SoundManager(self)

        # Menu principal
        self._main_menu = MainMenu(
            self,
            on_new_game=self._new_game,
            on_load_game=self._load_game,
        )
        self._main_menu.draw_main_menu()

    # ---- New Game (starters) ----

    def _new_game(self, slot_num):
        """Start a new game with Sword/Shield starters."""
        self.current_slot = slot_num
        self.sound_manager.play_sfx('menu_select')

        if self._main_menu:
            self._main_menu.destroy()
            self._main_menu = None

        from app.player.player_instance import Player
        from app.pokemon.pokemon import Pokemon
        from app.map_floor import MapFloor
        from engine.encounter import EncounterSystem
        from core.pokedex import Pokedex
        from ui.hud import ExplorationHUD

        self.pokedex = Pokedex()
        self.encounter_sys = EncounterSystem()

        # Carte
        lat, lon = detect_gps()
        self.map_floor = MapFloor(
            self, lat=lat, lon=lon, zoom=17,
            style="voyager_nolabels", cartoon=True,
        )

        # Joueur
        self.player = Player(self)
        self.player.spawn_self()
        self.player.key_bindings()

        # Equipe du joueur: 3 starters
        self.player_team = []
        for pokedex_id, level, is_shiny in STARTERS:
            poke = Pokemon(self)
            success = poke.spawn_from_pokedex(pokedex_id, level, is_shiny)
            if not success:
                poke.spawn_random_pokemon()
                poke.animated_character.hide()
                if poke._ground_circle:
                    poke._ground_circle.hide()
            self.player_team.append(poke)

            # Mark caught in pokedex
            if self.pokedex and poke.pokedex_id:
                self.pokedex.mark_caught(poke.pokedex_id, level=poke.level, is_shiny=poke.is_shiny)

        print(f"[Equipe] Votre equipe: {', '.join(p.name + ' Nv.' + str(p.level) for p in self.player_team)}")

        # Pokemon sauvages
        self.wild_pokemon = []
        for i in range(NUM_WILD_POKEMON):
            poke = Pokemon(self)
            poke.spawn_random_pokemon()
            poke.draw_name_tag()
            self.wild_pokemon.append(poke)

        # HUD
        self.hud = ExplorationHUD(
            self, player_team=self.player_team,
            on_pokedex=self._open_pokedex,
            on_team=self._open_team,
            on_heal=self._heal_team,
        )
        self.hud.setup()

        self._nearby_pokemon = None
        self._swap_slot_index = None

        self.accept("e", self._try_battle)
        self.accept("f", self._try_capture)
        self.accept("p", self._toggle_pokedex)
        self.accept("t", self._toggle_team)

        self.taskMgr.add(self._proximity_check_task, "proximity_check")

        self.state_mgr.change_state(GameState.EXPLORATION)
        print("[Jeu] Nouvelle partie lancee !")

        # Auto-save immediately
        self._auto_save()

    # ---- Load Game ----

    def _load_game(self, slot_num):
        """Load an existing save and resume game."""
        self.sound_manager.play_sfx('menu_select')
        save_data = SaveManager.load(slot_num)
        if not save_data:
            print(f"[Load] Slot {slot_num} vide ou corrompu, demarrage nouvelle partie")
            self._new_game(slot_num)
            return

        self.current_slot = slot_num

        if self._main_menu:
            self._main_menu.destroy()
            self._main_menu = None

        from app.player.player_instance import Player
        from app.pokemon.pokemon import Pokemon
        from app.map_floor import MapFloor
        from engine.encounter import EncounterSystem
        from core.pokedex import Pokedex
        from core.move import Move
        from ui.hud import ExplorationHUD

        self.pokedex = Pokedex()
        self.encounter_sys = EncounterSystem()

        # Restore pokedex state
        pokedex_data = save_data.get("pokedex", {})
        for pid_str, pdata in pokedex_data.items():
            pid = int(pid_str)
            if pid in self.pokedex.entries:
                self.pokedex.entries[pid]["status"] = pdata.get("status", "unknown")
                self.pokedex.entries[pid]["level"] = pdata.get("level", 0)
                self.pokedex.entries[pid]["is_shiny"] = pdata.get("is_shiny", False)

        # Carte
        lat, lon = detect_gps()
        self.map_floor = MapFloor(
            self, lat=lat, lon=lon, zoom=17,
            style="voyager_nolabels", cartoon=True,
        )

        # Joueur
        self.player = Player(self)
        self.player.spawn_self()
        self.player.key_bindings()

        # Restore player position
        player_data = save_data.get("player", {})
        pos = player_data.get("position", [0, 0, 0])
        heading = player_data.get("heading", 0)
        self.player.control_node.setPos(Point3(pos[0], pos[1], pos[2]))
        self.player.control_node.setH(heading)

        # Restore team
        self.player_team = []
        for poke_data in save_data.get("team", []):
            poke = Pokemon(self)
            pokedex_id = poke_data.get("pokedex_id")
            level = poke_data.get("level", 10)
            is_shiny = poke_data.get("is_shiny", False)

            success = poke.spawn_from_pokedex(pokedex_id, level, is_shiny)
            if not success:
                poke.spawn_random_pokemon()
                poke.animated_character.hide()
                if poke._ground_circle:
                    poke._ground_circle.hide()

            # Restore HP, XP, status
            poke.current_hp = poke_data.get("current_hp", poke.stats.get("hp", 1))
            poke.xp = poke_data.get("xp", 0)
            poke.status = poke_data.get("status", None)

            # Restore moves with current PP
            saved_moves = poke_data.get("moves", [])
            if saved_moves:
                poke.moves = []
                for mdata in saved_moves:
                    try:
                        move = Move.get_by_id(mdata["id"])
                        move.current_pp = mdata.get("current_pp", move.max_pp)
                        poke.moves.append(move)
                    except KeyError:
                        pass
                if not poke.moves:
                    try:
                        poke.moves = [Move.get_by_id(1)]
                    except KeyError:
                        pass

            self.player_team.append(poke)

        print(f"[Equipe] Equipe chargee: {', '.join(p.name + ' Nv.' + str(p.level) for p in self.player_team)}")

        # Pokemon sauvages (fresh random)
        self.wild_pokemon = []
        for i in range(NUM_WILD_POKEMON):
            poke = Pokemon(self)
            poke.spawn_random_pokemon()
            poke.draw_name_tag()
            self.wild_pokemon.append(poke)

        # HUD
        self.hud = ExplorationHUD(
            self, player_team=self.player_team,
            on_pokedex=self._open_pokedex,
            on_team=self._open_team,
            on_heal=self._heal_team,
        )
        self.hud.setup()

        self._nearby_pokemon = None
        self._swap_slot_index = None

        self.accept("e", self._try_battle)
        self.accept("f", self._try_capture)
        self.accept("p", self._toggle_pokedex)
        self.accept("t", self._toggle_team)

        self.taskMgr.add(self._proximity_check_task, "proximity_check")

        self.state_mgr.change_state(GameState.EXPLORATION)
        print(f"[Jeu] Partie chargee depuis slot {slot_num} !")

    # ---- Auto-save ----

    def _auto_save(self):
        """Save current state to current slot."""
        if self.current_slot and self.player:
            SaveManager.save(self.current_slot, self)

    def _setup_sky(self):
        """Create a sky sphere with a panoramic texture."""
        self.setBackgroundColor(0.53, 0.81, 0.92, 1)

        sky_path = os.path.join(GAME_DIR, "data", "sky_panorama.png")
        if not os.path.exists(sky_path):
            print("[Sky] sky_panorama.png not found, using solid color")
            return

        sky_tex = self.loader.loadTexture(Filename.fromOsSpecific(sky_path))
        if not sky_tex:
            return

        sky_tex.setWrapU(Texture.WMRepeat)
        sky_tex.setWrapV(Texture.WMClamp)
        sky_tex.setMinfilter(Texture.FTLinearMipmapLinear)
        sky_tex.setMagfilter(Texture.FTLinear)

        sky_sphere = self.loader.loadModel("models/misc/sphere")
        if not sky_sphere:
            sky_sphere = self.loader.loadModel("misc/sphere")
        if not sky_sphere:
            print("[Sky] Could not load sphere model")
            return

        sky_sphere.reparentTo(self.camera)
        sky_sphere.setScale(800)
        sky_sphere.setTexture(sky_tex, 1)
        sky_sphere.setLightOff()
        sky_sphere.setCompass()
        sky_sphere.setBin("background", 0)
        sky_sphere.setDepthWrite(False)
        sky_sphere.setDepthTest(False)
        sky_sphere.setTwoSided(True)
        self._sky_sphere = sky_sphere

    def _proximity_check_task(self, task):
        if not self.state_mgr.is_state(GameState.EXPLORATION):
            return task.cont

        player_pos = self.player.control_node.getPos()
        nearest = self.encounter_sys.check_proximity(player_pos, self.wild_pokemon)

        if nearest and nearest != self._nearby_pokemon:
            self._nearby_pokemon = nearest
            self.hud.show_encounter_hint(nearest.name)
        elif not nearest and self._nearby_pokemon:
            self._nearby_pokemon = None
            self.hud.hide_encounter_hint()

        return task.cont

    # ---- Combat (E) ----

    def _try_battle(self):
        if not self.state_mgr.is_state(GameState.EXPLORATION):
            return
        if self._nearby_pokemon is None:
            return

        alive = [p for p in self.player_team if not p.is_fainted()]
        if not alive:
            self.hud.show_encounter_hint("Tous vos Pokemon sont K.O. ! Soignez-les d'abord.")
            return

        enemy = self._nearby_pokemon
        self.encounter_sys.engage(enemy)
        self.hud.hide_encounter_hint()

        self._enter_battle(enemy)

    def _enter_battle(self, enemy_poke):
        from engine.battle_scene import BattleScene3D

        self.state_mgr.change_state(GameState.BATTLE)

        # Stopper les tasks camera du joueur
        self.taskMgr.remove("update_task")
        self.taskMgr.remove("mouse_rotation_task")

        # Desactiver le scroll zoom
        self.ignore("wheel_up")
        self.ignore("wheel_down")

        # Sauvegarder les positions pour la camera de combat
        enemy_pos = enemy_poke.animated_character.getPos(self.render)
        player_pos = self.player.control_node.getPos()

        # Cacher: joueur + tous les Pokemon sauvages
        self.player.control_node.hide()
        for p in self.wild_pokemon:
            p.animated_character.hide()
            if p.name_container:
                p.name_container.hide()
            if p._ground_circle:
                p._ground_circle.hide()
        # La carte reste VISIBLE
        self.hud.cleanup()

        # Desactiver le mouvement
        self.player.key_map = {k: False for k in self.player.key_map}

        # Scene de combat sur la carte
        self.sound_manager.play_sfx('battle_start')

        self.battle_scene = BattleScene3D(
            self, self.player_team, enemy_poke,
            self.pokedex,
            enemy_world_pos=enemy_pos,
            player_world_pos=player_pos,
            is_wild=True,
            on_battle_end=self._on_battle_end,
        )
        self.battle_scene.setup()

    def _on_battle_end(self, winner):
        from app.pokemon.pokemon import Pokemon

        if winner == "player":
            self.sound_manager.play_sfx('victory')
        elif winner == "enemy":
            self.sound_manager.play_sfx('defeat')

        if self.battle_scene:
            self.battle_scene.cleanup()
            self.battle_scene = None

        enemy = self.encounter_sys.engaged_pokemon
        if enemy and (enemy.is_fainted() or winner == "player"):
            if enemy in self.wild_pokemon:
                enemy.destroy()
                self.wild_pokemon.remove(enemy)
            new_poke = Pokemon(self)
            new_poke.spawn_random_pokemon()
            new_poke.draw_name_tag()
            self.wild_pokemon.append(new_poke)

        self.encounter_sys.disengage()
        self._nearby_pokemon = None

        self._restore_exploration()

        # Auto-save after battle
        self._auto_save()

    # ---- Capture 3D (F) ----

    def _try_capture(self):
        if not self.state_mgr.is_state(GameState.EXPLORATION):
            return
        if self._nearby_pokemon is None:
            return

        self.state_mgr.change_state(GameState.BATTLE)

        enemy = self._nearby_pokemon
        self.hud.hide_encounter_hint()

        # Stop player
        self.taskMgr.remove("update_task")
        self.taskMgr.remove("mouse_rotation_task")
        self.player.key_map = {k: False for k in self.player.key_map}

        from engine.capture_3d import Capture3D
        self._capture_3d = Capture3D(
            self, enemy.animated_character, enemy, self._on_capture_result
        )
        self._capture_3d.sound_manager = self.sound_manager
        self._capture_3d.start()

    def _on_capture_result(self, success):
        from app.pokemon.pokemon import Pokemon

        if self._capture_3d:
            self._capture_3d.cleanup()
            self._capture_3d = None

        enemy = self._nearby_pokemon

        if success and enemy:
            self.sound_manager.play_sfx('capture_success')
            # Pokedex update
            if self.pokedex and enemy.pokedex_id:
                self.pokedex.mark_caught(
                    enemy.pokedex_id,
                    level=enemy.level,
                    is_shiny=enemy.is_shiny,
                )
            # Remove et respawn
            enemy.destroy()
            if enemy in self.wild_pokemon:
                self.wild_pokemon.remove(enemy)
            new_poke = Pokemon(self)
            new_poke.spawn_random_pokemon()
            new_poke.draw_name_tag()
            self.wild_pokemon.append(new_poke)
            print(f"[Capture] {enemy.name} capture !")
        else:
            # Echec - le scale a deja ete restaure par capture_3d._show_failure
            pass

        self._nearby_pokemon = None
        self._restore_exploration()

        # Auto-save after capture
        if success:
            self._auto_save()

    # ---- Restauration exploration ----

    def _restore_exploration(self):
        """Restaure l'etat d'exploration apres combat ou capture."""
        from ui.hud import ExplorationHUD

        self.state_mgr.change_state(GameState.EXPLORATION)

        self.player.control_node.show()
        for p in self.wild_pokemon:
            p.animated_character.show()
            if p.name_container:
                p.name_container.show()
            if p._ground_circle:
                p._ground_circle.show()

        # Restaurer camera + tasks joueur
        self.camera.reparentTo(self.player.control_node)
        self.player._update_camera_orbit()
        self.taskMgr.add(self.player.update_camera_and_movement, "update_task")
        self.taskMgr.add(self.player.mouse_rotation_task, "mouse_rotation_task")

        # Restaurer le scroll zoom
        self.accept("wheel_up", self.player._zoom, [-1])
        self.accept("wheel_down", self.player._zoom, [1])

        # Reconstruire HUD
        self.hud = ExplorationHUD(
            self, player_team=self.player_team,
            on_pokedex=self._open_pokedex,
            on_team=self._open_team,
            on_heal=self._heal_team,
        )
        self.hud.setup()

    # ---- Pokedex ----

    def _toggle_pokedex(self):
        if self.state_mgr.is_state(GameState.POKEDEX):
            self._close_pokedex()
        elif self.state_mgr.is_state(GameState.EXPLORATION):
            self._open_pokedex()

    def _open_pokedex(self):
        if not self.state_mgr.is_state(GameState.EXPLORATION):
            return
        from ui.pokedex_ui import PokedexUI
        self.state_mgr.change_state(GameState.POKEDEX)
        self.player.key_map = {k: False for k in self.player.key_map}
        self._pokedex_ui = PokedexUI(self, self.pokedex, self._close_pokedex)
        self._pokedex_ui.show()

    def _close_pokedex(self):
        if hasattr(self, '_pokedex_ui') and self._pokedex_ui:
            self._pokedex_ui.cleanup()
            self._pokedex_ui = None
        self.state_mgr.change_state(GameState.EXPLORATION)

    # ---- Equipe ----

    def _toggle_team(self):
        if self.state_mgr.is_state(GameState.TEAM):
            self._close_team()
        elif self.state_mgr.is_state(GameState.EXPLORATION):
            self._open_team()

    def _open_team(self):
        if not self.state_mgr.is_state(GameState.EXPLORATION):
            return
        from ui.team_ui import TeamUI
        self.state_mgr.change_state(GameState.TEAM)
        self.player.key_map = {k: False for k in self.player.key_map}
        self._team_ui = TeamUI(self, self.player_team, self._close_team,
                               on_swap=self._on_team_swap)
        self._team_ui.show()

    def _close_team(self):
        if hasattr(self, '_team_ui') and self._team_ui:
            self._team_ui.cleanup()
            self._team_ui = None
        self.state_mgr.change_state(GameState.EXPLORATION)

    # ---- Swap: Equipe -> Pokedex -> remplacement ----

    def _on_team_swap(self, slot_index):
        """Called when user clicks 'Echanger' on a team slot."""
        self._swap_slot_index = slot_index
        old_name = self.player_team[slot_index].name

        # Close team UI
        if hasattr(self, '_team_ui') and self._team_ui:
            self._team_ui.cleanup()
            self._team_ui = None

        # Open Pokedex in swap mode
        from ui.pokedex_ui import PokedexUI
        self.state_mgr.change_state(GameState.POKEDEX)
        self._pokedex_ui = PokedexUI(
            self, self.pokedex, self._close_swap_pokedex,
            swap_mode=True, on_swap_select=self._on_swap_select,
        )
        self._pokedex_ui.show()
        print(f"[Swap] Choisissez un Pokemon pour remplacer {old_name} (slot {slot_index})")

    def _on_swap_select(self, pokedex_id, level, is_shiny):
        """Called when user picks a Pokemon from the Pokedex swap list."""
        from app.pokemon.pokemon import Pokemon

        slot = self._swap_slot_index
        if slot is None or slot >= len(self.player_team):
            self._swap_slot_index = None
            return

        # Destroy old Pokemon
        old_poke = self.player_team[slot]
        old_name = old_poke.name
        old_poke.destroy()

        # Create new Pokemon from Pokedex
        new_poke = Pokemon(self)
        success = new_poke.spawn_from_pokedex(pokedex_id, level, is_shiny)
        if not success:
            # Fallback: spawn random if pokedex entry failed
            new_poke.spawn_random_pokemon()
            new_poke.animated_character.hide()
            if new_poke._ground_circle:
                new_poke._ground_circle.hide()

        self.player_team[slot] = new_poke
        self._swap_slot_index = None

        print(f"[Swap] {old_name} remplace par {new_poke.name} Nv.{new_poke.level}")

        # Return to exploration
        self.state_mgr.change_state(GameState.EXPLORATION)

        # Auto-save after swap
        self._auto_save()

    def _close_swap_pokedex(self):
        """Called when swap Pokedex is closed without selection (cancel)."""
        if hasattr(self, '_pokedex_ui') and self._pokedex_ui:
            self._pokedex_ui.cleanup()
            self._pokedex_ui = None
        self._swap_slot_index = None
        self.state_mgr.change_state(GameState.EXPLORATION)

    # ---- Soin ----

    def _heal_team(self):
        if not self.state_mgr.is_state(GameState.EXPLORATION):
            return
        self.sound_manager.play_sfx('heal')
        for p in self.player_team:
            p.full_restore()
        print("[Equipe] Tous les Pokemon sont soignes !")
        self.hud.show_heal_message()

        # Auto-save after heal
        self._auto_save()


app = MyApp()
app.run()
