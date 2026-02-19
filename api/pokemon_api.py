import json
import requests
import sqlite3

pockemon_interface = {
    "id_pokemon": None,
    "galar_dex": None,
    "lvl": None,
    "name": None,
    "model_folder": None,
    "pokemon_data_from_api": None,
    "national_dex": None,
    "all_forms": None,
}


con = sqlite3.connect("pokemon.db")


def relate_pokemon_api_data_with_models():
    json_model_file = "game\\models\\galar_pokedex_models.json"
    json_to_save = "api\\test.json"
    all_pokemon_data = []
    with open(json_model_file, "r") as f:
        model_data = json.load(f)
        for pokemon_id in model_data:
            pockemon_interface["name"] = model_data[pokemon_id]["name"]
            pockemon_interface["galar_dex"] = model_data[pokemon_id]["galar_dex"]
            pockemon_interface["model_folder"] = model_data[pokemon_id]["model_folder"]
            pockemon_interface["national_dex"] = model_data[pokemon_id]["national_dex"]
            pockemon_interface["all_forms"] = model_data[pokemon_id]["all_forms"]
            pockemon_interface["pokemon_data_from_api"] = get_pokemon_data(model_data[pokemon_id]["name"])
            all_pokemon_data.append(pockemon_interface.copy())
            print(f"Processed {model_data[pokemon_id]['name']}")
        with open(json_to_save, "w") as f:
                json.dump(all_pokemon_data, f, indent=4)
            

def get_pokemon_data(pokemon_name: str) -> dict:
    # TODO: For all meta names take all poke info and insert to data base
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

            "stats": {
                s["stat"]["name"]: {
                    "base_stat": s["base_stat"],
                    "effort": s["effort"]
                } for s in data.get("stats", [])
            },

            "moves": [m["move"]["name"] for m in data.get("moves", [])],  
        }
        return pokemon_data
    else:
        print(f"Failed to fetch data for {pokemon_name}. Status code: {response.status_code}")
        return None


relate_pokemon_api_data_with_models()
