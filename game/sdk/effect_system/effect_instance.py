"""Single effect instance - loads a real waza model and animates it."""
import os

from panda3d.core import (
    ColorBlendAttrib,
    CullFaceAttrib,
    Filename,
    Point3,
    Vec3,
    Vec4,
)
from direct.interval.IntervalGlobal import (
    LerpPosInterval,
    LerpScaleInterval,
    LerpHprInterval,
    Sequence,
    Func,
    Wait,
    Parallel,
    LerpColorScaleInterval,
)


class EffectInstance:
    """Manages a single waza effect from spawn to cleanup.

    Styles:
      projectile - travels from point A to point B
      beam       - stretches from origin to target (Roblox style)
      contact    - spawns at target, plays in-place
      self_buff  - spawns on attacker
      ground     - spawns below target
      orbit      - orbits around target
    """

    PHASE_IDLE = "idle"
    PHASE_ACTIVE = "active"
    PHASE_DONE = "done"

    def __init__(self, waza_entry, loader, style="projectile"):
        self.waza_entry = waza_entry
        self._loader = loader
        self.style = style
        self.node = None
        self.phase = self.PHASE_IDLE
        self._sequence = None
        self._beam_wrapper = None

    def spawn(self, parent, origin_pos, target_pos, scale=1.0, duration=1.0,
              color=None, spin=False, attacker_height=0.0, defender_height=0.0):
        """Load the waza model and start the animation.

        Args:
            parent: NodePath to reparent to (render)
            origin_pos: Point3 start position
            target_pos: Point3 end position
            scale: float scale factor
            duration: animation duration in seconds
            color: optional (r,g,b,a) color scale
            spin: whether to add rotation during travel
            attacker_height: attacker model height for proportional scaling
            defender_height: defender model height for proportional scaling
        """
        self._attacker_height = attacker_height
        self._defender_height = defender_height

        egg_path = self.waza_entry.egg_path
        try:
            self.node = self._loader.loadModel(Filename.fromOsSpecific(egg_path))
            if self.node.isEmpty():
                print(f"[EFFECT] Empty model: {egg_path}")
                self.phase = self.PHASE_DONE
                return False
        except Exception as e:
            print(f"[EFFECT] Load error {self.waza_entry.name}: {e}")
            self.phase = self.PHASE_DONE
            return False

        # Rendering setup: additive blend for glow
        self.node.setLightOff()
        self.node.setDepthWrite(False)
        self.node.setDepthTest(True)
        self.node.setBin("fixed", 20)
        self.node.setAttrib(ColorBlendAttrib.make(
            ColorBlendAttrib.MAdd,
            ColorBlendAttrib.OOne,
            ColorBlendAttrib.OOne))
        self.node.setAttrib(CullFaceAttrib.make(CullFaceAttrib.MCullNone))
        self.node.setTwoSided(True)

        if color:
            r, g, b = color[0], color[1], color[2]
            a = color[3] if len(color) > 3 else 1.0
            # For primitive models (PG_*), strip textures and force flat color.
            # Use reduced values: additive blending doubles through front+back faces.
            if self.waza_entry.name.startswith("PG_") or any(
                    kw in self.waza_entry.name.lower() for kw in
                    ("sword", "hand", "tooth", "horn", "tail", "wing",
                     "whip", "needle", "foot", "bone", "hasami",
                     "hammer", "crab", "baton", "finger")):
                self.node.setTextureOff(100)
                dim = 0.4
                self.node.setColor(Vec4(r * dim, g * dim, b * dim, a), 100)
            else:
                self.node.setColorScale(r, g, b, a)

        # Auto-scale: normalize model size relative to the defender.
        # If defender_height is known, target sizes scale proportionally
        # so effects look correct on both small and large Pokemon.
        if self.style != "beam":
            bounds = self.node.getTightBounds()
            if bounds:
                bmin, bmax = bounds
                native_size = max(
                    abs(bmax.getX() - bmin.getX()),
                    abs(bmax.getY() - bmin.getY()),
                    abs(bmax.getZ() - bmin.getZ()))
                if native_size > 0.1:
                    # Base target sizes as fraction of the relevant Pokemon
                    # Attacker-centric styles use attacker height,
                    # defender-centric styles use defender height
                    target_ratios = {
                        "contact": 0.45,     # fist/claw ~45% of defender
                        "projectile": 0.35,  # ball/bullet ~35% of attacker
                        "self_buff": 0.80,   # aura ~80% of attacker
                        "ground": 2.0,       # quake ~200% of defender
                        "orbit": 1.0,        # ring ~100% of defender
                    }
                    ratio = target_ratios.get(self.style, 0.45)
                    if self.style in ("self_buff", "projectile"):
                        ref_height = attacker_height if attacker_height > 1.0 else 100.0
                    else:
                        ref_height = defender_height if defender_height > 1.0 else 100.0
                    target = ratio * ref_height
                    # Ensure minimum visible size: at least 25% of Pokemon
                    min_target = ref_height * 0.25
                    target = max(target, min_target)
                    # Undo the 0.12 base multiplier to get json_scale as
                    # a direct relative multiplier (1.0 = standard size)
                    json_rel = scale / 0.12 if scale > 0.001 else 1.0
                    scale = (target / native_size) * json_rel

        self.node.setScale(scale)
        self.node.reparentTo(parent)
        self.phase = self.PHASE_ACTIVE

        if self.style == "projectile":
            self._animate_projectile(origin_pos, target_pos, scale, duration, spin)
        elif self.style == "beam":
            self._animate_beam(origin_pos, target_pos, scale, duration)
        elif self.style == "contact":
            self._animate_contact(origin_pos, target_pos, scale, duration)
        elif self.style == "self_buff":
            self._animate_self(origin_pos, scale, duration)
        elif self.style == "ground":
            self._animate_ground(target_pos, scale, duration)
        elif self.style == "orbit":
            self._animate_orbit(target_pos, scale, duration)
        else:
            self._animate_projectile(origin_pos, target_pos, scale, duration, spin)

        return True

    def _animate_projectile(self, origin, target, scale, duration, spin):
        self.node.setPos(origin)
        self.node.setScale(0.01)

        # Look at target
        self.node.lookAt(target)

        intervals = [
            LerpScaleInterval(self.node, 0.12, scale, startScale=0.01),
            LerpPosInterval(self.node, duration, target, startPos=origin),
        ]

        if spin:
            intervals.append(
                LerpHprInterval(self.node, duration,
                                self.node.getHpr() + (0, 0, 720))
            )

        self._sequence = Sequence(
            Parallel(*intervals) if spin else Sequence(*intervals),
            Wait(0.05),
            Parallel(
                LerpScaleInterval(self.node, 0.25, 0.01),
                LerpColorScaleInterval(self.node, 0.25, Vec4(1, 1, 1, 0)),
            ),
            Func(self._done),
        )
        self._sequence.start()

    def _animate_beam(self, origin, target, scale, duration):
        """Beam stretches from origin to target like in Roblox.

        Uses a wrapper node: the wrapper is oriented toward the target via
        lookAt, and the model inside is rotated so its long axis aligns with
        the wrapper's Z.  The wrapper's non-uniform scale then stretches Z
        for length and X/Y for thickness.
        """
        distance = (target - origin).length()
        if distance < 0.1:
            self._done()
            return

        # Shift midpoint 5% toward target so beam model's thin tail
        # hides behind the attacker instead of extending past the mouth
        t = 0.60
        midpoint = Point3(
            origin.getX() + (target.getX() - origin.getX()) * t,
            origin.getY() + (target.getY() - origin.getY()) * t,
            origin.getZ() + (target.getZ() - origin.getZ()) * t,
        )

        # Measure native model bounds (reset transforms first)
        self.node.setPos(0, 0, 0)
        self.node.setHpr(0, 0, 0)
        self.node.setScale(1)
        bounds = self.node.getTightBounds()
        if bounds:
            bmin, bmax = bounds
            sx = abs(bmax.getX() - bmin.getX())
            sy = abs(bmax.getY() - bmin.getY())
            sz = abs(bmax.getZ() - bmin.getZ())
        else:
            sx = sy = sz = 50.0

        # Find longest axis (beam direction) and cross-section
        dims = sorted([(sx, 0), (sy, 1), (sz, 2)],
                       key=lambda d: d[0], reverse=True)
        native_len = max(dims[0][0], 1.0)
        long_axis = dims[0][1]
        native_cross = max((dims[1][0] + dims[2][0]) / 2, 1.0)

        # Create wrapper node oriented toward target
        parent = self.node.getParent()
        wrapper = parent.attachNewNode("beam_wrapper")
        wrapper.setPos(midpoint)
        wrapper.lookAt(origin)

        # Move model inside wrapper
        self.node.reparentTo(wrapper)
        self.node.setPos(0, 0, 0)
        self.node.setScale(1)

        # Rotate model so its long axis aligns with wrapper's -Z (forward)
        if long_axis == 0:      # X is long -> map X to -Z
            self.node.setHpr(90, 0, 0)
        elif long_axis == 1:    # Y is long -> map Y to -Z
            self.node.setHpr(0, -90, 0)
        else:                   # Z already the long axis
            self.node.setHpr(0, 0, 0)

        # Measure accurate bounds AFTER rotation in wrapper space
        b = self.node.getTightBounds(wrapper)
        if b:
            bmin_w, bmax_w = b
            # Center model so it spans symmetrically from wrapper origin
            self.node.setPos(
                -(bmin_w.getX() + bmax_w.getX()) / 2,
                -(bmin_w.getY() + bmax_w.getY()) / 2,
                -(bmin_w.getZ() + bmax_w.getZ()) / 2,
            )
            # Use post-rotation measurements for accurate stretch
            native_len = max(abs(bmax_w.getZ() - bmin_w.getZ()), 1.0)
            native_cross = max(
                (abs(bmax_w.getX() - bmin_w.getX()) +
                 abs(bmax_w.getY() - bmin_w.getY())) / 2, 1.0)

        # Scale factors
        stretch_factor = distance / native_len
        desired_thickness = max(scale * 30, 2.0)
        thickness_factor = desired_thickness / native_cross

        # Animate wrapper (Z = length along beam, X/Y = thickness)
        wrapper.setScale(0.01)
        full = Vec3(thickness_factor, thickness_factor, stretch_factor)
        thin = Vec3(0.01, 0.01, stretch_factor)

        self._beam_wrapper = wrapper

        self._sequence = Sequence(
            # Beam appears quickly
            LerpScaleInterval(wrapper, duration * 0.15, full,
                              startScale=Vec3(0.01, 0.01, 0.01)),
            # Hold
            Wait(duration * 0.55),
            # Thin out and fade
            Parallel(
                LerpScaleInterval(wrapper, duration * 0.3, thin),
                LerpColorScaleInterval(self.node, duration * 0.3,
                                       Vec4(1, 1, 1, 0)),
            ),
            Func(lambda: self._done_beam(wrapper)),
        )
        self._sequence.start()

    def _done_beam(self, wrapper):
        if self.node and not self.node.isEmpty():
            self.node.wrtReparentTo(self.node.getParent().getParent())
        if wrapper and not wrapper.isEmpty():
            wrapper.removeNode()
        self._beam_wrapper = None
        self._done()

    def _animate_contact(self, origin, target, scale, duration):
        """Contact animation with motion based on waza model type."""
        name = self.waza_entry.name.lower()
        # Auto-scaling handles sizing; just prevent zero scale
        visual_scale = max(scale, 0.001)

        # Attack direction (attacker -> defender)
        direction = target - origin
        dist = direction.length()
        if dist > 0.1:
            direction = Vec3(direction.getX() / dist,
                             direction.getY() / dist,
                             direction.getZ() / dist)
        else:
            direction = Vec3(1, 0, 0)

        # Perpendicular vectors (y-up coordinate system)
        up = Vec3(0, 1, 0)
        right = Vec3(direction.getZ(), 0, -direction.getX())

        # Scale offsets proportionally to defender size
        ref = self._defender_height if self._defender_height > 1.0 else 100.0
        offset = ref * 0.08  # approach distance

        if any(kw in name for kw in ("hand", "hammer", "finger", "crab", "baton")):
            # PUNCH: forward thrust into target
            start = Point3(target.getX() - direction.getX() * offset,
                           target.getY() - direction.getY() * offset,
                           target.getZ() - direction.getZ() * offset)
            punch_over = ref * 0.03
            overshoot = Point3(target.getX() + direction.getX() * punch_over,
                               target.getY() + direction.getY() * punch_over,
                               target.getZ() + direction.getZ() * punch_over)
            self.node.setPos(start)
            self.node.lookAt(target)
            self.node.setScale(0.01)
            self._sequence = Sequence(
                LerpScaleInterval(self.node, 0.06, visual_scale, startScale=0.01),
                LerpPosInterval(self.node, 0.10, target, startPos=start),
                LerpPosInterval(self.node, 0.06, overshoot),
                Wait(duration * 0.15),
                Parallel(
                    LerpScaleInterval(self.node, duration * 0.3, 0.01),
                    LerpColorScaleInterval(self.node, duration * 0.3, Vec4(1, 1, 1, 0)),
                ),
                Func(self._done),
            )

        elif any(kw in name for kw in ("sword", "hasami")):
            # SLASH: diagonal sweep with spinning blade rotation
            slash_off = ref * 0.08
            start = Point3(target.getX() + right.getX() * slash_off + up.getX() * slash_off,
                           target.getY() + right.getY() * slash_off + up.getY() * slash_off,
                           target.getZ() + right.getZ() * slash_off + up.getZ() * slash_off)
            end = Point3(target.getX() - right.getX() * slash_off - up.getX() * slash_off,
                         target.getY() - right.getY() * slash_off - up.getY() * slash_off,
                         target.getZ() - right.getZ() * slash_off - up.getZ() * slash_off)
            self.node.setPos(start)
            self.node.lookAt(end)
            self.node.setScale(0.01)
            start_hpr = self.node.getHpr()
            slash_hpr = Point3(start_hpr.getX(), start_hpr.getY(),
                               start_hpr.getZ() + 360)
            self._sequence = Sequence(
                LerpScaleInterval(self.node, 0.06, visual_scale, startScale=0.01),
                Parallel(
                    LerpPosInterval(self.node, 0.20, end, startPos=start),
                    LerpHprInterval(self.node, 0.20, slash_hpr, startHpr=start_hpr),
                ),
                Parallel(
                    LerpScaleInterval(self.node, duration * 0.25, 0.01),
                    LerpColorScaleInterval(self.node, duration * 0.25, Vec4(1, 1, 1, 0)),
                ),
                Func(self._done),
            )

        elif "tooth" in name:
            # BITE: snap at target
            self.node.setPos(target)
            self.node.lookAt(origin)
            self.node.setScale(0.01)
            self._sequence = Sequence(
                LerpScaleInterval(self.node, 0.10, visual_scale, startScale=0.01),
                Wait(duration * 0.3),
                Parallel(
                    LerpScaleInterval(self.node, duration * 0.3, 0.01),
                    LerpColorScaleInterval(self.node, duration * 0.3, Vec4(1, 1, 1, 0)),
                ),
                Func(self._done),
            )

        elif any(kw in name for kw in ("horn", "needle")):
            # STAB: fast forward thrust
            start = Point3(target.getX() - direction.getX() * offset,
                           target.getY() - direction.getY() * offset,
                           target.getZ() - direction.getZ() * offset)
            stab_over = ref * 0.05
            overshoot = Point3(target.getX() + direction.getX() * stab_over,
                               target.getY() + direction.getY() * stab_over,
                               target.getZ() + direction.getZ() * stab_over)
            self.node.setPos(start)
            self.node.lookAt(target)
            self.node.setScale(0.01)
            self._sequence = Sequence(
                LerpScaleInterval(self.node, 0.05, visual_scale, startScale=0.01),
                LerpPosInterval(self.node, 0.08, overshoot, startPos=start),
                Wait(duration * 0.15),
                Parallel(
                    LerpPosInterval(self.node, duration * 0.3, start),
                    LerpScaleInterval(self.node, duration * 0.3, 0.01),
                    LerpColorScaleInterval(self.node, duration * 0.3, Vec4(1, 1, 1, 0)),
                ),
                Func(self._done),
            )

        elif "tail" in name:
            # TAIL SWEEP: horizontal swing across target
            sweep_off = ref * 0.08
            start = Point3(target.getX() + right.getX() * sweep_off,
                           target.getY() + right.getY() * sweep_off,
                           target.getZ() + right.getZ() * sweep_off)
            end = Point3(target.getX() - right.getX() * sweep_off,
                         target.getY() - right.getY() * sweep_off,
                         target.getZ() - right.getZ() * sweep_off)
            self.node.setPos(start)
            self.node.lookAt(end)
            self.node.setScale(0.01)
            self._sequence = Sequence(
                LerpScaleInterval(self.node, 0.06, visual_scale, startScale=0.01),
                LerpPosInterval(self.node, 0.18, target, startPos=start),
                LerpPosInterval(self.node, 0.18, end),
                Parallel(
                    LerpScaleInterval(self.node, duration * 0.3, 0.01),
                    LerpColorScaleInterval(self.node, duration * 0.3, Vec4(1, 1, 1, 0)),
                ),
                Func(self._done),
            )

        elif "whip" in name:
            # WHIP LASH: forward crack
            whip_start = ref * 0.05
            whip_end = ref * 0.03
            start = Point3(origin.getX() + direction.getX() * whip_start,
                           origin.getY() + direction.getY() * whip_start,
                           origin.getZ() + direction.getZ() * whip_start)
            end = Point3(target.getX() + direction.getX() * whip_end,
                         target.getY() + direction.getY() * whip_end,
                         target.getZ() + direction.getZ() * whip_end)
            self.node.setPos(start)
            self.node.lookAt(target)
            self.node.setScale(0.01)
            self._sequence = Sequence(
                LerpScaleInterval(self.node, 0.08, visual_scale, startScale=0.01),
                LerpPosInterval(self.node, 0.12, end, startPos=start),
                Wait(duration * 0.1),
                Parallel(
                    LerpPosInterval(self.node, duration * 0.25, start),
                    LerpScaleInterval(self.node, duration * 0.3, 0.01),
                    LerpColorScaleInterval(self.node, duration * 0.3, Vec4(1, 1, 1, 0)),
                ),
                Func(self._done),
            )

        elif "wing" in name:
            # WING: sweep from above
            wing_off = ref * 0.05
            wing_up = ref * 0.06
            wing_dn = ref * 0.02
            start = Point3(target.getX() + right.getX() * wing_off,
                           target.getY() + wing_up,
                           target.getZ() + right.getZ() * wing_off)
            end = Point3(target.getX() - right.getX() * wing_off,
                         target.getY() - wing_dn,
                         target.getZ() - right.getZ() * wing_off)
            self.node.setPos(start)
            self.node.lookAt(end)
            self.node.setScale(0.01)
            self._sequence = Sequence(
                LerpScaleInterval(self.node, 0.06, visual_scale, startScale=0.01),
                LerpPosInterval(self.node, 0.15, target, startPos=start),
                LerpPosInterval(self.node, 0.15, end),
                Parallel(
                    LerpScaleInterval(self.node, duration * 0.3, 0.01),
                    LerpColorScaleInterval(self.node, duration * 0.3, Vec4(1, 1, 1, 0)),
                ),
                Func(self._done),
            )

        elif "foot" in name:
            # KICK: arc from high above, sweeping down onto target
            kick_back = ref * 0.10
            kick_high = ref * 0.25
            kick_mid_b = ref * 0.03
            kick_mid_h = ref * 0.08
            kick_low = ref * 0.01
            high = Point3(target.getX() - direction.getX() * kick_back,
                          target.getY() + kick_high,
                          target.getZ() - direction.getZ() * kick_back)
            mid = Point3(target.getX() - direction.getX() * kick_mid_b,
                         target.getY() + kick_mid_h,
                         target.getZ() - direction.getZ() * kick_mid_b)
            impact = Point3(target.getX(), target.getY() - kick_low, target.getZ())
            self.node.setPos(high)
            self.node.lookAt(target)
            self.node.setScale(0.01)
            self._sequence = Sequence(
                LerpScaleInterval(self.node, 0.06, visual_scale, startScale=0.01),
                LerpPosInterval(self.node, 0.10, mid, startPos=high),
                LerpPosInterval(self.node, 0.06, impact, startPos=mid),
                Wait(duration * 0.15),
                Parallel(
                    LerpScaleInterval(self.node, duration * 0.3, 0.01),
                    LerpColorScaleInterval(self.node, duration * 0.3, Vec4(1, 1, 1, 0)),
                ),
                Func(self._done),
            )

        elif "bone" in name:
            # CLUB SWING: arc from above
            club_back = ref * 0.04
            club_up = ref * 0.08
            start = Point3(target.getX() - direction.getX() * club_back,
                           target.getY() + club_up,
                           target.getZ() - direction.getZ() * club_back)
            self.node.setPos(start)
            self.node.lookAt(target)
            self.node.setScale(0.01)
            self._sequence = Sequence(
                LerpScaleInterval(self.node, 0.06, visual_scale, startScale=0.01),
                LerpPosInterval(self.node, 0.12, target, startPos=start),
                Wait(duration * 0.2),
                Parallel(
                    LerpScaleInterval(self.node, duration * 0.3, 0.01),
                    LerpColorScaleInterval(self.node, duration * 0.3, Vec4(1, 1, 1, 0)),
                ),
                Func(self._done),
            )

        else:
            # DEFAULT: pop-in at target (for unknown models)
            self.node.setPos(target)
            self.node.setScale(0.01)
            self._sequence = Sequence(
                LerpScaleInterval(self.node, 0.15, visual_scale, startScale=0.01),
                Wait(duration * 0.4),
                Parallel(
                    LerpScaleInterval(self.node, duration * 0.35, 0.01),
                    LerpColorScaleInterval(self.node, duration * 0.35, Vec4(1, 1, 1, 0)),
                ),
                Func(self._done),
            )

        self._sequence.start()

    def _animate_self(self, origin, scale, duration):
        # Auto-scaling handles sizing; just prevent zero scale
        visual_scale = max(scale, 0.001)
        self.node.setPos(origin)
        self.node.setScale(0.01)
        self._sequence = Sequence(
            LerpScaleInterval(self.node, 0.2, visual_scale, startScale=0.01),
            Wait(duration * 0.5),
            Parallel(
                LerpScaleInterval(self.node, duration * 0.4, 0.01),
                LerpColorScaleInterval(self.node, duration * 0.4, Vec4(1, 1, 1, 0)),
            ),
            Func(self._done),
        )
        self._sequence.start()

    def _animate_ground(self, target, scale, duration):
        ground = Point3(target.getX(), 0, target.getZ())
        self.node.setPos(ground)
        self.node.setScale(0.01)
        ref = self._defender_height if self._defender_height > 1.0 else 100.0
        rise_height = max(ref * 0.5, 10.0)
        rise_target = ground + Point3(0, rise_height, 0)
        self._sequence = Sequence(
            Parallel(
                LerpScaleInterval(self.node, 0.25, scale, startScale=0.01),
                LerpPosInterval(self.node, 0.25, rise_target, startPos=ground),
            ),
            Wait(duration * 0.3),
            Parallel(
                LerpScaleInterval(self.node, duration * 0.45, 0.01),
                LerpColorScaleInterval(self.node, duration * 0.45, Vec4(1, 1, 1, 0)),
                LerpPosInterval(self.node, duration * 0.45, ground),
            ),
            Func(self._done),
        )
        self._sequence.start()

    def _animate_orbit(self, center, scale, duration):
        ref = self._defender_height if self._defender_height > 1.0 else 100.0
        orbit_radius = max(ref * 0.5, 5.0)
        # Auto-scaling handles sizing; just prevent zero scale
        visual_scale = max(scale, 0.001)
        self.node.setPos(center + Point3(orbit_radius, 0, 0))
        self.node.setScale(0.01)
        # Create orbit by spinning a parent pivot
        pivot = self.node.getParent().attachNewNode("orbit_pivot")
        pivot.setPos(center)
        self.node.wrtReparentTo(pivot)
        self._sequence = Sequence(
            LerpScaleInterval(self.node, 0.15, visual_scale, startScale=0.01),
            LerpHprInterval(pivot, duration, (720, 0, 0)),
            Parallel(
                LerpScaleInterval(self.node, 0.3, 0.01),
                LerpColorScaleInterval(self.node, 0.3, Vec4(1, 1, 1, 0)),
            ),
            Func(lambda: self._done_orbit(pivot)),
        )
        self._sequence.start()

    def _done_orbit(self, pivot):
        if self.node and not self.node.isEmpty():
            self.node.wrtReparentTo(self.node.getParent().getParent())
        if pivot and not pivot.isEmpty():
            pivot.removeNode()
        self._done()

    def _done(self):
        self.phase = self.PHASE_DONE

    def cleanup(self):
        if self._sequence:
            self._sequence.finish()
            self._sequence = None
        if self._beam_wrapper and not self._beam_wrapper.isEmpty():
            self._beam_wrapper.removeNode()
            self._beam_wrapper = None
            self.node = None          # child of wrapper, already removed
        if self.node and not self.node.isEmpty():
            self.node.removeNode()
        self.node = None
        self.phase = self.PHASE_DONE

    @property
    def is_done(self):
        return self.phase == self.PHASE_DONE
