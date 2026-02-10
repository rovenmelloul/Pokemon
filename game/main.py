from direct.showbase.ShowBase import ShowBase


class MyApp(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)

        # Load the environment model.
        self.scene = self.loader.loadModel("models/environment")
        self.my_object = self.loader.loadModel("models/panda")
        self.my_object.reparentTo(self.render)
        self.my_object.setScale(0.05)
        self.my_object.setPos(0, 0, 0)
        
        # Reparent the model to render.
        self.scene.reparentTo(self.render)
        self.camera.reparentTo(self.my_object)
        # Apply scale and position transforms on the model.
        self.scene.setScale(0.25, 0.25, 0.25)
        self.scene.setPos(-8, 42, 0)


app = MyApp()
app.run()