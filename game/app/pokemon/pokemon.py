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
    Point3, VBase3, VBase4, TextNode,
    CardMaker, TextureStage, TransparencyAttrib,
    PNMImage, Texture,
    CollisionNode, CollisionSphere,  
)

from ..battle_system import CapturePokemon 

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


pockemon_interface = {
    "id_pokemon": None | int,
    "lvl": None | int,
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

json_all_info = None
json_all_info_path = "api\\test.json"
with open(json_all_info_path, "r") as f:
    json_all_info = json.load(f)


class Pokemon:
    def __init__(self, show_base: ShowBase, **kwargs):
        self.show_base = show_base
        
        self.is_capturing = False         
        self.captured = False              

        #POKEMON DATA
        self.id_pokemon = kwargs.get("id_pokemon", None)
        self.lvl = kwargs.get("lvl", None)

        self.random_galar_dex = random.randint(0, len(json_all_info) - 1)
        self.name = json_all_info[self.random_galar_dex]["name"]

        self.type = json_all_info[self.random_galar_dex]["pokemon_data_from_api"]["type"] if "pokemon_data_from_api" in json_all_info[self.random_galar_dex] and "type" in json_all_info[self.random_galar_dex]["pokemon_data_from_api"] else None

        self.height = kwargs.get("height", None)
        self.weight = kwargs.get("weight", None)
        self.abilities = kwargs.get("abilities", None)
        self.base_experience = kwargs.get("base_experience", None)
        self.level_evolution = kwargs.get("level_evolution", None)
        self.description = kwargs.get("description", None)

        # MODEL / ANIMATION DATA
        self.model_folder = json_all_info[self.random_galar_dex]["model_folder"] if "model_folder" in json_all_info[self.random_galar_dex] else None
        self.is_shiny = random.random() < SHINY_CHANCE

        self.lvl_board = {
            "low": "game\\gui\\src\\sprites\\title_for_low_lvl_pokemons.png",
            "average": "game\\gui\\src\\sprites\\title_for_avarage_lvl_pokemons.png",
            "high": "game\\gui\\src\\sprites\\title_for_high_lvl_pokemons.png",
        }

        # POSITION DATA
        self.start_position = (random.randint(-80, 80), random.randint(-80, 80), 0)

        self.sdk_pokemon = None
        self.anim_ctrl = None
        self.animated_character = self._load_model()
        self.animated_character.reparentTo(self.show_base.render)

        self.name_container = None
        self._ground_circle = None
        self._sparkle_task_name = None
        self._next_sparkle_time = 0
        
        self.setup_capture_collision()

        self.show_base.taskMgr.add(self.collision_with_player_task, "collision_with_player_task", extraArgs=[self.show_base.render.find("**/playerControl")], appendTask=True)

    def setup_capture_collision(self):
        col_node = CollisionNode(f'pokemon_capture_{id(self)}')
        self.capture_col_np = self.animated_character.attachNewNode(col_node)
        
        bounds = self.animated_character.getTightBounds()
        if bounds:
            bmin, bmax = bounds
            center_z = (bmin.z + bmax.z) / 2.0 + 1.0
            radius = max((bmax - bmin).length() / 2.0 * 0.85, 2.5)
            solid = CollisionSphere(0, 0, center_z, radius)
        else:
            solid = CollisionSphere(0, 0, 3.0, 3.5)
        
        col_node.addSolid(solid)


    def _load_model(self):
        model_dir = os.path.join(_MODELS_BASE, self.model_folder)
        self.sdk_pokemon = SDKPokemon(
            self.show_base, model_dir,
            use_shiny=self.is_shiny, auto_center=False)
        self.anim_ctrl = AnimationController(
            self.show_base, self.sdk_pokemon, auto_idle=True)
        return self.sdk_pokemon.actor

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
            footprint = max(abs(bmax.getX() - bmin.getX()),
                            abs(bmax.getY() - bmin.getY()),
                            abs(bmax.getZ() - bmin.getZ()))
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
            self.show_base.taskMgr.add(self._shiny_sparkle_task, self._sparkle_task_name)
            
    def collision_with_player_task(self, player_node, task):
        if self.captured or self.is_capturing:
            return task.cont

        pokemon_pos = self.animated_character.getPos()
        player_pos  = player_node.getPos()
        distance = (pokemon_pos - player_pos).length()

        if distance < 8.0 and distance > 0.001:
            print(f"Starting capture with {self.name}!")
            self.is_capturing = True
            CapturePokemon(self.show_base, player_node, self)   

        return task.cont

    def update_name_tag_task(self, task):
        if self.name_container:
            char_pos = self.animated_character.getPos(self.show_base.render)
            self.name_container.setPos(char_pos + Point3(0, 0, 4.8))
        return task.cont

    def get_info(self):
        return {
            "id_pokemon": self.id_pokemon,
            "lvl": self.lvl,
            "name": self.name,
            "type": getattr(self, 'type_', self.type),
            "height": self.height,
            "weight": self.weight,
            "abilities": self.abilities,
            "base_experience": self.base_experience,
            "level_evolution": self.level_evolution,
            "description": self.description,
            "animation_path": self.animation_path,
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
        if hasattr(self, 'capture_col_np'):
            self.capture_col_np.removeNode()