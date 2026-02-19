from direct.showbase.ShowBase import ShowBase
from panda3d.core import Filename  
from direct.actor.Actor import Actor
from app.player.player_instance import Player
from app.pokemon.pokemon import Pokemon

class MyApp(ShowBase):

    def __init__(self):
        ShowBase.__init__(self) 
        self.scene = self.loader.loadModel("models/environment")
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