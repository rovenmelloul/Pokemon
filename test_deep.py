import os, subprocess, time

os.chdir(r'C:\Users\Utilisateur\Desktop\Pokemon')
out = open(r'C:\Users\Utilisateur\deep_test.txt', 'w')
my_pid = os.getpid()

tests = {
    "shader_off": """
import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
base.render.setShaderOff()
actor = Actor('models/trainers/black_belt/black_belt.bam')
actor.reparentTo(base.render)
actor.setH(180)
base.run()
""",
    "static_loader": """
import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath
from direct.showbase.ShowBase import ShowBase
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
model = base.loader.loadModel('models/trainers/black_belt/black_belt.bam')
model.reparentTo(base.render)
model.setH(180)
base.run()
""",
    "delayed_rotation": """
import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
actor = Actor('models/trainers/black_belt/black_belt.bam')
actor.reparentTo(base.render)
def rotate(task):
    actor.setH(180)
    return task.done
base.taskMgr.doMethodLater(2.0, rotate, 'rotate')
base.run()
""",
    "no_skinning_flat": """
import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath, NodePath
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
actor = Actor('models/trainers/black_belt/black_belt.bam')
flat = NodePath('flat')
actor.instanceTo(flat)
flat.flattenStrong()
flat.reparentTo(base.render)
flat.setH(180)
base.run()
""",
}

for name, code in tests.items():
    tmpf = r'C:\Users\Utilisateur\Desktop\Pokemon\_test_code.py'
    with open(tmpf, 'w') as f:
        f.write(code)
    try:
        r = subprocess.run(['python', tmpf], capture_output=True, text=True, timeout=8)
        rc = r.returncode
        if rc in (-1073741819, 3221225501):
            line = f"{name}: CRASH"
        else:
            line = f"{name}: RC={rc}"
            if r.stderr:
                line += f" | {r.stderr[:120]}"
    except subprocess.TimeoutExpired:
        line = f"{name}: OK (running)"
    out.write(line + "\n")
    out.flush()
    subprocess.run(['powershell', '-Command',
        f'Get-Process python -ErrorAction SilentlyContinue | Where-Object {{$_.Id -ne {my_pid}}} | Stop-Process -Force'],
        capture_output=True, timeout=5)
    time.sleep(1)

out.write("DONE\n")
out.close()
