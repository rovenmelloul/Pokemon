"""
BattleScene3D -- Combat 3D sur la carte OSM.
Pas de fond artificiel: les Pokemon combattent directement sur la map.
Utilise le systeme d'effets waza du SDK pour les attaques.
"""
import os
import math
from panda3d.core import (
    Vec3, Vec4, Point3, CardMaker, TextNode,
    AmbientLight, DirectionalLight, TransparencyAttrib,
)
from direct.showbase.DirectObject import DirectObject
from direct.interval.IntervalGlobal import (
    Sequence, Parallel, Func, Wait, LerpPosInterval,
    LerpScaleInterval, LerpColorScaleInterval,
)
from direct.gui.OnscreenText import OnscreenText

from core.battle import BattleSystem
from core.xp_system import XPSystem
from core.pokedex import Pokedex
from ui.battle_ui import BattleUI

from sdk import Pokemon as SDKPokemon
from sdk import AnimationController
from sdk.effect_system import EffectManager
from sdk.effect_system.effect_definitions import EffectDefinitions

from pathlib import Path
_MODELS_BASE = str(Path(os.path.dirname(__file__), '..', '..', 'models', 'pokemon').resolve())
_OUTPUT_DIR = str(Path(os.path.dirname(__file__), '..', '..', 'models').resolve())
_EFFECTS_JSON = str(Path(os.path.dirname(__file__), '..', 'data', 'effects.json').resolve())


def _get_model_size(node):
    """Return the max dimension of a model's bounding box."""
    bounds = node.getTightBounds()
    if bounds:
        bmin, bmax = bounds
        sx = abs(bmax.getX() - bmin.getX())
        sy = abs(bmax.getY() - bmin.getY())
        sz = abs(bmax.getZ() - bmin.getZ())
        return max(sx, sy, sz)
    return 3.0  # fallback


def _get_model_height(node):
    """Return the Y (height) of a model's bounding box."""
    bounds = node.getTightBounds()
    if bounds:
        bmin, bmax = bounds
        return abs(bmax.getZ() - bmin.getZ())
    return 3.0


