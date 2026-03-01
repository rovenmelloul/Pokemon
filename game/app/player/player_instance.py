import os
import math
from pathlib import Path

from .movement import PlayerMove
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from panda3d.core import Point3, VBase3, KeyboardButton, MouseWatcher

from ..battle_system import CapturePokemon

from sdk import Pokemon as SDKPokemon
from sdk import AnimationController

# Absolute path to models/pokemon/ (one level above game/)
# Path.resolve() returns the true on-disk casing on Windows, which Panda3D requires.
_MODELS_BASE = str(Path(os.path.dirname(__file__), '..', '..', '..', 'models', 'pokemon').resolve())

class Player(PlayerMove, ShowBase):
    def __init__(self, show_base: ShowBase):
        self.show_base = show_base
        PlayerMove.__init__(self)

        self.start_position = (-8, 42, 0)

        self.sdk_pokemon = None
        self.anim_ctrl = None
        self.animated_character = self._load_model()

        self.key_map = {"forward": False, "backward": False, "left": False, "right": False, "attack": False}
        self.speed = 40
        self.turn_speed = 120

        self.control_node = self.show_base.render.attachNewNode("playerControl")

        self.animated_character.reparentTo(self.control_node)
        self.animated_character.setScale(0.05)
        self.animated_character.setPos(0, 0, 0)
        self.animated_character.setH(180)

        self.show_base.camera.reparentTo(self.control_node)
        self.show_base.camera.setPos(0, -12, 6)
        self.show_base.camera.lookAt(self.animated_character)

        self.show_base.disableMouse()

        self.heading = 0
        self.pitch = -15

        self.show_base.taskMgr.add(self.update_camera_and_movement, "update_task")
        self.show_base.taskMgr.add(self.mouse_rotation_task, "mouse_rotation_task")

    def _load_model(self):
        model_dir = os.path.join(_MODELS_BASE, "pm0001_00")
        self.sdk_pokemon = SDKPokemon(
            self.show_base, model_dir,
            use_shiny=False, auto_center=False)
        self.anim_ctrl = AnimationController(
            self.show_base, self.sdk_pokemon, auto_idle=True)
        return self.sdk_pokemon.actor

    def spawn_self(self):
        self.control_node.setPos(self.start_position)

    def mouse_rotation_task(self, task):
        if self.show_base.mouseWatcherNode.hasMouse():
            mx = self.show_base.mouseWatcherNode.getMouseX()
            my = self.show_base.mouseWatcherNode.getMouseY()

            sensitivity = 80

            self.heading -= mx * sensitivity * globalClock.getDt()
            self.pitch -= my * sensitivity * 0.7 * globalClock.getDt()

            self.pitch = max(-60, min(-5, self.pitch))

            self.control_node.setH(self.heading)
            self.show_base.camera.setP(self.pitch)

        return task.cont

    def update_camera_and_movement(self, task):
        dt = globalClock.getDt()
        move_dir = VBase3(0, 0, 0)

        if self.key_map["forward"]:
            move_dir.y += 1
        if self.key_map["backward"]:
            move_dir.y -= 1
        if self.key_map["left"]:
            move_dir.x -= 1
        if self.key_map["right"]:
            move_dir.x += 1

        if move_dir.length() > 0:
            move_dir.normalize()

            angle = math.radians(self.control_node.getH())
            dx = move_dir.x * math.cos(angle) - move_dir.y * math.sin(angle)
            dy = move_dir.x * math.sin(angle) + move_dir.y * math.cos(angle)

            self.control_node.setX(self.control_node.getX() + dx * self.speed * dt)
            self.control_node.setY(self.control_node.getY() + dy * self.speed * dt)

        moving = any(self.key_map[k] for k in ("forward", "backward", "left", "right"))
        if self.key_map.get("attack"):
            atk = self.anim_ctrl.find_attack_anim("physical")
            if atk and self.anim_ctrl.current_anim != atk:
                self.anim_ctrl.play(atk, loop=False)
        elif moving:
            walk = self.anim_ctrl.find_anim("fi20", "walk")
            if walk and self.anim_ctrl.current_anim != walk:
                self.anim_ctrl.play(walk, loop=True)
        else:
            idle = self.anim_ctrl.find_idle()
            if idle and self.anim_ctrl.current_anim != idle:
                self.anim_ctrl.play(idle, loop=True)

        return task.cont
    
    def collision_with_player_task(self, player_node, task):
        pokemon_pos = self.animated_character.getPos()
        player_pos  = player_node.getPos()

        direction = pokemon_pos - player_pos
        distance = direction.length()

        if distance < 8.0 and distance > 0.001:   
            capture = CapturePokemon(self.show_base, self)
            return task.done

        return task.cont

    def key_bindings(self):
        self.show_base.accept("w", self.set_key, ["forward", True])
        self.show_base.accept("w-up", self.set_key, ["forward", False])
        self.show_base.accept("s", self.set_key, ["backward", True])
        self.show_base.accept("s-up", self.set_key, ["backward", False])
        self.show_base.accept("a", self.set_key, ["left", True])
        self.show_base.accept("a-up", self.set_key, ["left", False])
        self.show_base.accept("d", self.set_key, ["right", True])
        self.show_base.accept("d-up", self.set_key, ["right", False])
        self.show_base.accept("f", self.set_key, ["attack", True])
        self.show_base.accept("f-up", self.set_key, ["attack", False])

    def set_key(self, key, value):
        self.key_map[key] = value
    def restore_camera_and_controls(self):

        self.show_base.camera.reparentTo(self.control_node)

        self.show_base.camera.setPos(0, -12, 6)
        self.show_base.camera.setHpr(0, 0, 0)  
        self.show_base.taskMgr.add(self.mouse_rotation_task, "mouse_rotation_task")
        self.show_base.taskMgr.add(self.update_camera_and_movement, "update_task")
        
        self.show_base.enableMouse()  
        self.show_base.disableMouse() 
        