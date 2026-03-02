import os, subprocess, time

os.chdir(r'C:\Users\Utilisateur\Desktop\Pokemon')
out = open(r'C:\Users\Utilisateur\hpr_results2.txt', 'w')
my_pid = os.getpid()

tests = {
    "static_model_rotated": """
import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath
from direct.showbase.ShowBase import ShowBase
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
model = base.loader.loadModel('models/trainers/black_belt/black_belt.bam')
model.reparentTo(base.render)
model.setHpr(180, -90, 0)
base.run()
""",
    "actor_flatten_then_run": """
import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
actor = Actor('models/trainers/black_belt/black_belt.bam')
actor.reparentTo(base.render)
actor.setHpr(180, -90, 0)
actor.flattenStrong()
base.run()
""",
    "actor_software_skinning": """
import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath, loadPrcFileData
loadPrcFileData('', 'hardware-animated-vertices false')
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
actor = Actor('models/trainers/black_belt/black_belt.bam')
actor.reparentTo(base.render)
actor.setHpr(180, -90, 0)
base.run()
""",
    "actor_setH_tiny": """
import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
actor = Actor('models/trainers/black_belt/black_belt.bam')
actor.reparentTo(base.render)
actor.setH(0.001)
base.run()
""",
}

for name, code in tests.items():
    tmpf = r'C:\Users\Utilisateur\Desktop\Pokemon\_hpr_test_code.py'
    with open(tmpf, 'w') as f:
        f.write(code)
    try:
        r = subprocess.run(['python', tmpf], capture_output=True, text=True, timeout=6)
        rc = r.returncode
        if rc in (-1073741819, 3221225501):
            line = f"{name}: CRASH"
        else:
            line = f"{name}: RC={rc}"
            if r.stderr:
                line += f" stderr={r.stderr[:150]}"
    except subprocess.TimeoutExpired:
        line = f"{name}: OK (running)"
    out.write(line + "\n")
    out.flush()
    subprocess.run(
        ['powershell', '-Command',
         f'Get-Process python -ErrorAction SilentlyContinue | Where-Object {{$_.Id -ne {my_pid}}} | Stop-Process -Force'],
        capture_output=True, timeout=5
    )
    time.sleep(1)

out.write("ALL DONE\n")
out.close()
