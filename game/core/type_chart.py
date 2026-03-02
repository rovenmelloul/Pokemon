"""
TypeChart -- Table d'efficacite des types (Gen 8, 18 types).
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


class TypeChart:
    _chart = None

    @classmethod
    def _load(cls):
        if cls._chart is not None:
            return
        path = os.path.join(DATA_DIR, "type_chart.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cls._chart = data["chart"]

    @classmethod
    def get_effectiveness(cls, atk_type, def_types):
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
    def get_effectiveness_message(cls, multiplier):
        if multiplier == 0:
            return "Ca n'affecte pas le Pokemon ennemi..."
        elif multiplier < 1:
            return "Ce n'est pas tres efficace..."
        elif multiplier > 1:
            return "C'est super efficace !"
        return None
