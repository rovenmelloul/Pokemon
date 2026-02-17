from .movement import PlayerMove
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from panda3d.core import Point3, VBase3, KeyboardButton, MouseWatcher
import math

class Player(PlayerMove, ShowBase):
    def __init__(self, show_base: ShowBase):
        self.show_base = show_base
        PlayerMove.__init__(self)
        
        self.start_position = (-8, 42, 0)
        self.scene = self.show_base.loader.loadModel("models/environment")
        
        self.anims = {
            "idle": "models/pm0001_00/anims/pm0001_00_fi20_walk01.egg",
            "attack": "models/pm0001_00/anims/pm0001_00_ba01_landA01.egg",
            "happy": "models/pm0001_00/anims/pm0001_00_kw32_happyA01.egg"
        }
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
        return Actor("models/pm0001_00/pm0001_00.egg", self.anims)

    def spawn_self(self):
        self.control_node.setPos(self.start_position)
        
        self.scene.reparentTo(self.show_base.render)
        self.scene.setScale(5)
        self.scene.setPos(-50, -50, -1)  

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
            if self.animated_character.getCurrentAnim() != "attack":
                self.animated_character.play("attack")
        elif moving:
            if self.animated_character.getCurrentAnim() != "idle":
                self.animated_character.loop("idle")
        else:
            self.animated_character.stop()

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