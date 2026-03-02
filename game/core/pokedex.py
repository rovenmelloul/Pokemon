"""Pokedex -- Tracks seen and caught Pokemon."""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


class Pokedex:
    def __init__(self):
        self.entries = {}
        self._evolutions = []
        self._load_pokemon_names()
        self._load_evolutions()

    def _load_pokemon_names(self):
        path = os.path.join(DATA_DIR, "pokemons.json")
        with open(path, "r", encoding="utf-8") as f:
            poke_list = json.load(f)
        for p in poke_list:
            self.entries[p["id"]] = {
                "name": p["name"],
                "types": p["types"],
                "base_stats": p.get("base_stats", {}),
                "sprite_id": p.get("sprite_id", p["id"]),
                "model_id": p.get("model_id"),
                "status": "unknown",
                "level": 0,
                "is_shiny": False,
            }

    def _load_evolutions(self):
        path = os.path.join(DATA_DIR, "evolutions.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self._evolutions = json.load(f)

    def mark_seen(self, pokemon_id):
        if pokemon_id in self.entries:
            if self.entries[pokemon_id]["status"] == "unknown":
                self.entries[pokemon_id]["status"] = "seen"

    def mark_caught(self, pokemon_id, level=5, is_shiny=False):
        if pokemon_id in self.entries:
            entry = self.entries[pokemon_id]
            entry["status"] = "caught"
            entry["level"] = max(entry["level"], level)
            if is_shiny:
                entry["is_shiny"] = True
            self._update_pre_evolutions(pokemon_id, level)

    def _update_pre_evolutions(self, caught_id, caught_level):
        for evo in self._evolutions:
            if evo["to_id"] == caught_id:
                pre_id = evo["from_id"]
                pre_level = evo["level"] - 1
                if pre_id in self.entries:
                    e = self.entries[pre_id]
                    if e["status"] == "unknown":
                        e["status"] = "caught"
                    e["level"] = max(e["level"], pre_level)
                    self._update_pre_evolutions(pre_id, pre_level)

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
                "types": entry["types"] if entry["status"] == "caught" else
                         entry["types"] if entry["status"] == "seen" else ["???"],
                "base_stats": entry.get("base_stats", {}) if entry["status"] == "caught" else {},
                "sprite_id": entry.get("sprite_id", pid),
                "model_id": entry.get("model_id"),
                "status": entry["status"],
                "level": entry.get("level", 0),
                "is_shiny": entry.get("is_shiny", False),
            })
        return result
