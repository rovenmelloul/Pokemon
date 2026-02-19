"""Load and manage effect definitions from effects.json."""
import json
import os


class EffectDef:
    """Definition of a single attack effect."""

    def __init__(self, data):
        self.name = data.get("name", "")
        self.type = data.get("type", "Normal")
        self.style = data.get("style", "projectile")  # projectile|contact|self|ground
        self.model = data.get("model", "PG_sphere")
        self.texture = data.get("texture", None)
        self.origin_bone = data.get("origin_bone", "EffShoot01_01")
        self.target_bone = data.get("target_bone", "EffCenter01")
        self.speed = data.get("speed", 8.0)
        self.scale = data.get("scale", 0.3)
        self.duration = data.get("duration", 0.5)
        self.color = data.get("color", None)  # [r, g, b, a] tint override

    def __repr__(self):
        return f"EffectDef({self.name!r}, type={self.type}, style={self.style})"


class EffectDefinitions:
    """Container for all effect definitions, loaded from effects.json."""

    def __init__(self, json_path=None):
        self.effects = {}  # name -> EffectDef
        self.type_defaults = {}  # type_name -> EffectDef
        if json_path is None:
            json_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "data", "effects.json"
            )
        self._json_path = json_path
        self.load()

    def load(self):
        """Load definitions from JSON file."""
        if not os.path.isfile(self._json_path):
            print(f"[EFFECTS] Warning: {self._json_path} not found")
            return
        try:
            with open(self._json_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[EFFECTS] Error loading {self._json_path}: {e}")
            return

        for entry in data.get("effects", []):
            edef = EffectDef(entry)
            self.effects[edef.name] = edef
            # First effect for each type becomes the default
            if edef.type not in self.type_defaults:
                self.type_defaults[edef.type] = edef

        print(f"[EFFECTS] Loaded {len(self.effects)} effects for "
              f"{len(self.type_defaults)} types")

    def get_effect(self, name):
        """Get an effect definition by name."""
        return self.effects.get(name)

    def get_effects_for_type(self, type_name):
        """Get all effect definitions for a given Pokemon type."""
        return [e for e in self.effects.values() if e.type == type_name]

    def get_default_for_type(self, type_name):
        """Get the default effect for a type."""
        return self.type_defaults.get(type_name)

    def get_all_types(self):
        """Return sorted list of all type names that have effects."""
        return sorted(self.type_defaults.keys())
