import os
import sys

GAME_DIR = os.path.dirname(os.path.abspath(__file__))
if GAME_DIR not in sys.path:
    sys.path.insert(0, GAME_DIR)

from direct.showbase.ShowBase import ShowBase
from panda3d.core import Filename, getModelPath
from direct.actor.Actor import Actor
from app.player.player_instance import Player
from app.pokemon.pokemon import Pokemon

# Resolve project root (one level above game/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class MyApp(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)
        getModelPath().prependDirectory(Filename.fromOsSpecific(PROJECT_ROOT))
        self.scene = self.loader.loadModel('models/environment')
        self.scene.reparentTo(self.render)
        self.scene.setScale(5)
        self.scene.setPos(-50, -50, -1)

        player = Player(self)
        player.spawn_self()
        player.key_bindings()

        for i in range(3):
            pokemon = Pokemon(self)
            pokemon.spawn_random_pokemon()
            pokemon.draw_name_tag()


app = MyApp()
app.run()
