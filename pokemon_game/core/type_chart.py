"""
TypeChart — Table d'efficacité des 18 types (Gen 8).
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class TypeChart:
    """Singleton-like qui charge le type_chart.json et expose les efficacités."""

    _chart: dict | None = None

    @classmethod
    def _load(cls):
        if cls._chart is not None:
            return
        path = os.path.join(DATA_DIR, "type_chart.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cls._chart = data["chart"]

    @classmethod
    def get_effectiveness(cls, atk_type: str, def_types: list[str]) -> float:
        """
        Calcule le multiplicateur d'efficacité d'un type d'attaque
        contre une liste de types défensifs.
        
        Exemple: get_effectiveness("water", ["fire"]) → 2.0
                 get_effectiveness("water", ["fire", "rock"]) → 4.0
                 get_effectiveness("normal", ["ghost"]) → 0.0
        """
        cls._load()
        multiplier = 1.0
        atk = atk_type.lower()
        if atk not in cls._chart:
            return 1.0
        for def_type in def_types:
            dt = def_type.lower()
            mult = cls._chart[atk].get(dt, 1.0)
            multiplier *= mult
        return multiplier

    @classmethod
    def get_effectiveness_message(cls, multiplier: float) -> str | None:
        """Retourne un message de contexte selon l'efficacité."""
        if multiplier == 0:
            return "Ça n'affecte pas le Pokémon ennemi..."
        elif multiplier < 1:
            return "Ce n'est pas très efficace..."
        elif multiplier > 1:
            return "C'est super efficace !"
        return None
