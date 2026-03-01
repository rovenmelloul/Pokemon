"""
Capture3D -- Systeme de capture par drag de pokeball depuis l'exploration.
Pokemon teleporte devant la camera, capture auto 100% a la collision.
"""
from direct.task import Task
from panda3d.core import (
    Point3, Vec3, CollisionNode, CollisionSphere,
    CollisionHandlerQueue, CollisionTraverser,
)
from direct.interval.IntervalGlobal import (
    Sequence, Parallel, Func, Wait,
    LerpPosInterval, LerpHprInterval, LerpScaleInterval,
)
from direct.gui.OnscreenText import OnscreenText


class Capture3D:
    """Capture 3D depuis l'exploration: drag pokeball vers un Pokemon."""

    GRAVITY = -35.0

    def __init__(self, app, enemy_actor, enemy_pokemon, on_result):
        self.app = app
        self.enemy_actor = enemy_actor
        self.enemy_pokemon = enemy_pokemon
        self.on_result = on_result

        self.pokeball = None
        self.ball_col_np = None
        self.ball_velocity = Vec3(0, 0, 0)
        self.is_dragging = False
        self.start_mouse_pos = (0, 0)

        self.c_trav = CollisionTraverser()
        self.handler = CollisionHandlerQueue()

        self.success_text = None
        self._hint_text = None
        self._active = False

        # Positions sauvegardees
        self._saved_enemy_pos = None
        self._saved_enemy_hpr = None
        self._saved_enemy_scale = None

    def start(self):
        """Demarre la sequence de capture."""
        self._active = True

        # Sauvegarder position/rotation/scale originales du pokemon
        self._saved_enemy_pos = self.enemy_actor.getPos(self.app.render)
        self._saved_enemy_hpr = self.enemy_actor.getHpr(self.app.render)
        self._saved_enemy_scale = self.enemy_actor.getScale()

        # Teleporter le pokemon devant la camera (position fixe)
        self.enemy_actor.setPos(0, 25, 0)
        self.enemy_actor.setHpr(180, 0, 0)

        # Camera fixe derriere le joueur
        self.app.camera.reparentTo(self.app.render)
        self.app.camera.setPos(0, -15, 8)
        self.app.camera.lookAt(self.enemy_actor)

        # Creer la pokeball
        self._create_pokeball()

        # Activer les inputs
        self.app.accept("mouse1", self._on_click)
        self.app.accept("mouse1-up", self._on_release)

        # Task camera qui suit le pokemon
        self.app.taskMgr.add(self._camera_task, "capture_camera_task")

        # Hint
        self._hint_text = OnscreenText(
            text="Glissez vers le haut pour lancer !",
            style=1, fg=(1, 1, 1, 1), scale=0.06,
            pos=(0, -0.85), shadow=(0, 0, 0, 0.6),
        )

    def _camera_task(self, task):
        """Camera fixe qui regarde le pokemon."""
        if not self._active:
            return Task.done
        desired_pos = Point3(0, -15, 8)
        cur = self.app.camera.getPos()
        self.app.camera.setPos(cur + (desired_pos - cur) * 0.1)
        self.app.camera.lookAt(self.enemy_actor)
        return Task.cont

    def _create_pokeball(self):
        """Cree la pokeball avec le vrai modele."""
        self.pokeball = self.app.loader.loadModel("models/pokeball/pokeball.egg")
        self.pokeball.reparentTo(self.app.render)
        self.pokeball.setScale(0.012)

        c_node = CollisionNode("pokeball_capture")
        c_node.addSolid(CollisionSphere(0, 0, 0, 1.1))
        self.ball_col_np = self.pokeball.attachNewNode(c_node)
        self.c_trav.addCollider(self.ball_col_np, self.handler)

        # Collision sphere sur l'ennemi
        enemy_col = self.enemy_actor.find("**/pokemon_capture_col")
        if not enemy_col or enemy_col.isEmpty():
            col_node = CollisionNode("pokemon_capture_col")
            col_node.addSolid(CollisionSphere(0, 0, 1.5, 2.5))
            self.enemy_actor.attachNewNode(col_node)

        self._place_pokeball()

    def _place_pokeball(self):
        """Place la pokeball devant la camera."""
        self.pokeball.setPos(self.app.camera, 0, 5.8, -4.4)
        self.pokeball.setQuat(self.app.camera.getQuat())

    def _reset_ball(self):
        """Reset la ball devant la camera."""
        self.app.taskMgr.remove("capture_ball_physics")
        self._place_pokeball()
        self.ball_velocity = Vec3(0, 0, 0)

    def _on_click(self):
        if not self._active:
            return
        if self.app.mouseWatcherNode.hasMouse():
            mouse_pos = self.app.mouseWatcherNode.getMouse()
            self.start_mouse_pos = (mouse_pos.getX(), mouse_pos.getY())
            self.is_dragging = True

    def _on_release(self):
        if not self._active or not self.is_dragging:
            self.is_dragging = False
            return
        if not self.app.mouseWatcherNode.hasMouse():
            self.is_dragging = False
            return

        end_pos = self.app.mouseWatcherNode.getMouse()
        dx = end_pos.getX() - self.start_mouse_pos[0]
        dy = end_pos.getY() - self.start_mouse_pos[1]

        if dy > 0.045:
            local_vel = Vec3(dx * 42, 48 + dy * 28, dy * 58)
            cam_quat = self.app.camera.getQuat(self.app.render)
            self.ball_velocity = cam_quat.xform(local_vel)
            self.app.taskMgr.add(self._physics_task, "capture_ball_physics")
        self.is_dragging = False

    def _physics_task(self, task):
        dt = globalClock.getDt()
        self.ball_velocity.setZ(self.ball_velocity.getZ() + self.GRAVITY * dt)
        self.pokeball.setPos(self.pokeball.getPos() + self.ball_velocity * dt)

        # Check collisions
        self.c_trav.traverse(self.app.render)
        for entry in self.handler.getEntries():
            into_path = entry.getIntoNodePath()
            ancestors = into_path.getAncestors()
            for anc in ancestors:
                if anc == self.enemy_actor:
                    self._on_ball_hit()
                    return Task.done

        # Ball hors limites -> reset
        if self.pokeball.getZ() < -2 or self.pokeball.getY() > 100:
            self._reset_ball()
            return Task.done

        return Task.cont

    def _on_ball_hit(self):
        """Ball touche le Pokemon -> capture automatique."""
        self.app.taskMgr.remove("capture_ball_physics")
        self.app.taskMgr.remove("capture_camera_task")
        self.app.ignore("mouse1")
        self.app.ignore("mouse1-up")

        target_pos = self.enemy_actor.getPos(self.app.render)

        capture_seq = Sequence(
            # Ball vole vers le pokemon
            LerpPosInterval(self.pokeball, 0.25, target_pos + Point3(0, 0, 2)),
            # Pokemon retrecit et disparait
            Parallel(
                LerpScaleInterval(self.enemy_actor, 0.4, 0.01),
                Func(lambda: self.enemy_actor.hide()),
            ),
            # Ball tombe au sol
            LerpPosInterval(
                self.pokeball, 0.15,
                Point3(target_pos.getX(), target_pos.getY(), 0.6),
            ),
            # Secousses
            Func(self._shake_ball),
            Wait(1.2),
            # Succes !
            Func(self._show_success),
            Wait(2.0),
            Func(lambda: self._finish(True)),
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
            LerpHprInterval(self.pokeball, 0.1, Vec3(0, 0, 0)),
        )
        shake.start()

    def _show_success(self):
        name = self.enemy_pokemon.name
        self.success_text = OnscreenText(
            text=f"GOTCHA !\n{name} est capture !",
            style=1, fg=(1, 0.9, 0.2, 1), scale=0.12,
            pos=(0, 0.6), shadow=(0, 0, 0, 0.6),
        )

    def _finish(self, success):
        self._active = False
        if self.on_result:
            self.on_result(success)

    def cleanup(self):
        """Nettoie tout."""
        self._active = False

        self.app.taskMgr.remove("capture_ball_physics")
        self.app.taskMgr.remove("capture_camera_task")
        self.app.ignore("mouse1")
        self.app.ignore("mouse1-up")

        if self.pokeball:
            self.pokeball.removeNode()
            self.pokeball = None

        # Remove capture collision from enemy
        if self.enemy_actor and not self.enemy_actor.isEmpty():
            col = self.enemy_actor.find("**/pokemon_capture_col")
            if col and not col.isEmpty():
                col.removeNode()

        if self.success_text:
            self.success_text.destroy()
            self.success_text = None

        if self._hint_text:
            self._hint_text.destroy()
            self._hint_text = None

        self.c_trav = None
        self.handler = None
