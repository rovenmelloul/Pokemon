"""
game_app.py — Application Panda3D principale.
Gère le menu principal et les transitions entre exploration et combat.
"""
import sys
import os
import random

# Assurer que le dossier pokemon_game est dans le path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, Vec4, loadPrcFileData

from core.pokemon import Pokemon
from core.pokedex import Pokedex
from engine.state_manager import StateManager, GameState
from engine.map_scene import MapScene
from engine.battle_scene import BattleScene
from engine.encounter import EncounterSystem
from ui.hud import ExplorationHUD
from ui.main_menu import MainMenu


# Configuration Panda3D
loadPrcFileData("", "window-title Pokémon Game")
loadPrcFileData("", "win-size 1280 720")
loadPrcFileData("", "show-frame-rate-meter #t")


class GameApp(ShowBase):
    """
    Application principale du jeu Pokémon.
    Démarre sur le menu principal, gère les scènes et les transitions.
    """

    def __init__(self):
        ShowBase.__init__(self)
        
        # Désactiver les contrôles caméra par défaut
        self.disableMouse()
        
        # État
        self.state_manager = StateManager()
        
        # Équipe du joueur
        self.team_player = [
            Pokemon.create(1, 15),   # Bulbasaur
            Pokemon.create(4, 15),   # Charmander
            Pokemon.create(7, 15),   # Squirtle
            Pokemon.create(10, 15),  # Pikachu
            Pokemon.create(18, 14),  # Gastly
            Pokemon.create(21, 14),  # Eevee
        ]
        
        # Pokédex
        self.pokedex = Pokedex()
        for p in self.team_player:
            self.pokedex.mark_caught(p.id)
        
        # Scènes
        self.map_scene = None
        self.battle_scene = None
        self.hud = None
        self.main_menu = None
        
        # Background
        self.setBackgroundColor(Vec4(0.05, 0.05, 0.12, 1))
        
        # Afficher le menu principal
        self._show_main_menu()

    # ─────────── Menu Principal ───────────

    def _show_main_menu(self):
        """Affiche le menu principal."""
        self.state_manager.change_state(GameState.MAIN_MENU)
        
        # Nettoyer les scènes précédentes
        self._cleanup_all_scenes()
        
        # Repositionner la caméra par défaut
        self.camera.reparentTo(self.render)
        self.camera.setPos(0, -10, 5)
        self.camera.lookAt(0, 0, 0)
        
        # Créer le menu
        self.main_menu = MainMenu(self, {
            "exploration": self._start_exploration,
            "wild_battle": self._start_wild_battle,
            "trainer_battle": self._start_trainer_battle,
            "pokedex": self._show_pokedex_from_menu,
            "heal": self._heal_team,
            "quit": self._quit_game,
        })
        self.main_menu.setup()
        
        # Contrôle Échap → quitter depuis le menu
        self.accept("escape", self._quit_game)

    def _cleanup_all_scenes(self):
        """Nettoie toutes les scènes actives."""
        if self.battle_scene:
            self.battle_scene.cleanup()
            self.battle_scene = None
        if self.map_scene:
            self.map_scene.cleanup()
            self.map_scene = None
        if self.hud:
            self.hud.cleanup()
            self.hud = None
        if self.main_menu:
            self.main_menu.cleanup()
            self.main_menu = None

    # ─────────── Exploration ───────────

    def _start_exploration(self):
        """Lance la scène d'exploration."""
        self.state_manager.change_state(GameState.EXPLORATION)
        
        # Nettoyer le menu
        if self.main_menu:
            self.main_menu.cleanup()
            self.main_menu = None
        
        # Nettoyer la scène de combat si elle existe
        if self.battle_scene:
            self.battle_scene.cleanup()
            self.battle_scene = None
        
        # Background exploration
        self.setBackgroundColor(Vec4(0.4, 0.6, 0.8, 1))
        
        # Créer la map
        self.map_scene = MapScene(
            self,
            on_encounter_callback=self._on_wild_encounter
        )
        self.map_scene.setup()
        
        # HUD
        self.hud = ExplorationHUD(self, self.team_player)
        self.hud.setup()
        
        # Échap → retour au menu
        self.accept("escape", self._return_to_menu)
        self.accept("p", self._show_pokedex_ingame)

    def _return_to_menu(self):
        """Retourne au menu principal depuis l'exploration."""
        self._show_main_menu()

    # ─────────── Combats ───────────

    def _on_wild_encounter(self, wild_pokemon: Pokemon):
        """Déclenché quand on rencontre un Pokémon sauvage en exploration."""
        self._start_battle([wild_pokemon], is_wild=True)

    def _start_wild_battle(self):
        """Lance un combat sauvage aléatoire depuis le menu."""
        # Nettoyer le menu
        if self.main_menu:
            self.main_menu.cleanup()
            self.main_menu = None
        
        wild_ids = [12, 13, 14, 23, 30]
        wild_id = random.choice(wild_ids)
        wild_level = random.randint(
            max(5, self.team_player[0].level - 5),
            self.team_player[0].level + 2
        )
        wild = Pokemon.create(wild_id, wild_level)
        self._start_battle([wild], is_wild=True)

    def _start_trainer_battle(self):
        """Lance un combat dresseur depuis le menu."""
        # Nettoyer le menu
        if self.main_menu:
            self.main_menu.cleanup()
            self.main_menu = None
        
        team_enemy = [
            Pokemon.create(15, 16),  # Machop
            Pokemon.create(14, 16),  # Geodude
            Pokemon.create(29, 17),  # Onix
        ]
        self._start_battle(team_enemy, is_wild=False)

    def _start_battle(self, enemy_team: list[Pokemon], is_wild: bool = True):
        """Lance un combat."""
        self.state_manager.change_state(GameState.BATTLE)
        
        # Background combat
        self.setBackgroundColor(Vec4(0.4, 0.6, 0.8, 1))
        
        # Pause l'exploration
        if self.map_scene:
            self.map_scene.pause_controls()
            self.map_scene.cleanup()
            self.map_scene = None
        if self.hud:
            self.hud.cleanup()
            self.hud = None
        
        # Créer la scène de combat
        self.battle_scene = BattleScene(
            self,
            self.team_player,
            enemy_team,
            self.pokedex,
            is_wild=is_wild,
            on_battle_end=self._on_battle_end
        )
        self.battle_scene.setup()
        
        # Pas d'Échap pendant le combat
        self.ignore("escape")

    def _on_battle_end(self, winner: str):
        """Callback de fin de combat."""
        from direct.interval.IntervalGlobal import Sequence, Wait, Func
        
        seq = Sequence(
            Wait(2.0),
            Func(self._return_to_menu_after_battle)
        )
        seq.start()

    def _return_to_menu_after_battle(self):
        """Retourne au menu principal après un combat."""
        if self.battle_scene:
            self.battle_scene.cleanup()
            self.battle_scene = None
        self._show_main_menu()

    # ─────────── Pokédex ───────────

    def _show_pokedex_from_menu(self):
        """Affiche le Pokédex depuis le menu principal."""
        pokedex_text = self.pokedex.display()
        print(pokedex_text)
        if self.main_menu:
            self.main_menu.show_message("📖 Pokédex affiché dans la console !")

    def _show_pokedex_ingame(self):
        """Affiche le Pokédex en jeu."""
        if self.state_manager.is_state(GameState.EXPLORATION):
            print(self.pokedex.display())

    # ─────────── Actions Menu ───────────

    def _heal_team(self):
        """Soigne toute l'équipe."""
        for p in self.team_player:
            p.full_restore()
        if self.main_menu:
            self.main_menu.show_message("✅ Toute l'équipe est soignée !")

    def _quit_game(self):
        """Quitte le jeu."""
        print("\n  👋 À bientôt, Dresseur !")
        self.userExit()
