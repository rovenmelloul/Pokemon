from movement.movement import PlayerMove
from camera.camera_movement import PlayerCamera


class Player(PlayerMove):
    
    def __init__(self):
        super.__init__()
        self.my_object = self.loader.loadModel("models/panda")
        self.position = (-8, 42, 0)
        
        
    def spawn_self():
        pass
    
    def relate_camera_with_player(self, camera):
        self.camera = camera
        self.camera.set_pos(self.position)
    
    def update_camera_position(self):
        if hasattr(self, 'camera'):
            self.camera.set_pos(self.position)
    
    def move_by_axis(self, axis, value):
        if axis == "x":
            self.position = (self.position[0] + value, self.position[1], self.position[2])
        elif axis == "y":
            self.position = (self.position[0], self.position[1] + value, self.position[2])
        elif axis == "z":
            self.position = (self.position[0], self.position[1], self.position[2] + value)
    
    def jump(self):
        pass