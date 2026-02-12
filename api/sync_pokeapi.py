#!/usr/bin/env python3
"""
sync_pokeapi.py — Synchronise les données depuis PokeAPI vers les fichiers JSON du jeu.
Récupère les 151 Pokémon de Kanto (Gen 1) et leurs moves.

Usage:
    python api/sync_pokeapi.py
"""
import json
import os
import sys
import time

# Ajouter le dossier racine au path
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT_DIR)

from api.pokemon_api import get_full_pokemon, get_move_data

DATA_DIR = os.path.join(ROOT_DIR, "pokemon_game", "data")

# Pokémon Gen 1 qu'on veut récupérer (les 151 de Kanto)
# On se limite aux plus importants pour ne pas surcharger l'API
POKEMON_IDS = [
    # Starters + évolutions
    1, 2, 3,      # Bulbasaur line
    4, 5, 6,      # Charmander line
    7, 8, 9,      # Squirtle line
    # Pikachu line
    25, 26,
    # Communs
    16, 17, 18,   # Pidgey line
    19, 20,       # Rattata line
    # Feu
    37, 38,       # Vulpix / Ninetales
    # Combat
    66, 67, 68,   # Machop line
    # Psy
    63, 64, 65,   # Abra line
    # Ghost
    92, 93, 94,   # Gastly line
    # Eau
    54, 55,       # Psyduck / Golduck
    129, 130,     # Magikarp / Gyarados
    # Dragon
    147, 148, 149, # Dratini line
    # Normal
    133,          # Eevee
    39, 40,       # Jigglypuff / Wigglytuff
    143,          # Snorlax
    # Roche/Sol
    74, 75, 76,   # Geodude line
    95,           # Onix
    # Électrique
    100, 101,     # Voltorb / Electrode
    # Insecte
    10, 11, 12,   # Caterpie line
    # Poison
    23, 24,       # Ekans / Arbok
    # Glace
    124,          # Jynx
    131,          # Lapras
    # Fée
    35, 36,       # Clefairy / Clefable
]


def sync_pokemon(pokemon_ids: list[int]) -> tuple[list[dict], set[int]]:
    """
    Récupère les données de tous les Pokémon spécifiés.
    Retourne (liste de pokemon, set de move_ids utilisés).
    """
    pokemons = []
    all_move_ids = set()
    total = len(pokemon_ids)

    for i, pid in enumerate(pokemon_ids):
        print(f"  [{i+1}/{total}] Récupération de Pokémon #{pid}...", end=" ", flush=True)
        try:
            poke = get_full_pokemon(pid)

            # Limiter le learnset aux 12 premiers moves level-up
            learnset = poke["learnset"][:12]
            poke["learnset"] = learnset

            # Collecter les move IDs
            for entry in learnset:
                all_move_ids.add(entry["move_id"])

            # Retirer le sprite_url du fichier final (pas nécessaire pour le jeu)
            poke.pop("sprite_url", None)

            # Garder le model_id si Bulbasaur
            if pid == 1:
                poke["model_id"] = "pm0001_00"

            pokemons.append(poke)
            print(f"✅ {poke['name']}")
        except Exception as e:
            print(f"❌ Erreur: {e}")

        # Rate limiting — PokeAPI recommande max 100 req/min
        time.sleep(0.5)

    return pokemons, all_move_ids


def sync_moves(move_ids: set[int]) -> list[dict]:
    """Récupère les données de tous les moves nécessaires."""
    moves = []
    sorted_ids = sorted(move_ids)
    total = len(sorted_ids)

    for i, mid in enumerate(sorted_ids):
        print(f"  [{i+1}/{total}] Récupération du move #{mid}...", end=" ", flush=True)
        try:
            move = get_move_data(mid)
            if move:
                moves.append(move)
                print(f"✅ {move['name']}")
            else:
                print("⚠️ Non trouvé")
        except Exception as e:
            print(f"❌ Erreur: {e}")

        time.sleep(0.3)

    return moves


def save_json(data, filename: str):
    """Sauvegarde les données en JSON formaté."""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"  📄 Sauvegardé: {filepath}")


def main():
    print("╔══════════════════════════════════════╗")
    print("║   🔄 SYNC POKEAPI → GAME DATA 🔄     ║")
    print("╚══════════════════════════════════════╝")
    print()

    # Backup des fichiers existants
    for filename in ["pokemons.json", "moves.json"]:
        src = os.path.join(DATA_DIR, filename)
        bak = os.path.join(DATA_DIR, f"{filename}.bak")
        if os.path.exists(src):
            import shutil
            shutil.copy2(src, bak)
            print(f"  💾 Backup: {bak}")

    print()

    # 1. Récupérer les Pokémon
    print("━━━ Pokémon ━━━")
    pokemons, all_move_ids = sync_pokemon(POKEMON_IDS)
    print(f"\n  Total: {len(pokemons)} Pokémon récupérés")
    print(f"  Moves référencés: {len(all_move_ids)}")

    print()

    # 2. Récupérer les moves
    print("━━━ Moves ━━━")
    moves = sync_moves(all_move_ids)
    print(f"\n  Total: {len(moves)} moves récupérés")

    print()

    # 3. Sauvegarder
    print("━━━ Sauvegarde ━━━")
    # Trier les Pokémon par ID
    pokemons.sort(key=lambda p: p["id"])
    # Trier les moves par ID
    moves.sort(key=lambda m: m["id"])

    save_json(pokemons, "pokemons.json")
    save_json(moves, "moves.json")

    print()
    print("✅ Synchronisation terminée !")
    print(f"   {len(pokemons)} Pokémon | {len(moves)} Moves")
    print()

    # Résumé des Pokémon
    print("━━━ Pokémon disponibles ━━━")
    for p in pokemons:
        types_str = "/".join(p["types"])
        print(f"  #{p['id']:3d} {p['name']:15s} [{types_str}]")


if __name__ == "__main__":
    main()
