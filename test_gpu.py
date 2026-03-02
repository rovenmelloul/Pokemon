import os, subprocess, time

os.chdir(r'C:\Users\Utilisateur\Desktop\Pokemon')
out = open(r'C:\Users\Utilisateur\gpu_test.txt', 'w')
my_pid = os.getpid()

# First get GPU info
gpu_code = """
import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath, loadPrcFileData
loadPrcFileData('', 'notify-level-display info')
from direct.showbase.ShowBase import ShowBase
base = ShowBase()
gsg = base.win.getGsg()
out = open(r'C:\\Users\\Utilisateur\\gpu_info.txt', 'w')
out.write(f"Driver renderer: {gsg.getDriverRenderer()}\\n")
out.write(f"Driver vendor: {gsg.getDriverVendor()}\\n")
out.write(f"Driver version: {gsg.getDriverVersion()}\\n")
out.write(f"GL version: {gsg.getDriverVersionMajor()}.{gsg.getDriverVersionMinor()}\\n")
out.write(f"Max texture size: {gsg.getMaxTextureSize()}\\n")
out.write(f"Supports GLSL: {gsg.getSupportsGlsl()}\\n")
out.close()
base.destroy()
"""
tmpf = r'C:\Users\Utilisateur\Desktop\Pokemon\_test_code.py'
with open(tmpf, 'w') as f:
    f.write(gpu_code)
subprocess.run(['python', tmpf], capture_output=True, text=True, timeout=10)
subprocess.run(['powershell', '-Command',
    f'Get-Process python -ErrorAction SilentlyContinue | Where-Object {{$_.Id -ne {my_pid}}} | Stop-Process -Force'],
    capture_output=True, timeout=5)
time.sleep(1)

# Now test alternative renderers
tests = {
    "tinydisplay_windowed": """
import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath, loadPrcFileData
loadPrcFileData('', 'load-display p3tinydisplay')
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
actor = Actor('models/trainers/black_belt/black_belt.bam')
actor.reparentTo(base.render)
actor.setHpr(180, -90, 0)
base.run()
""",
    "gl_debug": """
import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath, loadPrcFileData
loadPrcFileData('', 'gl-debug true')
loadPrcFileData('', 'gl-check-errors true')
loadPrcFileData('', 'notify-level-glgsg debug')
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
import sys
sys.stderr = open(r'C:\\Users\\Utilisateur\\gl_debug.txt', 'w')
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
actor = Actor('models/trainers/black_belt/black_belt.bam')
actor.reparentTo(base.render)
actor.setH(180)
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
