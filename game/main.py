from direct.showbase.ShowBase import ShowBase
from panda3d.core import Filename  
from direct.actor.Actor import Actor

class MyApp(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)

        # Load the environment model.
        self.scene = self.loader.loadModel("models/environment")
        
        # Use relative path correctly (from script dir)
        
        self.animated_model_path = Actor
        self.my_object = self.loader.loadModel("models/pm0001_00/pm0001_00.egg")
        self.animated_pokemon = Actor("models/pm0001_00/pm0001_00.egg", 
                                      {"idle": "models/pm0001_00/pm0001_00-walk.egg"},
                                      {"attack": "models/pm0001_00/pm0001_00-attack.egg"},
                                      {"death": "models/pm0001_00/pm0001_00-death.egg"})
        
        self.animated_pokemon.loop("idle")
        
        self.my_object.reparentTo(self.render)
        self.my_object.setScale(0.05)
        self.my_object.setPos(0, 0, 0)
        
        # Reparent the animated model to render.
        self.animated_pokemon.reparentTo(self.render)
        self.animated_pokemon.setScale(0.05)
        self.animated_pokemon.setPos(0, 0, 0)
        
        # Reparent the model to render.
        self.scene.reparentTo(self.render)
        self.camera.reparentTo(self.my_object)
        # Apply scale and position transforms on the model.
        self.scene.setScale(0.25, 0.25, 0.25)
        self.scene.setPos(-8, 42, 0)

app = MyApp()
app.run()