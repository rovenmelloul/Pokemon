"""
ExplorationHUD -- HUD d'exploration avec barre d'outils.
"""
from panda3d.core import TextNode
from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton


class ExplorationHUD:
    def __init__(self, app, player_team=None, zone_name="Exploration",
                 on_pokedex=None, on_team=None, on_heal=None):
        self.app = app
        self.player_team = player_team or []
        self.zone_name = zone_name
        self.on_pokedex = on_pokedex
        self.on_team = on_team
        self.on_heal = on_heal

        self.encounter_hint = None
        self.toolbar_frame = None

    def setup(self):
        self.toolbar_frame = DirectFrame(
            frameColor=(0.08, 0.08, 0.12, 0.85),
            frameSize=(-1.35, 1.35, -0.07, 0.07),
            pos=(0, 0, -0.93)
        )
        btn_style = {
            "text_scale": 0.045,
            "frameSize": (-0.2, 0.2, -0.04, 0.05),
            "relief": 1,
            "text_fg": (1, 1, 1, 1),
        }
        DirectButton(
            text="Pokedex",
            frameColor=(0.7, 0.2, 0.2, 1),
            pos=(-0.5, 0, -0.005),
            command=self._do_pokedex,
            parent=self.toolbar_frame,
            **btn_style
        )
        DirectButton(
            text="Equipe",
            frameColor=(0.2, 0.5, 0.8, 1),
            pos=(0, 0, -0.005),
            command=self._do_team,
            parent=self.toolbar_frame,
            **btn_style
        )
        DirectButton(
            text="Soigner",
            frameColor=(0.2, 0.7, 0.3, 1),
            pos=(0.5, 0, -0.005),
            command=self._do_heal,
            parent=self.toolbar_frame,
            **btn_style
        )

    def _do_pokedex(self):
        if self.on_pokedex:
            self.on_pokedex()

    def _do_team(self):
        if self.on_team:
            self.on_team()

    def _do_heal(self):
        if self.on_heal:
            self.on_heal()

    def show_encounter_hint(self, pokemon_name):
        if self.encounter_hint:
            self.encounter_hint.destroy()
        self.encounter_hint = DirectLabel(
            text=f"[E] Combat  [F] Capture  -  {pokemon_name}",
            text_fg=(1, 0.9, 0.2, 1), text_scale=0.06,
            frameColor=(0, 0, 0, 0.6),
            pos=(0, 0, -0.2),
        )

    def hide_encounter_hint(self):
        if self.encounter_hint:
            self.encounter_hint.destroy()
            self.encounter_hint = None

    def show_heal_message(self):
        if hasattr(self, '_heal_msg') and self._heal_msg:
            self._heal_msg.destroy()
        self._heal_msg = DirectLabel(
            text="Tous les Pokemon sont soignes !",
            text_fg=(0.3, 1, 0.3, 1), text_scale=0.06,
            frameColor=(0, 0, 0, 0.6),
            pos=(0, 0, 0.1),
        )
        self.app.taskMgr.doMethodLater(2.0, self._hide_heal_msg, "hide_heal_msg")

    def _hide_heal_msg(self, task):
        if hasattr(self, '_heal_msg') and self._heal_msg:
            self._heal_msg.destroy()
            self._heal_msg = None
        return task.done

    def update(self):
        pass

    def cleanup(self):
        self.hide_encounter_hint()
        if hasattr(self, '_heal_msg') and self._heal_msg:
            self._heal_msg.destroy()
            self._heal_msg = None
        if self.toolbar_frame:
            self.toolbar_frame.destroy()
            self.toolbar_frame = None
