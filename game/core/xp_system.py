"""
XPSystem -- XP gain, level-up and auto-evolution.
"""
import json
import os
from .pokemon_stats import PokemonStats
from .move import Move

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


class XPSystem:
    _xp_curve = None
    _evolutions = None

    @classmethod
    def _load_data(cls):
        if cls._xp_curve is None:
            path = os.path.join(DATA_DIR, "xp_curve.json")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cls._xp_curve = {int(k): v for k, v in data["levels"].items()}
        if cls._evolutions is None:
            path = os.path.join(DATA_DIR, "evolutions.json")
            with open(path, "r", encoding="utf-8") as f:
                cls._evolutions = json.load(f)

    @classmethod
    def xp_for_level(cls, level):
        cls._load_data()
        return cls._xp_curve.get(level, 0)

    @classmethod
    def xp_to_next_level(cls, pokemon):
        cls._load_data()
        if pokemon.level >= 100:
            return 0
        needed = cls._xp_curve.get(pokemon.level + 1, 0)
        return max(0, needed - pokemon.xp)

    @classmethod
    def calculate_xp_gain(cls, winner, loser, is_wild=True):
        a = 1.5 if not is_wild else 1.0
        base = loser.base_xp
        level = loser.level
        xp = int((base * level * a) / 5)
        return max(1, xp)

    @classmethod
    def award_xp(cls, pokemon, xp_amount):
        cls._load_data()
        events = []
        pokemon.xp += xp_amount
        events.append({"type": "xp", "amount": xp_amount, "total": pokemon.xp})

        while pokemon.level < 100:
            xp_needed = cls._xp_curve.get(pokemon.level + 1, float("inf"))
            if pokemon.xp < xp_needed:
                break
            pokemon.level_up()
            events.append({"type": "level_up", "new_level": pokemon.level})
            new_moves = pokemon.learn_new_moves_for_level()
            for move in new_moves:
                events.append({"type": "new_move", "move": move})
            evo = cls._check_evolution(pokemon)
            if evo:
                events.append(evo)

        return events

    @classmethod
    def _check_evolution(cls, pokemon):
        cls._load_data()
        for evo in cls._evolutions:
            if evo["from_id"] == pokemon.id and pokemon.level >= evo["level"]:
                old_name = pokemon.name
                PokemonStats.load_pokemon_db()
                new_data = PokemonStats._pokemon_db.get(evo["to_id"])
                if new_data:
                    pokemon.id = new_data["id"]
                    pokemon.name = new_data["name"]
                    pokemon.types = new_data["types"]
                    pokemon.base_stats = new_data["base_stats"]
                    pokemon.base_xp = new_data.get("base_xp", pokemon.base_xp)
                    pokemon.capture_rate = new_data.get("capture_rate", pokemon.capture_rate)
                    pokemon.learnset = new_data.get("learnset", pokemon.learnset)
                    pokemon.model_id = new_data.get("model_id")
                    old_hp = pokemon.stats["hp"]
                    pokemon.stats = pokemon._calculate_stats()
                    hp_diff = pokemon.stats["hp"] - old_hp
                    pokemon.current_hp += hp_diff
                    return {
                        "type": "evolution",
                        "from": old_name,
                        "to": pokemon.name,
                        "new_id": pokemon.id
                    }
        return None

    @classmethod
    def format_events(cls, events):
        messages = []
        for evt in events:
            if evt["type"] == "xp":
                messages.append(f"  +{evt['amount']} XP!")
            elif evt["type"] == "level_up":
                messages.append(f"  Level up! Now Lv.{evt['new_level']}!")
            elif evt["type"] == "new_move":
                messages.append(f"  Learned {evt['move'].name}!")
            elif evt["type"] == "evolution":
                messages.append(f"  {evt['from']} evolved into {evt['to']}!")
        return messages
