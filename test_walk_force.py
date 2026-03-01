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

# Test 5 random pokemon
random.seed(99)
for trial in range(5):
    idx = random.randint(0, len(data) - 1)
    folder = data[idx].get('model_folder')
    if not folder or not os.path.isdir(os.path.join(_MODELS_BASE, folder)):
        continue

    model_dir = os.path.join(_MODELS_BASE, folder)
    p = SDKPokemon(base, model_dir, auto_center=False)
    ctrl = AnimationController(base, p, auto_idle=True)

    walk = ctrl.find_anim("fi20", "walk")
    idle = ctrl.find_idle()
    print(f"\n=== {folder} ===")
    print(f"  idle={idle}, walk={walk}")

    # Force play walk
    if walk:
        result = ctrl.play(walk, loop=True)
        base.taskMgr.step()
        print(f"  play(walk) returned: {result}")
        print(f"  current_anim after walk: {ctrl.current_anim}")
        print(f"  actor.getCurrentAnim(): {p.actor.getCurrentAnim()}")

    # Force play idle
    if idle:
        result = ctrl.play(idle, loop=True)
        base.taskMgr.step()
        print(f"  play(idle) returned: {result}")
        print(f"  current_anim after idle: {ctrl.current_anim}")
        print(f"  actor.getCurrentAnim(): {p.actor.getCurrentAnim()}")

    # Simulate full move_randomly logic for 500 frames (8+ seconds)
    velocity = Point3(0)
    is_moving = False
    next_change_time = 2.0
    walk_count = 0
    idle_count = 0

    for frame in range(500):
        t = frame * 0.016
        speed = velocity.length()
        if speed > 0.01:
            if not is_moving:
                w = ctrl.find_anim("fi20", "walk")
                if w:
                    ctrl.play(w, loop=True)
                    walk_count += 1
                is_moving = True
        else:
            if is_moving:
                i = ctrl.find_idle()
                if i:
                    ctrl.play(i, loop=True)
                    idle_count += 1
                is_moving = False

        if t >= next_change_time:
            if random.random() < 0.35:
                velocity = Point3(0)
            else:
                angle = random.uniform(0, 360)
                spd = random.uniform(0.5, 1.4)
                velocity = Point3(
                    spd * math.cos(math.radians(angle)),
                    spd * math.sin(math.radians(angle)),
                    0)
            next_change_time = t + random.uniform(1.0, 3.0)

    print(f"  Over 8 sec: walk played {walk_count}x, idle played {idle_count}x")
    p.destroy()

sys.exit(0)
