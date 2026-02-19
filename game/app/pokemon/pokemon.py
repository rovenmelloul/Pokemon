import json
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from panda3d.core import (
    Point3, VBase3, TextNode, BillboardEffect,
    AmbientLight, DirectionalLight, VBase4, NodePath,
    CardMaker, TextureStage, TransparencyAttrib, 
)
import math
import random

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
        
        
        #POKEMON DATA 
        self.id_pokemon = kwargs.get("id_pokemon", None)        
        self.lvl = kwargs.get("lvl", None)
         
        self.random_galar_dex = random.randint(1, 397) - 1
        self.name = json_all_info[self.random_galar_dex]["name"]
         
        self.type = json_all_info[self.random_galar_dex]["pokemon_data_from_api"]["type"] if "pokemon_data_from_api" in json_all_info[self.random_galar_dex] and "type" in json_all_info[self.random_galar_dex]["pokemon_data_from_api"] else None
        
        self.height = kwargs.get("height", None)
        self.weight = kwargs.get("weight", None)
        self.abilities = kwargs.get("abilities", None)
        self.base_experience = kwargs.get("base_experience", None)
        self.level_evolution = kwargs.get("level_evolution", None)
        self.description = kwargs.get("description", None)
        
        # ------------ ANIMATION DATA -------------
        self.model_folder = json_all_info[self.random_galar_dex]["model_folder"] if "model_folder" in json_all_info[self.random_galar_dex] else None
        self.anims = {
            "idle":   f"models/pokemon/{self.model_folder}/anims/{self.model_folder}_fi20_walk01.egg",
            "attack": f"models/pokemon/{self.model_folder}/anims/{self.model_folder}_ba01_landA01.egg",
        }
        
        self.lvl_board = {
            "low": "game\\gui\\src\\sprites\\title_for_low_lvl_pokemons.png",
            "average": "game\\gui\\src\\sprites\\title_for_avarage_lvl_pokemons.png",
            "high": "game\\gui\\src\\sprites\\title_for_high_lvl_pokemons.png",
        }
        
        # ------------ POSITION DATA -------------
        self.start_position = (random.randint(-5000, 5000), random.randint(-5000, 5000), 0)
        self.animated_character = self._load_model()
        self.animated_character.reparentTo(self.show_base.render)

        self.velocity = Point3(0)
        self.next_change_time = 0
        self.is_moving = False
        self.name_container = None
        # ------------ POSITION DATA -------------
    def _load_model(self):
        actor = Actor(f"models/pokemon/{self.model_folder}/{self.model_folder}.egg", self.anims)
        actor.pose("idle", 0)
        return actor

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

        self.velocity = Point3(0)
        self.next_change_time = 0
        self.is_moving = False
        self.animated_character.pose("idle", 0)

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

        # Text
        text_node = TextNode('name_text')
        full_text = self.name
        if self.lvl is not None:
            full_text += f"\nLv.{self.lvl}"
        if hasattr(self, 'type_') and self.type_:
            full_text += f" ({self.type_})"

        text_node.setText(full_text)
        text_node.setAlign(TextNode.ACenter)
        text_node.setTextColor(1, 1, 1, 1)

        text_np = self.name_container.attachNewNode(text_node)
        text_np.setPos(0, 0, 0)

        # Sprite right of text
        badge_tex = self.show_base.loader.loadTexture(badge_path)
        if badge_tex:
            cm = CardMaker("badge")
            cm.setFrame(-0.8, 0.8, -0.8, 0.8)
            badge_np = self.name_container.attachNewNode(cm.generate())
            badge_np.setTexture(badge_tex)
            badge_np.setTransparency(TransparencyAttrib.MAlpha)
            badge_np.setPos(-5.0, 0, 0)          
            badge_np.setScale(2.3)            

        self.show_base.taskMgr.add(self.move_randomly_task, "move_randomly_task")
        self.show_base.taskMgr.add(self.update_name_tag_task, "update_name_tag_task")

    def update_name_tag_task(self, task):
        if self.name_container:
            char_pos = self.animated_character.getPos(self.show_base.render)
            self.name_container.setPos(char_pos + Point3(0, 0, 4.8))
        return task.cont

    def move_randomly_task(self, task):
        dt = globalClock.getDt()
        pos = self.animated_character.getPos()

        new_pos = Point3(pos + self.velocity * dt)

        bounds = 100.0
        if new_pos.x < -bounds:
            self.velocity.x = -self.velocity.x
            new_pos.x = -bounds + 5
        elif new_pos.x > bounds:
            self.velocity.x = -self.velocity.x
            new_pos.x = bounds - 5

        if new_pos.y < -bounds:
            self.velocity.y = -self.velocity.y
            new_pos.y = -bounds + 5
        elif new_pos.y > bounds:
            self.velocity.y = -self.velocity.y
            new_pos.y = bounds - 5

        self.animated_character.setPos(new_pos)

        speed = self.velocity.length()
        if speed > 0.01:
            angle = math.degrees(math.atan2(self.velocity.y, self.velocity.x))
            self.animated_character.setH(angle)
            if not self.is_moving:
                self.animated_character.loop("idle")
                self.is_moving = True
        else:
            if self.is_moving:
                self.animated_character.pose("happy", 0)
                self.is_moving = False

        if task.time >= self.next_change_time:
            if random.random() < 0.35:
                self.velocity = Point3(0)
            else:
                angle = random.uniform(0, 360)
                speed = random.uniform(0.5, 1.4)
                self.velocity = Point3(
                    speed * math.cos(math.radians(angle)),
                    speed * math.sin(math.radians(angle)),
                    0
                )
            self.next_change_time = task.time + random.uniform(1.0, 3.0)

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

