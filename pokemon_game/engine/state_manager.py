"""
StateManager — Machine à états pour l'application Panda3D.
"""
from enum import Enum


class GameState(Enum):
    MAIN_MENU = "main_menu"
    EXPLORATION = "exploration"
    BATTLE = "battle"
    POKEDEX = "pokedex"
    PAUSE = "pause"


class StateManager:
    """
    Gère les transitions d'état de l'application.
    MAIN_MENU → EXPLORATION ↔ BATTLE
                           → POKEDEX
                           → PAUSE
    """

    def __init__(self):
        self.current_state: GameState = GameState.MAIN_MENU
        self.previous_state: GameState | None = None
        self._listeners: dict[GameState, list] = {}

    def change_state(self, new_state: GameState):
        """Change l'état courant et notifie les listeners."""
        self.previous_state = self.current_state
        self.current_state = new_state
        # Notifier les listeners
        if new_state in self._listeners:
            for callback in self._listeners[new_state]:
                callback(self.previous_state, new_state)

    def on_state_enter(self, state: GameState, callback):
        """Enregistre un callback quand on entre dans un état."""
        if state not in self._listeners:
            self._listeners[state] = []
        self._listeners[state].append(callback)

    def is_state(self, state: GameState) -> bool:
        return self.current_state == state

    def go_back(self):
        """Retourne à l'état précédent."""
        if self.previous_state:
            self.change_state(self.previous_state)
