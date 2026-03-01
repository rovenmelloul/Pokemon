"""
CaptureSystem -- Official Gen 3+ capture formula.
"""
import math
import random
from .pokemon_stats import PokemonStats

POKEBALL_RATES = {
    "pokeball": 1.0,
    "superball": 1.5,
    "hyperball": 2.0,
    "masterball": 255.0,
}

STATUS_BONUS = {
    "sleep": 2.5,
    "freeze": 2.5,
    "paralysis": 1.5,
    "poison": 1.5,
    "burn": 1.5,
    None: 1.0,
}


class CaptureSystem:
    @staticmethod
    def attempt_capture(pokemon, ball_type="pokeball"):
        ball_rate = POKEBALL_RATES.get(ball_type, 1.0)
        if ball_type == "masterball":
            return {
                "success": True, "shakes": 4, "ball_type": ball_type,
                "message": f"{pokemon.name} was caught with the Master Ball!"
            }
        max_hp = pokemon.stats["hp"]
        cur_hp = pokemon.current_hp
        capture_rate = pokemon.capture_rate
        status_mult = STATUS_BONUS.get(pokemon.status, 1.0)
        a = ((3 * max_hp - 2 * cur_hp) * capture_rate * ball_rate) / (3 * max_hp)
        a *= status_mult
        a = min(a, 255.0)
        if a >= 255:
            return {
                "success": True, "shakes": 4, "ball_type": ball_type,
                "message": f"Gotcha! {pokemon.name} was caught!"
            }
        if a <= 0:
            b = 0
        else:
            b = 65536 / math.pow(255.0 / a, 0.25)
        shakes = 0
        for _ in range(4):
            if random.randint(0, 65535) < b:
                shakes += 1
            else:
                break
        if shakes == 4:
            return {
                "success": True, "shakes": 4, "ball_type": ball_type,
                "message": f"Gotcha! {pokemon.name} was caught!"
            }
        shake_messages = {
            0: f"Oh no! {pokemon.name} broke free immediately!",
            1: f"Aww! So close! {pokemon.name} broke free!",
            2: f"Hmm... {pokemon.name} broke free!",
            3: f"So close! {pokemon.name} broke free at the last moment!"
        }
        return {
            "success": False, "shakes": shakes, "ball_type": ball_type,
            "message": shake_messages.get(shakes, f"{pokemon.name} broke free!")
        }

    @staticmethod
    def capture_probability(pokemon, ball_type="pokeball"):
        if ball_type == "masterball":
            return 1.0
        ball_rate = POKEBALL_RATES.get(ball_type, 1.0)
        max_hp = pokemon.stats["hp"]
        cur_hp = pokemon.current_hp
        capture_rate = pokemon.capture_rate
        status_mult = STATUS_BONUS.get(pokemon.status, 1.0)
        a = ((3 * max_hp - 2 * cur_hp) * capture_rate * ball_rate) / (3 * max_hp)
        a *= status_mult
        a = min(a, 255.0)
        if a >= 255:
            return 1.0
        if a <= 0:
            return 0.0
        b = 65536 / math.pow(255.0 / a, 0.25)
        p = (b / 65536) ** 4
        return min(1.0, max(0.0, p))
