import os, sys, json, random, math
sys.path.insert(0, 'game')
from pathlib import Path
from panda3d.core import loadPrcFileData, Point3, ClockObject
loadPrcFileData('', 'window-type none')
loadPrcFileData('', 'audio-library-name null')
from direct.showbase.ShowBase import ShowBase
base = ShowBase()
from sdk import Pokemon as SDKPokemon, AnimationController

_MODELS_BASE = str(Path('models/pokemon').resolve())

model_dir = os.path.join(_MODELS_BASE, 'pm0001_00')
p = SDKPokemon(base, model_dir, auto_center=False)
ctrl = AnimationController(base, p, auto_idle=True)

print("After auto_idle: current_anim =", ctrl.current_anim, "is_playing =", ctrl.is_playing)

# Simulate what move_randomly_task does
velocity = Point3(0)
is_moving = False
next_change_time = 0

for frame in range(20):
    fake_time = frame * 0.016  # ~60fps
    speed = velocity.length()

    if speed > 0.01:
        if not is_moving:
            walk = ctrl.find_anim("fi20", "walk")
            if walk:
                ctrl.play(walk, loop=True)
                print(f"  frame {frame}: PLAY WALK ({walk})")
            is_moving = True
    else:
        if is_moving:
            idle = ctrl.find_idle()
            if idle:
                ctrl.play(idle, loop=True)
                print(f"  frame {frame}: PLAY IDLE ({idle})")
            else:
                print(f"  frame {frame}: find_idle() returned None!")
            is_moving = False

    if fake_time >= next_change_time:
        if random.random() < 0.35:
            velocity = Point3(0)
            print(f"  frame {frame}: timer -> STOP (vel=0)")
        else:
            angle = random.uniform(0, 360)
            spd = random.uniform(0.5, 1.4)
            velocity = Point3(spd * math.cos(math.radians(angle)), spd * math.sin(math.radians(angle)), 0)
            print(f"  frame {frame}: timer -> MOVE (vel={velocity.length():.2f})")
        next_change_time = fake_time + random.uniform(1.0, 3.0)

    print(f"  frame {frame}: t={fake_time:.3f} is_moving={is_moving} speed={speed:.2f} anim={ctrl.current_anim}")

sys.exit(0)
