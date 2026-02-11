"""
game_app.py — Application Panda3D principale.
Gère les transitions entre exploration et combat.
"""
import sys
import os

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


# Configuration Panda3D
loadPrcFileData("", "window-title Pokémon Game")
loadPrcFileData("", "win-size 1280 720")
loadPrcFileData("", "show-frame-rate-meter #t")


class GameApp(ShowBase):
    """
    Application principale du jeu Pokémon.
    Gère les scènes (exploration, combat) et les transitions.
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
        
        # Background
        self.setBackgroundColor(Vec4(0.4, 0.6, 0.8, 1))
        
        # Démarrer en exploration
        self._start_exploration()
        
        # Contrôles globaux
        self.accept("escape", self._toggle_pause)
        self.accept("p", self._show_pokedex)

    def _start_exploration(self):
        """Lance la scène d'exploration."""
        self.state_manager.change_state(GameState.EXPLORATION)
        
        # Nettoyer la scène de combat si elle existe
        if self.battle_scene:
            self.battle_scene.cleanup()
            self.battle_scene = None
        
        # Créer la map
        self.map_scene = MapScene(
            self,
            on_encounter_callback=self._on_wild_encounter
        )
        self.map_scene.setup()
        
        # HUD
        self.hud = ExplorationHUD(self, self.team_player)
        self.hud.setup()

    def _on_wild_encounter(self, wild_pokemon: Pokemon):
        """Déclenché quand on rencontre un Pokémon sauvage."""
        self._start_battle([wild_pokemon], is_wild=True)

    def _start_battle(self, enemy_team: list[Pokemon], is_wild: bool = True):
        """Lance un combat."""
        self.state_manager.change_state(GameState.BATTLE)
        
        # Pause l'exploration
        if self.map_scene:
            self.map_scene.pause_controls()
            self.map_scene.cleanup()
        if self.hud:
            self.hud.cleanup()
        
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

    def _on_battle_end(self, winner: str):
        """Callback de fin de combat."""
        # Petit délai avant de retourner à l'exploration
        from direct.interval.IntervalGlobal import Sequence, Wait, Func
        
        seq = Sequence(
            Wait(2.0),
            Func(self._return_to_exploration)
        )
        seq.start()

    def _return_to_exploration(self):
        """Retourne à l'exploration après un combat."""
        if self.battle_scene:
            self.battle_scene.cleanup()
            self.battle_scene = None
        self._start_exploration()

    def _toggle_pause(self):
        """Toggle pause."""
        if self.state_manager.is_state(GameState.EXPLORATION):
            print("  Menu Pause - Appuyez sur Échap pour reprendre")
        elif self.state_manager.is_state(GameState.BATTLE):
            pass  # Pas de pause en combat

    def _show_pokedex(self):
        """Affiche le Pokédex."""
        if self.state_manager.is_state(GameState.EXPLORATION):
            print(self.pokedex.display())
