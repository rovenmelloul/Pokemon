"""
encounter.py — Système de rencontres aléatoires Pokémon.
"""
import random
from core.pokemon import Pokemon


# Zones de rencontre : chaque zone a une liste de Pokémons possibles avec poids
ENCOUNTER_ZONES = {
    "route_1": {
        "name": "Route 1",
        "encounter_rate": 0.15,  # 15% de chance par pas dans l'herbe
        "level_range": (3, 7),
        "pokemon_table": [
            {"id": 16, "weight": 40},  # Pidgey
            {"id": 19, "weight": 40},  # Rattata
            {"id": 37, "weight": 15},  # Vulpix
            {"id": 25, "weight": 5},   # Pikachu
        ]
    },
    "route_2": {
        "name": "Route 2",
        "encounter_rate": 0.20,
        "level_range": (5, 12),
        "pokemon_table": [
            {"id": 16, "weight": 25},  # Pidgey
            {"id": 19, "weight": 20},  # Rattata
            {"id": 74, "weight": 20},  # Geodude
            {"id": 66, "weight": 15},  # Machop
            {"id": 63, "weight": 10},  # Abra
            {"id": 92, "weight": 10},  # Gastly
        ]
    },
    "water_cave": {
        "name": "Caverne Aquatique",
        "encounter_rate": 0.25,
        "level_range": (10, 20),
        "pokemon_table": [
            {"id": 129, "weight": 30}, # Magikarp
            {"id": 74, "weight": 25},  # Geodude
            {"id": 95, "weight": 20},  # Onix
            {"id": 92, "weight": 15},  # Gastly
            {"id": 147, "weight": 10}, # Dratini
        ]
    }
}


class EncounterSystem:
    """Gère les rencontres aléatoires sur la map."""

    @staticmethod
    def check_encounter(zone_id: str) -> bool:
        """Vérifie si une rencontre a lieu dans la zone donnée."""
        zone = ENCOUNTER_ZONES.get(zone_id)
        if not zone:
            return False
        return random.random() < zone["encounter_rate"]

    @staticmethod
    def generate_wild_pokemon(zone_id: str) -> Pokemon | None:
        """Génère un Pokémon sauvage basé sur la zone."""
        zone = ENCOUNTER_ZONES.get(zone_id)
        if not zone:
            return None

        # Sélection pondérée
        table = zone["pokemon_table"]
        total_weight = sum(entry["weight"] for entry in table)
        roll = random.randint(1, total_weight)
        
        cumulative = 0
        selected_id = table[0]["id"]
        for entry in table:
            cumulative += entry["weight"]
            if roll <= cumulative:
                selected_id = entry["id"]
                break

        # Niveau aléatoire dans la plage
        min_lvl, max_lvl = zone["level_range"]
        level = random.randint(min_lvl, max_lvl)

        return Pokemon.create(selected_id, level)

    @staticmethod
    def get_zone_info(zone_id: str) -> dict | None:
        """Retourne les infos d'une zone."""
        return ENCOUNTER_ZONES.get(zone_id)

    @staticmethod
    def get_all_zones() -> dict:
        return ENCOUNTER_ZONES
