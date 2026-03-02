"""Test p3tinydisplay with full features: rotation + textures + controlJoint"""
import os
os.chdir(r'C:\Users\Utilisateur\Desktop\Pokemon')
from panda3d.core import Filename, getModelPath, loadPrcFileData, Texture
loadPrcFileData('', 'load-display p3tinydisplay')
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor

base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))

# Restore the original clean BAM (with all columns, doesn't matter for tinydisplay)
actor = Actor(Filename.fromOsSpecific(
    r'C:\Users\Utilisateur\Desktop\BlackBelt\fixed_model.bam').getFullpath())
actor.reparentTo(base.render)
actor.setScale(1)
actor.setHpr(180, -90, 0)

# Apply texture
model_dir = os.path.join('models', 'trainers', 'black_belt', 'images')
tex = Texture()
tex.read(Filename.fromOsSpecific(os.path.join(model_dir, 'tr0050_00_body_col.png')))
print(f"Texture loaded: {tex.getXSize()}x{tex.getYSize()}")

for gn in actor.findAllMatches('**/+GeomNode'):
    name = gn.getName().lower()
    if 'body' in name or 'leg' in name or 'dogi' in name:
        gn.setTexture(tex, 1)
        print(f"  Applied to {gn.getName()}")

# Test controlJoint
joint = actor.controlJoint(None, 'modelRoot', 'LThigh')
print(f"controlJoint LThigh: {joint}")

print("\nRENDER OK - starting base.run()")
base.run()
