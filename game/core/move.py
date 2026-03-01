"""
Move -- Represents a Pokemon attack.
Loaded from moves.json.
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


class Move:
    """A Pokemon attack with type, power, accuracy, PP, category."""

    _move_db: dict = {}

    @classmethod
    def load_moves(cls):
        """Load all moves from moves.json."""
        if cls._move_db:
            return
        path = os.path.join(DATA_DIR, "moves.json")
        with open(path, "r", encoding="utf-8") as f:
            moves_list = json.load(f)
        for m in moves_list:
            cls._move_db[m["id"]] = m

    @classmethod
    def get_by_id(cls, move_id: int) -> "Move":
        """Return a Move from its ID."""
        cls.load_moves()
        data = cls._move_db[move_id]
        return cls(data)

    def __init__(self, data: dict):
        self.id: int = data["id"]
        self.name: str = data["name"]
        self.type: str = data["type"]
        self.category: str = data["category"]
        self.power: int = data.get("power", 0)
        self.accuracy: int = data.get("accuracy", 100)
        self.max_pp: int = data.get("pp", 10)
        self.current_pp: int = self.max_pp
        self.priority: int = data.get("priority", 0)
        self.effect = data.get("effect")

    def use(self) -> bool:
        if self.current_pp <= 0:
            return False
        self.current_pp -= 1
        return True

    def restore_pp(self, amount=None):
        if amount is None:
            self.current_pp = self.max_pp
        else:
            self.current_pp = min(self.current_pp + amount, self.max_pp)

    def is_damaging(self) -> bool:
        return self.category in ("physical", "special") and self.power > 0

    def __repr__(self):
        return (f"<Move {self.name} ({self.type}/{self.category}) "
                f"PWR={self.power} ACC={self.accuracy} PP={self.current_pp}/{self.max_pp}>")
