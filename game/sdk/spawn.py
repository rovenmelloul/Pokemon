"""Pokemon model loader with rendering corrections for Panda3D.

Loads a Pokemon .egg model as a Panda3D Actor, applies all necessary
rendering fixes (transparency, emission, eye decals, normal maps),
loads animations and UV animation sidecars, and initializes the
eye/mouth sprite-sheet system.

Usage:
    from sdk.spawn import Pokemon
    poke = Pokemon(base, "output/pokemon/pm0025_00")
    poke.actor.reparentTo(base.render)
"""
import os
import re
import json
import copy

from direct.actor.Actor import Actor
from panda3d.core import (
    Filename, MaterialAttrib, TextureAttrib, TextureStage,
    TransparencyAttrib, AlphaTestAttrib, ColorBlendAttrib,
    CullFaceAttrib, RenderAttrib, GeomNode, LColor,
    GeomVertexReader, GeomVertexWriter, InternalName,
    SamplerState, Texture, PNMImage,
)

# ===== CONFIGURATION =====
CONFIG = {
    "pokemon_subdir": "pokemon",
    "double_sided": True,
    "emission_color": (0.3, 0.3, 0.3, 1.0),
    "core_bin_order": 5,
    "mask_bin_order": 10,
    "mask_alpha_threshold": 0.5,
    "default_eye_offset": (0.0, 0.0),
    "default_mouth_offset": (-0.5, 0.0),
    "uvanim_material_patterns": ["Fire", "Flame", "Effect", "Core", "Mask", "Water", "Electric"],
    "hidden_material_patterns": ["IncNon"],
    "core_material_re": r'^([A-Z][a-z]+)Core',
    "mask_material_re": r'^([A-Z][a-z]+)Mask',
    "red_min_r": 200, "red_max_g": 50, "red_max_b": 50,
}


