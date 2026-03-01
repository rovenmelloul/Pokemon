"""
ExplorationHUD -- HUD during map exploration.
"""
from panda3d.core import TextNode
from direct.gui.DirectGui import DirectFrame, DirectLabel


class ExplorationHUD:
    def __init__(self, app, team=None, zone_name="Exploration"):
        self.app = app
        self.team = team or []
        self.zone_name = zone_name
        self.hud_frame = None
        self.zone_label = None
        self.team_labels = []
        self.encounter_hint = None

    def setup(self):
        self.hud_frame = DirectFrame(
            frameColor=(0.05, 0.05, 0.1, 0.7),
            frameSize=(-1.35, 1.35, -0.08, 0.08),
            pos=(0, 0, 0.92)
        )
        self.zone_label = DirectLabel(
            text=self.zone_name,
            text_fg=(1, 1, 1, 1), text_scale=0.04,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-1.25, 0, -0.01),
            parent=self.hud_frame
        )
        self._update_team_display()

    def _update_team_display(self):
        for label in self.team_labels:
            label.destroy()
        self.team_labels = []
        for i, poke in enumerate(self.team):
            hp_ratio = poke.hp_fraction()
            if poke.is_fainted():
                color = (0.5, 0.2, 0.2, 1)
                icon = "X"
            elif hp_ratio > 0.5:
                color = (0.2, 0.7, 0.2, 1)
                icon = "O"
            elif hp_ratio > 0.2:
                color = (0.8, 0.7, 0.1, 1)
                icon = "o"
            else:
                color = (0.8, 0.2, 0.1, 1)
                icon = "!"
            label = DirectLabel(
                text=icon,
                text_fg=color, text_scale=0.05,
                frameColor=(0, 0, 0, 0),
                pos=(0.5 + i * 0.12, 0, -0.01),
                parent=self.hud_frame
            )
            self.team_labels.append(label)

    def show_encounter_hint(self, pokemon_name):
        if self.encounter_hint:
            self.encounter_hint.destroy()
        self.encounter_hint = DirectLabel(
            text=f"Press E to battle {pokemon_name}!",
            text_fg=(1, 0.9, 0.2, 1), text_scale=0.06,
            frameColor=(0, 0, 0, 0.6),
            pos=(0, 0, -0.2),
        )

    def hide_encounter_hint(self):
        if self.encounter_hint:
            self.encounter_hint.destroy()
            self.encounter_hint = None

    def update(self):
        self._update_team_display()

    def cleanup(self):
        self.hide_encounter_hint()
        for label in self.team_labels:
            label.destroy()
        if self.hud_frame:
            self.hud_frame.destroy()
