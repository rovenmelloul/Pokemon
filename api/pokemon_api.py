import requests

BASE_URL = "https://pokeapi.co/api/v2"
DEFAULT_TIMEOUT = 10

pockemon_interface = {
    "id_pokemon": None | int,
    "name": None | str,
    "type": None | list,
    "height": None | int,
    "weight": None | int,
    "abilities": None | list,
    "base_experience": None | int,
    "level_evolution": None | int,
    "description": None | str,
}


def _get_json(url: str) -> dict:
    response = requests.get(url, timeout=DEFAULT_TIMEOUT)
    if response.status_code != 200:
        raise ValueError(f"Erreur PokeAPI: {response.status_code} pour {url}")
    return response.json()


def _format_name(name: str) -> str:
    if not name:
        return name
    return name.replace("-", " ").title()


def _extract_id(url: str) -> int:
    return int(url.rstrip("/").split("/")[-1])


def get_pokemon_data(pokemon_name: str) -> dict:
    url = f"{BASE_URL}/pokemon/{pokemon_name}"
    data = _get_json(url)
    pokemon_data = {
        "id_pokemon": data.get("id"),
        "name": data.get("name"),
        "type": [t["type"]["name"] for t in data.get("types", [])],
        "height": data.get("height"),
        "weight": data.get("weight"),
        "abilities": [a["ability"]["name"] for a in data.get("abilities", [])],
        "hidden_ability": [
            a["ability"]["name"]
            for a in data.get("abilities", [])
            if a.get("is_hidden", False)
        ],
        "base_experience": data.get("base_experience"),
    }
    return pokemon_data


def get_full_pokemon(pokemon_id_or_name: str | int) -> dict:
    """
    Récupère un Pokémon complet pour le jeu (format pokemons.json).
    """
    data = _get_json(f"{BASE_URL}/pokemon/{pokemon_id_or_name}")
    species = _get_json(f"{BASE_URL}/pokemon-species/{pokemon_id_or_name}")

    stats_map = {
        "hp": "hp",
        "attack": "attack",
        "defense": "defense",
        "special-attack": "sp_attack",
        "special-defense": "sp_defense",
        "speed": "speed",
    }
    base_stats = {}
    for s in data.get("stats", []):
        stat_name = s["stat"]["name"]
        key = stats_map.get(stat_name)
        if key:
            base_stats[key] = s["base_stat"]

    types = [t["type"]["name"] for t in sorted(data.get("types", []), key=lambda x: x["slot"])]

    learnset = []
    for move in data.get("moves", []):
        move_id = _extract_id(move["move"]["url"])
        level_entries = [
            d["level_learned_at"]
            for d in move.get("version_group_details", [])
            if d.get("move_learn_method", {}).get("name") == "level-up"
        ]
        if not level_entries:
            continue
        learnset.append({
            "move_id": move_id,
            "level": min(level_entries),
        })

    learnset.sort(key=lambda x: (x["level"], x["move_id"]))

    return {
        "id": data.get("id"),
        "name": _format_name(data.get("name")),
        "types": types,
        "base_stats": base_stats,
        "capture_rate": species.get("capture_rate"),
        "base_xp": data.get("base_experience"),
        "learnset": learnset,
        "model_id": None,
    }


def get_move_data(move_id_or_name: str | int) -> dict:
    """
    Récupère un move (format moves.json).
    """
    data = _get_json(f"{BASE_URL}/move/{move_id_or_name}")
    return {
        "id": data.get("id"),
        "name": _format_name(data.get("name")),
        "type": data.get("type", {}).get("name"),
        "category": data.get("damage_class", {}).get("name"),
        "power": data.get("power"),
        "accuracy": data.get("accuracy"),
        "pp": data.get("pp"),
    }
