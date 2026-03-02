import os, subprocess, time

os.chdir(r'C:\Users\Utilisateur\Desktop\Pokemon')
out = open(r'C:\Users\Utilisateur\clean_test.txt', 'w')
my_pid = os.getpid()

tests = {
    "no_rotation": "pass",
    "setH_180": "actor.setH(180)",
    "setP_neg90": "actor.setP(-90)",
    "setHpr_180_neg90_0": "actor.setHpr(180,-90,0)",
}

for name, xform in tests.items():
    code = f"""import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
actor = Actor('models/trainers/black_belt/black_belt.bam')
actor.reparentTo(base.render)
{xform}
base.run()
"""
    tmpf = r'C:\Users\Utilisateur\Desktop\Pokemon\_test_code.py'
    with open(tmpf, 'w') as f:
        f.write(code)
    try:
        r = subprocess.run(['python', tmpf], capture_output=True, text=True, timeout=6)
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
