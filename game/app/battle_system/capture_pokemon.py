from direct.task import Task
from panda3d.core import Point3, Vec3, CollisionNode, CollisionSphere, CollisionHandlerQueue, CollisionTraverser
from direct.interval.IntervalGlobal import Sequence, LerpPosInterval, LerpHprInterval, Wait, Func

class CapturePokemon:
    def __init__(self, game, player, enemy_pokemon):
        self.game = game                
        self.player = player             
        self.enemy_pokemon = enemy_pokemon
        
        self.in_battle = True
        self.is_dragging = False
        self.pokeball = None
        
        self.saved_cam_pos = self.game.camera.getPos()
        self.saved_cam_hpr = self.game.camera.getHpr()

        self.gravity = -35.0
        self.ball_velocity = Vec3(0, 0, 0)
        self.c_trav = CollisionTraverser()
        self.handler = CollisionHandlerQueue()
        

        self.start_capture_pokemon()
        self.setup_input()

    def stop_pokemon(self):
        self.game.taskMgr.remove("move_randomly_task")
        self.game.taskMgr.remove("update_task")
        self.game.taskMgr.remove("mouse_rotation_task")

    def setup_input(self):
        self.game.accept("mouse1", self.on_click)
        self.game.accept("mouse1-up", self.on_release)

    def create_pokeball(self):
        self.pokeball = self.game.loader.loadModel("models/misc/sphere")
        self.pokeball.reparentTo(self.game.render)
        self.pokeball.setScale(0.6)
        self.pokeball.setColor(1, 0.2, 0.2, 1)
        

        c_node = CollisionNode('pokeball')
        c_node.addSolid(CollisionSphere(0, 0, 0, 1.1))
        self.ball_col_np = self.pokeball.attachNewNode(c_node)
        self.c_trav.addCollider(self.ball_col_np, self.handler)
        
        self.reset_ball()

    def reset_ball(self):
        self.game.taskMgr.remove("ball_physics")
        self.pokeball.setPos(self.game.camera, 0, 8, -3)
        self.ball_velocity = Vec3(0, 0, 0)
        
    def place_pokeball(self):
        #by vector forward of camera .getQuat().getForward()
        self.pokeball.setPos(self.game.camera, 0, 8, -3)

    def on_click(self):
            if self.game.mouseWatcherNode.hasMouse():
                mouse_pos = self.game.mouseWatcherNode.getMouse()
                self.start_mouse_pos = (mouse_pos.getX(), mouse_pos.getY())
                self.is_dragging = True

    def on_release(self):
        if self.is_dragging and self.game.mouseWatcherNode.hasMouse():
            end_pos = self.game.mouseWatcherNode.getMouse()
            
            dx = end_pos.getX() - self.start_mouse_pos[0]
            dy = end_pos.getY() - self.start_mouse_pos[1]
            
            if dy > 0.05: 
                self.ball_velocity = Vec3(dx * 45, dy * 55, dy * 35)
                self.game.taskMgr.add(self.physics_task, "ball_physics")
            
            self.is_dragging = False

    def physics_task(self, task):
        dt = globalClock.getDt()
        self.ball_velocity.setZ(self.ball_velocity.getZ() + self.gravity * dt)
        self.pokeball.setPos(self.pokeball.getPos() + self.ball_velocity * dt)

        self.c_trav.traverse(self.game.render)
        for entry in self.handler.getEntries():
            if self.enemy_pokemon.animated_character in entry.getIntoNodePath().getAncestors():
                self.start_capture_animation()
                return Task.done

        if self.pokeball.getZ() < -2 or self.pokeball.getY() > 100:
            self.reset_ball()
            return Task.done
        return Task.cont

    def start_capture_animation(self):
        self.game.taskMgr.remove("ball_physics")
        
        target_pos = self.enemy_pokemon.animated_character.getPos()
        

        capture_seq = Sequence(
            LerpPosInterval(self.pokeball, 0.2, target_pos),
            Func(self.enemy_pokemon.animated_character.hide),
            LerpPosInterval(self.pokeball, 0.3, Point3(target_pos.getX(), target_pos.getY(), 0)),
            LerpHprInterval(self.pokeball, 0.2, Vec3(0, 0, 20)),
            LerpHprInterval(self.pokeball, 0.2, Vec3(0, 0, -20)),
            Wait(0.5),
            Func(self.finish_capture)
        )
        capture_seq.start()

    def finish_capture(self):
        self.end_battle()

    def start_capture_pokemon(self):
        self.stop_pokemon()
        self.create_pokeball()
        self.enemy_pokemon.animated_character.setPos(0, 25, 0)
        self.enemy_pokemon.animated_character.loop("wait")
        
        self.game.taskMgr.add(self.camera_battle_task, "battle_camera_task")

    def camera_battle_task(self, task):
        if not self.in_battle: return Task.done
        desired_pos = Point3(0, -15, 8)
        self.game.camera.setPos(self.game.camera.getPos() + (desired_pos - self.game.camera.getPos()) * 0.1)
        self.game.camera.lookAt(self.enemy_pokemon.animated_character)
        return Task.cont

    def end_battle(self):
        self.in_battle = False
        self.game.taskMgr.remove("battle_camera_task")
        self.game.camera.setPos(self.saved_cam_pos)
        self.game.camera.setHpr(self.saved_cam_hpr)
        if self.pokeball: self.pokeball.removeNode()