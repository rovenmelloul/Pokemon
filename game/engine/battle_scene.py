"""
BattleScene3D -- 3D battle scene using SDK Pokemon models.
Integrates BattleSystem with real 3D models loaded via sdk.spawn.Pokemon.
"""
import os
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
from core.capture import CaptureSystem
from core.xp_system import XPSystem
from core.pokedex import Pokedex
from ui.battle_ui import BattleUI

from sdk import Pokemon as SDKPokemon
from sdk import AnimationController

from pathlib import Path
_MODELS_BASE = str(Path(os.path.dirname(__file__), '..', '..', 'models', 'pokemon').resolve())


class BattleScene3D(DirectObject):
    """
    3D battle scene with real Pokemon models via the SDK.
    Shows two Pokemon face to face with animations.
    """

    def __init__(self, app, player_pokemon, enemy_pokemon,
                 pokedex, is_wild=True, on_battle_end=None):
        """
        Args:
            app: ShowBase instance
            player_pokemon: the player's Pokemon (game/app/pokemon/pokemon.py instance)
            enemy_pokemon: the wild/enemy Pokemon
            pokedex: Pokedex instance
            on_battle_end: callback(winner_str)
        """
        super().__init__()
        self.app = app
        self.pokedex = pokedex
        self.is_wild = is_wild
        self.on_battle_end = on_battle_end

        # Build battle teams (single Pokemon each for now)
        self.player_pokemon = player_pokemon
        self.enemy_pokemon = enemy_pokemon

        # The BattleSystem operates on objects with combat stats
        # Our hybrid Pokemon class has all needed attributes
        self.battle = BattleSystem(
            [player_pokemon], [enemy_pokemon], is_wild
        )

        if pokedex and enemy_pokemon.pokedex_id:
            pokedex.mark_seen(enemy_pokemon.pokedex_id)

        # Scene nodes
        self.scene_root = None
        self.player_model_node = None
        self.enemy_model_node = None
        self.player_sdk = None
        self.enemy_sdk = None
        self.player_anim = None
        self.enemy_anim = None

        # UI
        self.battle_ui = None
        self.is_animating = False

    def setup(self):
        """Initialize the battle scene."""
        self.scene_root = self.app.render.attachNewNode("battle_scene")

        self._build_terrain()
        self._setup_lighting()
        self._setup_camera()
        self._load_pokemon_models()

        # UI
        self.battle_ui = BattleUI(self.app, self.battle, self)
        self.battle_ui.setup()
        self.battle_ui.update_display()

        self._play_intro()

    def _build_terrain(self):
        cm = CardMaker("ground")
        cm.setFrame(-15, 15, -10, 10)
        ground = self.scene_root.attachNewNode(cm.generate())
        ground.setP(-90)
        ground.setColor(0.35, 0.55, 0.3, 1)
        ground.setPos(0, 0, 0)

        # Player platform
        cm2 = CardMaker("platform_player")
        cm2.setFrame(-3, 3, -1.5, 1.5)
        plat = self.scene_root.attachNewNode(cm2.generate())
        plat.setP(-90)
        plat.setColor(0.5, 0.4, 0.3, 1)
        plat.setPos(-5, 5, 0.01)

        # Enemy platform
        cm3 = CardMaker("platform_enemy")
        cm3.setFrame(-3, 3, -1.5, 1.5)
        plat_e = self.scene_root.attachNewNode(cm3.generate())
        plat_e.setP(-90)
        plat_e.setColor(0.5, 0.4, 0.3, 1)
        plat_e.setPos(5, 12, 0.01)

    def _setup_lighting(self):
        alight = AmbientLight("battle_ambient")
        alight.setColor(Vec4(0.5, 0.5, 0.5, 1))
        self.scene_root.setLight(self.scene_root.attachNewNode(alight))
        dlight = DirectionalLight("battle_sun")
        dlight.setColor(Vec4(0.9, 0.85, 0.7, 1))
        dlnp = self.scene_root.attachNewNode(dlight)
        dlnp.setHpr(30, -60, 0)
        self.scene_root.setLight(dlnp)

    def _setup_camera(self):
        self.app.camera.reparentTo(self.scene_root)
        self.app.camera.setPos(-8, -5, 8)
        self.app.camera.lookAt(Point3(0, 8, 2))

    def _load_pokemon_models(self):
        """Load real 3D models via SDK."""
        self.player_model_node, self.player_sdk, self.player_anim = (
            self._load_sdk_model(self.player_pokemon, Vec3(-5, 5, 0), Vec3(45, 0, 0))
        )
        self.enemy_model_node, self.enemy_sdk, self.enemy_anim = (
            self._load_sdk_model(self.enemy_pokemon, Vec3(5, 12, 0), Vec3(-135, 0, 0))
        )

    def _load_sdk_model(self, pokemon, pos, hpr):
        """Load a Pokemon model using the SDK for correct rendering."""
        model_folder = pokemon.model_folder
        if not model_folder:
            return self._create_placeholder(pokemon, pos, hpr), None, None

        model_dir = os.path.join(_MODELS_BASE, model_folder)
        if not os.path.isdir(model_dir):
            return self._create_placeholder(pokemon, pos, hpr), None, None

        try:
            sdk_poke = SDKPokemon(
                self.app, model_dir,
                use_shiny=pokemon.is_shiny, auto_center=False
            )
            anim_ctrl = AnimationController(
                self.app, sdk_poke, auto_idle=True
            )
            actor = sdk_poke.actor
            actor.reparentTo(self.scene_root)
            actor.setScale(0.05)
            actor.setPos(pos)
            actor.setHpr(hpr)

            idle = anim_ctrl.find_idle()
            if idle:
                anim_ctrl.play(idle, loop=True)

            return actor, sdk_poke, anim_ctrl
        except Exception as e:
            print(f"[BattleScene] Model load error for {model_folder}: {e}")
            return self._create_placeholder(pokemon, pos, hpr), None, None

    def _create_placeholder(self, pokemon, pos, hpr):
        placeholder = self.scene_root.attachNewNode(f"placeholder_{pokemon.name}")
        # Simple colored cube
        cm = CardMaker("face")
        cm.setFrame(-1.5, 1.5, 0, 3)
        for angle in [0, 90, 180, 270]:
            face = placeholder.attachNewNode(cm.generate())
            face.setH(angle)
            face.setPos(0, 0, 0)

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
        placeholder.setHpr(hpr)

        # Name label
        OnscreenText(
            text=pokemon.name, pos=(0, 0), scale=0.5,
            fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
            parent=placeholder, align=TextNode.ACenter
        )
        return placeholder

    def _play_intro(self):
        name = self.battle.active_enemy.name
        text = f"A wild {name} appeared!" if self.is_wild else "Trainer battle!"
        seq = Sequence(
            Wait(0.3),
            Func(self.battle_ui.show_message, text),
            Wait(2.0),
            Func(self.battle_ui.show_action_menu),
        )
        seq.start()

    # ---- Combat actions ----

    def on_attack(self, move_index):
        if self.is_animating:
            return
        self.is_animating = True

        player_action = {"type": "attack", "move_index": move_index}
        enemy_action = self.battle.get_enemy_action()
        logs = self.battle.execute_turn(player_action, enemy_action)

        # Play attack animation on player model
        if self.player_anim:
            atk_anim = self.player_anim.find_anim("ba20", "buturi")
            if atk_anim:
                self.player_anim.play(atk_anim, loop=False)

        self._show_messages_sequence(logs)

    def on_switch(self, pokemon_index):
        if self.is_animating:
            return
        self.is_animating = True
        player_action = {"type": "switch", "pokemon_index": pokemon_index}
        enemy_action = self.battle.get_enemy_action()
        logs = self.battle.execute_turn(player_action, enemy_action)
        self._show_messages_sequence(logs)

    def on_capture(self, ball_type="pokeball"):
        if self.is_animating:
            return
        self.is_animating = True
        result = CaptureSystem.attempt_capture(self.battle.active_enemy, ball_type)

        messages = [f"Throwing {ball_type.title()}!"]
        for i in range(result["shakes"]):
            messages.append(f"... shake {i+1} ...")
        messages.append(result["message"])

        if result["success"]:
            if self.pokedex and self.battle.active_enemy.pokedex_id:
                self.pokedex.mark_caught(self.battle.active_enemy.pokedex_id)
            self.battle.is_over = True
            self.battle.winner = "player"

        self._show_messages_sequence(messages)

    def on_run(self):
        if not self.is_wild:
            self.battle_ui.show_message("Can't run from a trainer battle!")
            return
        self.battle.is_over = True
        self._end_battle()

    def _show_messages_sequence(self, messages):
        intervals = []
        for msg in messages:
            if msg.strip():
                intervals.append(Func(self.battle_ui.show_message, msg))
                intervals.append(Wait(1.0))
        intervals.append(Func(self._after_turn))
        Sequence(*intervals).start()

    def _after_turn(self):
        self.battle_ui.update_display()
        self.is_animating = False

        if self.battle.is_over:
            self._end_battle()
        elif self.battle.player_needs_switch():
            self.battle_ui.show_switch_menu(forced=True)
        else:
            # Return to idle
            if self.player_anim:
                idle = self.player_anim.find_idle()
                if idle:
                    self.player_anim.play(idle, loop=True)
            self.battle_ui.show_action_menu()

    def _end_battle(self):
        if self.battle.winner == "player":
            for pokemon in self.battle.team_player:
                if not pokemon.is_fainted():
                    xp = XPSystem.calculate_xp_gain(
                        pokemon, self.battle.team_enemy[0], self.is_wild
                    )
                    events = XPSystem.award_xp(pokemon, xp)
                    msgs = XPSystem.format_events(events)
                    for msg in msgs:
                        print(msg)

        if self.on_battle_end:
            self.on_battle_end(self.battle.winner)

    def cleanup(self):
        self.ignoreAll()
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
