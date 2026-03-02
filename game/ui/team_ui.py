"""
TeamUI -- Interface de gestion d'equipe.
"""
from panda3d.core import TextNode
from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton, DirectWaitBar,
)


class TeamUI:
    def __init__(self, base, player_team, on_close_callback, on_swap=None):
        self.base = base
        self.team = player_team
        self.on_close = on_close_callback
        self.on_swap = on_swap
        self.frame = None

    def show(self):
        self.frame = DirectFrame(
            frameColor=(0.05, 0.05, 0.1, 0.92),
            frameSize=(-1.5, 1.5, -1, 1),
            pos=(0, 0, 0),
        )
        DirectLabel(
            parent=self.frame,
            text="VOTRE EQUIPE",
            scale=0.09,
            pos=(0, 0, 0.85),
            text_fg=(0.4, 0.8, 1, 1),
            frameColor=(0, 0, 0, 0),
        )
        for i, poke in enumerate(self.team):
            y = 0.6 - i * 0.42
            self._create_pokemon_card(poke, y, i)

        DirectButton(
            parent=self.frame,
            text="Fermer [T]",
            scale=0.05,
            pos=(0, 0, -0.9),
            command=self._close,
            frameSize=(-3, 3, -1, 1),
            text_fg=(1, 1, 1, 1),
            frameColor=(0.4, 0.2, 0.2, 1),
        )

    def _create_pokemon_card(self, poke, y_pos, slot_index):
        card = DirectFrame(
            parent=self.frame,
            frameColor=(0.12, 0.12, 0.18, 0.9),
            frameSize=(-1.2, 1.2, -0.18, 0.18),
            pos=(0, 0, y_pos),
        )
        name_color = (1, 0.84, 0, 1) if poke.is_shiny else (1, 1, 1, 1)
        prefix = "[*] " if poke.is_shiny else ""
        DirectLabel(
            parent=card,
            text=f"{prefix}{poke.name}  Nv.{poke.level}",
            text_fg=name_color, text_scale=0.05,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-1.1, 0, 0.08),
        )
        types_str = " / ".join(poke.types)
        DirectLabel(
            parent=card,
            text=types_str,
            text_fg=(0.7, 0.7, 0.7, 1), text_scale=0.035,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-1.1, 0, 0.02),
        )
        hp_ratio = poke.hp_fraction()
        if hp_ratio > 0.5:
            bar_color = (0.2, 0.8, 0.2, 1)
        elif hp_ratio > 0.2:
            bar_color = (0.9, 0.7, 0.1, 1)
        else:
            bar_color = (0.9, 0.2, 0.1, 1)
        DirectWaitBar(
            parent=card,
            range=poke.stats.get("hp", 1),
            value=poke.current_hp,
            barColor=bar_color,
            frameColor=(0.3, 0.3, 0.3, 1),
            frameSize=(-0.5, 0.5, -0.008, 0.02),
            pos=(-0.6, 0, -0.06),
        )
        DirectLabel(
            parent=card,
            text=f"PV: {poke.current_hp}/{poke.stats.get('hp', 0)}",
            text_fg=(1, 1, 1, 1), text_scale=0.03,
            frameColor=(0, 0, 0, 0),
            pos=(-0.6, 0, -0.12),
        )
        stats = poke.stats
        stat_text = (
            f"ATQ:{stats.get('attack', 0)}  DEF:{stats.get('defense', 0)}  "
            f"AtqS:{stats.get('sp_attack', 0)}  DefS:{stats.get('sp_defense', 0)}  "
            f"VIT:{stats.get('speed', 0)}"
        )
        DirectLabel(
            parent=card,
            text=stat_text,
            text_fg=(0.6, 0.6, 0.6, 1), text_scale=0.028,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(0.15, 0, 0.08),
        )
        moves_text = "Attaques: "
        if poke.moves:
            move_names = [f"{m.name}({m.current_pp}/{m.max_pp})" for m in poke.moves]
            moves_text += ", ".join(move_names)
        else:
            moves_text += "Aucune"
        DirectLabel(
            parent=card,
            text=moves_text,
            text_fg=(0.5, 0.5, 0.5, 1), text_scale=0.028,
            text_align=TextNode.ALeft,
            text_wordwrap=40,
            frameColor=(0, 0, 0, 0),
            pos=(0.15, 0, -0.02),
        )

        # Echanger button
        if self.on_swap:
            DirectButton(
                parent=card,
                text="Echanger",
                text_fg=(1, 1, 1, 1),
                scale=0.05,
                frameColor=(0.2, 0.45, 0.7, 1),
                frameSize=(-2.2, 2.2, -0.6, 0.8),
                pos=(0.95, 0, -0.1),
                command=self._do_swap,
                extraArgs=[slot_index],
            )

        if poke.is_fainted():
            label_x = 0.65 if self.on_swap else 0.85
            DirectLabel(
                parent=card,
                text="K.O.",
                text_fg=(1, 0.2, 0.2, 1), text_scale=0.04,
                frameColor=(0, 0, 0, 0),
                pos=(label_x, 0, -0.1),
            )
        elif poke.status:
            status_names = {
                "poison": "EMPOISONNE",
                "burn": "BRULE",
                "paralysis": "PARALYSE",
                "sleep": "ENDORMI",
                "freeze": "GELE",
            }
            status_colors = {
                "poison": (0.6, 0.2, 0.8, 1),
                "burn": (1, 0.4, 0.1, 1),
                "paralysis": (0.9, 0.8, 0.1, 1),
                "sleep": (0.5, 0.5, 0.5, 1),
                "freeze": (0.4, 0.7, 0.9, 1),
            }
            label_x = 0.65 if self.on_swap else 0.85
            DirectLabel(
                parent=card,
                text=status_names.get(poke.status, poke.status.upper()),
                text_fg=status_colors.get(poke.status, (1, 1, 1, 1)),
                text_scale=0.035,
                frameColor=(0, 0, 0, 0),
                pos=(label_x, 0, -0.1),
            )

    def _do_swap(self, slot_index):
        if self.on_swap:
            self.on_swap(slot_index)

    def _close(self):
        callback = self.on_close
        self.on_close = None
        self.cleanup()
        if callback:
            callback()

    def cleanup(self):
        self.on_close = None
        self.on_swap = None
        if self.frame:
            self.frame.destroy()
            self.frame = None
