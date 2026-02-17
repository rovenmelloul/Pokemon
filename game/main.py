from direct.showbase.ShowBase import ShowBase
from panda3d.core import Filename  
from direct.actor.Actor import Actor
from app.player.player_instance import Player

class MyApp(ShowBase):

    def __init__(self):
        ShowBase.__init__(self) 
        player = Player(self)
        player.spawn_self()
        player.key_bindings()
    

app = MyApp()
app.run()