"""Load and query the moves database from data/moves.json."""
import json
import os

# Project root is 3 levels up: sdk/effect_system/move_database.py -> project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


class MoveDatabase:
    """Provides access to Pokemon move definitions for the battle system."""

    def __init__(self, json_path=None):
        if json_path is None:
            json_path = os.path.join(_PROJECT_ROOT, "data", "moves.json")
        self._moves = []
        self._by_name = {}
        self._types = set()
        self._load(json_path)

    def _load(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[MoveDB] Failed to load {path}: {e}")
            return
        for m in data.get("moves", []):
            self._moves.append(m)
            self._by_name[m["name"].lower()] = m
            self._types.add(m["type"])
        print(f"[MoveDB] Loaded {len(self._moves)} moves, "
              f"{len(self._types)} types")

    def get_all(self):
        """Return all moves as a list of dicts."""
        return list(self._moves)

    def get_by_type(self, type_name):
        """Return moves of a given type."""
        return [m for m in self._moves
                if m["type"].lower() == type_name.lower()]

    def get_by_name(self, name):
        """Return a single move by name (case-insensitive)."""
        return self._by_name.get(name.lower())

    def get_types(self):
        """Return sorted list of all type names."""
        return sorted(self._types)

    @property
    def count(self):
        return len(self._moves)
