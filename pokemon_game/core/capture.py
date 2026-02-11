"""
CaptureSystem — Formule de capture officielle Gen 3+.
"""
import math
import random
from .pokemon import Pokemon


# Multiplicateurs des Pokéballs
POKEBALL_RATES = {
    "pokeball": 1.0,
    "superball": 1.5,
    "hyperball": 2.0,
    "masterball": 255.0  # Capture garantie
}

# Bonus de statut
STATUS_BONUS = {
    "sleep": 2.5,
    "freeze": 2.5,
    "paralysis": 1.5,
    "poison": 1.5,
    "burn": 1.5,
    None: 1.0
}


class CaptureSystem:
    """
    Système de capture Pokémon avec formule officielle Gen 3+.
    
    Formule :
    a = ((3*maxHP - 2*curHP) * capture_rate * ball_rate) / (3*maxHP) * status_bonus
    
    Si a >= 255 → capture garantie
    Sinon b = 65536 / (255/a)^(1/4)
    4 checks RNG : chaque check doit être < b pour réussir
    """

    @staticmethod
    def attempt_capture(pokemon: Pokemon, ball_type: str = "pokeball") -> dict:
        """
        Tente de capturer un Pokémon.
        
        Retourne :
        {
            "success": bool,
            "shakes": int (0-3 avant échec, ou 4 si capture),
            "ball_type": str,
            "message": str
        }
        """
        ball_rate = POKEBALL_RATES.get(ball_type, 1.0)

        # Master Ball = capture instantanée
        if ball_type == "masterball":
            return {
                "success": True,
                "shakes": 4,
                "ball_type": ball_type,
                "message": f"✨ {pokemon.name} est capturé avec la Master Ball !"
            }

        max_hp = pokemon.stats["hp"]
        cur_hp = pokemon.current_hp
        capture_rate = pokemon.capture_rate
        status_mult = STATUS_BONUS.get(pokemon.status, 1.0)

        # Formule a
        a = ((3 * max_hp - 2 * cur_hp) * capture_rate * ball_rate) / (3 * max_hp)
        a *= status_mult
        a = min(a, 255.0)

        # Capture garantie si a >= 255
        if a >= 255:
            return {
                "success": True,
                "shakes": 4,
                "ball_type": ball_type,
                "message": f"✨ Gotcha ! {pokemon.name} est capturé !"
            }

        # Calcul de b
        if a <= 0:
            b = 0
        else:
            b = 65536 / math.pow(255.0 / a, 0.25)

        # 4 checks RNG
        shakes = 0
        for _ in range(4):
            check = random.randint(0, 65535)
            if check < b:
                shakes += 1
            else:
                break

        if shakes == 4:
            return {
                "success": True,
                "shakes": 4,
                "ball_type": ball_type,
                "message": f"✨ Gotcha ! {pokemon.name} est capturé !"
            }
        else:
            shake_messages = {
                0: f"Oh non ! {pokemon.name} s'est échappé immédiatement !",
                1: f"Aargh ! C'était presque ! {pokemon.name} s'est échappé !",
                2: f"Hmmm... {pokemon.name} s'est libéré !",
                3: f"Si près ! {pokemon.name} s'est échappé au dernier moment !"
            }
            return {
                "success": False,
                "shakes": shakes,
                "ball_type": ball_type,
                "message": shake_messages.get(shakes, f"{pokemon.name} s'est échappé !")
            }

    @staticmethod
    def capture_probability(pokemon: Pokemon, ball_type: str = "pokeball") -> float:
        """
        Calcule la probabilité approximative de capture (0.0 à 1.0).
        Utile pour l'UI.
        """
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
