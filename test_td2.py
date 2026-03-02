import os
os.chdir(r'C:\Users\Utilisateur\Desktop\Pokemon')
from panda3d.core import Filename, getModelPath, loadPrcFileData, Texture
loadPrcFileData('', 'load-display p3tinydisplay')

log = open(r'C:\Users\Utilisateur\td_log.txt', 'w')
def logp(msg):
    log.write(msg + '\n')
    log.flush()

try:
    from direct.showbase.ShowBase import ShowBase
    from direct.actor.Actor import Actor

    base = ShowBase()
    getModelPath().prependDirectory(Filename.fromOsSpecific(os.path.abspath('.')))
    logp("STEP 1: ShowBase OK")

    actor = Actor(Filename.fromOsSpecific(
        r'C:\Users\Utilisateur\Desktop\BlackBelt\fixed_model.bam').getFullpath())
    logp(f"STEP 2: Actor loaded, {len(actor.getJoints())} joints")

    actor.reparentTo(base.render)
    actor.setScale(1)
    actor.setHpr(180, -90, 0)
    logp("STEP 3: setHpr(180,-90,0) applied")

    # Texture
    img = os.path.join('models', 'trainers', 'black_belt', 'images', 'tr0050_00_body_col.png')
    tex = Texture()
    tex.read(Filename.fromOsSpecific(img))
    logp(f"STEP 4: Texture {tex.getXSize()}x{tex.getYSize()}")

    for gn in actor.findAllMatches('**/+GeomNode'):
        name = gn.getName().lower()
        if 'body' in name or 'leg' in name or 'dogi' in name:
            gn.setTexture(tex, 1)

    logp("STEP 5: Textures applied")

    joint = actor.controlJoint(None, 'modelRoot', 'LThigh')
    logp(f"STEP 6: controlJoint = {joint}")

    # Run for a few frames
    def check(task):
        logp(f"STEP 7: Frame rendered OK (frame {task.frame})")
        if task.frame > 3:
            base.userExit()
            return task.done
        return task.cont

    base.taskMgr.add(check, 'check')
    logp("STEP 8: Starting base.run()")
    base.run()
    logp("STEP 9: Clean exit")
except Exception as e:
    import traceback
    logp(f"ERROR: {traceback.format_exc()}")
log.close()
