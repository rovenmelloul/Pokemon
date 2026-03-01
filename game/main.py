"""Pokemon 3D - Main entry point.
OSM map + wild Pokemon + proximity battle + Pokedex.
"""
import os
import sys
import json
import urllib.request

GAME_DIR = os.path.dirname(os.path.abspath(__file__))
if GAME_DIR not in sys.path:
    sys.path.insert(0, GAME_DIR)

from direct.showbase.ShowBase import ShowBase
from panda3d.core import Filename, getModelPath, Point3
from app.player.player_instance import Player
from app.pokemon.pokemon import Pokemon
from app.map_floor import MapFloor
from engine.state_manager import GameState, StateManager
from engine.encounter import EncounterSystem
from engine.battle_scene import BattleScene3D
from core.pokedex import Pokedex
from ui.hud import ExplorationHUD

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

NUM_WILD_POKEMON = 5
ENCOUNTER_DISTANCE = 12.0


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

        # Game state
        self.state_mgr = StateManager()
        self.pokedex = Pokedex()
        self.encounter_sys = EncounterSystem()
        self.battle_scene = None

        # Map
        lat, lon = detect_gps()
        self.map_floor = MapFloor(
            self, lat=lat, lon=lon, zoom=17,
            style="voyager_nolabels", cartoon=True,
        )

        # Player
        self.player = Player(self)
        self.player.spawn_self()
        self.player.key_bindings()

        # Wild Pokemon
        self.wild_pokemon = []
        for i in range(NUM_WILD_POKEMON):
            poke = Pokemon(self)
            poke.spawn_random_pokemon()
            poke.draw_name_tag()
            self.wild_pokemon.append(poke)

        # HUD
        self.hud = ExplorationHUD(self, team=self.wild_pokemon[:1])
        self.hud.setup()

        # Encounter hint state
        self._nearby_pokemon = None

        # Key binding for battle trigger
        self.accept("e", self._try_battle)
        # Pokedex key
        self.accept("p", self._toggle_pokedex)

        # Proximity check task
        self.taskMgr.add(self._proximity_check_task, "proximity_check")

    def _proximity_check_task(self, task):
        """Check if player is near a wild Pokemon."""
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

    def _try_battle(self):
        """Triggered when player presses E near a wild Pokemon."""
        if not self.state_mgr.is_state(GameState.EXPLORATION):
            return
        if self._nearby_pokemon is None:
            return

        enemy = self._nearby_pokemon
        self.encounter_sys.engage(enemy)
        self.hud.hide_encounter_hint()

        # Use the first wild pokemon as "player's pokemon" for the battle
        # (In a full game, the player would have their own team)
        player_poke = self._get_player_pokemon()

        self._enter_battle(player_poke, enemy)

    def _get_player_pokemon(self):
        """Get or create the player's Pokemon for battle."""
        # For now, create a fresh Bulbasaur-like Pokemon from the first wild one
        # In a full game, the player would have a persistent team
        # Use the first wild pokemon that isn't the enemy
        for p in self.wild_pokemon:
            if p is not self._nearby_pokemon and not p.is_fainted():
                return p
        # Fallback: create a new one
        poke = Pokemon(self)
        poke.spawn_random_pokemon()
        return poke

    def _enter_battle(self, player_poke, enemy_poke):
        """Transition from exploration to battle."""
        self.state_mgr.change_state(GameState.BATTLE)

        # Hide exploration elements
        self.player.control_node.hide()
        for p in self.wild_pokemon:
            p.animated_character.hide()
            if p.name_container:
                p.name_container.hide()
            if p._ground_circle:
                p._ground_circle.hide()
        self.map_floor.root.hide()
        self.hud.cleanup()

        # Disable player movement
        self.player.key_map = {k: False for k in self.player.key_map}

        # Create battle scene
        self.battle_scene = BattleScene3D(
            self, player_poke, enemy_poke,
            self.pokedex, is_wild=True,
            on_battle_end=self._on_battle_end
        )
        self.battle_scene.setup()

    def _on_battle_end(self, winner):
        """Called when battle finishes."""
        if self.battle_scene:
            self.battle_scene.cleanup()
            self.battle_scene = None

        # Remove defeated enemy from wild list
        enemy = self.encounter_sys.engaged_pokemon
        if enemy and (enemy.is_fainted() or winner == "player"):
            if enemy in self.wild_pokemon:
                enemy.destroy()
                self.wild_pokemon.remove(enemy)
            # Spawn a replacement
            new_poke = Pokemon(self)
            new_poke.spawn_random_pokemon()
            new_poke.draw_name_tag()
            self.wild_pokemon.append(new_poke)

        self.encounter_sys.disengage()
        self._nearby_pokemon = None

        # Restore exploration
        self.state_mgr.change_state(GameState.EXPLORATION)
        self.player.control_node.show()
        for p in self.wild_pokemon:
            p.animated_character.show()
            if p.name_container:
                p.name_container.show()
            if p._ground_circle:
                p._ground_circle.show()
        self.map_floor.root.show()

        # Restore camera
        self.camera.reparentTo(self.player.control_node)
        self.player._update_camera_orbit()

        # Rebuild HUD
        self.hud = ExplorationHUD(self, team=self.wild_pokemon[:1])
        self.hud.setup()

    def _toggle_pokedex(self):
        """Toggle Pokedex UI with P key."""
        if self.state_mgr.is_state(GameState.POKEDEX):
            self._close_pokedex()
        elif self.state_mgr.is_state(GameState.EXPLORATION):
            self._open_pokedex()

    def _open_pokedex(self):
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


app = MyApp()
app.run()
