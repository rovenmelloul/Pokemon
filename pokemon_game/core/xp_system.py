"""
XPSystem — Gestion de l'expérience, montée de niveau et évolution automatique.
"""
import json
import math
import os
from .pokemon import Pokemon

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class XPSystem:
    """
    Gère :
    - Calcul XP gagné après un combat
    - Level up
    - Évolution automatique au bon niveau
    - Apprentissage de nouvelles attaques
    """

    _xp_curve: dict | None = None
    _evolutions: list | None = None

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
    def xp_for_level(cls, level: int) -> int:
        """XP total requis pour atteindre un niveau donné."""
        cls._load_data()
        return cls._xp_curve.get(level, 0)

    @classmethod
    def xp_to_next_level(cls, pokemon: Pokemon) -> int:
        """XP restant pour le prochain niveau."""
        cls._load_data()
        if pokemon.level >= 100:
            return 0
        needed = cls._xp_curve.get(pokemon.level + 1, 0)
        return max(0, needed - pokemon.xp)

    @classmethod
    def calculate_xp_gain(cls, winner: Pokemon, loser: Pokemon, 
                          is_wild: bool = True) -> int:
        """
        Calcule les XP gagnés après un combat.
        Formule simplifiée (Gen 5+) :
        xp = (base_xp * loser_level) / (5 * (1 si dresseur, 1.5 si sauvage))
        """
        a = 1.5 if not is_wild else 1.0  # Bonus dresseur
        base = loser.base_xp
        level = loser.level
        xp = int((base * level * a) / 5)
        return max(1, xp)

    @classmethod
    def award_xp(cls, pokemon: Pokemon, xp_amount: int) -> list[dict]:
        """
        Attribue des XP à un Pokémon.
        Gère les level ups multiples si nécessaire.
        
        Retourne une liste d'événements :
        [
            {"type": "xp", "amount": int, "total": int},
            {"type": "level_up", "new_level": int},
            {"type": "new_move", "move": Move},
            {"type": "evolution", "from": str, "to": str, "new_id": int}
        ]
        """
        cls._load_data()
        events = []
        pokemon.xp += xp_amount
        events.append({"type": "xp", "amount": xp_amount, "total": pokemon.xp})

        # Vérifier les level ups
        while pokemon.level < 100:
            xp_needed = cls._xp_curve.get(pokemon.level + 1, float("inf"))
            if pokemon.xp < xp_needed:
                break

            pokemon.level_up()
            events.append({"type": "level_up", "new_level": pokemon.level})

            # Nouvelles attaques
            new_moves = pokemon.learn_new_moves_for_level()
            for move in new_moves:
                events.append({"type": "new_move", "move": move})

            # Vérifier évolution
            evo = cls._check_evolution(pokemon)
            if evo:
                events.append(evo)

        return events

    @classmethod
    def _check_evolution(cls, pokemon: Pokemon) -> dict | None:
        """Vérifie et effectue l'évolution si le niveau est atteint."""
        cls._load_data()
        for evo in cls._evolutions:
            if evo["from_id"] == pokemon.id and pokemon.level >= evo["level"]:
                old_name = pokemon.name
                # Charger les données du nouveau Pokémon
                Pokemon.load_pokemon_db()
                new_data = Pokemon._pokemon_db.get(evo["to_id"])
                if new_data:
                    pokemon.id = new_data["id"]
                    pokemon.name = new_data["name"]
                    pokemon.types = new_data["types"]
                    pokemon.base_stats = new_data["base_stats"]
                    pokemon.base_xp = new_data.get("base_xp", pokemon.base_xp)
                    pokemon.capture_rate = new_data.get("capture_rate", pokemon.capture_rate)
                    pokemon.learnset = new_data.get("learnset", pokemon.learnset)
                    pokemon.model_id = new_data.get("model_id")
                    # Recalculer les stats
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
    def format_events(cls, events: list[dict]) -> list[str]:
        """Formate les événements en messages lisibles."""
        messages = []
        for evt in events:
            if evt["type"] == "xp":
                messages.append(f"  ✨ +{evt['amount']} XP !")
            elif evt["type"] == "level_up":
                messages.append(f"  🆙 Montée au niveau {evt['new_level']} !")
            elif evt["type"] == "new_move":
                messages.append(f"  📖 {evt['move'].name} appris !")
            elif evt["type"] == "evolution":
                messages.append(f"  🌟 {evt['from']} évolue en {evt['to']} !")
        return messages
