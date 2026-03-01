"""
EncounterSystem -- Proximity-based encounter on the 3D map.
When the player gets close to a wild Pokemon, trigger battle.
"""
import math

# Distance threshold to trigger encounter (in world units)
ENCOUNTER_DISTANCE = 12.0


class EncounterSystem:
    """Checks proximity between player and spawned wild Pokemon."""

    def __init__(self):
        self.engaged_pokemon = None  # Currently engaged Pokemon (avoid re-trigger)

    def check_proximity(self, player_pos, wild_pokemon_list):
        """
        Check if the player is close enough to any wild Pokemon.
        Returns the closest Pokemon within range, or None.
        """
        if self.engaged_pokemon is not None:
            return None

        closest = None
        closest_dist = ENCOUNTER_DISTANCE

        for poke in wild_pokemon_list:
            if poke.is_fainted():
                continue
            poke_pos = poke.animated_character.getPos()
            dx = player_pos.getX() - poke_pos.getX()
            dy = player_pos.getY() - poke_pos.getY()
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < closest_dist:
                closest_dist = dist
                closest = poke

        return closest

    def engage(self, pokemon):
        self.engaged_pokemon = pokemon

    def disengage(self):
        self.engaged_pokemon = None
