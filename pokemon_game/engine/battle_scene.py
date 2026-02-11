"""
battle_scene.py — Scène de combat 3D Panda3D.
Affiche les modèles .egg, gère les animations et intègre le BattleSystem.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from panda3d.core import (
    Vec3, Vec4, Point3, CardMaker, TextNode,
    AmbientLight, DirectionalLight, Spotlight,
    TransparencyAttrib
)
from direct.showbase.DirectObject import DirectObject
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import (
    Sequence, Parallel, Func, Wait, LerpPosInterval,
    LerpScaleInterval, LerpColorScaleInterval
)
from direct.gui.OnscreenText import OnscreenText

from core.pokemon import Pokemon
from core.battle import BattleSystem
from core.capture import CaptureSystem
from core.xp_system import XPSystem
from core.pokedex import Pokedex
from ui.battle_ui import BattleUI


# Mapping des animations .egg pour pm0001_00 (Bulbasaur)
POKEMON_ANIMS = {
    "pm0001_00": {
        "idle": "models/pm0001_00/anims/pm0001_00_ba10_waitA01.egg",
        "attack_physical": "models/pm0001_00/anims/pm0001_00_ba20_buturi01.egg",
        "attack_special": "models/pm0001_00/anims/pm0001_00_ba21_tokusyu01.egg",
        "damage": "models/pm0001_00/anims/pm0001_00_ba30_damageS01.egg",
        "down": "models/pm0001_00/anims/pm0001_00_ba41_down01.egg",
        "walk": "models/pm0001_00/anims/pm0001_00_fi20_walk01.egg",
        "roar": "models/pm0001_00/anims/pm0001_00_ba02_roar01.egg",
    }
}

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "game", "models")


class BattleScene(DirectObject):
    """
    Scène de combat 3D avec :
    - Terrain de combat
    - 2 Pokémons face à face (modèles .egg)
    - Animations (idle, attaque, dégâts, KO)
    - Intégration avec BattleUI pour les menus et barres HP
    """

    def __init__(self, app, team_player: list[Pokemon], team_enemy: list[Pokemon],
                 pokedex: Pokedex, is_wild: bool = True,
                 on_battle_end=None):
        super().__init__()
        self.app = app
        self.pokedex = pokedex
        self.is_wild = is_wild
        self.on_battle_end = on_battle_end

        # Système de combat
        self.battle = BattleSystem(team_player, team_enemy, is_wild)
        pokedex.mark_seen(self.battle.active_enemy.id)

        # Nodes
        self.scene_root = None
        self.player_model = None
        self.enemy_model = None
        self.terrain = None

        # UI
        self.battle_ui = None
        self.is_animating = False

    def setup(self):
        """Initialise la scène de combat."""
        self.scene_root = self.app.render.attachNewNode("battle_scene")
        
        self._build_terrain()
        self._setup_lighting()
        self._setup_camera()
        self._load_pokemon_models()
        
        # UI
        self.battle_ui = BattleUI(self.app, self.battle, self)
        self.battle_ui.setup()
        self.battle_ui.update_display()
        
        # Intro animation
        self._play_intro()

    def _build_terrain(self):
        """Construit le terrain de combat."""
        # Sol
        cm = CardMaker("ground")
        cm.setFrame(-15, 15, -10, 10)
        ground = self.scene_root.attachNewNode(cm.generate())
        ground.setP(-90)
        ground.setColor(0.35, 0.55, 0.3, 1)  # Vert herbe
        ground.setPos(0, 0, 0)

        # Plateforme joueur
        cm2 = CardMaker("platform_player")
        cm2.setFrame(-3, 3, -1.5, 1.5)
        plat_p = self.scene_root.attachNewNode(cm2.generate())
        plat_p.setP(-90)
        plat_p.setColor(0.5, 0.4, 0.3, 1)
        plat_p.setPos(-5, 5, 0.01)

        # Plateforme ennemi
        cm3 = CardMaker("platform_enemy")
        cm3.setFrame(-3, 3, -1.5, 1.5)
        plat_e = self.scene_root.attachNewNode(cm3.generate())
        plat_e.setP(-90)
        plat_e.setColor(0.5, 0.4, 0.3, 1)
        plat_e.setPos(5, 12, 0.01)

    def _setup_lighting(self):
        """Éclairage de la scène combat."""
        alight = AmbientLight("battle_ambient")
        alight.setColor(Vec4(0.5, 0.5, 0.5, 1))
        self.scene_root.setLight(self.scene_root.attachNewNode(alight))

        dlight = DirectionalLight("battle_sun")
        dlight.setColor(Vec4(0.9, 0.85, 0.7, 1))
        dlnp = self.scene_root.attachNewNode(dlight)
        dlnp.setHpr(30, -60, 0)
        self.scene_root.setLight(dlnp)

    def _setup_camera(self):
        """Positionne la caméra pour le combat."""
        self.app.camera.reparentTo(self.scene_root)
        self.app.camera.setPos(-8, -5, 8)
        self.app.camera.lookAt(Point3(0, 8, 2))

    def _load_pokemon_models(self):
        """Charge les modèles des Pokémons actifs."""
        self.player_model = self._load_model(
            self.battle.active_player, 
            pos=Vec3(-5, 5, 0), 
            hpr=Vec3(45, 0, 0),
            is_player=True
        )
        self.enemy_model = self._load_model(
            self.battle.active_enemy,
            pos=Vec3(5, 12, 0),
            hpr=Vec3(-135, 0, 0),
            is_player=False
        )

    def _load_model(self, pokemon: Pokemon, pos: Vec3, hpr: Vec3,
                    is_player: bool) -> Actor | None:
        """Charge un modèle .egg avec animations si disponible."""
        model_id = pokemon.model_id
        if not model_id:
            # Pas de modèle 3D, créer un placeholder
            return self._create_placeholder(pokemon, pos, hpr, is_player)

        model_path = os.path.join(MODELS_DIR, model_id, f"{model_id}.egg")
        if not os.path.exists(model_path):
            return self._create_placeholder(pokemon, pos, hpr, is_player)

        # Charger avec animations
        anims = POKEMON_ANIMS.get(model_id, {})
        # Convertir les chemins relatifs en absolus
        anim_dict = {}
        for anim_name, anim_path in anims.items():
            full_path = os.path.join(os.path.dirname(__file__), "..", "..", anim_path)
            if os.path.exists(full_path):
                anim_dict[anim_name] = full_path

        try:
            actor = Actor(model_path, anim_dict)
            actor.reparentTo(self.scene_root)
            actor.setScale(0.05)
            actor.setPos(pos)
            actor.setHpr(hpr)
            if "idle" in anim_dict:
                actor.loop("idle")
            return actor
        except Exception as e:
            print(f"Erreur chargement modèle {model_id}: {e}")
            return self._create_placeholder(pokemon, pos, hpr, is_player)

    def _create_placeholder(self, pokemon: Pokemon, pos: Vec3, hpr: Vec3,
                            is_player: bool):
        """Crée un placeholder simple pour les Pokémons sans modèle 3D."""
        placeholder = self.scene_root.attachNewNode(f"placeholder_{pokemon.name}")
        
        try:
            box = self.app.loader.loadModel("models/box")
            if box:
                box.reparentTo(placeholder)
                box.setScale(1.5, 1.5, 2)
                box.setPos(0, 0, 1)
                # Couleur basée sur le type
                type_colors = {
                    "fire": Vec4(1, 0.4, 0.1, 1),
                    "water": Vec4(0.2, 0.5, 1, 1),
                    "grass": Vec4(0.2, 0.8, 0.3, 1),
                    "electric": Vec4(1, 0.9, 0.2, 1),
                    "poison": Vec4(0.6, 0.2, 0.8, 1),
                    "psychic": Vec4(1, 0.3, 0.7, 1),
                    "normal": Vec4(0.7, 0.7, 0.6, 1),
                    "ghost": Vec4(0.4, 0.3, 0.6, 1),
                    "fighting": Vec4(0.8, 0.3, 0.2, 1),
                    "rock": Vec4(0.6, 0.5, 0.3, 1),
                    "ground": Vec4(0.7, 0.6, 0.3, 1),
                    "flying": Vec4(0.5, 0.6, 0.9, 1),
                    "bug": Vec4(0.5, 0.7, 0.2, 1),
                    "ice": Vec4(0.5, 0.8, 0.9, 1),
                    "dragon": Vec4(0.4, 0.3, 0.9, 1),
                    "dark": Vec4(0.3, 0.2, 0.2, 1),
                    "steel": Vec4(0.6, 0.6, 0.7, 1),
                    "fairy": Vec4(0.9, 0.5, 0.7, 1),
                }
                color = type_colors.get(pokemon.types[0], Vec4(0.7, 0.7, 0.7, 1))
                box.setColor(color)
        except Exception:
            pass

        # Nom au-dessus
        name_text = OnscreenText(
            text=pokemon.name,
            pos=(0, 0), scale=0.5,
            fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
            parent=placeholder, align=TextNode.ACenter
        )
        
        placeholder.setPos(pos)
        placeholder.setHpr(hpr)
        return placeholder

    def _play_intro(self):
        """Animation d'introduction du combat."""
        seq = Sequence(
            Wait(0.5),
            Func(self._show_intro_text),
            Wait(2.0),
            Func(self._hide_intro_text),
        )
        seq.start()

    def _show_intro_text(self):
        name = self.battle.active_enemy.name
        if self.is_wild:
            text = f"Un {name} sauvage apparaît !"
        else:
            text = "Combat de dresseur !"
        self.battle_ui.show_message(text)

    def _hide_intro_text(self):
        self.battle_ui.show_action_menu()

    # ─────────── Actions de combat ───────────

    def on_attack(self, move_index: int):
        """Le joueur choisit une attaque."""
        if self.is_animating:
            return

        self.is_animating = True
        player_action = {"type": "attack", "move_index": move_index}
        enemy_action = self.battle.get_enemy_action()
        
        logs = self.battle.execute_turn(player_action, enemy_action)
        self._animate_turn(logs)

    def on_switch(self, pokemon_index: int):
        """Le joueur switch de Pokémon."""
        if self.is_animating:
            return

        self.is_animating = True
        player_action = {"type": "switch", "pokemon_index": pokemon_index}
        enemy_action = self.battle.get_enemy_action()
        
        logs = self.battle.execute_turn(player_action, enemy_action)
        self._reload_player_model()
        self._animate_turn(logs)

    def on_capture(self, ball_type: str = "pokeball"):
        """Le joueur tente une capture."""
        if self.is_animating:
            return

        self.is_animating = True
        result = CaptureSystem.attempt_capture(self.battle.active_enemy, ball_type)
        
        messages = [f"Lancer de {ball_type.title()} !"]
        for i in range(result["shakes"]):
            messages.append(f"... shake {i+1} ...")
        messages.append(result["message"])
        
        if result["success"]:
            self.pokedex.mark_caught(self.battle.active_enemy.id)
            self.battle.is_over = True
            self.battle.winner = "player"
        
        self._show_messages_sequence(messages)

    def on_run(self):
        """Le joueur fuit."""
        if not self.is_wild:
            self.battle_ui.show_message("Impossible de fuir !")
            return
        self.battle.is_over = True
        self._end_battle()

    def _animate_turn(self, logs: list[str]):
        """Anime le tour et affiche les logs un par un."""
        self._show_messages_sequence(logs)

    def _show_messages_sequence(self, messages: list[str]):
        """Affiche une séquence de messages."""
        intervals = []
        for msg in messages:
            if msg.strip():
                intervals.append(Func(self.battle_ui.show_message, msg))
                intervals.append(Wait(1.0))

        intervals.append(Func(self._after_turn))
        seq = Sequence(*intervals)
        seq.start()

    def _after_turn(self):
        """Après un tour, mettre à jour l'UI et vérifier l'état."""
        self.battle_ui.update_display()
        self.is_animating = False

        if self.battle.is_over:
            self._end_battle()
        elif self.battle.player_needs_switch():
            self.battle_ui.show_switch_menu(forced=True)
        else:
            self.battle_ui.show_action_menu()

    def _reload_player_model(self):
        """Recharge le modèle joueur après un switch."""
        if self.player_model:
            self.player_model.removeNode()
        self.player_model = self._load_model(
            self.battle.active_player,
            pos=Vec3(-5, 5, 0),
            hpr=Vec3(45, 0, 0),
            is_player=True
        )

    def _reload_enemy_model(self):
        """Recharge le modèle ennemi."""
        if self.enemy_model:
            self.enemy_model.removeNode()
        self.enemy_model = self._load_model(
            self.battle.active_enemy,
            pos=Vec3(5, 12, 0),
            hpr=Vec3(-135, 0, 0),
            is_player=False
        )

    def _end_battle(self):
        """Fin du combat, attribuer XP si victoire."""
        if self.battle.winner == "player":
            # XP pour tous les Pokémons vivants
            for pokemon in self.battle.team_player:
                if not pokemon.is_fainted():
                    xp = XPSystem.calculate_xp_gain(
                        pokemon, self.battle.team_enemy[0], self.is_wild
                    )
                    events = XPSystem.award_xp(pokemon, xp)
                    msgs = XPSystem.format_events(events)
                    for msg in msgs:
                        print(msg)  # TODO: afficher en UI

        if self.on_battle_end:
            self.on_battle_end(self.battle.winner)

    def cleanup(self):
        """Nettoie la scène."""
        self.ignoreAll()
        if self.battle_ui:
            self.battle_ui.cleanup()
        if self.player_model:
            self.player_model.removeNode()
        if self.enemy_model:
            self.enemy_model.removeNode()
        if self.scene_root:
            self.scene_root.removeNode()
