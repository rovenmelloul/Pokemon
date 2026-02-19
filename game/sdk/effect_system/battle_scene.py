"""Battle scene: loads attacker + defender Actors, plays attack animations."""
import os

from panda3d.core import Filename, Point3
from direct.actor.Actor import Actor


class BattleScene:
    """Manages a battle scene with attacker and defender Pokemon.

    Handles loading, positioning, idle animations, and attack animation
    triggering for both combatants.
    """

    # Default positions (y-up coordinate system)
    ATTACKER_POS = Point3(-20, 0, 0)
    DEFENDER_POS = Point3(35, 0, 0)

    def __init__(self, base):
        self._base = base
        self.attacker = None
        self.attacker_name = ""
        self.attacker_anims = []
        self.defender = None
        self.defender_name = ""
        self.defender_anims = []

    def load_pokemon(self, egg_path, role="attacker"):
        """Load a Pokemon Actor for the given role.

        Args:
            egg_path: path to the .egg model
            role: "attacker" or "defender"

        Returns:
            Actor or None
        """
        actor = self._load_actor(egg_path)
        if not actor:
            return None

        if role == "attacker":
            if self.attacker:
                self.attacker.cleanup()
                self.attacker.removeNode()
            self.attacker = actor
            self.attacker_name = os.path.basename(os.path.dirname(egg_path))
            self._position_actor(actor, self.ATTACKER_POS, face_right=True)
            self.attacker_anims = self._load_anims(actor, egg_path)
            self._play_idle(actor, self.attacker_anims)
            print(f"[BATTLE] Attacker: {self.attacker_name} "
                  f"({len(self.attacker_anims)} anims)")
        else:
            if self.defender:
                self.defender.cleanup()
                self.defender.removeNode()
            self.defender = actor
            self.defender_name = os.path.basename(os.path.dirname(egg_path))
            self._position_actor(actor, self.DEFENDER_POS, face_right=False)
            self.defender_anims = self._load_anims(actor, egg_path)
            self._play_idle(actor, self.defender_anims)
            print(f"[BATTLE] Defender: {self.defender_name} "
                  f"({len(self.defender_anims)} anims)")

        return actor

    def _load_actor(self, egg_path):
        try:
            actor = Actor(Filename.fromOsSpecific(egg_path))
            if actor.isEmpty():
                return None
            actor.reparentTo(self._base.render)
            actor.setTwoSided(True)
            return actor
        except Exception as e:
            print(f"[BATTLE] Load error: {e}")
            return None

    # Target height for normalized Pokemon in battle
    TARGET_HEIGHT = 15.0

    def _position_actor(self, actor, pos, face_right=True):
        """Center, scale to standard height, and place the actor at pos."""
        # Normalize size first
        bounds = actor.getTightBounds()
        if bounds:
            bmin, bmax = bounds
            height = bmax.getY() - bmin.getY()
            if height > 0:
                scale = self.TARGET_HEIGHT / height
                actor.setScale(scale)
                # Recompute bounds after scaling
                bounds = actor.getTightBounds()
                bmin, bmax = bounds
            center = (bmin + bmax) / 2
            # Place so feet are at Y=0 and centered on pos X
            actor.setPos(pos.getX() - center.getX(),
                         pos.getY() - bmin.getY(),
                         pos.getZ() - center.getZ())
        else:
            actor.setPos(pos)

        # In y-up, models default to facing -Z.
        # Rotate so attacker faces +X (right) and defender faces -X (left)
        if face_right:
            actor.setH(-90)   # face +X direction (toward defender)
        else:
            actor.setH(90)    # face -X direction (toward attacker)

    def _load_anims(self, actor, egg_path):
        """Load animations from the anims/ subdirectory."""
        anims_dir = os.path.join(os.path.dirname(egg_path), "anims")
        if not os.path.isdir(anims_dir):
            return []
        anim_dict = {}
        for f in sorted(os.listdir(anims_dir)):
            if f.endswith(".egg"):
                name = os.path.splitext(f)[0]
                anim_dict[name] = Filename.fromOsSpecific(
                    os.path.join(anims_dir, f))
        if anim_dict:
            actor.loadAnims(anim_dict)
            return sorted(actor.getAnimNames())
        return []

    def _play_idle(self, actor, anim_names):
        """Play idle/wait animation if available."""
        for name in anim_names:
            if "waitA" in name or "ba10_waitA" in name:
                actor.loop(name)
                return
        if anim_names:
            actor.loop(anim_names[0])

    def play_attack_anim(self):
        """Play an attack animation on the attacker, then return to idle."""
        if not self.attacker:
            return
        # Find an attack animation
        attack_anim = None
        for name in self.attacker_anims:
            if any(kw in name.lower() for kw in
                   ("attack", "ba20", "ba21", "atk", "ba30")):
                attack_anim = name
                break
        if not attack_anim and self.attacker_anims:
            # Fallback: anything that isn't wait/idle
            for name in self.attacker_anims:
                if "wait" not in name.lower() and "idle" not in name.lower():
                    attack_anim = name
                    break

        if attack_anim:
            self.attacker.play(attack_anim)
            # Schedule return to idle
            try:
                dur = self.attacker.getDuration(attack_anim)
            except Exception:
                dur = 1.5
            self._base.taskMgr.doMethodLater(
                max(dur, 0.5),
                lambda t: self._play_idle(self.attacker, self.attacker_anims),
                "return_to_idle"
            )
            return attack_anim
        return None

    def play_hit_anim(self):
        """Play a hit/damage animation on the defender."""
        if not self.defender:
            return
        hit_anim = None
        for name in self.defender_anims:
            if any(kw in name.lower() for kw in ("damage", "hit", "ba50", "ba51")):
                hit_anim = name
                break
        if hit_anim:
            self.defender.play(hit_anim)
            try:
                dur = self.defender.getDuration(hit_anim)
            except Exception:
                dur = 1.0
            self._base.taskMgr.doMethodLater(
                max(dur, 0.5),
                lambda t: self._play_idle(self.defender, self.defender_anims),
                "defender_return_idle"
            )

    def cleanup(self):
        """Remove both actors."""
        if self.attacker:
            self.attacker.cleanup()
            self.attacker.removeNode()
            self.attacker = None
        if self.defender:
            self.defender.cleanup()
            self.defender.removeNode()
            self.defender = None
