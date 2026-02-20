from direct.task import Task
from panda3d.core import Point3

from ..player import Player

class Battle:
    def __init__(self, game, player:Player, enemy_pokemon):
        self.game = game                
        self.player = player             
        self.enemy_pokemon = enemy_pokemon
        
        self.saved_cam_pos = self.game.camera.getPos()
        self.saved_cam_hpr = self.game.camera.getHpr()
        
        self.in_battle = True
        
        self.start_battle()

    def start_battle(self):
        print(f"Battle {self.enemy_pokemon.name} (Lv.{self.enemy_pokemon.lvl}) af!")
        
        self.enemy_pokemon.animated_character.lookAt(self.player)
        self.enemy_pokemon.animated_character.loop("attack")
        
        self.player.setPos(-8, -12, 0)
        self.player.lookAt(Point3(8, 8, 2))
        
                
        self.enemy_pokemon.animated_character.setPos(8, 8, 2)
        self.enemy_pokemon.animated_character.lookAt(self.player)
        self.game.taskMgr.add(self.camera_battle_task, "battle_camera_task")
        


    def camera_battle_task(self, task):
        if not self.in_battle:
            return Task.done
        
        desired_pos = Point3(0, -30, 18)          
        desired_hpr = (0, -25, 0)                 
        
        t = globalClock.getDt() * 4.0           
        current_pos = self.game.camera.getPos()
        current_hpr = self.game.camera.getHpr()
        
        new_pos = current_pos + (desired_pos - current_pos) * t
        new_hpr = current_hpr + (Point3(desired_hpr) - current_hpr) * t
        
        self.game.camera.setPos(new_pos)
        self.game.camera.setHpr(new_hpr)
        

        
        return Task.cont

    def end_battle(self):
        self.in_battle = False
        self.game.taskMgr.remove("battle_camera_task")
        self.game.camera.setPos(self.saved_cam_pos)
        self.game.camera.setHpr(self.saved_cam_hpr)
