import os, sys, json, random
sys.path.insert(0, 'game')
from pathlib import Path
from panda3d.core import loadPrcFileData
loadPrcFileData('', 'window-type none')
loadPrcFileData('', 'audio-library-name null')
from direct.showbase.ShowBase import ShowBase
base = ShowBase()
from sdk import Pokemon as SDKPokemon, AnimationController

_MODELS_BASE = str(Path('models/pokemon').resolve())
with open('api/test.json') as f:
    data = json.load(f)

# Test 20 random pokemon
random.seed(42)
problems = []
for i in range(20):
    idx = random.randint(0, len(data) - 1)
    folder = data[idx].get('model_folder')
    if not folder:
        continue
    model_dir = os.path.join(_MODELS_BASE, folder)
    if not os.path.isdir(model_dir):
        continue
    try:
        p = SDKPokemon(base, model_dir, auto_center=False)
        ctrl = AnimationController(base, p, auto_idle=False)
        idle = ctrl.find_idle()
        has_wait = any('ba10' in n.lower() for n in p.anim_names)
        is_walk = idle and ('walk' in idle.lower() or 'fi20' in idle.lower())
        status = 'OK' if has_wait else 'FALLBACK'
        if is_walk:
            status = 'WALK AS IDLE!'
        print('%s: idle=%s [%s] (%d anims)' % (folder, idle, status, len(p.anim_names)))
        if is_walk:
            problems.append(folder)
        p.destroy()
    except Exception as e:
        print('%s: ERROR %s' % (folder, e))

if problems:
    print('\n!!! PROBLEM: these Pokemon have walk as idle:', problems)
else:
    print('\nAll OK - no Pokemon has walk as idle')
sys.exit(0)
