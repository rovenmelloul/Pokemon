"""Pokemon -- 3D model + combat stats hybrid class."""
import json
import os
import math
import random
from pathlib import Path

from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import (
    Sequence, Parallel, LerpPosInterval, LerpColorScaleInterval, Func,
)
from panda3d.core import (
    Point3, VBase3, VBase4, TextNode, BillboardEffect,
    AmbientLight, DirectionalLight, NodePath,
    CardMaker, TextureStage, TransparencyAttrib,
    PNMImage, Texture,
)

from sdk import Pokemon as SDKPokemon
from sdk import AnimationController

SHINY_CHANCE = 1 / 3

_MODELS_BASE = str(Path(os.path.dirname(__file__), '..', '..', '..', 'models', 'pokemon').resolve())

# --- Shared procedural textures ---
_circle_tex = None
_sparkle_tex = None


def _get_circle_texture():
    global _circle_tex
    if _circle_tex is not None:
        return _circle_tex
    size = 128
    img = PNMImage(size, size, 4)
    img.fill(0, 0, 0)
    img.alphaFill(0)
    cx = cy = size / 2.0
    outer_r = size / 2.0 - 2
    ring_w = 5.0
    inner_r = outer_r - ring_w
    for y in range(size):
        for x in range(size):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist <= outer_r:
                if dist >= inner_r:
                    edge = min(1.0, (outer_r - dist) * 2)
                    inner_edge = min(1.0, (dist - inner_r) * 2)
                    alpha = 0.75 * edge * inner_edge
                    img.setXelA(x, y, 0.2, 0.6, 1.0, alpha)
                else:
                    img.setXelA(x, y, 0.15, 0.5, 0.95, 0.07)
    _circle_tex = Texture("ground_circle")
    _circle_tex.load(img)
    return _circle_tex


def _get_sparkle_texture():
    global _sparkle_tex
    if _sparkle_tex is not None:
        return _sparkle_tex
    size = 32
    img = PNMImage(size, size, 4)
    img.fill(0, 0, 0)
    img.alphaFill(0)
    cx = cy = size / 2.0
    for y in range(size):
        for x in range(size):
            dx = abs(x - cx) / cx
            dy = abs(y - cy) / cy
            star_h = max(0, 1.0 - dx * 4) * max(0, 1.0 - dy * 1.5)
            star_v = max(0, 1.0 - dy * 4) * max(0, 1.0 - dx * 1.5)
            glow = max(0, 1.0 - math.sqrt(dx * dx + dy * dy) * 1.8)
            val = min(1.0, max(star_h, star_v) + glow * 0.25)
            if val > 0.01:
                img.setXelA(x, y, 1.0, 0.93, 0.3, val)
    _sparkle_tex = Texture("sparkle")
    _sparkle_tex.load(img)
    return _sparkle_tex


# ---------- Load data sources ----------
json_all_info = None
json_all_info_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'api', 'test.json')
with open(json_all_info_path, "r", encoding="utf-8") as f:
    json_all_info = json.load(f)

# Build model_folder -> pokemons.json stats mapping
_combat_db = {}
_combat_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'pokemons.json')
if os.path.exists(_combat_db_path):
    with open(_combat_db_path, "r", encoding="utf-8") as f:
        _combat_list = json.load(f)
    for _p in _combat_list:
        _combat_db[_p["id"]] = _p
        if _p.get("model_id"):
            _combat_db[_p["model_id"]] = _p

# Load moves database
from core.move import Move
Move.load_moves()


def _api_stats_to_base_stats(api_stats):
    """Convert test.json pokemon_data_from_api.stats to base_stats dict."""
    mapping = {
        "hp": "hp", "attack": "attack", "defense": "defense",
        "special-attack": "sp_attack", "special-defense": "sp_defense",
        "speed": "speed"
    }
    result = {}
    for api_key, our_key in mapping.items():
        if api_key in api_stats:
            result[our_key] = api_stats[api_key].get("base_stat", 50)
        else:
            result[our_key] = 50
    return result


def _calculate_stat(base, iv, ev, level, is_hp=False):
    """Gen 3+ stat formula."""
    if is_hp:
        return math.floor((2 * base + iv + math.floor(ev / 4)) * level / 100) + level + 10
    return math.floor((2 * base + iv + math.floor(ev / 4)) * level / 100) + 5


