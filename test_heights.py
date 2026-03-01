import os, sys
sys.path.insert(0, 'game')
from pathlib import Path
from panda3d.core import loadPrcFileData
loadPrcFileData('', 'window-type none')
loadPrcFileData('', 'audio-library-name null')
from direct.showbase.ShowBase import ShowBase
base = ShowBase()
from sdk import Pokemon as SDKPokemon
_MODELS_BASE = str(Path('models/pokemon').resolve())
for folder in ['pm0001_00','pm0006_00','pm0006_81_00','pm0003_00','pm0004_00']:
    try:
        p = SDKPokemon(base, os.path.join(_MODELS_BASE, folder), auto_center=False)
        b = p.actor.getTightBounds()
        if b:
            h = abs(b[1].getZ()-b[0].getZ())
            print('%s: height=%.0f -> circle=%.0f' % (folder, h, 40*h/100))
        p.destroy()
    except Exception as e:
        print('%s: ERROR %s' % (folder, e))
sys.exit(0)
