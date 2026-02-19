"""Auto-discover all converted waza models and their textures."""
import os


class WazaEntry:
    """A single waza model with its egg path and available textures."""

    def __init__(self, name, egg_path, textures, category="waza"):
        self.name = name
        self.egg_path = egg_path
        self.textures = textures  # list of .png paths
        self.category = category  # "waza" or "g_effect"

    @property
    def has_textures(self):
        return len(self.textures) > 0

    def __repr__(self):
        tex_count = len(self.textures)
        return f"WazaEntry({self.name!r}, {tex_count} tex)"


class WazaCatalog:
    """Scans output directory and catalogs all available waza/g_effect models."""

    # Categories of waza models for classification
    BEAMS = {"ew058_at_beam", "ew058_df_beam", "ew069_beam", "ew035_line01",
             "ew168_line01", "ew753_line01"}
    HANDS = {n for n in [] if True}  # filled dynamically
    SWORDS = {"ew014_swordM"}
    PROJECTILES = {"ew246_bullet", "ew529_bullet01", "ew529_bullet03",
                   "ew143_1_bullet_wing01"}
    RINGS = {"ew020_ringM", "ew020_ring_1_M", "eg_coop_ring"}
    SHELLS = {"ew110_shell", "ew128_shell", "ew504_shell"}
    PRIMITIVES = {"PG_sphere", "PG_cube", "PG_cone", "PG_cylinder_l",
                  "PG_cylinder_ll", "PG_cylinder_m", "PG_cylinder_s"}

    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.entries = {}  # name -> WazaEntry
        self._scan()

    def _scan(self):
        """Scan waza/ and g_effect/ directories."""
        for cat in ("waza", "g_effect"):
            cat_dir = os.path.join(self.output_dir, cat)
            if not os.path.isdir(cat_dir):
                continue
            for folder in sorted(os.listdir(cat_dir)):
                folder_path = os.path.join(cat_dir, folder)
                if not os.path.isdir(folder_path):
                    continue
                egg_files = [f for f in os.listdir(folder_path) if f.endswith(".egg")]
                if not egg_files:
                    continue
                textures = [
                    os.path.join(folder_path, f)
                    for f in os.listdir(folder_path)
                    if f.endswith(".png")
                ]
                for egg_file in egg_files:
                    name = os.path.splitext(egg_file)[0]
                    entry = WazaEntry(
                        name=name,
                        egg_path=os.path.join(folder_path, egg_file),
                        textures=textures,
                        category=cat,
                    )
                    self.entries[name] = entry

    def get(self, name):
        """Get a WazaEntry by name."""
        return self.entries.get(name)

    def get_all(self):
        """Return all entries as a sorted list."""
        return sorted(self.entries.values(), key=lambda e: e.name)

    def get_by_pattern(self, pattern):
        """Return entries whose name contains the pattern."""
        pattern = pattern.lower()
        return [e for e in self.entries.values() if pattern in e.name.lower()]

    def get_beams(self):
        """Return beam-type waza models."""
        return [e for e in self.entries.values()
                if e.name in self.BEAMS or "beam" in e.name.lower()
                or "line" in e.name.lower()]

    def get_hands(self):
        """Return hand-type waza models."""
        return [e for e in self.entries.values()
                if "hand" in e.name.lower() or "finger" in e.name.lower()]

    def get_weapons(self):
        """Return weapon-like waza models (swords, horns, etc.)."""
        return [e for e in self.entries.values()
                if any(kw in e.name.lower() for kw in
                       ("sword", "horn", "needle", "tooth", "bone", "hammer",
                        "whip", "baton", "hasami", "crab"))]

    def get_shapes(self):
        """Return primitive shapes (PG_*)."""
        return [e for e in self.entries.values()
                if e.name.startswith("PG_")]

    def get_misc(self):
        """Return everything that isn't a beam, hand, weapon, or shape."""
        known = set()
        for lst in (self.get_beams(), self.get_hands(),
                    self.get_weapons(), self.get_shapes()):
            for e in lst:
                known.add(e.name)
        return [e for e in self.entries.values() if e.name not in known]

    @property
    def count(self):
        return len(self.entries)
