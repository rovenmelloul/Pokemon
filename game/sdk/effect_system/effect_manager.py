"""Orchestrates waza effects: spawning, updating, cleanup."""
from panda3d.core import Point3

from .bone_resolver import BoneResolver
from .waza_catalog import WazaCatalog
from .effect_instance import EffectInstance


class EffectManager:
    """Manages waza effects in a Panda3D scene.

    Usage:
        mgr = EffectManager(base, output_dir)
        mgr.fire(catalog.get("ew058_at_beam"), origin, target, style="projectile")
    """

    def __init__(self, base, output_dir):
        self._base = base
        self._output_dir = output_dir
        self._bone_resolver = BoneResolver()
        self._catalog = WazaCatalog(output_dir)
        self._active = []
        self._task_name = "effect_manager_update"
        self._base.taskMgr.add(self._update, self._task_name)

    @property
    def catalog(self):
        return self._catalog

    @property
    def bone_resolver(self):
        return self._bone_resolver

    def fire(self, waza_entry, origin_pos, target_pos, style="projectile",
             scale=1.0, duration=1.0, color=None, spin=False,
             attacker_height=0.0, defender_height=0.0):
        """Fire a waza effect.

        Args:
            waza_entry: WazaEntry from catalog
            origin_pos: Point3 start position
            target_pos: Point3 target position
            style: "projectile", "contact", "self_buff", "ground", "orbit"
            scale: size multiplier
            duration: seconds
            color: optional (r,g,b,a)
            spin: rotate during travel
            attacker_height: attacker model height for proportional scaling
            defender_height: defender model height for proportional scaling

        Returns:
            EffectInstance or None
        """
        if waza_entry is None:
            return None

        inst = EffectInstance(waza_entry, self._base.loader, style=style)
        ok = inst.spawn(self._base.render, origin_pos, target_pos,
                        scale=scale, duration=duration, color=color,
                        spin=spin, attacker_height=attacker_height,
                        defender_height=defender_height)
        if ok:
            self._active.append(inst)
            return inst
        return None

    def fire_from_bones(self, waza_entry, attacker, defender,
                        origin_bone="EffShoot01_01", target_bone="EffCenter01",
                        style="projectile", scale=1.0, duration=1.0,
                        color=None, spin=False,
                        attacker_height=0.0, defender_height=0.0):
        """Fire using bone resolution on actors.

        Args:
            waza_entry: WazaEntry from catalog
            attacker: Actor or NodePath
            defender: Actor or NodePath
            origin_bone: bone name on attacker
            target_bone: bone name on defender
            attacker_height: attacker model height for proportional scaling
            defender_height: defender model height for proportional scaling
            + same as fire()
        """
        origin_np = self._bone_resolver.resolve(attacker, origin_bone)
        origin_pos = origin_np.getPos(self._base.render) if origin_np else Point3(0, 0, 0)

        target_np = self._bone_resolver.resolve(defender, target_bone)
        if target_np:
            target_pos = target_np.getPos(self._base.render)
        elif hasattr(defender, "getPos"):
            target_pos = defender.getPos(self._base.render)
        else:
            target_pos = Point3(15, 0, 0)

        return self.fire(waza_entry, origin_pos, target_pos,
                         style=style, scale=scale, duration=duration,
                         color=color, spin=spin,
                         attacker_height=attacker_height,
                         defender_height=defender_height)

    def _update(self, task):
        done = [e for e in self._active if e.is_done]
        for e in done:
            e.cleanup()
            self._active.remove(e)
        return task.cont

    def cleanup_all(self):
        for e in self._active:
            e.cleanup()
        self._active.clear()

    @property
    def active_count(self):
        return len(self._active)

    def on_actor_changed(self):
        self._bone_resolver.clear_cache()
        self.cleanup_all()

    def destroy(self):
        self.cleanup_all()
        self._base.taskMgr.remove(self._task_name)
