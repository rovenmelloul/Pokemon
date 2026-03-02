
import os
os.chdir(r'C:\Users\Utilisateur\Desktop\Pokemon')
from panda3d.core import Filename, getModelPath
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
actor = Actor('models/trainers/black_belt/black_belt.bam')
actor.reparentTo(base.render)
actor.setH(0.001)
base.run()