class Pokemon:
    """A Pokemon model with rendering corrections, animations, and UV system.

    Wraps a Panda3D Actor with all the fixes needed for correct rendering
    of SwSh-exported .egg models.

    Args:
        base: ShowBase instance
        model_dir: path to the pokemon folder (contains .egg + anims/)
        use_shiny: if True, load the _rare.egg variant
        auto_center: if True, center the model at origin
        config: optional dict to override CONFIG defaults
    """

    def __init__(self, base, model_dir, use_shiny=False, auto_center=True, config=None):
        self._base = base
        self._config = {**CONFIG, **(config or {})}
        self._model_dir = os.path.abspath(model_dir)
        self._is_shiny = use_shiny
        self._tasks = []

        # Public state
        self.actor = None
        self.name = os.path.basename(self._model_dir)
        self.anim_names = []
        self.uvanim_data = {}
        self.mat_meta = None
        self.height = 0.0
        self.bounds_size = 0.0

        # Internal UV state
        self._eye_mouth_geom_data = []
        self._eye_mouth_current_offset = {}
        self._eye_mouth_uv_scale = {}
        self._iris_eye_offset = {}
        self._red_translate_positions = {}
        self._uvanim_mat_nps = {}
        self._hidden_geometry_nps = []
        self._outline_geometry_nps = []

        # Load
        self._load(auto_center)

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def model_dir(self):
        return self._model_dir

    @property
    def is_shiny(self):
        return self._is_shiny

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def destroy(self):
        """Clean up the Actor and all associated tasks."""
        for task_name in self._tasks:
            self._base.taskMgr.remove(task_name)
        self._tasks.clear()
        if self.actor:
            self.actor.cleanup()
            self.actor.removeNode()
            self.actor = None

    def apply_default_face(self):
        """Apply the default face expression (iris-aware eye + happy mouth)."""
        changed = False
        for gn, gi, mname, *_ in self._eye_mouth_geom_data:
            mlow = mname.lower()
            su, sv = self._eye_mouth_uv_scale.get(mname, (1.0, 1.0))
            if "eye" in mlow:
                if mlow in self._iris_eye_offset:
                    tu, tv = self._iris_eye_offset[mlow]
                else:
                    tu, tv = self._config["default_eye_offset"]
                if self.set_eye_mouth_uv(mname, tu * su, tv * sv):
                    changed = True
            elif "mouth" in mlow:
                tu, tv = self._config["default_mouth_offset"]
                if self.set_eye_mouth_uv(mname, tu * su, tv * sv):
                    changed = True
        return changed

    def set_eye_mouth_uv(self, mat_name, du, dv):
        """Set absolute UV offset for an eye/mouth material.

        Returns True if the offset changed, False if already current.
        """
        current = self._eye_mouth_current_offset.get(mat_name)
        if current == (du, dv):
            return False

        for gn, gi, mname, base_uvs, *_ in self._eye_mouth_geom_data:
            if mname != mat_name:
                continue
            geom = gn.modifyGeom(gi)
            vdata = geom.modifyVertexData()
            writer = GeomVertexWriter(vdata, InternalName.getTexcoord())
            for bu, bv in base_uvs:
                writer.setData2f(bu + du, bv + dv)

        self._eye_mouth_current_offset[mat_name] = (du, dv)
        return True

    def get_eye_mouth_uv_scale(self, mat_name):
        """Return (scale_u, scale_v) for an eye/mouth material."""
        return self._eye_mouth_uv_scale.get(mat_name, (1.0, 1.0))

    def get_uvanim_mat_nps(self):
        """Return dict of material_name -> [NodePath] for UV scroll."""
        return dict(self._uvanim_mat_nps)

    def get_iris_eye_offset(self, mat_name):
        """Return auto-detected (du, dv) for an iris eye material."""
        return self._iris_eye_offset.get(mat_name.lower(),
                                         self._config["default_eye_offset"])

    def get_red_tile_positions(self, mat_name):
        """Return set of (du, dv) positions to avoid (red placeholders)."""
        return self._red_translate_positions.get(mat_name.lower(), set())

    # ------------------------------------------------------------------
    # Static utilities
    # ------------------------------------------------------------------

    @staticmethod
    def list_available(output_dir):
        """List available Pokemon model directories under output_dir/pokemon/."""
        pokemon_dir = os.path.join(output_dir, "pokemon")
        if not os.path.isdir(pokemon_dir):
            return []
        result = []
        for folder in sorted(os.listdir(pokemon_dir)):
            folder_path = os.path.join(pokemon_dir, folder)
            if not os.path.isdir(folder_path):
                continue
            egg_files = [f for f in os.listdir(folder_path)
                         if f.endswith(".egg") and "_rare" not in f]
            if egg_files:
                result.append(folder_path)
        return result

    # ------------------------------------------------------------------
    # Internal: loading pipeline
    # ------------------------------------------------------------------

    def _load(self, auto_center):
        """Full loading pipeline."""
        # 1. Find egg file
        egg_path = self._find_egg()
        if not egg_path:
            raise FileNotFoundError(
                f"No .egg file found in {self._model_dir}")

        # 2. Load Actor
        panda_path = Filename.fromOsSpecific(egg_path)
        self.actor = Actor(panda_path)
        if self.actor.isEmpty():
            raise RuntimeError(f"Empty model: {egg_path}")

        # 3. Double-sided
        if self._config["double_sided"]:
            self.actor.setTwoSided(True)

        # 4. Load material metadata
        self._load_mat_meta(egg_path)

        # 5. Apply rendering corrections (order matters)
        self._apply_effect_group_transparency()
        self._hide_hidden_geometry()
        self._apply_emission_glow()
        self._strip_normal_map_stages()
        self._fix_eye_decal_lighting()

        # 6. Load animations
        self._load_animations()

        # 7. Load UV animation sidecars
        self._load_uvanim_sidecars()

        # 8. Build material -> NodePath mapping for UV scroll
        self._build_uvanim_mat_nps()

        # 9. Initialize eye/mouth UV system
        self._init_eye_mouth_uvanim(egg_path)

        # 10. Auto-center
        if auto_center:
            self._auto_center()

    def _find_egg(self):
        """Find the .egg file in model_dir."""
        if not os.path.isdir(self._model_dir):
            return None
        candidates = []
        for f in os.listdir(self._model_dir):
            if self._is_shiny:
                if f.endswith("_rare.egg"):
                    candidates.append(f)
            else:
                if f.endswith(".egg") and "_rare" not in f:
                    candidates.append(f)
        if candidates:
            return os.path.join(self._model_dir, sorted(candidates)[0])
        return None

    def _load_mat_meta(self, egg_path):
        """Load _meta.json for the model."""
        meta_path = os.path.splitext(egg_path)[0] + "_meta.json"
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r") as f:
                    self.mat_meta = json.load(f)
            except Exception:
                self.mat_meta = None
        else:
            self.mat_meta = None

    def _load_animations(self):
        """Load all .egg animations from the anims/ subdirectory."""
        anims_dir = os.path.join(self._model_dir, "anims")
        if not os.path.isdir(anims_dir):
            return
        anim_dict = {}
        for f in sorted(os.listdir(anims_dir)):
            if f.endswith(".egg"):
                anim_dict[os.path.splitext(f)[0]] = Filename.fromOsSpecific(
                    os.path.join(anims_dir, f))
        if anim_dict:
            self.actor.loadAnims(anim_dict)
            self.anim_names = sorted(self.actor.getAnimNames())

    def _load_uvanim_sidecars(self):
        """Load .uvanim JSON sidecars from anims/ directory."""
        anims_dir = os.path.join(self._model_dir, "anims")
        if not os.path.isdir(anims_dir):
            return
        for f in os.listdir(anims_dir):
            if f.endswith(".uvanim"):
                anim_name = os.path.splitext(f)[0]
                try:
                    with open(os.path.join(anims_dir, f), "r") as uf:
                        self.uvanim_data[anim_name] = json.load(uf)
                except Exception:
                    pass

    def _build_uvanim_mat_nps(self):
        """Build material_name -> [NodePath] mapping for UV animation."""
        self._uvanim_mat_nps = {}
        if not self.actor or not self.mat_meta:
            return
        for gnp in self.actor.findAllMatches("**/+GeomNode"):
            geom_node = gnp.node()
            for gi in range(geom_node.getNumGeoms()):
                state = geom_node.getGeomState(gi)
                mat_attr = state.getAttrib(MaterialAttrib)
                if mat_attr:
                    panda_mat = mat_attr.getMaterial()
                    if panda_mat:
                        mname = panda_mat.getName()
                        if mname:
                            self._uvanim_mat_nps.setdefault(
                                mname, []).append(gnp)

    def _auto_center(self):
        """Center the model at origin and compute size metrics."""
        bounds = self.actor.getTightBounds()
        if bounds:
            bmin, bmax = bounds
            center = (bmin + bmax) / 2
            size_vec = bmax - bmin
            self.height = size_vec.getY()  # Y-up
            self.bounds_size = size_vec.length()
            self.actor.setPos(-center.getX(), -center.getY(), -center.getZ())
        else:
            self.height = 0.0
            self.bounds_size = 0.0

    # ------------------------------------------------------------------
    # Rendering corrections
    # ------------------------------------------------------------------

    def _apply_effect_group_transparency(self):
        """Core/Mask materials: additive blend for fire/smoke effects."""
        cfg = self._config
        _CORE_RE = re.compile(cfg["core_material_re"])
        _MASK_RE = re.compile(cfg["mask_material_re"])

        for gnp in self.actor.findAllMatches("**/+GeomNode"):
            src_gn = gnp.node()
            effect_core = []
            effect_mask = []
            for gi in range(src_gn.getNumGeoms()):
                state = src_gn.getGeomState(gi)
                mat_attr = state.getAttrib(MaterialAttrib)
                if not mat_attr or not mat_attr.getMaterial():
                    continue
                name = mat_attr.getMaterial().getName()
                if _CORE_RE.match(name):
                    effect_core.append(gi)
                elif _MASK_RE.match(name):
                    effect_mask.append(gi)

            # Core: additive glow (OOne, OOne)
            if effect_core:
                core_gn = GeomNode("effect_core_geo")
                for gi in effect_core:
                    geom = src_gn.modifyGeom(gi)
                    state = src_gn.getGeomState(gi)
                    core_gn.addGeom(geom.makeCopy(), state)
                core_np = gnp.attachNewNode(core_gn)
                core_np.setLightOff()
                core_np.setAttrib(ColorBlendAttrib.make(
                    ColorBlendAttrib.MAdd,
                    ColorBlendAttrib.OOne,
                    ColorBlendAttrib.OOne))
                core_np.setDepthTest(True)
                core_np.setDepthWrite(False)
                core_np.setBin("fixed", cfg["core_bin_order"])
                core_np.setAttrib(CullFaceAttrib.make(
                    CullFaceAttrib.MCullClockwise))

            # Mask: additive + alpha test
            if effect_mask:
                mask_gn = GeomNode("effect_mask_geo")
                for gi in effect_mask:
                    geom = src_gn.modifyGeom(gi)
                    state = src_gn.getGeomState(gi)
                    state = state.removeAttrib(TransparencyAttrib)
                    mask_gn.addGeom(geom.makeCopy(), state)
                mask_np = gnp.attachNewNode(mask_gn)
                mask_np.setAttrib(AlphaTestAttrib.make(
                    RenderAttrib.MGreaterEqual, cfg["mask_alpha_threshold"]))
                mask_np.setAttrib(ColorBlendAttrib.make(
                    ColorBlendAttrib.MAdd,
                    ColorBlendAttrib.OIncomingAlpha,
                    ColorBlendAttrib.OOne))
                mask_np.setDepthTest(True)
                mask_np.setDepthWrite(False)
                mask_np.setBin("fixed", cfg["mask_bin_order"])
                mask_np.setLightOff()
                mask_np.setAttrib(CullFaceAttrib.make(
                    CullFaceAttrib.MCullClockwise))

            # Remove original effect geoms from parent
            all_effect = effect_core + effect_mask
            for gi in sorted(all_effect, reverse=True):
                src_gn.removeGeom(gi)

    def _hide_hidden_geometry(self):
        """Hide particle/emitter/outline/IncNon geometry."""
        self._hidden_geometry_nps = []
        self._outline_geometry_nps = []

        # Method 1: by group name
        for np in self.actor.findAllMatches("**/hidden_geometry"):
            np.hide()
            self._hidden_geometry_nps.append(np)
        for np in self.actor.findAllMatches("**/outline_geometry"):
            np.hide()
            self._outline_geometry_nps.append(np)

        # Method 2: remove IncNon geoms from shared GeomNodes
        hide_patterns = self._config["hidden_material_patterns"]
        for gnp in self.actor.findAllMatches("**/+GeomNode"):
            gn = gnp.node()
            remove_indices = []
            for gi in range(gn.getNumGeoms()):
                state = gn.getGeomState(gi)
                mat_attr = state.getAttrib(MaterialAttrib)
                if not mat_attr or not mat_attr.getMaterial():
                    continue
                mat_name = mat_attr.getMaterial().getName()
                if any(pat in mat_name for pat in hide_patterns):
                    remove_indices.append(gi)
            for gi in sorted(remove_indices, reverse=True):
                gn.removeGeom(gi)

    def _apply_emission_glow(self):
        """Boost additive emission TextureStages (antennae glow)."""
        emission_color = LColor(*self._config["emission_color"])
        glow_count = 0
        processed_nps = set()

        for gnp in self.actor.findAllMatches("**/+GeomNode"):
            gn = gnp.node()
            for gi in range(gn.getNumGeoms()):
                state = gn.getGeomState(gi)
                tex_attr = state.getAttrib(TextureAttrib)
                if not tex_attr:
                    continue
                has_add_stage = False
                for si in range(tex_attr.getNumOnStages()):
                    ts = tex_attr.getOnStage(si)
                    if ts.getMode() == TextureStage.MAdd:
                        has_add_stage = True
                        break
                if not has_add_stage:
                    continue
                mat_attr = state.getAttrib(MaterialAttrib)
                if mat_attr and mat_attr.getMaterial():
                    mat_name = mat_attr.getMaterial().getName()
                    if "Core" in mat_name or "Mask" in mat_name:
                        continue
                gnp_id = id(gn)
                if gnp_id not in processed_nps:
                    processed_nps.add(gnp_id)
                glow_count += 1

        if glow_count:
            for gnp in self.actor.findAllMatches("**/+GeomNode"):
                gn = gnp.node()
                has_emission = False
                for gi in range(gn.getNumGeoms()):
                    state = gn.getGeomState(gi)
                    tex_attr = state.getAttrib(TextureAttrib)
                    if not tex_attr:
                        continue
                    for si in range(tex_attr.getNumOnStages()):
                        ts = tex_attr.getOnStage(si)
                        if ts.getMode() == TextureStage.MAdd:
                            tex = tex_attr.getOnTexture(ts)
                            if tex:
                                ts.setColor(LColor(1, 1, 1, 1))
                                has_emission = True
                            break
                if has_emission:
                    for gi in range(gn.getNumGeoms()):
                        state = gn.getGeomState(gi)
                        mat_attr = state.getAttrib(MaterialAttrib)
                        if mat_attr and mat_attr.getMaterial():
                            mat = mat_attr.getMaterial()
                            mat.setEmission(emission_color)

    def _fix_eye_decal_lighting(self):
        """Restructure MDecal eye stages so they receive vertex lighting."""
        # Create a 1x1 white texture for the lighting combine stage
        white_img = PNMImage(1, 1)
        white_img.fill(1, 1, 1)
        white_img.addAlpha()
        white_img.setAlpha(0, 0, 1)
        white_tex = Texture("eye_lighting_white")
        white_tex.load(white_img)

        for gnp in self.actor.findAllMatches("**/+GeomNode"):
            gn = gnp.node()
            for gi in range(gn.getNumGeoms()):
                state = gn.getGeomState(gi)
                mat_attr = state.getAttrib(MaterialAttrib)
                if not mat_attr or not mat_attr.getMaterial():
                    continue
                mname = mat_attr.getMaterial().getName().lower()
                if 'eye' not in mname:
                    continue

                tex_attr = state.getAttrib(TextureAttrib)
                if not tex_attr:
                    continue

                decal_stage = None
                modulate_stage = None
                for si in range(tex_attr.getNumOnStages()):
                    ts = tex_attr.getOnStage(si)
                    if ts.getMode() == TextureStage.MDecal:
                        decal_stage = ts
                    elif ts.getMode() == TextureStage.MModulate:
                        modulate_stage = ts

                if not decal_stage or not modulate_stage:
                    continue

                iris_tex = tex_attr.getOnTexture(modulate_stage)
                replace_ts = TextureStage(
                    modulate_stage.getName() + "_replace")
                replace_ts.setSort(modulate_stage.getSort())
                replace_ts.setMode(TextureStage.MReplace)
                replace_ts.setTexcoordName(
                    modulate_stage.getTexcoordName())

                lighting_ts = TextureStage("eye_lighting")
                lighting_ts.setSort(decal_stage.getSort() + 5)
                lighting_ts.setCombineRgb(
                    TextureStage.CMModulate,
                    TextureStage.CSPrevious,
                    TextureStage.COSrcColor,
                    TextureStage.CSPrimaryColor,
                    TextureStage.COSrcColor)
                lighting_ts.setCombineAlpha(
                    TextureStage.CMReplace,
                    TextureStage.CSPrevious,
                    TextureStage.COSrcAlpha)

                new_attr = tex_attr.removeOnStage(modulate_stage)
                new_attr = new_attr.addOnStage(replace_ts, iris_tex)
                new_attr = new_attr.addOnStage(lighting_ts, white_tex)
                new_state = state.removeAttrib(TextureAttrib)
                new_state = new_state.addAttrib(new_attr)
                gn.setGeomState(gi, new_state)

    def _strip_normal_map_stages(self):
        """Remove MNormal TextureStages (not supported without shader)."""
        for gnp in self.actor.findAllMatches("**/+GeomNode"):
            gn = gnp.node()
            for gi in range(gn.getNumGeoms()):
                state = gn.getGeomState(gi)
                tex_attr = state.getAttrib(TextureAttrib)
                if not tex_attr:
                    continue
                stages_to_remove = []
                for si in range(tex_attr.getNumOnStages()):
                    ts = tex_attr.getOnStage(si)
                    if ts.getMode() == TextureStage.MNormal:
                        stages_to_remove.append(ts)
                if stages_to_remove:
                    new_attr = tex_attr
                    for ts in stages_to_remove:
                        new_attr = new_attr.removeOnStage(ts)
                    new_state = state.removeAttrib(TextureAttrib)
                    new_state = new_state.addAttrib(new_attr)
                    gn.setGeomState(gi, new_state)

    # ------------------------------------------------------------------
    # Eye/mouth UV system
    # ------------------------------------------------------------------

    def _init_eye_mouth_uvanim(self, egg_path):
        """Initialize eye/mouth UV animation system."""
        self._eye_mouth_geom_data = []
        self._eye_mouth_current_offset = {}
        self._eye_mouth_uv_scale = {}

        # Load UV scale from _meta.json
        if self.mat_meta:
            for mat in self.mat_meta.get("materials", []):
                mname = mat.get("name", "")
                if not any(p.lower() in mname.lower()
                           for p in ("Eye", "Mouth")):
                    continue
                su, sv = 1.0, 1.0
                for v in mat.get("values", []):
                    vn = v.get("name", "")
                    if vn == "ColorUVScaleU":
                        su = v.get("value", 1.0)
                    elif vn == "ColorUVScaleV":
                        sv = v.get("value", 1.0)
                self._eye_mouth_uv_scale[mname] = (su, sv)

        # Walk geoms for eye/mouth materials
        for gnp in self.actor.findAllMatches("**/+GeomNode"):
            gn = gnp.node()
            for gi in range(gn.getNumGeoms()):
                state = gn.getGeomState(gi)
                mat_attr = state.getAttrib(MaterialAttrib)
                if not mat_attr:
                    continue
                mat = mat_attr.getMaterial()
                if not mat:
                    continue
                mname = mat.getName()
                if not any(p.lower() in mname.lower()
                           for p in ("Eye", "Mouth")):
                    continue

                # Copy-on-write for vertex data
                geom = gn.modifyGeom(gi)
                vdata = geom.modifyVertexData()

                # Store base UVs
                reader = GeomVertexReader(vdata, InternalName.getTexcoord())
                base_uvs = []
                while not reader.isAtEnd():
                    uv = reader.getData2f()
                    base_uvs.append((uv.getX(), uv.getY()))

                # Force wrap modes
                for ts in gnp.findAllTextureStages():
                    tex = gnp.findTexture(ts)
                    if tex:
                        tex.setWrapU(SamplerState.WM_mirror)
                        tex.setWrapV(SamplerState.WM_repeat)

                # Find used vertices
                used_verts = set()
                for pi in range(geom.getNumPrimitives()):
                    prim = geom.getPrimitive(pi)
                    prim_d = prim.decompose()
                    for vi in range(prim_d.getNumVertices()):
                        used_verts.add(prim_d.getVertex(vi))

                g_us = [base_uvs[vi][0] for vi in sorted(used_verts)
                        if vi < len(base_uvs)]
                g_vs = [base_uvs[vi][1] for vi in sorted(used_verts)
                        if vi < len(base_uvs)]
                u_lo = min(g_us) if g_us else 0.0
                u_hi = max(g_us) if g_us else 0.0
                v_lo = min(g_vs) if g_vs else 0.0
                v_hi = max(g_vs) if g_vs else 0.0

                self._eye_mouth_geom_data.append(
                    (gn, gi, mname, base_uvs, u_lo, u_hi, v_lo, v_hi))
                self._eye_mouth_current_offset[mname] = (0.0, 0.0)

        # Detect red placeholders and auto-detect iris offsets
        self._iris_eye_offset = {}
        self._red_translate_positions = {}
        self._detect_red_tiles_and_iris(egg_path)

        # Apply default face
        self.apply_default_face()

    def _detect_red_tiles_and_iris(self, egg_path):
        """Detect red placeholder tiles and auto-detect best iris offset."""
        try:
            from PIL import Image as PILImage
        except ImportError:
            return

        cfg = self._config

        # Load eye/mouth textures
        tex_images = {}
        for fn in os.listdir(self._model_dir):
            fnl = fn.lower()
            if not fnl.endswith('.png') or '_col' not in fnl:
                continue
            if 'nor' in fnl or 'rare' in fnl:
                continue
            if 'eye' in fnl:
                tex_images['eye'] = PILImage.open(
                    os.path.join(self._model_dir, fn)).convert("RGBA")
            elif 'mouth' in fnl:
                tex_images['mouth'] = PILImage.open(
                    os.path.join(self._model_dir, fn)).convert("RGBA")

        # Detect red tiles for each eye/mouth material
        for gn, gi, mname, base_uvs, u_lo, u_hi, v_lo, v_hi in self._eye_mouth_geom_data:
            mlow = mname.lower()
            if mlow in self._red_translate_positions:
                continue
            su, sv = self._eye_mouth_uv_scale.get(mname, (1.0, 1.0))
            u_center = (u_lo + u_hi) / 2.0
            v_center = (v_lo + v_hi) / 2.0

            img = None
            if 'eye' in mlow and 'eye' in tex_images:
                img = tex_images['eye']
            elif 'mouth' in mlow and 'mouth' in tex_images:
                img = tex_images['mouth']
            if img is None:
                continue

            w, h = img.size
            red_translates = set()
            for du_raw in [0.0, -0.5]:
                for dv_raw in [0.0, 0.25, 0.5, 0.75]:
                    du_sc = du_raw * su
                    dv_sc = dv_raw * sv
                    fu = u_center + du_sc
                    fv = v_center + dv_sc
                    # Mirror wrap U
                    u_mod = fu % 2.0
                    if u_mod < 0:
                        u_mod += 2.0
                    if u_mod > 1.0:
                        u_mod = 2.0 - u_mod
                    # Repeat wrap V
                    v_mod = fv % 1.0
                    if v_mod < 0:
                        v_mod += 1.0
                    px_x = min(int(u_mod * w), w - 1)
                    px_y = min(int((1.0 - v_mod) * h), h - 1)
                    is_red = False
                    for dx in [-2, 0, 2]:
                        for dy in [-2, 0, 2]:
                            sx = max(0, min(px_x + dx, w - 1))
                            sy = max(0, min(px_y + dy, h - 1))
                            p = img.getpixel((sx, sy))[:3]
                            if (p[0] > cfg["red_min_r"] and
                                    p[1] < cfg["red_max_g"] and
                                    p[2] < cfg["red_max_b"]):
                                is_red = True
                                break
                        if is_red:
                            break
                    if is_red:
                        red_translates.add(
                            (round(du_raw, 2), round(dv_raw, 2)))
            if red_translates:
                self._red_translate_positions[mlow] = red_translates

        # Auto-detect iris offset (transparent pixel method)
        for gn, gi, mname, base_uvs, u_lo, u_hi, v_lo, v_hi in self._eye_mouth_geom_data:
            mlow = mname.lower()
            if 'eye' not in mlow or mlow in self._iris_eye_offset:
                continue
            img = tex_images.get('eye')
            if img is None:
                continue
            w, h = img.size
            su, sv = self._eye_mouth_uv_scale.get(mname, (1.0, 1.0))
            red_set = self._red_translate_positions.get(mlow, set())
            best_offset = None
            best_transparent = 0
            for du_raw in [0.0, -0.5]:
                for dv_raw in [0.0, 0.25, 0.5, 0.75]:
                    if (round(du_raw, 2), round(dv_raw, 2)) in red_set:
                        continue
                    du_sc = du_raw * su
                    dv_sc = dv_raw * sv
                    transparent = 0
                    for bu, bv in base_uvs:
                        fu = bu + du_sc
                        fv = bv + dv_sc
                        u_mod = abs(fu) % 2.0
                        if u_mod > 1.0:
                            u_mod = 2.0 - u_mod
                        v_mod = fv % 1.0
                        if v_mod < 0:
                            v_mod += 1.0
                        px_x = min(int(u_mod * w), w - 1)
                        px_y = min(int((1.0 - v_mod) * h), h - 1)
                        if img.getpixel((px_x, px_y))[3] < 128:
                            transparent += 1
                    if transparent > best_transparent:
                        best_transparent = transparent
                        best_offset = (du_raw, dv_raw)
            if best_offset and best_transparent > 0:
                self._iris_eye_offset[mlow] = best_offset
            else:
                # Fallback: color variance method
                self._detect_iris_by_variance(
                    mname, base_uvs, u_lo, u_hi, v_lo, v_hi,
                    img, red_set)

    def _detect_iris_by_variance(self, mname, base_uvs, u_lo, u_hi,
                                 v_lo, v_hi, img, red_set):
        """Fallback iris detection using color variance."""
        import statistics
        mlow = mname.lower()
        su, sv = self._eye_mouth_uv_scale.get(mname, (1.0, 1.0))
        w, h = img.size

        offset_variances = {}
        for du_raw in [0.0, -0.5]:
            for dv_raw in [0.0, 0.25, 0.5, 0.75]:
                if (round(du_raw, 2), round(dv_raw, 2)) in red_set:
                    continue
                du_sc = du_raw * su
                dv_sc = dv_raw * sv
                pixels_r, pixels_g, pixels_b = [], [], []
                sample_count = min(len(base_uvs), 40)
                step = max(1, len(base_uvs) // sample_count)
                for idx_s in range(0, len(base_uvs), step):
                    bu, bv = base_uvs[idx_s]
                    fu = bu + du_sc
                    fv = bv + dv_sc
                    u_mod = abs(fu) % 2.0
                    if u_mod > 1.0:
                        u_mod = 2.0 - u_mod
                    v_mod = fv % 1.0
                    if v_mod < 0:
                        v_mod += 1.0
                    px_x = min(int(u_mod * w), w - 1)
                    px_y = min(int((1.0 - v_mod) * h), h - 1)
                    p = img.getpixel((px_x, px_y))[:3]
                    pixels_r.append(p[0])
                    pixels_g.append(p[1])
                    pixels_b.append(p[2])
                if pixels_r and len(pixels_r) > 1:
                    var_r = statistics.pvariance(pixels_r)
                    var_g = statistics.pvariance(pixels_g)
                    var_b = statistics.pvariance(pixels_b)
                    offset_variances[(du_raw, dv_raw)] = var_r + var_g + var_b

        if offset_variances:
            default_var = offset_variances.get((0.0, 0.0), 0)
            best_off = max(offset_variances, key=offset_variances.get)
            best_var = offset_variances[best_off]
            if best_var > 100 and default_var < best_var * 0.4:
                self._iris_eye_offset[mlow] = best_off
