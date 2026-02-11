"""
Pokemon — Représente un Pokémon avec ses stats, level, moves et statut.
"""
import json
import math
import os
from .move import Move

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class Pokemon:
    """
    Un Pokémon avec :
    - Stats calculées depuis base_stats + level (formule Gen 3+)
    - HP courants
    - Moveset (4 max)
    - Statut (none / poison / burn / paralysis / sleep / freeze)
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
    def create(cls, pokemon_id: int, level: int, move_ids: list[int] | None = None) -> "Pokemon":
        """
        Crée un Pokémon à partir de son ID et d'un niveau.
        Si move_ids n'est pas donné, on prend les 4 dernières attaques
        apprises au niveau actuel.
        """
        cls.load_pokemon_db()
        data = cls._pokemon_db[pokemon_id].copy()
        return cls(data, level, move_ids)

    def __init__(self, data: dict, level: int, move_ids: list[int] | None = None):
        self.id: int = data["id"]
        self.name: str = data["name"]
        self.types: list[str] = data["types"]
        self.base_stats: dict = data["base_stats"]
        self.capture_rate: int = data.get("capture_rate", 45)
        self.base_xp: int = data.get("base_xp", 64)
        self.learnset: list[dict] = data.get("learnset", [])
        self.model_id: str | None = data.get("model_id")
        self.level: int = level

        # IVs simplifié (fixé 15 pour tous)
        self.ivs = {"hp": 15, "attack": 15, "defense": 15,
                    "sp_attack": 15, "sp_defense": 15, "speed": 15}
        # EVs à 0
        self.evs = {"hp": 0, "attack": 0, "defense": 0,
                    "sp_attack": 0, "sp_defense": 0, "speed": 0}

        # Calcul des stats
        self.stats = self._calculate_stats()
        self.current_hp: int = self.stats["hp"]

        # XP
        self.xp: int = 0

        # Statut
        self.status: str | None = None  # poison, burn, paralysis, sleep, freeze

        # Moves
        Move.load_moves()
        if move_ids:
            self.moves = [Move.get_by_id(mid) for mid in move_ids[:4]]
        else:
            self.moves = self._auto_moveset()

    def _calculate_stats(self) -> dict:
        """Calcul stats Gen 3+ : floor((2*base + IV + floor(EV/4)) * level / 100) + 5"""
        stats = {}
        for stat_name in ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]:
            base = self.base_stats[stat_name]
            iv = self.ivs[stat_name]
            ev = self.evs[stat_name]
            if stat_name == "hp":
                # HP = floor((2*base + IV + floor(EV/4)) * level / 100) + level + 10
                stats[stat_name] = math.floor(
                    (2 * base + iv + math.floor(ev / 4)) * self.level / 100
                ) + self.level + 10
            else:
                # Stat = floor((2*base + IV + floor(EV/4)) * level / 100) + 5
                stats[stat_name] = math.floor(
                    (2 * base + iv + math.floor(ev / 4)) * self.level / 100
                ) + 5
        return stats

    def _auto_moveset(self) -> list[Move]:
        """Sélectionne les 4 dernières attaques apprises au niveau actuel."""
        available = [
            entry for entry in self.learnset
            if entry["level"] <= self.level
        ]
        # Trier par niveau décroissant, prendre les 4 dernières
        available.sort(key=lambda x: x["level"], reverse=True)
        selected = available[:4]
        return [Move.get_by_id(entry["move_id"]) for entry in selected]

    def take_damage(self, damage: int) -> int:
        """Inflige des dégâts au Pokémon. Retourne les dégâts effectifs."""
        actual = min(damage, self.current_hp)
        self.current_hp -= actual
        return actual

    def heal(self, amount: int | None = None):
        """Soigne le Pokémon. None = full heal."""
        if amount is None:
            self.current_hp = self.stats["hp"]
        else:
            self.current_hp = min(self.current_hp + amount, self.stats["hp"])

    def is_fainted(self) -> bool:
        return self.current_hp <= 0

    def hp_fraction(self) -> float:
        """Retourne le ratio HP (0.0 à 1.0)."""
        return self.current_hp / self.stats["hp"] if self.stats["hp"] > 0 else 0

    def level_up(self):
        """Monte d'un niveau et recalcule les stats."""
        old_max_hp = self.stats["hp"]
        self.level += 1
        self.stats = self._calculate_stats()
        # Augmente les HP courants proportionnellement
        hp_diff = self.stats["hp"] - old_max_hp
        self.current_hp += hp_diff

    def learn_new_moves_for_level(self) -> list[Move]:
        """Vérifie s'il y a de nouvelles attaques à apprendre au niveau actuel."""
        new_moves = []
        for entry in self.learnset:
            if entry["level"] == self.level:
                move = Move.get_by_id(entry["move_id"])
                # Vérifie que le Pokémon ne connaît pas déjà cette attaque
                if not any(m.id == move.id for m in self.moves):
                    if len(self.moves) < 4:
                        self.moves.append(move)
                        new_moves.append(move)
                    else:
                        # Remplace l'attaque la plus faible
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

    def set_status(self, status: str):
        """Applique un statut (seulement si aucun n'est actif)."""
        if self.status is None:
            self.status = status

    def clear_status(self):
        self.status = None

    def full_restore(self):
        """Full heal + clear status + restore PP."""
        self.current_hp = self.stats["hp"]
        self.status = None
        for move in self.moves:
            move.restore_pp()

    def __repr__(self):
        types_str = "/".join(self.types)
        return (f"<{self.name} Lv.{self.level} [{types_str}] "
                f"HP={self.current_hp}/{self.stats['hp']} "
                f"Status={self.status or 'OK'}>")
