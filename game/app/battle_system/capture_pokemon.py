from direct.task import Task
from panda3d.core import Point3, Vec3, CollisionNode, CollisionSphere, CollisionHandlerQueue, CollisionTraverser
from direct.interval.IntervalGlobal import Sequence, Parallel, LerpPosInterval, LerpHprInterval, LerpScaleInterval, Wait, Func, LerpPosHprInterval
from direct.gui.OnscreenText import OnscreenText


class CapturePokemon:
    def __init__(self, game, player_param, enemy_pokemon):
        self.game = game
        self.enemy_pokemon = enemy_pokemon

        # Automatically detect whether we received the full Player object or just a NodePath
        if hasattr(player_param, 'control_node') and hasattr(player_param, 'restore_camera_and_controls'):
            self.player = player_param         
        else:
            self.player = getattr(game, 'player', None)  

        if not self.player or not hasattr(self.player, 'control_node'):
            raise RuntimeError("Could not find Player object! Check main.py")

        self.in_battle = True
        self.is_dragging = False
        self.pokeball = None

        # Save camera position relative to the player's control_node
        self.saved_cam_local_pos = self.game.camera.getPos(self.player.control_node)
        self.saved_cam_local_hpr = self.game.camera.getHpr(self.player.control_node)

        self.gravity = -35.0
        self.ball_velocity = Vec3(0, 0, 0)

        self.c_trav = CollisionTraverser()
        self.handler = CollisionHandlerQueue()

        self.success_text = None

        self.start_capture_pokemon()
        self.setup_input()
        
    def stop_pokemon(self):
        self.game.taskMgr.remove("move_randomly_task")
        self.game.taskMgr.remove("update_task")
        self.game.taskMgr.remove("mouse_rotation_task")

    def restore_normal_game_state(self):
        self.in_battle = False

        self.game.taskMgr.remove("battle_camera_task")
        self.game.taskMgr.remove("ball_physics")
        self.game.ignore("mouse1")
        self.game.ignore("mouse1-up")

        # Smooth camera return (relative to control_node)
        restore_seq = Sequence(
            LerpPosHprInterval(
                self.game.camera,
                duration=1.2,
                pos=self.saved_cam_local_pos,
                hpr=self.saved_cam_local_hpr,
                blendType="easeOut"
            ),
            Func(self._finish_restore)
        )
        restore_seq.start()

        if self.pokeball:
            self.pokeball.removeNode()

        if self.enemy_pokemon:
            self.enemy_pokemon.captured = True
            self.enemy_pokemon.destroy()

        if self.success_text:
            self.game.taskMgr.doMethodLater(3.0, lambda t: self.success_text.destroy(), "remove_success_text")

        print("Pokémon caught! Restoring game state...")

    def _finish_restore(self):
        """Final restoration of player controls"""
        self.player.restore_camera_and_controls()
        print("Game fully restored - you can now run and catch more Pokémon!")

    # ==================== ALL OTHER METHODS REMAIN UNCHANGED ====================

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

    def place_pokeball(self):
        self.pokeball.setPos(self.game.camera, 0, 5.8, -4.4)
        self.pokeball.setQuat(self.game.camera.getQuat())

    def reset_ball(self):
        self.game.taskMgr.remove("ball_physics")
        self.place_pokeball()
        self.ball_velocity = Vec3(0, 0, 0)

    def on_click(self):
        if self.game.mouseWatcherNode.hasMouse():
            mouse_pos = self.game.mouseWatcherNode.getMouse()
            self.start_mouse_pos = (mouse_pos.getX(), mouse_pos.getY())
            self.is_dragging = True

    def on_release(self):
        if not (self.is_dragging and self.game.mouseWatcherNode.hasMouse()):
            self.is_dragging = False
            return

        end_pos = self.game.mouseWatcherNode.getMouse()
        dx = end_pos.getX() - self.start_mouse_pos[0]
        dy = end_pos.getY() - self.start_mouse_pos[1]

        if dy > 0.045:
            local_vel = Vec3(dx * 42, 48 + dy * 28, dy * 58)
            cam_quat = self.game.camera.getQuat(self.game.render)
            self.ball_velocity = cam_quat.xform(local_vel)
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
        target_pos = self.enemy_pokemon.animated_character.getPos(self.game.render)

        capture_seq = Sequence(
            LerpPosInterval(self.pokeball, 0.25, target_pos + Point3(0, 0, 2)),
            Parallel(
                LerpScaleInterval(self.enemy_pokemon.animated_character, 0.4, 0.01),
                Func(self.enemy_pokemon.animated_character.hide)
            ),
            LerpPosInterval(self.pokeball, 0.15, Point3(target_pos.getX(), target_pos.getY(), 0.6)),
            Func(self._shake_ball),
            Wait(1.2),
            Func(self._show_success),
            Wait(2.0),
            Func(self.restore_normal_game_state)
        )
        capture_seq.start()

    def _shake_ball(self):
        shake = Sequence(
            LerpHprInterval(self.pokeball, 0.08, Vec3(0, 0, 25)),
            LerpHprInterval(self.pokeball, 0.08, Vec3(0, 0, -25)),
            LerpHprInterval(self.pokeball, 0.08, Vec3(0, 0, 25)),
            LerpHprInterval(self.pokeball, 0.08, Vec3(0, 0, -25)),
            LerpHprInterval(self.pokeball, 0.08, Vec3(0, 0, 15)),
            LerpHprInterval(self.pokeball, 0.08, Vec3(0, 0, -15)),
            LerpHprInterval(self.pokeball, 0.1, Vec3(0, 0, 0))
        )
        shake.start()

    def _show_success(self):
        name = self.enemy_pokemon.name
        self.success_text = OnscreenText(
            text=f"GOTCHA!\n{name} was caught!",
            style=1,
            fg=(1, 0.9, 0.2, 1),
            scale=0.12,
            pos=(0, 0.6),
            shadow=(0, 0, 0, 0.6)
        )

    def start_capture_pokemon(self):
        self.stop_pokemon()
        self.create_pokeball()
        self.enemy_pokemon.animated_character.setPos(0, 25, 0)
        self.enemy_pokemon.animated_character.loop("wait")
        self.game.taskMgr.add(self.camera_battle_task, "battle_camera_task")

    def camera_battle_task(self, task):
        if not self.in_battle:
            return Task.done
        desired_pos = Point3(0, -15, 8)
        self.game.camera.setPos(self.game.camera.getPos() + (desired_pos - self.game.camera.getPos()) * 0.1)
        self.game.camera.lookAt(self.enemy_pokemon.animated_character)
        return Task.cont