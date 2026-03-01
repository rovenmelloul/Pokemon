"""Pokemon animation controller and attack manager for Panda3D.

Provides skeletal + UV animation playback for a Pokemon instance,
and coordinates complete attack sequences with waza effects.

Usage:
    from spawn import Pokemon
    from animation import AnimationController, AttackManager

    poke = Pokemon(base, "output/pokemon/pm0025_00")
    ctrl = AnimationController(base, poke)  # auto-plays idle
    ctrl.play("kw32_happyA01", loop=True)

    attacks = AttackManager(base, output_dir="output")
    attacks.execute_move("Flamethrower", attacker=poke, defender=other)
"""
import os

from panda3d.core import TextureStage

try:
    from effect_system import EffectManager, MoveDatabase
except ImportError:
    EffectManager = None
    MoveDatabase = None

# ===== CONFIGURATION =====
ANIM_CONFIG = {
    "effect_scale_factor": 0.12,
    "effect_delay": 0.15,
    "hit_timing_ratio": 0.7,
    "default_speed": 1.0,
    "min_speed": 0.1,
    "max_speed": 10.0,
    "moves_json": "data/moves.json",
    "effects_json": "data/effects.json",
}

# Animation prefixes by category
ANIM_PREFIXES = {
    "entrance": "ba01",
    "roar": "ba02",
    "idle": "ba10",
    "physical": "ba20",
    "special": "ba21",
    "damage": "ba30",
    "faint": "ba41",
    "walk": "fi20",
    "run": "fi21",
    "drowse": "kw20",
    "sleep": "kw21",
    "happy": "kw32",
    "play": "kw35",
    "eat": "kw50",
    "touch": "kw60",
}

# Effect colors by Pokemon type (RGBA)
TYPE_EFFECT_COLORS = {
    "Fire": (1.0, 0.5, 0.15, 1), "Water": (0.2, 0.5, 1.0, 1),
    "Electric": (1.0, 1.0, 0.2, 1), "Ice": (0.5, 0.85, 1.0, 1),
    "Grass": (0.3, 1.0, 0.2, 1), "Fighting": (0.9, 0.35, 0.15, 1),
    "Poison": (0.8, 0.15, 1.0, 1), "Ground": (0.85, 0.6, 0.2, 1),
    "Flying": (0.5, 0.65, 1.0, 1), "Psychic": (1.0, 0.2, 0.8, 1),
    "Bug": (0.6, 0.9, 0.1, 1), "Rock": (0.75, 0.55, 0.3, 1),
    "Ghost": (0.6, 0.15, 0.85, 1), "Dragon": (0.35, 0.2, 1.0, 1),
    "Dark": (0.35, 0.15, 0.5, 1), "Steel": (0.7, 0.75, 0.95, 1),
    "Normal": (0.9, 0.85, 0.7, 1), "Fairy": (1.0, 0.45, 0.75, 1),
}

# UV animation material patterns
UVANIM_MATERIAL_PATTERNS = [
    "Fire", "Flame", "Effect", "Core", "Mask", "Water", "Electric",
]


