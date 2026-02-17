import requests
import sqlite3

pockemon_interface = {
    "id_pokemon": None | int,
    "lvl":None | int,
    "name": None | str,
    "type": None | list,
    "height": None | int,
    "weight": None | int,
    "abilities": None | list,
    "base_experience": None | int,
    "level_evolution": None | int,
    "description": None | str,
    "animation_path": None,
}

def get_pokemon_data(pokemon_name: str) -> dict:
    #TODO: For all meta names take all poke info and insert to data base
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        pokemon_data = {
            "id_pokemon": data.get("id"),
            "name": data.get("name"),
            "type": [t["type"]["name"] for t in data.get("types", [])],
            "height": data.get("height"),
            "weight": data.get("weight"),
            "abilities": [a["ability"]["name"] for a in data.get("abilities", [])],
            "hidden_ability": [a["ability"]["name"] for a in data.get("abilities", []) if a.get("is_hidden", False)],
            "base_experience": data.get("base_experience"),
        }
        return pokemon_data
    else:
        raise ValueError(f"Pokemon '{pokemon_name}' not found.")
    
print(get_pokemon_data("pikachu"))