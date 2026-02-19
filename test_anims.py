import os, sys, json
sys.path.insert(0, 'game')
from pathlib import Path
from panda3d.core import loadPrcFileData
loadPrcFileData('', 'window-type none')
loadPrcFileData('', 'audio-library-name null')
from direct.showbase.ShowBase import ShowBase
base = ShowBase()
from sdk import Pokemon as SDKPokemon, AnimationController

_MODELS_BASE = str(Path('models/pokemon').resolve())

# Test Bulbasaur
model_dir = os.path.join(_MODELS_BASE, 'pm0001_00')
p = SDKPokemon(base, model_dir, auto_center=False)
ctrl = AnimationController(base, p, auto_idle=False)
print('=== pm0001_00 ===')
print('total anims:', len(p.anim_names))
print('find_idle:', ctrl.find_idle())
print('find_walk:', ctrl.find_anim('fi20', 'walk'))
idle = ctrl.find_idle()
print('play idle result:', ctrl.play(idle, loop=True) if idle else 'NO IDLE')

# Test Grookey
with open('api/test.json') as f:
    data = json.load(f)
folder = data[0]['model_folder']
print('\n=== ' + folder + ' ===')
model_dir2 = os.path.join(_MODELS_BASE, folder)
p2 = SDKPokemon(base, model_dir2, auto_center=False)
ctrl2 = AnimationController(base, p2, auto_idle=False)
print('total anims:', len(p2.anim_names))
print('find_idle:', ctrl2.find_idle())
print('find_walk:', ctrl2.find_anim('fi20', 'walk'))

sys.exit(0)
