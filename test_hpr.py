import os, subprocess, time, sys

os.chdir(r'C:\Users\Utilisateur\Desktop\Pokemon')
out = open(r'C:\Users\Utilisateur\hpr_results.txt', 'w')

template = r"""import os
os.chdir(r'C:\Users\Utilisateur\Desktop\Pokemon')
from panda3d.core import Filename, getModelPath
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
actor = Actor('models/trainers/black_belt/black_belt.bam')
actor.reparentTo(base.render)
{XFORM}
base.run()
"""

tests = [
    ("no_transform", "pass"),
    ("setH_180", "actor.setH(180)"),
    ("setP_neg90", "actor.setP(-90)"),
    ("setHpr_180_0_0", "actor.setHpr(180,0,0)"),
    ("setHpr_0_neg90_0", "actor.setHpr(0,-90,0)"),
    ("setHpr_180_neg90_0", "actor.setHpr(180,-90,0)"),
    ("parent_pivot", "pivot=base.render.attachNewNode('p');actor.wrtReparentTo(pivot);pivot.setHpr(180,-90,0)"),
]

for name, xform in tests:
    code = template.replace("{XFORM}", xform)
    tmpf = r'C:\Users\Utilisateur\Desktop\Pokemon\_hpr_test_code.py'
    with open(tmpf, 'w') as f:
        f.write(code)
    try:
        r = subprocess.run(['python', tmpf], capture_output=True, text=True, timeout=5)
        if r.returncode in (-1073741819, 3221225501):
            line = f"{name}: CRASH (segfault)"
        else:
            line = f"{name}: RC={r.returncode}"
    except subprocess.TimeoutExpired:
        line = f"{name}: OK (running)"
    out.write(line + "\n")
    out.flush()
    subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], capture_output=True, timeout=3)
    time.sleep(1)

out.write("ALL DONE\n")
out.close()