class AnimationController:
    """Controls skeletal and UV animation playback for a Pokemon.

    Args:
        base: ShowBase instance
        pokemon: Pokemon instance (from spawn.py)
        auto_idle: if True, automatically play idle animation on init
        config: optional dict to override ANIM_CONFIG defaults
    """

    def __init__(self, base, pokemon, auto_idle=True, config=None):
        self._base = base
        self._pokemon = pokemon
        self._config = {**ANIM_CONFIG, **(config or {})}
        self._current_anim = None
        self._is_playing = False
        self._is_looping = True
        self._speed = self._config["default_speed"]
        self._on_finished_cb = None
        self._anim_index = -1
        self._tasks = []

        # Start UV anim task
        task_name = f"uvanim_{id(self)}"
        self._tasks.append(task_name)
        self._base.taskMgr.add(self._uvanim_task, task_name)

        if auto_idle and pokemon.anim_names:
            idle = self.find_idle()
            if idle:
                self.play(idle, loop=True)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_anim(self):
        return self._current_anim

    @property
    def is_playing(self):
        return self._is_playing

    @property
    def is_looping(self):
        return self._is_looping

    @property
    def speed(self):
        return self._speed

    @property
    def current_frame(self):
        if not self._current_anim or not self._pokemon.actor:
            return 0
        ctrl = self._pokemon.actor.getAnimControl(self._current_anim)
        return ctrl.getFrame() if ctrl and ctrl.isPlaying() else 0

    @property
    def num_frames(self):
        if not self._current_anim or not self._pokemon.actor:
            return 0
        try:
            return self._pokemon.actor.getNumFrames(self._current_anim)
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Playback methods
    # ------------------------------------------------------------------

    def play(self, name, loop=True):
        """Play an animation by name.

        Args:
            name: animation name (must be in pokemon.anim_names)
            loop: if True, loop; if False, play once
        """
        actor = self._pokemon.actor
        if not actor or name not in self._pokemon.anim_names:
            return False

        self._current_anim = name
        self._is_looping = loop
        self._is_playing = True

        # Update index
        try:
            self._anim_index = self._pokemon.anim_names.index(name)
        except ValueError:
            self._anim_index = -1

        actor.setPlayRate(self._speed, name)
        if loop:
            actor.loop(name)
        else:
            actor.play(name)
            # Schedule finish check
            self._schedule_finish_check(name)

        return True

    def stop(self):
        """Stop the current animation."""
        if self._pokemon.actor and self._current_anim:
            self._pokemon.actor.stop(self._current_anim)
        self._is_playing = False

    def pose(self, name, frame):
        """Pose at a specific frame."""
        actor = self._pokemon.actor
        if not actor or name not in self._pokemon.anim_names:
            return False
        self._current_anim = name
        self._is_playing = False
        actor.pose(name, frame)
        return True

    def next_anim(self):
        """Switch to the next animation in the list. Returns the new name."""
        names = self._pokemon.anim_names
        if not names:
            return None
        self._anim_index = (self._anim_index + 1) % len(names)
        name = names[self._anim_index]
        self.play(name, loop=self._is_looping)
        return name

    def prev_anim(self):
        """Switch to the previous animation. Returns the new name."""
        names = self._pokemon.anim_names
        if not names:
            return None
        self._anim_index = (self._anim_index - 1) % len(names)
        name = names[self._anim_index]
        self.play(name, loop=self._is_looping)
        return name

    def set_speed(self, value):
        """Set playback speed."""
        cfg = self._config
        self._speed = max(cfg["min_speed"], min(value, cfg["max_speed"]))
        if self._pokemon.actor and self._current_anim:
            self._pokemon.actor.setPlayRate(
                self._speed, self._current_anim)

    def speed_up(self, factor=1.5):
        """Increase speed by factor."""
        self.set_speed(self._speed * factor)

    def speed_down(self, factor=1.5):
        """Decrease speed by factor."""
        self.set_speed(self._speed / factor)

    # ------------------------------------------------------------------
    # Animation search
    # ------------------------------------------------------------------

    def find_anim(self, *keywords):
        """Find first animation matching any keyword (substring match).

        Returns the animation name or None.
        """
        for name in self._pokemon.anim_names:
            nl = name.lower()
            for kw in keywords:
                if kw.lower() in nl:
                    return name
        return None

    def find_idle(self):
        """Find the best idle/wait animation."""
        result = self.find_anim("ba10_waita", "kw01_wait")
        if result:
            return result
        result = self.find_anim("wait")
        if result:
            return result
        return self._pokemon.anim_names[0] if self._pokemon.anim_names else None

    def find_attack_anim(self, category="physical"):
        """Find an attack animation by category.

        Args:
            category: "physical", "special", or "status"
        """
        if category == "physical":
            return self.find_anim("ba20", "buturi")
        elif category == "special":
            return self.find_anim("ba21", "tokusyu")
        # Fallback
        return self.find_anim("ba20", "ba21", "attack", "buturi", "tokusyu")

    def find_damage_anim(self):
        """Find a damage/hit animation."""
        return self.find_anim("ba30", "damages", "damage", "hit")

    def categorize_all(self):
        """Group all animations by category.

        Returns dict of category -> [anim_name, ...].
        """
        result = {}
        for name in self._pokemon.anim_names:
            nl = name.lower()
            matched = False
            for cat, prefix in ANIM_PREFIXES.items():
                if prefix in nl:
                    result.setdefault(cat, []).append(name)
                    matched = True
                    break
            if not matched:
                result.setdefault("other", []).append(name)
        return result

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_anim_finished(self, callback):
        """Register a callback for when a non-looping animation finishes.

        Args:
            callback: callable(anim_name)
        """
        self._on_finished_cb = callback

    def destroy(self):
        """Clean up tasks."""
        for task_name in self._tasks:
            self._base.taskMgr.remove(task_name)
        self._tasks.clear()
        self._is_playing = False

    # ------------------------------------------------------------------
    # Internal: finish detection
    # ------------------------------------------------------------------

    def _schedule_finish_check(self, name):
        """Schedule a task to detect when a non-looping anim finishes."""
        task_name = f"anim_finish_{id(self)}"
        self._base.taskMgr.remove(task_name)
        if task_name not in self._tasks:
            self._tasks.append(task_name)

        def check(task):
            actor = self._pokemon.actor
            if not actor:
                return task.done
            ctrl = actor.getAnimControl(name)
            if not ctrl or not ctrl.isPlaying():
                self._is_playing = False
                if self._on_finished_cb:
                    self._on_finished_cb(name)
                return task.done
            return task.cont
        self._base.taskMgr.add(check, task_name)

    # ------------------------------------------------------------------
    # Internal: UV animation task
    # ------------------------------------------------------------------

    def _uvanim_task(self, task):
        """Per-frame: sync UV offsets for eyes/mouth/effects with current frame."""
        poke = self._pokemon
        if not self._is_playing or not self._current_anim or not poke.actor:
            return task.cont

        anim_name = self._current_anim
        uvanim = poke.uvanim_data.get(anim_name)

        ctrl = poke.actor.getAnimControl(anim_name)
        if not ctrl or not ctrl.isPlaying():
            return task.cont

        frame = ctrl.getFrame()
        anim_tracks = uvanim.get("tracks", {}) if uvanim else {}
        anim_num_frames = uvanim.get("num_frames", 1) if uvanim else 1
        anim_frame = min(frame, anim_num_frames - 1)

        has_eye = any("Eye" in t for t in anim_tracks)
        has_mouth = any("Mouth" in t for t in anim_tracks)

        # Apply eye/mouth from animation tracks
        for mat_name, vals in anim_tracks.items():
            if any(p.lower() in mat_name.lower()
                   for p in ("Eye", "Mouth")):
                self._apply_eye_mouth_track(mat_name, vals, anim_frame)
                continue

            # Other materials: only animate whitelisted (fire/effects)
            if not any(p.lower() in mat_name.lower()
                       for p in UVANIM_MATERIAL_PATTERNS):
                continue
            nps = poke._uvanim_mat_nps.get(mat_name, [])
            if not nps:
                continue

            tu = vals.get("ColorUVTranslateU")
            tv = vals.get("ColorUVTranslateV")
            if tu or tv:
                du = tu[anim_frame] if tu else 0.0
                dv = tv[anim_frame] if tv else 0.0
                for np in nps:
                    np.setTexOffset(TextureStage.getDefault(), du, dv)

            l1tu = vals.get("Layer1UVTranslateU")
            l1tv = vals.get("Layer1UVTranslateV")
            if l1tu or l1tv:
                du1 = l1tu[anim_frame] if l1tu else 0.0
                dv1 = l1tv[anim_frame] if l1tv else 0.0
                for np in nps:
                    stage = self._get_layer1_stage(np)
                    if stage:
                        np.setTexOffset(stage, du1, dv1)

        # Default eye when no tracks
        if not has_eye:
            for gn, gi, mname, *_ in poke._eye_mouth_geom_data:
                mlow = mname.lower()
                if "eye" in mlow:
                    su, sv = poke._eye_mouth_uv_scale.get(mname, (1.0, 1.0))
                    if mlow in poke._iris_eye_offset:
                        tu, tv = poke._iris_eye_offset[mlow]
                    else:
                        tu, tv = poke._config["default_eye_offset"]
                    poke.set_eye_mouth_uv(mname, tu * su, tv * sv)

        # Default mouth when no tracks
        if not has_mouth:
            for gn, gi, mname, *_ in poke._eye_mouth_geom_data:
                if "mouth" in mname.lower():
                    su, sv = poke._eye_mouth_uv_scale.get(mname, (1.0, 1.0))
                    tu, tv = poke._config["default_mouth_offset"]
                    poke.set_eye_mouth_uv(mname, tu * su, tv * sv)

        return task.cont

    def _apply_eye_mouth_track(self, mat_name, vals, frame):
        """Apply eye/mouth UV offset from a .uvanim track.
        Skips frames that would land on red placeholder tiles."""
        poke = self._pokemon
        tu = vals.get("ColorUVTranslateU")
        tv = vals.get("ColorUVTranslateV")
        if not tu and not tv:
            return False
        nf = max(len(tu) if tu else 0, len(tv) if tv else 0)
        f = min(frame, nf - 1) if nf > 0 else 0
        du = tu[f] if tu else 0.0
        dv = tv[f] if tv else 0.0

        su, sv = poke._eye_mouth_uv_scale.get(mat_name, (1.0, 1.0))

        # Check red placeholder
        red_set = poke._red_translate_positions.get(mat_name.lower(), set())
        if red_set and (round(du, 2), round(dv, 2)) in red_set:
            return False

        du *= su
        dv *= sv
        return poke.set_eye_mouth_uv(mat_name, du, dv)

    @staticmethod
    def _get_layer1_stage(np):
        """Find the TextureStage named 'UVMap.1' on a NodePath."""
        for ts in np.findAllTextureStages():
            if ts.getName() == "UVMap.1":
                return ts
        return None


