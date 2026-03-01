"""
Pokedex -- Tracks seen and caught Pokemon.
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


class Pokedex:
    def __init__(self):
        self.entries = {}
        self._load_pokemon_names()

    def _load_pokemon_names(self):
        path = os.path.join(DATA_DIR, "pokemons.json")
        with open(path, "r", encoding="utf-8") as f:
            poke_list = json.load(f)
        for p in poke_list:
            self.entries[p["id"]] = {
                "name": p["name"],
                "types": p["types"],
                "status": "unknown"
            }

    def mark_seen(self, pokemon_id):
        if pokemon_id in self.entries:
            if self.entries[pokemon_id]["status"] == "unknown":
                self.entries[pokemon_id]["status"] = "seen"

    def mark_caught(self, pokemon_id):
        if pokemon_id in self.entries:
            self.entries[pokemon_id]["status"] = "caught"

    def get_status(self, pokemon_id):
        if pokemon_id in self.entries:
            return self.entries[pokemon_id]["status"]
        return "unknown"

    def get_seen_count(self):
        return sum(1 for e in self.entries.values() if e["status"] in ("seen", "caught"))

    def get_caught_count(self):
        return sum(1 for e in self.entries.values() if e["status"] == "caught")

    def get_total_count(self):
        return len(self.entries)

    def completion_rate(self):
        total = self.get_total_count()
        if total == 0:
            return 0.0
        return self.get_caught_count() / total

    def get_entries_list(self):
        result = []
        for pid in sorted(self.entries.keys()):
            entry = self.entries[pid]
            result.append({
                "id": pid,
                "name": entry["name"] if entry["status"] != "unknown" else "???",
                "types": entry["types"] if entry["status"] == "caught" else ["???"],
                "status": entry["status"]
            })
        return result
