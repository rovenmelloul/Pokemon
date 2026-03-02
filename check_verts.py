import os, math
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

# Check all vertex data
nan_count = 0
inf_count = 0
huge_count = 0
max_val = 0
total_verts = 0
problem_nodes = []

for gn in actor.findAllMatches('**/+GeomNode'):
    node = gn.node()
    for gi in range(node.getNumGeoms()):
        geom = node.getGeom(gi)
        vdata = geom.getVertexData()
        fmt = vdata.getFormat()
        n = vdata.getNumRows()
        total_verts += n
        
        for col_idx in range(fmt.getNumColumns()):
            col = fmt.getColumn(col_idx)
            col_name = col.getName().getBasename()
            
            from panda3d.core import GeomVertexReader
            reader = GeomVertexReader(vdata, col.getName())
            for i in range(n):
                reader.setRow(i)
                d = reader.getData4f()
                for c in range(4):
                    v = d[c]
                    if math.isnan(v):
                        nan_count += 1
                        if gn.getName() not in problem_nodes:
                            problem_nodes.append(gn.getName())
                    elif math.isinf(v):
                        inf_count += 1
                        if gn.getName() not in problem_nodes:
                            problem_nodes.append(gn.getName())
                    elif abs(v) > 1e6:
                        huge_count += 1
                        if gn.getName() not in problem_nodes:
                            problem_nodes.append(gn.getName())
                    if abs(v) > max_val and not math.isnan(v) and not math.isinf(v):
                        max_val = abs(v)

print(f"Total vertices: {total_verts}")
print(f"NaN: {nan_count}, Inf: {inf_count}, Huge(>1e6): {huge_count}")
print(f"Max absolute value: {max_val}")
if problem_nodes:
    print(f"Problem nodes: {problem_nodes}")
else:
    print("No problematic vertex data found")

# Also check the vertex format for any unusual columns
for gn in actor.findAllMatches('**/+GeomNode'):
    node = gn.node()
    for gi in range(node.getNumGeoms()):
        geom = node.getGeom(gi)
        vdata = geom.getVertexData()
        fmt = vdata.getFormat()
        cols = [fmt.getColumn(i).getName().getBasename() for i in range(fmt.getNumColumns())]
        print(f"  {gn.getName()}: {vdata.getNumRows()} verts, cols={cols}")
        break  # just first geom

base.destroy()
