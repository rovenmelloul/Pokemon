import os, sys, random, math, json
sys.path.insert(0, 'game')
from pathlib import Path
from panda3d.core import loadPrcFileData, Point3
loadPrcFileData('', 'window-type none')
loadPrcFileData('', 'audio-library-name null')
from direct.showbase.ShowBase import ShowBase
base = ShowBase()
from sdk import Pokemon as SDKPokemon, AnimationController

_MODELS_BASE = str(Path('models/pokemon').resolve())
with open('api/test.json') as f:
    data = json.load(f)

# Pick a random pokemon with a model
random.seed(42)
for _ in range(50):
    idx = random.randint(0, len(data) - 1)
    folder = data[idx].get('model_folder')
    if folder and os.path.isdir(os.path.join(_MODELS_BASE, folder)):
        break

print("Testing:", folder)
model_dir = os.path.join(_MODELS_BASE, folder)
p = SDKPokemon(base, model_dir, auto_center=False)
ctrl = AnimationController(base, p, auto_idle=True)

# Check what find_anim returns
walk = ctrl.find_anim("fi20", "walk")
idle = ctrl.find_idle()
print("find_idle():", idle)
print("find_anim('fi20', 'walk'):", walk)
print("All anims:", p.anim_names)

# Simulate the task logic
velocity = Point3(0)
is_moving = False
next_change_time = 2.0

for frame in range(200):
    t = frame * 0.016  # ~60fps
    speed = velocity.length()

    if speed > 0.01:
        if not is_moving:
            walk_anim = ctrl.find_anim("fi20", "walk")
            if walk_anim:
                ctrl.play(walk_anim, loop=True)
                print(f"  t={t:.2f}: PLAY WALK ({walk_anim}), current_anim={ctrl.current_anim}")
            is_moving = True
    else:
        if is_moving:
            idle_anim = ctrl.find_idle()
            if idle_anim:
                ctrl.play(idle_anim, loop=True)
                print(f"  t={t:.2f}: PLAY IDLE ({idle_anim}), current_anim={ctrl.current_anim}")
            is_moving = False

    if t >= next_change_time:
        if random.random() < 0.35:
            velocity = Point3(0)
            print(f"  t={t:.2f}: -> STOP (velocity=0)")
        else:
            angle = random.uniform(0, 360)
            spd = random.uniform(0.5, 1.4)
            velocity = Point3(
                spd * math.cos(math.radians(angle)),
                spd * math.sin(math.radians(angle)),
                0)
            print(f"  t={t:.2f}: -> MOVE (velocity={velocity.length():.2f})")
        next_change_time = t + random.uniform(1.0, 3.0)

    base.taskMgr.step()

print("\nFinal state: is_moving=%s, current_anim=%s" % (is_moving, ctrl.current_anim))
p.destroy()
sys.exit(0)
