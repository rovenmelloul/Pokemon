"""Download Pokemon sprites from PokeAPI GitHub for the Pokedex."""
import json
import os
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITES_DIR = os.path.join(SCRIPT_DIR, "data", "sprites")
TEST_JSON = os.path.join(SCRIPT_DIR, "..", "api", "test.json")
SPRITE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{}.png"
UA = "PokemonGoGame/1.0 (educational)"


def main():
    os.makedirs(SPRITES_DIR, exist_ok=True)
    with open(TEST_JSON, "r", encoding="utf-8") as f:
        all_pokemon = json.load(f)

    ids_to_download = set()
    for entry in all_pokemon:
        api_data = entry.get("pokemon_data_from_api")
        if api_data and isinstance(api_data, dict):
            pid = api_data.get("id_pokemon")
            if pid:
                ids_to_download.add(pid)

    print(f"[Sprites] {len(ids_to_download)} unique PokeAPI IDs to download")
    downloaded = 0
    skipped = 0
    failed = 0

    for pid in sorted(ids_to_download):
        out_path = os.path.join(SPRITES_DIR, f"{pid}.png")
        if os.path.exists(out_path):
            skipped += 1
            continue
        url = SPRITE_URL.format(pid)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=10).read()
            with open(out_path, "wb") as f:
                f.write(data)
            downloaded += 1
            if downloaded % 50 == 0:
                print(f"  ... {downloaded} downloaded")
        except Exception as e:
            failed += 1
            if failed <= 5:
                print(f"  [!] Failed #{pid}: {e}")

    print(f"[Sprites] Done: {downloaded} new, {skipped} cached, {failed} failed")


if __name__ == "__main__":
    main()
