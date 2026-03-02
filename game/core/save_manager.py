"""SaveManager -- 3 save slots, JSON format."""
import json
import os
from datetime import datetime

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "saves")


class SaveManager:

    @staticmethod
    def _slot_path(slot_num):
        return os.path.join(SAVE_DIR, f"save_{slot_num}.json")

    @staticmethod
    def list_slots():
        """Return [slot1, slot2, slot3] where each is None or metadata dict."""
        results = []
        for i in range(1, 4):
            path = SaveManager._slot_path(i)
            if os.path.exists(path) and os.path.getsize(path) > 0:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    team = data.get("team", [])
                    results.append({
                        "slot_num": i,
                        "timestamp": data.get("timestamp", "?"),
                        "team_names": [p["name"] for p in team],
                        "team_levels": [p["level"] for p in team],
                        "save_name": data.get("save_name", ""),
                    })
                except Exception:
                    results.append(None)
            else:
                results.append(None)
        return results

    @staticmethod
    def save(slot_num, app):
        """Serialize current game state to save file."""
        try:
            player_pos = app.player.control_node.getPos()
            player_h = app.player.control_node.getH()

            team_data = []
            for poke in app.player_team:
                team_data.append(poke.to_save_dict())

            pokedex_data = {}
            if app.pokedex:
                for pid, entry in app.pokedex.entries.items():
                    if entry["status"] != "unknown":
                        pokedex_data[str(pid)] = {
                            "status": entry["status"],
                            "level": entry["level"],
                            "is_shiny": entry["is_shiny"],
                        }

            save_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "player": {
                    "position": [player_pos.x, player_pos.y, player_pos.z],
                    "heading": player_h,
                },
                "team": team_data,
                "pokedex": pokedex_data,
            }

            os.makedirs(SAVE_DIR, exist_ok=True)
            path = SaveManager._slot_path(slot_num)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            print(f"[Save] Partie sauvegardee dans slot {slot_num}")
            return True
        except Exception as e:
            print(f"[Save] Erreur sauvegarde: {e}")
            return False

    @staticmethod
    def load(slot_num):
        """Load save data from file. Returns dict or None."""
        path = SaveManager._slot_path(slot_num)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Save] Erreur chargement: {e}")
            return None

    @staticmethod
    def rename(slot_num, new_name):
        """Rename a save slot."""
        path = SaveManager._slot_path(slot_num)
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["save_name"] = new_name
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[Save] Slot {slot_num} renomme: {new_name}")
        except Exception as e:
            print(f"[Save] Erreur renommage: {e}")

    @staticmethod
    def delete(slot_num):
        """Delete a save file."""
        path = SaveManager._slot_path(slot_num)
        if os.path.exists(path):
            os.remove(path)
            print(f"[Save] Slot {slot_num} supprime")
