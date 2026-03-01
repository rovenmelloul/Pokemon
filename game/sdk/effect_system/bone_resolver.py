"""Resolve Eff* bones on Panda3D Actors with intelligent fallback."""

# The 12 universal Eff* bones present on all Pokemon models.
UNIVERSAL_EFF_BONES = [
    "EffShoot01_01",
    "EffAttack01_01",
    "EffCenter01",
    "EffMouth01",
    "EffOverHead01",
    "EffFront01",
    "EffFoot01",
    "EffFoot02",
    "EffEye01",
    "EffEye02",
    "EffHeadCenter01",
    "EffGcloud01",
]

# Fallback chains: if the requested bone is missing, try these in order.
_FALLBACK_CHAINS = {
    "EffShoot01_01": ["EffAttack01_01", "EffCenter01"],
    "EffAttack01_01": ["EffShoot01_01", "EffCenter01"],
    "EffMouth01": ["EffHeadCenter01", "EffCenter01"],
    "EffOverHead01": ["EffHeadCenter01", "EffCenter01"],
    "EffFront01": ["EffCenter01"],
    "EffFoot01": ["EffFoot02", "EffCenter01"],
    "EffFoot02": ["EffFoot01", "EffCenter01"],
    "EffEye01": ["EffEye02", "EffHeadCenter01"],
    "EffEye02": ["EffEye01", "EffHeadCenter01"],
    "EffHeadCenter01": ["EffMouth01", "EffCenter01"],
    "EffGcloud01": ["EffCenter01"],
}


class BoneResolver:
    """Resolves bone names to exposed joint NodePaths on a Panda3D Actor."""

    def __init__(self):
        # Cache: (actor_id, bone_name) -> NodePath
        self._cache = {}

    def resolve(self, actor, bone_name):
        """Resolve a bone name to a NodePath on the given Actor.

        Tries the exact bone name first, then walks the fallback chain.
        Returns None if no bone could be resolved.
        """
        if actor is None or actor.isEmpty():
            return None

        cache_key = (id(actor), bone_name)
        if cache_key in self._cache:
            np = self._cache[cache_key]
            if np and not np.isEmpty():
                return np
            # Stale cache entry
            del self._cache[cache_key]

        # Try exact name
        np = self._try_expose(actor, bone_name)
        if np:
            self._cache[cache_key] = np
            return np

        # Try fallback chain
        chain = _FALLBACK_CHAINS.get(bone_name, [])
        for fallback in chain:
            np = self._try_expose(actor, fallback)
            if np:
                self._cache[cache_key] = np
                return np

        # Last resort: EffCenter01
        if bone_name != "EffCenter01":
            np = self._try_expose(actor, "EffCenter01")
            if np:
                self._cache[cache_key] = np
                return np

        return None

    def _try_expose(self, actor, bone_name):
        """Try to expose a joint by name. Returns NodePath or None."""
        try:
            joint = actor.exposeJoint(None, "modelRoot", bone_name)
            if joint and not joint.isEmpty():
                return joint
        except Exception:
            pass
        return None

    def get_available_bones(self, actor):
        """Return list of Eff* bone names that exist on this Actor."""
        if actor is None or actor.isEmpty():
            return []
        available = []
        try:
            joints = actor.getJoints()
        except Exception:
            return []
        joint_names = {j.getName() for j in joints if j.getName()}
        for bone in UNIVERSAL_EFF_BONES:
            if bone in joint_names:
                available.append(bone)
        return available

    def clear_cache(self):
        """Clear the resolution cache (call when actor changes)."""
        self._cache.clear()
