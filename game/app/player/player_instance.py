from movement.movement import PlayerMove
from camera.camera_movement import PlayerCamera


class Player(PlayerMove):
    
    def __init__(self):
        super.__init__()
        self.my_object = self.loader.loadModel("models/panda")
        self.position = (-8, 42, 0)
        
        
    def spawn_self():
        pass
    
    def relate_camera_with_player():
        pass
    
    def move_by_axis():
        pass
    
    def jump():
        pass