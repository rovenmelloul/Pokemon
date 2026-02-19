import os, sys, random, math
sys.path.insert(0, 'game')
from pathlib import Path
from panda3d.core import loadPrcFileData, Point3
loadPrcFileData('', 'window-type none')
loadPrcFileData('', 'audio-library-name null')
from direct.showbase.ShowBase import ShowBase
base = ShowBase()
from sdk import Pokemon as SDKPokemon, AnimationController

_MODELS_BASE = str(Path('models/pokemon').resolve())
model_dir = os.path.join(_MODELS_BASE, 'pm0001_00')
p = SDKPokemon(base, model_dir, auto_center=False)
ctrl = AnimationController(base, p, auto_idle=True)

# Check initial state
print("=== INIT ===")
print("ctrl.current_anim:", ctrl.current_anim)
print("actor.getCurrentAnim():", p.actor.getCurrentAnim())

# Explicit idle
idle = ctrl.find_idle()
walk = ctrl.find_anim("fi20", "walk")
print("\nidle name:", idle)
print("walk name:", walk)

ctrl.play(idle, loop=True)
base.taskMgr.step()
print("\n=== AFTER IDLE ===")
print("actor.getCurrentAnim():", p.actor.getCurrentAnim())

# Switch to walk
ctrl.play(walk, loop=True)
base.taskMgr.step()
print("\n=== AFTER WALK ===")
print("actor.getCurrentAnim():", p.actor.getCurrentAnim())

# Switch back to idle
ctrl.play(idle, loop=True)
base.taskMgr.step()
print("\n=== AFTER IDLE AGAIN ===")
print("actor.getCurrentAnim():", p.actor.getCurrentAnim())

# Check tight bounds for circle sizing
bounds = p.actor.getTightBounds()
if bounds:
    bmin, bmax = bounds
    h = abs(bmax.getZ() - bmin.getZ())
    print(f"\nModel height (Z): {h:.1f} -> circle multiplier: {h/100:.2f} -> scale: {40*h/100:.1f}")

sys.exit(0)