class Pokemon:
    def __init__(self, show_base: ShowBase, **kwargs):
        self.show_base = show_base

        # Pokemon identity
        self.id_pokemon = kwargs.get("id_pokemon", None)
        self.pokedex_id = None  # ID in pokemons.json (combat DB)
        self.lvl = kwargs.get("lvl", None)

        self.random_galar_dex = random.randint(0, len(json_all_info) - 1)
        self.name = json_all_info[self.random_galar_dex]["name"]

        api_data = json_all_info[self.random_galar_dex].get("pokemon_data_from_api") or {}
        self.type = api_data.get("type", [])
        self.height = kwargs.get("height", None)
        self.weight = kwargs.get("weight", None)
        self.abilities = kwargs.get("abilities", None)
        self.base_experience = kwargs.get("base_experience", None)
        self.level_evolution = kwargs.get("level_evolution", None)
        self.description = kwargs.get("description", None)

        # Model / animation
        self.model_folder = json_all_info[self.random_galar_dex].get("model_folder")
        self.is_shiny = random.random() < SHINY_CHANCE

        self.lvl_board = {
            "low": "game\\gui\\src\\sprites\\title_for_low_lvl_pokemons.png",
            "average": "game\\gui\\src\\sprites\\title_for_avarage_lvl_pokemons.png",
            "high": "game\\gui\\src\\sprites\\title_for_high_lvl_pokemons.png",
        }

        # Position
        self.start_position = (random.randint(-80, 80), random.randint(-80, 80), 0)

        # ---------- COMBAT STATS ----------
        self.base_stats = {}
        self.stats = {}
        self.current_hp = 0
        self.moves = []
        self.capture_rate = 45
        self.base_xp = 64
        self.status = None
        self.types = list(self.type) if self.type else ["normal"]
        self.xp = 0
        self.level = 5
        self.learnset = []

        self.sdk_pokemon = None
        self.anim_ctrl = None
        self.animated_character = self._load_model()
        self.animated_character.reparentTo(self.show_base.render)

        self.name_container = None
        self._ground_circle = None
        self._sparkle_task_name = None
        self._next_sparkle_time = 0

    def _load_model(self):
        model_dir = os.path.join(_MODELS_BASE, self.model_folder)
        self.sdk_pokemon = SDKPokemon(
            self.show_base, model_dir,
            use_shiny=self.is_shiny, auto_center=False)
        self.anim_ctrl = AnimationController(
            self.show_base, self.sdk_pokemon, auto_idle=True)
        return self.sdk_pokemon.actor

    def _init_combat_stats(self):
        """Initialize combat stats from pokemons.json or test.json API data."""
        # Try to find matching entry in combat DB by model_folder
        combat_data = _combat_db.get(self.model_folder)

        if combat_data:
            # Full combat data from pokemons.json
            self.pokedex_id = combat_data["id"]
            self.base_stats = combat_data["base_stats"]
            self.capture_rate = combat_data.get("capture_rate", 45)
            self.base_xp = combat_data.get("base_xp", 64)
            self.learnset = combat_data.get("learnset", [])
            self.types = combat_data["types"]
        else:
            # Fallback: derive from test.json API data
            api_data = json_all_info[self.random_galar_dex].get("pokemon_data_from_api") or {}
            self.pokedex_id = api_data.get("id_pokemon")
            if api_data.get("stats"):
                self.base_stats = _api_stats_to_base_stats(api_data["stats"])
            else:
                self.base_stats = {"hp": 50, "attack": 50, "defense": 50,
                                   "sp_attack": 50, "sp_defense": 50, "speed": 50}
            self.capture_rate = 45
            self.base_xp = api_data.get("base_experience", 64) or 64
            self.types = api_data.get("type", ["normal"])
            self.learnset = []

        # Calculate stats from base_stats + level
        ivs = 15
        self.stats = {}
        for stat_name in ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]:
            base = self.base_stats.get(stat_name, 50)
            self.stats[stat_name] = _calculate_stat(base, ivs, 0, self.level, stat_name == "hp")
        self.current_hp = self.stats["hp"]

        # Auto-generate moveset
        if self.learnset:
            available = [e for e in self.learnset if e["level"] <= self.level]
            available.sort(key=lambda x: x["level"], reverse=True)
            self.moves = []
            for entry in available[:4]:
                try:
                    self.moves.append(Move.get_by_id(entry["move_id"]))
                except KeyError:
                    pass
        if not self.moves:
            # Fallback: give Tackle + Growl
            try:
                self.moves = [Move.get_by_id(1)]  # Tackle
            except KeyError:
                pass

    def _create_ground_circle(self):
        tex = _get_circle_texture()
        cm = CardMaker("ground_circle")
        cm.setFrame(-1, 1, -1, 1)
        self._ground_circle = self.animated_character.attachNewNode(cm.generate())
        self._ground_circle.setTexture(tex)
        self._ground_circle.setTransparency(TransparencyAttrib.MAlpha)
        self._ground_circle.setP(-90)
        self._ground_circle.setPos(0, 0, 1)
        bounds = self.animated_character.getTightBounds()
        if bounds:
            bmin, bmax = bounds
            sx = abs(bmax.getX() - bmin.getX())
            sy = abs(bmax.getY() - bmin.getY())
            sz = abs(bmax.getZ() - bmin.getZ())
            footprint = max(sx, sy, sz)
            multiplier = max(footprint / 60.0, 0.4)
        else:
            multiplier = 1.0
        self._ground_circle.setScale(80 * multiplier)
        self._ground_circle.setLightOff()
        self._ground_circle.setDepthWrite(False)
        self._ground_circle.setBin("transparent", 10)

    def _shiny_sparkle_task(self, task):
        if task.time >= self._next_sparkle_time:
            self._spawn_sparkle()
            self._next_sparkle_time = task.time + random.uniform(0.3, 1.0)
        return task.cont

    def _spawn_sparkle(self):
        tex = _get_sparkle_texture()
        cm = CardMaker("sparkle")
        s = random.uniform(0.25, 0.6)
        cm.setFrame(-s, s, -s, s)
        sparkle = self.show_base.render.attachNewNode(cm.generate())
        sparkle.setTexture(tex)
        sparkle.setTransparency(TransparencyAttrib.MAlpha)
        sparkle.setBillboardPointEye()
        sparkle.setLightOff()
        sparkle.setDepthWrite(False)
        sparkle.setBin("fixed", 20)
        pos = self.animated_character.getPos(self.show_base.render)
        start = Point3(
            pos.x + random.uniform(-1.5, 1.5),
            pos.y + random.uniform(-1.5, 1.5),
            pos.z + random.uniform(0.5, 3.5),
        )
        sparkle.setPos(start)
        duration = random.uniform(0.8, 1.5)
        end_pos = start + Point3(
            random.uniform(-0.3, 0.3),
            random.uniform(-0.3, 0.3),
            random.uniform(1.5, 3.0),
        )
        Sequence(
            Parallel(
                LerpPosInterval(sparkle, duration, end_pos),
                LerpColorScaleInterval(sparkle, duration, VBase4(1, 1, 1, 0)),
            ),
            Func(sparkle.removeNode),
        ).start()

    def spawn_random_pokemon(self):
        self.id_pokemon = random.randint(1, 898)
        self.lvl = random.randint(1, 100)
        self.level = self.lvl
        self.name = self.name or f"Pokemon_{self.id_pokemon}"
        self.type_ = random.choice(["Fire", "Water", "Grass", "Electric"])
        self.height = random.randint(1, 20)
        self.weight = random.randint(1, 100)
        self.abilities = [f"Ability_{i}" for i in range(random.randint(1, 3))]
        self.base_experience = random.randint(50, 500)
        self.level_evolution = random.randint(1, 100)
        self.description = f"This is a {self.type_} type Pokemon named {self.name}."
        self.animation_path = f"animations/{self.name}.anim"

        self.animated_character.setPos(self.start_position)
        self.animated_character.setScale(0.05)

        # Initialize combat stats
        self._init_combat_stats()

        idle = self.anim_ctrl.find_idle()
        if idle:
            self.anim_ctrl.play(idle, loop=True)

        self._create_ground_circle()

    def draw_name_tag(self):
        from panda3d.core import CardMaker, TransparencyAttrib

        if self.lvl <= 30:
            badge_path = self.lvl_board["low"]
        elif self.lvl <= 60:
            badge_path = self.lvl_board["average"]
        else:
            badge_path = self.lvl_board["high"]

        self.name_container = self.show_base.render.attachNewNode("name_container")
        self.name_container.setBillboardPointEye()
        self.name_container.setScale(0.45)
        self.name_container.setTransparency(TransparencyAttrib.MAlpha)

        text_node = TextNode('name_text')
        full_text = self.name
        if self.is_shiny:
            full_text = "[*] " + full_text
        if self.lvl is not None:
            full_text += f"\nLv.{self.lvl}"
        if hasattr(self, 'type_') and self.type_:
            full_text += f" ({self.type_})"

        text_node.setText(full_text)
        text_node.setAlign(TextNode.ACenter)
        if self.is_shiny:
            text_node.setTextColor(1, 0.84, 0, 1)
        else:
            text_node.setTextColor(1, 1, 1, 1)

        text_np = self.name_container.attachNewNode(text_node)
        text_np.setPos(0, 0, 0)

        badge_tex = self.show_base.loader.loadTexture(badge_path)
        if badge_tex:
            cm = CardMaker("badge")
            cm.setFrame(-0.8, 0.8, -0.8, 0.8)
            badge_np = self.name_container.attachNewNode(cm.generate())
            badge_np.setTexture(badge_tex)
            badge_np.setTransparency(TransparencyAttrib.MAlpha)
            badge_np.setPos(-5.0, 0, 0)
            badge_np.setScale(2.3)

        self.show_base.taskMgr.add(self.update_name_tag_task, f"name_tag_{id(self)}")

        if self.is_shiny:
            self._sparkle_task_name = f"shiny_sparkle_{id(self)}"
            self._next_sparkle_time = 0
            self.show_base.taskMgr.add(
                self._shiny_sparkle_task, self._sparkle_task_name)

    def update_name_tag_task(self, task):
        if self.name_container:
            char_pos = self.animated_character.getPos(self.show_base.render)
            self.name_container.setPos(char_pos + Point3(0, 0, 4.8))
        return task.cont

    # ---------- COMBAT METHODS ----------

    def take_damage(self, damage):
        actual = min(damage, self.current_hp)
        self.current_hp -= actual
        return actual

    def heal(self, amount=None):
        if amount is None:
            self.current_hp = self.stats.get("hp", 1)
        else:
            self.current_hp = min(self.current_hp + amount, self.stats.get("hp", 1))

    def is_fainted(self):
        return self.current_hp <= 0

    def hp_fraction(self):
        max_hp = self.stats.get("hp", 1)
        return self.current_hp / max_hp if max_hp > 0 else 0

    def level_up(self):
        old_max_hp = self.stats.get("hp", 1)
        self.level += 1
        self.lvl = self.level
        ivs = 15
        for stat_name in ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]:
            base = self.base_stats.get(stat_name, 50)
            self.stats[stat_name] = _calculate_stat(base, ivs, 0, self.level, stat_name == "hp")
        hp_diff = self.stats["hp"] - old_max_hp
        self.current_hp += hp_diff

    def set_status(self, status):
        if self.status is None:
            self.status = status

    def clear_status(self):
        self.status = None

    def full_restore(self):
        self.current_hp = self.stats.get("hp", 1)
        self.status = None
        for move in self.moves:
            move.restore_pp()

    def learn_new_moves_for_level(self):
        new_moves = []
        for entry in self.learnset:
            if entry["level"] == self.level:
                try:
                    move = Move.get_by_id(entry["move_id"])
                except KeyError:
                    continue
                if not any(m.id == move.id for m in self.moves):
                    if len(self.moves) < 4:
                        self.moves.append(move)
                        new_moves.append(move)
                    else:
                        weakest_idx = 0
                        weakest_power = self.moves[0].power
                        for i, m in enumerate(self.moves):
                            if m.power < weakest_power:
                                weakest_power = m.power
                                weakest_idx = i
                        if move.power > weakest_power:
                            self.moves[weakest_idx] = move
                            new_moves.append(move)
        return new_moves

    def get_info(self):
        return {
            "id_pokemon": self.id_pokemon,
            "pokedex_id": self.pokedex_id,
            "lvl": self.lvl,
            "name": self.name,
            "type": getattr(self, 'type_', self.type),
            "types": self.types,
            "height": self.height,
            "weight": self.weight,
            "abilities": self.abilities,
            "base_experience": self.base_experience,
            "level_evolution": self.level_evolution,
            "description": self.description,
            "stats": self.stats,
            "current_hp": self.current_hp,
        }

    def destroy(self):
        if self._sparkle_task_name:
            self.show_base.taskMgr.remove(self._sparkle_task_name)
        if self.anim_ctrl:
            self.anim_ctrl.destroy()
            self.anim_ctrl = None
        if self.sdk_pokemon:
            self.sdk_pokemon.destroy()
            self.sdk_pokemon = None
        if self._ground_circle:
            self._ground_circle.removeNode()
            self._ground_circle = None
        if self.name_container:
            self.name_container.removeNode()
            self.name_container = None