class BattleScene3D(DirectObject):
    """Combat 3D directement sur la carte."""

    BATTLE_DIST = 20     # Distance entre les 2 Pokemon
    CAM_BACK_BASE = 28   # Camera derriere le joueur (base)
    CAM_HEIGHT_BASE = 10  # Hauteur camera (base)

    def __init__(self, app, player_team, enemy_pokemon,
                 pokedex, enemy_world_pos, player_world_pos,
                 is_wild=True, on_battle_end=None):
        super().__init__()
        self.app = app
        self.pokedex = pokedex
        self.is_wild = is_wild
        self.on_battle_end = on_battle_end

        self.player_team = player_team
        self.enemy_pokemon = enemy_pokemon

        # Positions sur la carte
        self.enemy_world_pos = enemy_world_pos
        self.player_world_pos = player_world_pos

        # Direction joueur -> ennemi
        dx = player_world_pos.x - enemy_world_pos.x
        dy = player_world_pos.y - enemy_world_pos.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1:
            dx, dy, dist = 0, -1, 1
        self._ndx = dx / dist
        self._ndy = dy / dist

        # Positions de combat (sur la carte)
        self.player_battle_pos = Point3(
            enemy_world_pos.x + self._ndx * self.BATTLE_DIST,
            enemy_world_pos.y + self._ndy * self.BATTLE_DIST,
            0,
        )
        self.enemy_battle_pos = Point3(enemy_world_pos.x, enemy_world_pos.y, 0)

        # Premier Pokemon non-KO du joueur
        self.player_pokemon = player_team[0]
        for p in player_team:
            if not p.is_fainted():
                self.player_pokemon = p
                break

        self.battle = BattleSystem(player_team, [enemy_pokemon], is_wild)

        if pokedex and enemy_pokemon.pokedex_id:
            pokedex.mark_seen(enemy_pokemon.pokedex_id)

        # Nodes
        self.scene_root = None
        self.player_model_node = None
        self.enemy_model_node = None
        self.player_sdk = None
        self.enemy_sdk = None
        self.player_anim = None
        self.enemy_anim = None

        # Effect system
        self.effect_mgr = None
        self.effect_defs = None

        # UI
        self.battle_ui = None
        self.is_animating = False
        self.ending = False

    def setup(self):
        self.scene_root = self.app.render.attachNewNode("battle_scene")

        # Init effect system
        self.effect_mgr = EffectManager(self.app, _OUTPUT_DIR)
        self.effect_defs = EffectDefinitions(_EFFECTS_JSON)
        print(f"[Combat] Waza catalog: {self.effect_mgr.catalog.count} modeles")

        self._setup_lighting()
        self._load_pokemon_models()
        self._setup_camera()

        self.battle_ui = BattleUI(self.app, self.battle, self)
        self.battle_ui.setup()
        self.battle_ui.update_display()

        self._play_intro()

    def _setup_lighting(self):
        alight = AmbientLight("battle_ambient")
        alight.setColor(Vec4(0.6, 0.6, 0.6, 1))
        self.scene_root.setLight(self.scene_root.attachNewNode(alight))
        dlight = DirectionalLight("battle_sun")
        dlight.setColor(Vec4(0.9, 0.85, 0.7, 1))
        dlnp = self.scene_root.attachNewNode(dlight)
        dlnp.setHpr(30, -60, 0)
        self.scene_root.setLight(dlnp)

    def _setup_camera(self):
        # Measure model sizes and adapt camera distance
        player_size = _get_model_size(self.player_model_node) if self.player_model_node else 3.0
        enemy_size = _get_model_size(self.enemy_model_node) if self.enemy_model_node else 3.0
        biggest = max(player_size, enemy_size)

        # Scale camera distance: base is tuned for size ~3-4
        scale_factor = max(1.0, biggest / 4.0)
        cam_side = self.CAM_BACK_BASE * scale_factor * 0.85
        cam_height = self.CAM_HEIGHT_BASE * scale_factor * 0.7

        # Side vector (perpendicular to battle axis) for lateral view
        side_x = -self._ndy
        side_y = self._ndx

        # Camera looks at the midpoint between the two Pokemon
        mid = Point3(
            (self.player_battle_pos.x + self.enemy_battle_pos.x) / 2,
            (self.player_battle_pos.y + self.enemy_battle_pos.y) / 2,
            biggest * 0.3,
        )

        self.app.camera.reparentTo(self.app.render)
        cam_pos = Point3(
            mid.x + side_x * cam_side,
            mid.y + side_y * cam_side,
            cam_height,
        )
        self.app.camera.setPos(cam_pos)
        self.app.camera.lookAt(mid)

    def _load_pokemon_models(self):
        self.player_model_node, self.player_sdk, self.player_anim = (
            self._load_sdk_model(self.player_pokemon, self.player_battle_pos)
        )
        self.enemy_model_node, self.enemy_sdk, self.enemy_anim = (
            self._load_sdk_model(self.enemy_pokemon, self.enemy_battle_pos)
        )
        # Face each other: headsUp orients +Y toward target, but models face -Y,
        # so we add 180 degrees to flip them around.
        if self.player_model_node:
            self.player_model_node.headsUp(self.enemy_battle_pos)
            self.player_model_node.setH(self.player_model_node.getH() + 180)
        if self.enemy_model_node:
            self.enemy_model_node.headsUp(self.player_battle_pos)
            self.enemy_model_node.setH(self.enemy_model_node.getH() + 180)

    def _load_sdk_model(self, pokemon, pos):
        model_folder = pokemon.model_folder
        if not model_folder:
            return self._create_placeholder(pokemon, pos), None, None

        model_dir = os.path.join(_MODELS_BASE, model_folder)
        if not os.path.isdir(model_dir):
            return self._create_placeholder(pokemon, pos), None, None

        try:
            sdk_poke = SDKPokemon(
                self.app, model_dir,
                use_shiny=pokemon.is_shiny, auto_center=False
            )
            anim_ctrl = AnimationController(
                self.app, sdk_poke, auto_idle=False
            )
            actor = sdk_poke.actor
            actor.reparentTo(self.scene_root)
            actor.setScale(0.05)
            actor.setPos(pos)

            return actor, sdk_poke, anim_ctrl
        except Exception as e:
            print(f"[Combat] Erreur modele {model_folder}: {e}")
            return self._create_placeholder(pokemon, pos), None, None

    def _create_placeholder(self, pokemon, pos):
        placeholder = self.scene_root.attachNewNode(f"placeholder_{pokemon.name}")
        cm = CardMaker("face")
        cm.setFrame(-1.5, 1.5, 0, 3)
        for angle in [0, 90, 180, 270]:
            face = placeholder.attachNewNode(cm.generate())
            face.setH(angle)

        type_colors = {
            "fire": Vec4(1, 0.4, 0.1, 1), "water": Vec4(0.2, 0.5, 1, 1),
            "grass": Vec4(0.2, 0.8, 0.3, 1), "electric": Vec4(1, 0.9, 0.2, 1),
            "poison": Vec4(0.6, 0.2, 0.8, 1), "normal": Vec4(0.7, 0.7, 0.6, 1),
            "ghost": Vec4(0.4, 0.3, 0.6, 1), "fighting": Vec4(0.8, 0.3, 0.2, 1),
            "rock": Vec4(0.6, 0.5, 0.3, 1), "ground": Vec4(0.7, 0.6, 0.3, 1),
            "flying": Vec4(0.5, 0.6, 0.9, 1), "bug": Vec4(0.5, 0.7, 0.2, 1),
            "ice": Vec4(0.5, 0.8, 0.9, 1), "dragon": Vec4(0.4, 0.3, 0.9, 1),
            "dark": Vec4(0.3, 0.2, 0.2, 1), "steel": Vec4(0.6, 0.6, 0.7, 1),
            "fairy": Vec4(0.9, 0.5, 0.7, 1), "psychic": Vec4(1, 0.3, 0.7, 1),
        }
        ptype = pokemon.types[0] if pokemon.types else "normal"
        placeholder.setColor(type_colors.get(ptype, Vec4(0.7, 0.7, 0.7, 1)))
        placeholder.setPos(pos)

        OnscreenText(
            text=pokemon.name, pos=(0, 0), scale=0.5,
            fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
            parent=placeholder, align=TextNode.ACenter
        )
        return placeholder

    # ---- Animation helpers ----

    def _play_anim(self, anim_ctrl, *keywords, loop=False):
        """Play first matching animation. Returns True if found."""
        if not anim_ctrl:
            return False
        anim = anim_ctrl.find_anim(*keywords)
        if anim:
            anim_ctrl.play(anim, loop=loop)
            return True
        return False

    def _play_idle(self, anim_ctrl):
        """Play idle animation on a controller."""
        if anim_ctrl:
            idle = anim_ctrl.find_idle()
            if idle:
                anim_ctrl.play(idle, loop=True)

    # ---- Waza Effect helpers ----

    def _fire_effect(self, move, attacker_node, defender_node):
        """Fire a waza effect for the given move. Uses effect_defs + catalog."""
        if not self.effect_mgr or not self.effect_defs:
            return

        # Try to find effect by exact move name first
        edef = self.effect_defs.get_effect(move.name)
        # Fallback: by type
        if not edef:
            edef = self.effect_defs.get_default_for_type(move.type)
        if not edef:
            return

        # Get waza model from catalog
        waza = self.effect_mgr.catalog.get(edef.model)
        if not waza:
            print(f"[Combat] Waza model '{edef.model}' not found in catalog")
            return

        # Get model heights for proportional scaling
        atk_h = _get_model_height(attacker_node) if attacker_node else 3.0
        def_h = _get_model_height(defender_node) if defender_node else 3.0

        color = tuple(edef.color) if edef.color else None

        self.effect_mgr.fire_from_bones(
            waza,
            attacker_node, defender_node,
            origin_bone=edef.origin_bone,
            target_bone=edef.target_bone,
            style=edef.style,
            scale=edef.scale,
            duration=edef.duration,
            color=color,
            spin=(edef.style == "projectile"),
            attacker_height=atk_h,
            defender_height=def_h,
        )

    # ---- Intro ----

    @property
    def sound(self):
        """Get SoundManager from app if available."""
        return getattr(self.app, 'sound_manager', None)

    def _play_intro(self):
        name = self.battle.active_enemy.name
        text = f"Un {name} sauvage apparait !" if self.is_wild else "Combat dresseur !"

        # Play entrance animations
        self._play_anim(self.enemy_anim, "ba01_land", "ba01", loop=False)
        self._play_anim(self.player_anim, "ba01_land", "ba01", loop=False)

        seq = Sequence(
            Wait(0.3),
            Func(self.battle_ui.show_message, text),
            Wait(1.5),
            # Roar/cry for enemy
            Func(lambda: self._play_anim(self.enemy_anim, "ba02_roar", "ba02", loop=False)),
            Wait(1.0),
            # Both to idle
            Func(lambda: self._play_idle(self.player_anim)),
            Func(lambda: self._play_idle(self.enemy_anim)),
            Wait(0.3),
            Func(self.battle_ui.show_action_menu),
        )
        seq.start()

    # ---- Actions de combat ----

    def on_attack(self, move_index):
        if self.is_animating or self.ending:
            return
        self.is_animating = True

        player_action = {"type": "attack", "move_index": move_index}
        enemy_action = self.battle.get_enemy_action()

        # Determine move for animation + effect
        player_move = None
        if move_index < len(self.battle.active_player.moves):
            player_move = self.battle.active_player.moves[move_index]

        # Get enemy move for effect
        enemy_move = None
        if enemy_action.get("type") == "attack":
            ei = enemy_action.get("move_index", 0)
            if ei < len(self.battle.active_enemy.moves):
                enemy_move = self.battle.active_enemy.moves[ei]

        logs = self.battle.execute_turn(player_action, enemy_action)

        # Build animation sequence interleaved with messages
        intervals = []

        # --- Player attacks ---
        # Player attack animation
        if player_move and player_move.category == "special":
            intervals.append(Func(lambda: self._play_anim(
                self.player_anim, "ba21_tokusyu", "ba21", "ba20", loop=False)))
        else:
            intervals.append(Func(lambda: self._play_anim(
                self.player_anim, "ba20_buturi", "ba20", loop=False)))
        intervals.append(Wait(0.3))

        # Fire waza effect + sound: player -> enemy
        if player_move:
            pm = player_move
            intervals.append(Func(lambda: [
                self._fire_effect(pm, self.player_model_node, self.enemy_model_node),
                self.sound and self.sound.play_attack_sfx(pm.type)
            ]))
        intervals.append(Wait(0.6))

        # Enemy takes damage animation + hit sound
        intervals.append(Func(lambda: [
            self._play_anim(self.enemy_anim, "ba30_damage", "ba30", "damage", loop=False),
            self.sound and self.sound.play_sfx('hit')
        ]))
        intervals.append(Wait(0.5))

        # Show battle messages
        for msg in logs:
            if msg.strip():
                intervals.append(Func(self.battle_ui.show_message, msg))
                intervals.append(Wait(0.8))

        # --- Enemy counter-attacks ---
        # Enemy attack animation
        if enemy_move and enemy_move.category == "special":
            intervals.append(Func(lambda: self._play_anim(
                self.enemy_anim, "ba21_tokusyu", "ba21", "ba20", loop=False)))
        else:
            intervals.append(Func(lambda: self._play_anim(
                self.enemy_anim, "ba20_buturi", "ba21_tokusyu", "ba20", "ba21", loop=False)))
        intervals.append(Wait(0.3))

        # Fire waza effect + sound: enemy -> player
        if enemy_move:
            em = enemy_move
            intervals.append(Func(lambda: [
                self._fire_effect(em, self.enemy_model_node, self.player_model_node),
                self.sound and self.sound.play_attack_sfx(em.type)
            ]))
        intervals.append(Wait(0.6))

        # Player takes damage animation + hit sound
        intervals.append(Func(lambda: [
            self._play_anim(self.player_anim, "ba30_damage", "ba30", "damage", loop=False),
            self.sound and self.sound.play_sfx('hit')
        ]))
        intervals.append(Wait(0.5))

        # Check faint animations
        intervals.append(Func(self._check_faint_anims))
        intervals.append(Wait(0.3))

        # Return to idle
        intervals.append(Func(self._both_to_idle))
        intervals.append(Func(self._after_turn))

        Sequence(*intervals).start()

    def _check_faint_anims(self):
        """Play faint animation if a Pokemon is KO."""
        if self.battle.active_enemy.is_fainted() and self.enemy_anim:
            self._play_anim(self.enemy_anim, "ba41_down", "ba41", "down", "faint", loop=False)
        if self.battle.active_player.is_fainted() and self.player_anim:
            self._play_anim(self.player_anim, "ba41_down", "ba41", "down", "faint", loop=False)

    def _both_to_idle(self):
        """Return both Pokemon to idle if not fainted."""
        if not self.battle.active_player.is_fainted():
            self._play_idle(self.player_anim)
        if not self.battle.active_enemy.is_fainted():
            self._play_idle(self.enemy_anim)

    def on_switch(self, pokemon_index):
        if self.is_animating or self.ending:
            return
        self.is_animating = True
        player_action = {"type": "switch", "pokemon_index": pokemon_index}
        enemy_action = self.battle.get_enemy_action()
        logs = self.battle.execute_turn(player_action, enemy_action)
        self._show_messages_sequence(logs)

    def on_run(self):
        if not self.is_wild:
            self.battle_ui.show_message("Impossible de fuir un combat dresseur !")
            return
        self.battle.is_over = True
        self.battle.winner = "run"
        self._end_battle()

    def _show_messages_sequence(self, messages):
        intervals = []
        for msg in messages:
            if msg.strip():
                intervals.append(Func(self.battle_ui.show_message, msg))
                intervals.append(Wait(1.0))
        intervals.append(Func(self._after_turn))
        Sequence(*intervals).start()

    def _swap_player_model(self):
        if self.player_anim:
            self.player_anim.destroy()
            self.player_anim = None
        if self.player_sdk:
            self.player_sdk.destroy()
            self.player_sdk = None
        elif self.player_model_node:
            self.player_model_node.removeNode()
            self.player_model_node = None

        # Clear bone cache since actor changed
        if self.effect_mgr:
            self.effect_mgr.on_actor_changed()

        self.player_pokemon = self.battle.active_player
        self.player_model_node, self.player_sdk, self.player_anim = (
            self._load_sdk_model(self.player_pokemon, self.player_battle_pos)
        )
        # Face enemy (add 180 because models face -Y)
        if self.player_model_node:
            self.player_model_node.headsUp(self.enemy_battle_pos)
            self.player_model_node.setH(self.player_model_node.getH() + 180)
        # Entrance animation
        self._play_anim(self.player_anim, "ba01_land", "ba01", loop=False)

    def _after_turn(self):
        if self.battle.active_player is not self.player_pokemon:
            self._swap_player_model()

        self.battle_ui.update_display()
        self.is_animating = False

        if self.battle.is_over:
            self._end_battle()
        elif self.battle.player_needs_switch():
            self.battle_ui.show_switch_menu(forced=True)
        else:
            self._both_to_idle()
            self.battle_ui.show_action_menu()

    def _end_battle(self):
        if self.ending:
            return
        self.ending = True
        self.is_animating = True

        messages = []
        has_evolution = False

        if self.battle.winner == "player":
            messages.append("Vous avez gagne le combat !")
            # Play faint on enemy
            self._play_anim(self.enemy_anim, "ba41_down", "ba41", loop=False)
            for pokemon in self.battle.team_player:
                if not pokemon.is_fainted():
                    xp = XPSystem.calculate_xp_gain(
                        pokemon, self.battle.team_enemy[0], self.is_wild
                    )
                    events = XPSystem.award_xp(pokemon, xp)
                    msgs = XPSystem.format_events(events)
                    for m in msgs:
                        messages.append(f"{pokemon.name}: {m}")
                    for evt in events:
                        if evt["type"] == "evolution" and pokemon is self.player_pokemon:
                            has_evolution = True
        elif self.battle.winner == "enemy":
            messages.append("Vous avez perdu le combat...")
            # Play faint on player
            self._play_anim(self.player_anim, "ba41_down", "ba41", loop=False)
        else:
            messages.append("Vous avez fui !")

        intervals = []
        for msg in messages:
            intervals.append(Func(self.battle_ui.show_message, msg))
            intervals.append(Wait(1.5))
        if has_evolution:
            intervals.append(Func(self._swap_player_model))
            intervals.append(Wait(1.0))
        intervals.append(Wait(0.5))
        intervals.append(Func(self._finish_battle))
        Sequence(*intervals).start()

    def _finish_battle(self):
        if self.on_battle_end:
            self.on_battle_end(self.battle.winner)

    def cleanup(self):
        self.ignoreAll()
        if self.effect_mgr:
            self.effect_mgr.destroy()
            self.effect_mgr = None
        if self.battle_ui:
            self.battle_ui.cleanup()
        if self.player_anim:
            self.player_anim.destroy()
        if self.player_sdk:
            self.player_sdk.destroy()
        elif self.player_model_node:
            self.player_model_node.removeNode()
        if self.enemy_anim:
            self.enemy_anim.destroy()
        if self.enemy_sdk:
            self.enemy_sdk.destroy()
        elif self.enemy_model_node:
            self.enemy_model_node.removeNode()
        if self.scene_root:
            self.scene_root.removeNode()
