import os
os.chdir(r'C:\Users\Utilisateur\Desktop\Pokemon')
from panda3d.core import Filename, getModelPath, loadPrcFileData
loadPrcFileData('', 'load-display p3tinydisplay')
loadPrcFileData('', 'window-type offscreen')
loadPrcFileData('', 'audio-library-name null')
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor

base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
actor = Actor('models/trainers/black_belt/black_belt.bam')

# Check bounds
b = actor.getTightBounds()
if b:
    mn, mx = b
    print(f"Bounds min: {mn}")
    print(f"Bounds max: {mx}")
    print(f"Size X: {mx.x - mn.x:.3f}")
    print(f"Size Y: {mx.y - mn.y:.3f}")
    print(f"Size Z: {mx.z - mn.z:.3f}")
    tallest = max(mx.x-mn.x, mx.y-mn.y, mx.z-mn.z)
    if tallest == mx.z - mn.z:
        print("Tallest axis: Z (Z-up, correct for Panda3D)")
    elif tallest == mx.y - mn.y:
        print("Tallest axis: Y (Y-up, needs rotation)")
    else:
        print("Tallest axis: X (??)")

# Check joint hierarchy root
joints = actor.getJoints()
print(f"\nTotal joints: {len(joints)}")
for j in joints[:5]:
    print(f"  Joint: {j.getName()}")

# Check transform_index range
max_idx = 0
from panda3d.core import GeomVertexReader
for gn in actor.findAllMatches('**/+GeomNode'):
    node = gn.node()
    for gi in range(node.getNumGeoms()):
        geom = node.getGeom(gi)
        vdata = geom.getVertexData()
        reader = GeomVertexReader(vdata, 'transform_index')
        for i in range(vdata.getNumRows()):
            reader.setRow(i)
            d = reader.getData4i()
            for c in range(4):
                if d[c] > max_idx:
                    max_idx = d[c]
print(f"\nMax transform_index: {max_idx} (joints: {len(joints)})")
if max_idx >= len(joints):
    print("WARNING: transform_index exceeds joint count!")

# Check TransformBlendTable sizes
from panda3d.core import TransformBlendTable
for gn in actor.findAllMatches('**/+GeomNode'):
    node = gn.node()
    for gi in range(node.getNumGeoms()):
        geom = node.getGeom(gi)
        vdata = geom.getVertexData()
        tbt = vdata.getTransformBlendTable()
        if tbt:
            print(f"  {gn.getName()}: TransformBlendTable entries={tbt.getNumBlends()}, max_transforms={tbt.getMaxSimultaneousTransforms()}")
            break

base.destroy()