class AttackManager:
    """Coordinates complete attack sequences: anim + waza effect + damage.

    Delegates effect rendering to effect_system.EffectManager and move
    lookup to effect_system.MoveDatabase.

    Args:
        base: ShowBase instance
        output_dir: path to the output/ directory
        config: optional dict to override ANIM_CONFIG defaults
    """

    def __init__(self, base, output_dir, config=None):
        self._base = base
        self._output_dir = os.path.abspath(output_dir)
        self._config = {**ANIM_CONFIG, **(config or {})}
        self._last_move = None
        self._tasks = []

        # Initialize EffectManager
        self.effect_manager = None
        if EffectManager is not None and os.path.isdir(self._output_dir):
            self.effect_manager = EffectManager(base, self._output_dir)

        # Initialize MoveDatabase
        self.move_database = None
        if MoveDatabase is not None:
            self.move_database = MoveDatabase()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_move(self, move_name, attacker, defender,
                     attacker_ctrl=None, defender_ctrl=None,
                     on_complete=None):
        """Execute a complete battle move sequence.

        Args:
            move_name: str name of the move (e.g. "Flamethrower")
                       OR a move dict from MoveDatabase
            attacker: Pokemon instance
            defender: Pokemon instance (or NodePath for target position)
            attacker_ctrl: optional AnimationController for attacker
            defender_ctrl: optional AnimationController for defender
            on_complete: optional callback when sequence finishes
        """
        if not self.effect_manager:
            return

        # Resolve move
        if isinstance(move_name, str):
            if not self.move_database:
                return
            move = self.move_database.get_by_name(move_name)
            if not move:
                return
        else:
            move = move_name

        self._last_move = move

        # Resolve actors
        atk_actor = attacker.actor if hasattr(attacker, 'actor') else attacker
        def_actor = defender.actor if hasattr(defender, 'actor') else defender

        if not atk_actor or atk_actor.isEmpty():
            return

        # Get waza model
        catalog = self.effect_manager.catalog
        waza = catalog.get(move["waza"])
        if not waza:
            waza = catalog.get("PG_sphere")
        if not waza:
            return

        cfg = self._config
        is_physical = move.get("category") == "physical"
        effect_delay = cfg["effect_delay"]
        move_duration = move.get("duration", 0.8)
        effect_scale = move.get("scale", 1.0) * cfg["effect_scale_factor"]
        effect_color = TYPE_EFFECT_COLORS.get(move.get("type"))

        # Compute heights
        attacker_height = self._get_height(atk_actor)
        defender_height = self._get_height(def_actor) if def_actor else 0.0

        # Get animation names
        if attacker_ctrl:
            atk_anims = attacker.anim_names if hasattr(attacker, 'anim_names') else []
        else:
            atk_anims = attacker.anim_names if hasattr(attacker, 'anim_names') else []

        def_anims = []
        if defender_ctrl and hasattr(defender, 'anim_names'):
            def_anims = defender.anim_names

        # 1) Attacker plays attack animation
        if is_physical:
            atk_anim = self._find_by_keywords(atk_anims, ["ba20", "buturi"])
        else:
            atk_anim = self._find_by_keywords(atk_anims, ["ba21", "tokusyu"])
        if not atk_anim:
            atk_anim = self._find_by_keywords(
                atk_anims, ["ba20", "ba21", "attack", "buturi", "tokusyu"])
        if not atk_anim:
            for name in atk_anims:
                nl = name.lower()
                if not any(kw in nl for kw in ("wait", "idle", "walk", "run",
                                                "drowse", "eye", "mouth", "loop")):
                    atk_anim = name
                    break

        if atk_anim:
            atk_actor.play(atk_anim)

        # Determine defender target for effect
        if def_actor and not def_actor.isEmpty():
            defender_target = def_actor
        elif hasattr(defender, 'actor') and defender.actor:
            defender_target = defender.actor
        else:
            defender_target = defender  # NodePath or dummy

        # 2) Fire waza effect after delay
        def fire_effect(task):
            self.effect_manager.fire_from_bones(
                waza, atk_actor, defender_target,
                origin_bone=move.get("origin", "EffShoot01_01"),
                target_bone=move.get("target", "EffCenter01"),
                style=move.get("style", "projectile"),
                scale=effect_scale,
                duration=move_duration,
                color=effect_color,
                attacker_height=attacker_height,
                defender_height=defender_height)
            return task.done

        task_name = f"attack_fire_{id(self)}_{id(move)}"
        self._tasks.append(task_name)
        self._base.taskMgr.doMethodLater(
            effect_delay, fire_effect, task_name)

        # 3) Defender plays damage animation on hit
        if def_actor and not def_actor.isEmpty() and def_anims:
            hit_delay = effect_delay + move_duration * cfg["hit_timing_ratio"]
            dmg_anim = self._find_by_keywords(
                def_anims, ["ba30", "damages", "damage", "hit"])

            def play_defender_hit(task):
                if def_actor and not def_actor.isEmpty() and dmg_anim:
                    def_actor.play(dmg_anim)
                    # Return defender to idle
                    try:
                        dur = def_actor.getDuration(dmg_anim)
                    except Exception:
                        dur = 1.0
                    if defender_ctrl:
                        idle = defender_ctrl.find_idle()
                        if idle:
                            idle_task = f"def_idle_{id(self)}_{id(move)}"
                            self._tasks.append(idle_task)
                            self._base.taskMgr.doMethodLater(
                                max(dur, 0.5),
                                lambda t: defender_ctrl.play(idle, loop=True),
                                idle_task)
                return task.done

            hit_task = f"attack_hit_{id(self)}_{id(move)}"
            self._tasks.append(hit_task)
            self._base.taskMgr.doMethodLater(
                hit_delay, play_defender_hit, hit_task)

        # 4) Return attacker to idle
        if atk_anim and atk_actor:
            try:
                atk_dur = atk_actor.getDuration(atk_anim)
            except Exception:
                atk_dur = 1.5

            if attacker_ctrl:
                idle_anim = attacker_ctrl.find_idle()
                if idle_anim:
                    ret_task = f"atk_idle_{id(self)}_{id(move)}"
                    self._tasks.append(ret_task)
                    self._base.taskMgr.doMethodLater(
                        max(atk_dur, 0.5),
                        lambda t: attacker_ctrl.play(idle_anim, loop=True),
                        ret_task)

        # 5) on_complete callback
        if on_complete:
            total_dur = effect_delay + move_duration + 0.5
            cb_task = f"attack_cb_{id(self)}_{id(move)}"
            self._tasks.append(cb_task)
            self._base.taskMgr.doMethodLater(
                total_dur, lambda t: on_complete(), cb_task)

    def get_move(self, name):
        """Look up a move by name."""
        if self.move_database:
            return self.move_database.get_by_name(name)
        return None

    def get_moves_by_type(self, type_name):
        """Get all moves of a given type."""
        if self.move_database:
            return self.move_database.get_by_type(type_name)
        return []

    def get_all_moves(self):
        """Get all available moves."""
        if self.move_database:
            return self.move_database.get_all()
        return []

    def replay_last(self):
        """Replay the last executed move (requires same attacker/defender)."""
        return self._last_move

    def cleanup(self):
        """Clean up active effects."""
        if self.effect_manager:
            self.effect_manager.cleanup_all()
        for task_name in self._tasks:
            self._base.taskMgr.remove(task_name)
        self._tasks.clear()

    def destroy(self):
        """Full cleanup including EffectManager."""
        self.cleanup()
        if self.effect_manager:
            self.effect_manager.destroy()
            self.effect_manager = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_by_keywords(anim_list, keywords):
        """Find first animation matching any keyword."""
        for name in anim_list:
            nl = name.lower()
            for kw in keywords:
                if kw in nl:
                    return name
        return None

    @staticmethod
    def _get_height(actor):
        """Get model height from tight bounds."""
        if not actor or actor.isEmpty():
            return 0.0
        try:
            tb = actor.getTightBounds()
            if tb:
                return (tb[1] - tb[0]).getY()
        except Exception:
            pass
        return 0.0
