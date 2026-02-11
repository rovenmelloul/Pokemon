"""
map_scene.py — Scène d'exploration avec map en grille.
Navigation ZQSD/flèches, hautes herbes pour rencontres.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from panda3d.core import (
    Vec3, Vec4, Point3, CardMaker, TextNode,
    AmbientLight, DirectionalLight, CollisionTraverser,
    CollisionNode, CollisionSphere, CollisionHandlerQueue,
    CollisionRay, BitMask32, TransparencyAttrib
)
from direct.showbase.DirectObject import DirectObject
from direct.gui.OnscreenText import OnscreenText

from engine.encounter import EncounterSystem


# Map layout : 0=vide, 1=herbe, 2=chemin, 3=arbre, 4=eau
MAP_LAYOUT = [
    [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
    [3, 2, 2, 2, 2, 1, 1, 1, 2, 2, 2, 2, 1, 1, 1, 3],
    [3, 2, 3, 3, 2, 1, 1, 1, 2, 3, 3, 2, 1, 1, 1, 3],
    [3, 2, 3, 3, 2, 2, 2, 2, 2, 3, 3, 2, 2, 2, 2, 3],
    [3, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 1, 1, 2, 3],
    [3, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 2, 1, 1, 2, 3],
    [3, 1, 1, 1, 2, 2, 2, 2, 1, 1, 1, 2, 2, 2, 2, 3],
    [3, 2, 2, 2, 2, 3, 3, 2, 2, 2, 2, 2, 3, 3, 2, 3],
    [3, 2, 3, 3, 2, 3, 3, 2, 3, 3, 2, 2, 3, 3, 2, 3],
    [3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3],
    [3, 1, 1, 2, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 2, 3],
    [3, 1, 1, 2, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 2, 3],
    [3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3],
    [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
]

TILE_SIZE = 2.0
TILE_COLORS = {
    0: Vec4(0.2, 0.2, 0.2, 1),   # Vide
    1: Vec4(0.2, 0.7, 0.2, 1),   # Herbe haute (rencontre)
    2: Vec4(0.6, 0.5, 0.3, 1),   # Chemin
    3: Vec4(0.1, 0.4, 0.1, 1),   # Arbre (bloquant)
    4: Vec4(0.2, 0.4, 0.8, 1),   # Eau (bloquant)
}


class MapScene(DirectObject):
    """
    Scène d'exploration en vue du dessus.
    Le joueur se déplace sur une grille, les hautes herbes déclenchent des rencontres.
    """

    def __init__(self, app, on_encounter_callback=None):
        super().__init__()
        self.app = app
        self.on_encounter = on_encounter_callback
        self.map_node = None
        self.player_node = None
        self.player_pos = [4, 4]  # Position de départ (grille)
        self.move_speed = 0.15  # Secondes par déplacement
        self.is_moving = False
        self.current_zone = "route_1"
        self.step_count = 0
        self.zone_text = None

    def setup(self):
        """Initialise la scène de map."""
        self.map_node = self.app.render.attachNewNode("map_root")
        self._build_map()
        self._create_player()
        self._setup_camera()
        self._setup_controls()
        self._setup_lighting()
        self._setup_hud()

    def _build_map(self):
        """Construit la map à partir du layout."""
        cm = CardMaker("tile")
        cm.setFrame(-TILE_SIZE/2, TILE_SIZE/2, -TILE_SIZE/2, TILE_SIZE/2)

        for row_idx, row in enumerate(MAP_LAYOUT):
            for col_idx, tile in enumerate(row):
                tile_node = self.map_node.attachNewNode(f"tile_{row_idx}_{col_idx}")
                card = tile_node.attachNewNode(cm.generate())
                card.setP(-90)  # Flat on ground
                card.setColor(TILE_COLORS.get(tile, Vec4(0.5, 0.5, 0.5, 1)))
                tile_node.setPos(col_idx * TILE_SIZE, row_idx * TILE_SIZE, 0)
                
                # Ajouter des petits cubes pour les arbres
                if tile == 3:
                    tree = self.app.loader.loadModel("models/box")
                    if tree:
                        tree.reparentTo(tile_node)
                        tree.setScale(0.8, 0.8, 1.5)
                        tree.setPos(0, 0, 0.75)
                        tree.setColor(0.1, 0.5, 0.15, 1)

    def _create_player(self):
        """Crée le marqueur joueur."""
        self.player_node = self.map_node.attachNewNode("player")
        
        # Simple cube coloré pour le joueur
        try:
            model = self.app.loader.loadModel("models/box")
            if model:
                model.reparentTo(self.player_node)
                model.setScale(0.6, 0.6, 0.8)
                model.setPos(0, 0, 0.4)
                model.setColor(1, 0.2, 0.2, 1)
        except Exception:
            pass
        
        self._update_player_pos()

    def _setup_camera(self):
        """Configure la caméra en vue du dessus."""
        self.app.camera.reparentTo(self.player_node)
        self.app.camera.setPos(0, -5, 20)
        self.app.camera.lookAt(self.player_node)

    def _setup_lighting(self):
        """Configure l'éclairage."""
        # Lumière ambiante
        alight = AmbientLight("ambient")
        alight.setColor(Vec4(0.4, 0.4, 0.4, 1))
        self.map_node.setLight(self.map_node.attachNewNode(alight))
        
        # Lumière directionnelle
        dlight = DirectionalLight("sun")
        dlight.setColor(Vec4(0.8, 0.8, 0.7, 1))
        dlnp = self.map_node.attachNewNode(dlight)
        dlnp.setHpr(45, -45, 0)
        self.map_node.setLight(dlnp)

    def _setup_hud(self):
        """Configure le HUD."""
        self.zone_text = OnscreenText(
            text=f"📍 {self.current_zone.replace('_', ' ').title()}",
            pos=(-1.2, 0.9), scale=0.06,
            fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
            align=TextNode.ALeft
        )

    def _setup_controls(self):
        """Configure les contrôles de mouvement."""
        self.accept("arrow_up", self._move, [0, 1])
        self.accept("arrow_down", self._move, [0, -1])
        self.accept("arrow_left", self._move, [-1, 0])
        self.accept("arrow_right", self._move, [1, 0])
        self.accept("z", self._move, [0, 1])
        self.accept("s", self._move, [0, -1])
        self.accept("q", self._move, [-1, 0])
        self.accept("d", self._move, [1, 0])
        self.accept("w", self._move, [0, 1])
        self.accept("a", self._move, [-1, 0])

    def _move(self, dx: int, dy: int):
        """Déplace le joueur d'une case."""
        if self.is_moving:
            return
        
        new_x = self.player_pos[0] + dx
        new_y = self.player_pos[1] + dy
        
        # Vérifier les limites
        if (new_y < 0 or new_y >= len(MAP_LAYOUT) or
            new_x < 0 or new_x >= len(MAP_LAYOUT[0])):
            return
        
        # Vérifier si la case est bloquante
        tile = MAP_LAYOUT[new_y][new_x]
        if tile in (3, 4):  # Arbre ou eau
            return
        
        self.player_pos = [new_x, new_y]
        self._update_player_pos()
        self.step_count += 1
        
        # Vérifier rencontre dans l'herbe haute
        if tile == 1:
            self._check_encounter()

    def _update_player_pos(self):
        """Met à jour la position visuelle du joueur."""
        self.player_node.setPos(
            self.player_pos[0] * TILE_SIZE,
            self.player_pos[1] * TILE_SIZE,
            0
        )

    def _check_encounter(self):
        """Vérifie si une rencontre a lieu."""
        if EncounterSystem.check_encounter(self.current_zone):
            wild = EncounterSystem.generate_wild_pokemon(self.current_zone)
            if wild and self.on_encounter:
                self.on_encounter(wild)

    def cleanup(self):
        """Nettoie la scène."""
        self.ignoreAll()
        if self.map_node:
            self.map_node.removeNode()
        if self.zone_text:
            self.zone_text.destroy()

    def pause_controls(self):
        """Désactive les contrôles temporairement."""
        self.ignoreAll()

    def resume_controls(self):
        """Réactive les contrôles."""
        self._setup_controls()
