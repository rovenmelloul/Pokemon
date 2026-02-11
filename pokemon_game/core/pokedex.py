"""
Pokedex — Suivi des Pokémons vus et capturés.
"""
import json
import os
from .pokemon import Pokemon

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class Pokedex:
    """
    Pokédex avec 3 statuts par Pokémon :
    - "unknown" : jamais rencontré
    - "seen" : vu en combat
    - "caught" : capturé
    """

    def __init__(self):
        self.entries: dict[int, dict] = {}
        self._load_pokemon_names()

    def _load_pokemon_names(self):
        """Charge les noms depuis pokemons.json pour l'affichage."""
        path = os.path.join(DATA_DIR, "pokemons.json")
        with open(path, "r", encoding="utf-8") as f:
            poke_list = json.load(f)
        for p in poke_list:
            self.entries[p["id"]] = {
                "name": p["name"],
                "types": p["types"],
                "status": "unknown"
            }

    def mark_seen(self, pokemon_id: int):
        """Marque un Pokémon comme vu (seulement s'il n'est pas déjà capturé)."""
        if pokemon_id in self.entries:
            if self.entries[pokemon_id]["status"] == "unknown":
                self.entries[pokemon_id]["status"] = "seen"

    def mark_caught(self, pokemon_id: int):
        """Marque un Pokémon comme capturé."""
        if pokemon_id in self.entries:
            self.entries[pokemon_id]["status"] = "caught"

    def get_status(self, pokemon_id: int) -> str:
        """Retourne le statut d'un Pokémon."""
        if pokemon_id in self.entries:
            return self.entries[pokemon_id]["status"]
        return "unknown"

    def get_seen_count(self) -> int:
        """Nombre de Pokémons vus ou capturés."""
        return sum(1 for e in self.entries.values() if e["status"] in ("seen", "caught"))

    def get_caught_count(self) -> int:
        """Nombre de Pokémons capturés."""
        return sum(1 for e in self.entries.values() if e["status"] == "caught")

    def get_total_count(self) -> int:
        """Nombre total de Pokémons dans le Pokédex."""
        return len(self.entries)

    def completion_rate(self) -> float:
        """Taux de complétion (capturés / total)."""
        total = self.get_total_count()
        if total == 0:
            return 0.0
        return self.get_caught_count() / total

    def get_entries_list(self) -> list[dict]:
        """Retourne la liste des entrées pour l'affichage."""
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

    def display(self) -> str:
        """Affichage texte du Pokédex."""
        lines = []
        lines.append("═══════════ POKÉDEX ═══════════")
        lines.append(f"  Vus: {self.get_seen_count()} | Capturés: {self.get_caught_count()} | Total: {self.get_total_count()}")
        lines.append(f"  Complétion: {self.completion_rate()*100:.1f}%")
        lines.append("───────────────────────────────")

        status_icons = {"unknown": "⬛", "seen": "👁️ ", "caught": "🔴"}
        for entry in self.get_entries_list():
            icon = status_icons[entry["status"]]
            types_str = "/".join(entry["types"])
            lines.append(f"  {icon} #{entry['id']:03d} {entry['name']:12s} [{types_str}]")

        lines.append("═══════════════════════════════")
        return "\n".join(lines)
