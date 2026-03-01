"""
PokemonStats -- Stats-based Pokemon for battle/capture/XP.
Loaded from pokemons.json (dev-roven data).
"""
import json
import math
import os
from .move import Move

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


class PokemonStats:
    """
    A Pokemon with stats, level, moves and status for the battle system.
    This is the 'combat data' side; the 3D rendering is handled by
    game/app/pokemon/pokemon.py which wraps this.
    """

    _pokemon_db: dict = {}

    @classmethod
    def load_pokemon_db(cls):
        if cls._pokemon_db:
            return
        path = os.path.join(DATA_DIR, "pokemons.json")
        with open(path, "r", encoding="utf-8") as f:
            poke_list = json.load(f)
        for p in poke_list:
            cls._pokemon_db[p["id"]] = p

    @classmethod
    def create(cls, pokemon_id, level, move_ids=None):
        cls.load_pokemon_db()
        data = cls._pokemon_db[pokemon_id].copy()
        return cls(data, level, move_ids)

    def __init__(self, data, level, move_ids=None):
        self.id = data["id"]
        self.name = data["name"]
        self.types = data["types"]
        self.base_stats = data["base_stats"]
        self.capture_rate = data.get("capture_rate", 45)
        self.base_xp = data.get("base_xp", 64)
        self.learnset = data.get("learnset", [])
        self.model_id = data.get("model_id")
        self.level = level

        self.ivs = {"hp": 15, "attack": 15, "defense": 15,
                    "sp_attack": 15, "sp_defense": 15, "speed": 15}
        self.evs = {"hp": 0, "attack": 0, "defense": 0,
                    "sp_attack": 0, "sp_defense": 0, "speed": 0}

        self.stats = self._calculate_stats()
        self.current_hp = self.stats["hp"]
        self.xp = 0
        self.status = None

        Move.load_moves()
        if move_ids:
            self.moves = [Move.get_by_id(mid) for mid in move_ids[:4]]
        else:
            self.moves = self._auto_moveset()

    def _calculate_stats(self):
        stats = {}
        for stat_name in ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]:
            base = self.base_stats[stat_name]
            iv = self.ivs[stat_name]
            ev = self.evs[stat_name]
            if stat_name == "hp":
                stats[stat_name] = math.floor(
                    (2 * base + iv + math.floor(ev / 4)) * self.level / 100
                ) + self.level + 10
            else:
                stats[stat_name] = math.floor(
                    (2 * base + iv + math.floor(ev / 4)) * self.level / 100
                ) + 5
        return stats

    def _auto_moveset(self):
        available = [
            entry for entry in self.learnset
            if entry["level"] <= self.level
        ]
        available.sort(key=lambda x: x["level"], reverse=True)
        selected = available[:4]
        return [Move.get_by_id(entry["move_id"]) for entry in selected]

    def take_damage(self, damage):
        actual = min(damage, self.current_hp)
        self.current_hp -= actual
        return actual

    def heal(self, amount=None):
        if amount is None:
            self.current_hp = self.stats["hp"]
        else:
            self.current_hp = min(self.current_hp + amount, self.stats["hp"])

    def is_fainted(self):
        return self.current_hp <= 0

    def hp_fraction(self):
        return self.current_hp / self.stats["hp"] if self.stats["hp"] > 0 else 0

    def level_up(self):
        old_max_hp = self.stats["hp"]
        self.level += 1
        self.stats = self._calculate_stats()
        hp_diff = self.stats["hp"] - old_max_hp
        self.current_hp += hp_diff

    def learn_new_moves_for_level(self):
        new_moves = []
        for entry in self.learnset:
            if entry["level"] == self.level:
                move = Move.get_by_id(entry["move_id"])
                if not any(m.id == move.id for m in self.moves):
                    if len(self.moves) < 4:
                        self.moves.append(move)
                        new_moves.append(move)
                    else:
                        weakest_idx = 0
                        weakest_power = self.moves[0].power
                        for i, m in enumerate(self.moves):
                            if m.power < weakest_power:
                                weakest_power = m.power
                                weakest_idx = i
                        if move.power > weakest_power:
                            self.moves[weakest_idx] = move
                            new_moves.append(move)
        return new_moves

    def set_status(self, status):
        if self.status is None:
            self.status = status

    def clear_status(self):
        self.status = None

    def full_restore(self):
        self.current_hp = self.stats["hp"]
        self.status = None
        for move in self.moves:
            move.restore_pp()

    def __repr__(self):
        types_str = "/".join(self.types)
        return (f"<{self.name} Lv.{self.level} [{types_str}] "
                f"HP={self.current_hp}/{self.stats['hp']} "
                f"Status={self.status or 'OK'}>")
