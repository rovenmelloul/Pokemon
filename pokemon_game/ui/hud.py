"""
hud.py — HUD pour la phase d'exploration.
"""
from panda3d.core import TextNode
from direct.gui.DirectGui import DirectFrame, DirectLabel
from direct.gui.OnscreenText import OnscreenText


class ExplorationHUD:
    """
    HUD durant l'exploration :
    - Équipe résumée (icônes HP)
    - Zone actuelle
    - Compteur de pas
    """

    def __init__(self, app, team, zone_name="Route 1"):
        self.app = app
        self.team = team
        self.zone_name = zone_name
        self.step_count = 0
        
        # UI Elements
        self.hud_frame = None
        self.zone_label = None
        self.team_labels = []

    def setup(self):
        """Crée le HUD."""
        # Cadre principal (haut de l'écran)
        self.hud_frame = DirectFrame(
            frameColor=(0.05, 0.05, 0.1, 0.7),
            frameSize=(-1.35, 1.35, -0.08, 0.08),
            pos=(0, 0, 0.92)
        )
        
        # Zone
        self.zone_label = DirectLabel(
            text=f"📍 {self.zone_name}",
            text_fg=(1, 1, 1, 1), text_scale=0.04,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-1.25, 0, -0.01),
            parent=self.hud_frame
        )
        
        # Équipe (résumé)
        self._update_team_display()

    def _update_team_display(self):
        """Met à jour l'affichage de l'équipe."""
        for label in self.team_labels:
            label.destroy()
        self.team_labels = []
        
        for i, poke in enumerate(self.team):
            hp_ratio = poke.hp_fraction()
            if poke.is_fainted():
                color = (0.5, 0.2, 0.2, 1)
                icon = "💀"
            elif hp_ratio > 0.5:
                color = (0.2, 0.7, 0.2, 1)
                icon = "🟢"
            elif hp_ratio > 0.2:
                color = (0.8, 0.7, 0.1, 1)
                icon = "🟡"
            else:
                color = (0.8, 0.2, 0.1, 1)
                icon = "🔴"
            
            label = DirectLabel(
                text=f"{icon}",
                text_fg=color, text_scale=0.05,
                frameColor=(0, 0, 0, 0),
                pos=(0.5 + i * 0.12, 0, -0.01),
                parent=self.hud_frame
            )
            self.team_labels.append(label)

    def update_zone(self, zone_name: str):
        """Met à jour le nom de la zone."""
        self.zone_name = zone_name
        if self.zone_label:
            self.zone_label["text"] = f"📍 {zone_name}"

    def update(self):
        """Met à jour le HUD complet."""
        self._update_team_display()

    def cleanup(self):
        """Nettoie le HUD."""
        for label in self.team_labels:
            label.destroy()
        if self.hud_frame:
            self.hud_frame.destroy()
