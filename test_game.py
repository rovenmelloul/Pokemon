"""Quick game launch test - exits after a few frames"""
import os, sys
os.chdir(r'C:\Users\Utilisateur\Desktop\Pokemon')
sys.path.insert(0, 'game')

log = open(r'C:\Users\Utilisateur\game_test_log.txt', 'w')
def logp(msg):
    log.write(msg + '\n')
    log.flush()
    print(msg)

try:
    logp("Starting game import...")
    from panda3d.core import loadPrcFileData
    loadPrcFileData('', 'load-display p3tinydisplay')

    # Import main module
    from main import MyApp
    logp("MyApp imported OK")

    app = MyApp()
    logp("MyApp created OK")

    # Run for a few frames then exit
    frame_count = [0]
    def check_frame(task):
        frame_count[0] += 1
        logp(f"Frame {frame_count[0]}")
        if frame_count[0] >= 5:
            app.userExit()
            return task.done
        return task.cont

    app.taskMgr.add(check_frame, 'test_check')
    logp("Starting base.run()...")
    app.run()
    logp("CLEAN EXIT")
except Exception as e:
    import traceback
    logp(f"ERROR: {traceback.format_exc()}")

log.close()
