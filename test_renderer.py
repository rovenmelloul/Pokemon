import os, subprocess, time

os.chdir(r'C:\Users\Utilisateur\Desktop\Pokemon')
out = open(r'C:\Users\Utilisateur\render_test2.txt', 'w')
my_pid = os.getpid()

# First restore the original (unrotated) BAM that was known to work at identity
import shutil
shutil.copy2(r'C:\Users\Utilisateur\Desktop\BlackBelt\fixed_model.bam',
             r'C:\Users\Utilisateur\Desktop\Pokemon\models\trainers\black_belt\black_belt.bam')

configs = {
    "default_no_rotation": ("", "pass"),
    "default_setH180": ("", "actor.setH(180)"),
    "no_hw_anim_no_rotation": ("loadPrcFileData('','hardware-animated-vertices false')", "pass"),
    "no_hw_anim_setH180": ("loadPrcFileData('','hardware-animated-vertices false')", "actor.setH(180)"),
    "basic_shaders_no_rotation": ("loadPrcFileData('','basic-shaders-only true')", "pass"),
    "basic_shaders_setH180": ("loadPrcFileData('','basic-shaders-only true')", "actor.setH(180)"),
    "no_auto_shader_no_rotation": ("", "actor.clearShader(); pass"),
    "no_auto_shader_setH180": ("", "actor.clearShader(); actor.setH(180)"),
    "gl21_setH180": ("loadPrcFileData('','gl-version 2 1')", "actor.setH(180)"),
    "flat_model_setH180": ("", "model = base.loader.loadModel('models/trainers/black_belt/black_belt.bam'); model.reparentTo(base.render); model.setH(180)"),
}

for name, (prc, xform) in configs.items():
    # Special handling for flat_model test
    if name == "flat_model_setH180":
        code = f"""import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath, loadPrcFileData
{prc}
from direct.showbase.ShowBase import ShowBase
base = ShowBase()
getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
{xform}
base.run()
"""
    else:
        code = f"""import os
os.chdir(r'C:\\Users\\Utilisateur\\Desktop\\Pokemon')
from panda3d.core import Filename, getModelPath, loadPrcFileData
{prc}
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
            if r.stderr:
                line += f" | {r.stderr[:100]}"
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
