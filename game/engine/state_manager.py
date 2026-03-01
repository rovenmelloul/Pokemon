"""StateManager -- Game state machine."""
from enum import Enum


class GameState(Enum):
    EXPLORATION = "exploration"
    BATTLE = "battle"
    POKEDEX = "pokedex"
    PAUSE = "pause"


class StateManager:
    def __init__(self):
        self.current_state = GameState.EXPLORATION
        self.previous_state = None
        self._listeners = {}

    def change_state(self, new_state):
        self.previous_state = self.current_state
        self.current_state = new_state
        if new_state in self._listeners:
            for callback in self._listeners[new_state]:
                callback(self.previous_state, new_state)

    def on_state_enter(self, state, callback):
        if state not in self._listeners:
            self._listeners[state] = []
        self._listeners[state].append(callback)

    def is_state(self, state):
        return self.current_state == state

    def go_back(self):
        if self.previous_state:
            self.change_state(self.previous_state)
