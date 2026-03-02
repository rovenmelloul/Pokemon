import os
import math
from pathlib import Path

from .movement import PlayerMove
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from panda3d.core import (
    Point3, VBase3, MouseButton, Filename,
    Texture, TextureStage, TransparencyAttrib,
)

_MODELS_BASE = str(Path(os.path.dirname(__file__), '..', '..', '..', 'models').resolve())

# Texture mapping: geom name substring -> texture file
_TEX_MAP = {
    'body': 'tr0050_00_body_col.png',
    'leg': 'tr0050_00_body_col.png',
    'dogi': 'tr0050_00_body_col.png',
    'backdogi': 'tr0050_00_body_col.png',
    'face': 'tr0050_00_face_col.png',
    'mouth': 'tr0050_00_face_col.png',
    'beard': 'tr0050_00_face_col.png',
    'facepart': 'tr0050_00_face_col.png',
    'angrypart': 'tr0050_00_face_col.png',
    'eyelash': 'tr0050_00_face_col.png',
    'eyeline': 'tr0050_00_face_col.png',
    'eye': 'tr0050_00_eye_col.png',
    'headband': 'tr0050_00_hair_col.png',
    'hair': 'tr0050_00_hair_col.png',
    'tooth': 'tr0050_00_face_col.png',
    'tongue': 'tr0050_00_face_col.png',
}


class Player(PlayerMove, ShowBase):
    def __init__(self, show_base: ShowBase):
        self.show_base = show_base
        PlayerMove.__init__(self)

        self.start_position = (0, 0, 0)

        self.sdk_pokemon = None
        self.anim_ctrl = None
        self.animated_character = self._load_model()
        self._current_anim = None
        self._anim_time = 0.0

        self.key_map = {"forward": False, "backward": False, "left": False, "right": False}
        self.speed = 40

        self.control_node = self.show_base.render.attachNewNode("playerControl")

        self.animated_character.reparentTo(self.control_node)
        self.animated_character.setScale(1.0)
        self.animated_character.setPos(0, 0, 0)
        # Y-up model from glTF: rotate -90 pitch to stand in Z-up, face forward
        self.animated_character.setHpr(180, -90, 0)

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

        # Setup procedural animation joints
        self._setup_joints()

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
        model_dir = os.path.join(_MODELS_BASE, "trainers", "black_belt")
        model_bam = Filename.fromOsSpecific(
            os.path.join(model_dir, "black_belt.bam")).getFullpath()

        actor = Actor(model_bam)

        # Apply textures manually (FBX2glTF didn't embed them)
        self._apply_textures(actor, model_dir)

        actor.setLightOff()
        return actor

    def _apply_textures(self, actor, model_dir):
        """Apply textures to GeomNodes based on name matching."""
        img_dir = os.path.join(model_dir, "images")
        tex_cache = {}

        for geom_np in actor.findAllMatches('**/+GeomNode'):
            name = geom_np.getName().lower()
            # Find matching texture
            tex_file = None
            # Check longer substrings first
            for substr in sorted(_TEX_MAP.keys(), key=len, reverse=True):
                if substr in name:
                    tex_file = _TEX_MAP[substr]
                    break

            if tex_file:
                if tex_file not in tex_cache:
                    tex_path = os.path.join(img_dir, tex_file)
                    if os.path.exists(tex_path):
                        tex = Texture()
                        tex.read(Filename.fromOsSpecific(tex_path))
                        tex.setMinfilter(Texture.FTLinearMipmapLinear)
                        tex.setMagfilter(Texture.FTLinear)
                        tex_cache[tex_file] = tex
                    else:
                        tex_cache[tex_file] = None

                tex = tex_cache.get(tex_file)
                if tex:
                    geom_np.setTexture(tex, 1)
                    if 'eyelash' in name or 'eyeline' in name:
                        geom_np.setTransparency(TransparencyAttrib.MAlpha)

    def _setup_joints(self):
        """Get control of joints for procedural animation."""
        a = self.animated_character
        self._j = {}
        joint_names = [
            'LThigh', 'LLeg', 'LFoot',
            'RThigh', 'RLeg', 'RFoot',
            'LArm', 'LForeArm',
            'RArm', 'RForeArm',
            'Spine1', 'Spine2', 'Waist', 'Hips',
        ]
        for name in joint_names:
            j = a.controlJoint(None, 'modelRoot', name)
            if j:
                self._j[name] = j

    def _animate_idle(self, dt):
        """Subtle breathing / swaying."""
        self._anim_time += dt
        t = self._anim_time

        if 'Spine2' in self._j:
            sway = math.sin(t * 1.5) * 1.0
            self._j['Spine2'].setR(sway * 0.5)
            self._j['Spine2'].setH(sway * 0.3)

        for arm, sign in [('LArm', 1), ('RArm', -1)]:
            if arm in self._j:
                sway = math.sin(t * 1.2 + sign * 0.5) * 1.5
                self._j[arm].setP(sway)

    def _animate_walk(self, dt):
        """Walking cycle."""
        self._anim_time += dt
        t = self._anim_time
        freq = 5.0
        phase = t * freq

        # Thigh swing
        thigh_amp = 25.0
        for thigh, sign in [('LThigh', 1), ('RThigh', -1)]:
            if thigh in self._j:
                swing = math.sin(phase) * thigh_amp * sign
                self._j[thigh].setP(swing)

        # Knee bend
        knee_amp = 30.0
        for leg, sign in [('LLeg', 1), ('RLeg', -1)]:
            if leg in self._j:
                raw = math.sin(phase) * sign
                bend = max(0, -raw) * knee_amp
                self._j[leg].setP(bend)

        # Arm swing (opposite to legs)
        arm_amp = 18.0
        for arm, sign in [('LArm', -1), ('RArm', 1)]:
            if arm in self._j:
                swing = math.sin(phase) * arm_amp * sign
                self._j[arm].setP(swing)

        # Forearm bend
        forearm_amp = 12.0
        for forearm, sign in [('LForeArm', -1), ('RForeArm', 1)]:
            if forearm in self._j:
                raw = math.sin(phase) * sign
                bend = max(0, raw) * forearm_amp
                self._j[forearm].setP(bend)

        # Subtle body bob via Hips
        if 'Hips' in self._j:
            bob = abs(math.sin(phase)) * 0.02
            self._j['Hips'].setPos(0, -bob, 0)

    def _reset_joints(self):
        """Reset all joints to rest pose."""
        for name, j in self._j.items():
            j.setPos(0, 0, 0)
            j.setHpr(0, 0, 0)

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
            self._animate_walk(dt)
            self._current_anim = "walking"
        else:
            if self._current_anim == "walking":
                self._reset_joints()
            self._animate_idle(dt)
            self._current_anim = "idle"

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
