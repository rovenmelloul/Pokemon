
import os
os.chdir(r'C:\Users\Utilisateur\Desktop\Pokemon')
from panda3d.core import Filename, getModelPath, loadPrcFileData
loadPrcFileData('', 'gl-debug true')
loadPrcFileData('', 'gl-check-errors true')
loadPrcFileData('', 'notify-level-glgsg debug')
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
import sys
sys.stderr = open(r'C:\Users\Utilisateur\gl_debug.txt', 'w')
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
actor = Actor('models/trainers/black_belt/black_belt.bam')
actor.reparentTo(base.render)
actor.setH(180)
base.run()
