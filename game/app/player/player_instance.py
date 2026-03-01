import os
import math
from pathlib import Path

from .movement import PlayerMove
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from panda3d.core import Point3, VBase3, MouseButton

from sdk import Pokemon as SDKPokemon
from sdk import AnimationController

_MODELS_BASE = str(Path(os.path.dirname(__file__), '..', '..', '..', 'models', 'pokemon').resolve())

class Player(PlayerMove, ShowBase):
    def __init__(self, show_base: ShowBase):
        self.show_base = show_base
        PlayerMove.__init__(self)

        self.start_position = (0, 0, 0)

        self.sdk_pokemon = None
        self.anim_ctrl = None
        self.animated_character = self._load_model()

        self.key_map = {"forward": False, "backward": False, "left": False, "right": False}
        self.speed = 40

        self.control_node = self.show_base.render.attachNewNode("playerControl")

        self.animated_character.reparentTo(self.control_node)
        self.animated_character.setScale(0.05)
        self.animated_character.setPos(0, 0, 0)
        self.animated_character.setH(180)

        # Camera orbit
        self.heading = 0
        self.pitch = -45
        self.cam_dist = 22
        self.cam_dist_min = 8
        self.cam_dist_max = 80
        self._last_mouse = None

        self.show_base.camera.reparentTo(self.control_node)
        self._update_camera_orbit()

        self.show_base.disableMouse()

        self.show_base.taskMgr.add(self.update_camera_and_movement, "update_task")
        self.show_base.taskMgr.add(self.mouse_rotation_task, "mouse_rotation_task")

    def _update_camera_orbit(self):
        pitch_rad = math.radians(-self.pitch)
        cy = -self.cam_dist * math.cos(pitch_rad)
        cz = self.cam_dist * math.sin(pitch_rad)
        self.show_base.camera.setPos(0, cy, max(cz, 1.5))
        self.show_base.camera.lookAt(self.control_node, Point3(0, 0, 1.5))

    def _zoom(self, direction):
        self.cam_dist += direction * 3
        self.cam_dist = max(self.cam_dist_min, min(self.cam_dist_max, self.cam_dist))
        self._update_camera_orbit()

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
        mw = self.show_base.mouseWatcherNode
        if not mw.hasMouse():
            self._last_mouse = None
            return task.cont

        mx = mw.getMouseX()
        my = mw.getMouseY()

        if mw.isButtonDown(MouseButton.three()):
            if self._last_mouse is not None:
                dx = mx - self._last_mouse[0]
                dy = my - self._last_mouse[1]

                sensitivity = 500
                self.heading -= dx * sensitivity
                self.pitch -= dy * sensitivity * 0.7
                self.pitch = max(-85, min(-5, self.pitch))

                self.control_node.setH(self.heading)
                self._update_camera_orbit()

            self._last_mouse = (mx, my)
        else:
            self._last_mouse = None

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
        if moving:
            walk = self.anim_ctrl.find_anim("fi20", "walk")
            if walk and self.anim_ctrl.current_anim != walk:
                self.anim_ctrl.play(walk, loop=True)
        else:
            idle = self.anim_ctrl.find_idle()
            if idle and self.anim_ctrl.current_anim != idle:
                self.anim_ctrl.play(idle, loop=True)

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

        # Zoom
        self.show_base.accept("wheel_up", self._zoom, [-1])
        self.show_base.accept("wheel_down", self._zoom, [1])

    def set_key(self, key, value):
        self.key_map[key] = value
