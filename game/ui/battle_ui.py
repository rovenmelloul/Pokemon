"""
BattleUI -- Interface de combat (barres PV, menus, messages).
"""
from panda3d.core import Vec4, TextNode, TransparencyAttrib, CardMaker
from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectLabel, DirectWaitBar
)
from direct.gui.OnscreenText import OnscreenText


class BattleUI:
    def __init__(self, app, battle, battle_scene):
        self.app = app
        self.battle = battle
        self.scene = battle_scene

        self.player_info_frame = None
        self.enemy_info_frame = None
        self.action_frame = None
        self.message_frame = None
        self.move_frame = None
        self.switch_frame = None

        self.player_hp_bar = None
        self.enemy_hp_bar = None
        self.player_hp_text = None
        self.enemy_hp_text = None
        self.player_name_text = None
        self.enemy_name_text = None
        self.message_text = None

    def setup(self):
        self._create_player_info()
        self._create_enemy_info()
        self._create_message_box()
        self._create_action_menu()

    def _create_player_info(self):
        self.player_info_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.1, 0.8),
            frameSize=(-0.5, 0.5, -0.15, 0.15),
            pos=(0.85, 0, -0.55)
        )
        poke = self.battle.active_player
        self.player_name_text = DirectLabel(
            text=f"{poke.name}  Nv.{poke.level}",
            text_fg=(1, 1, 1, 1), text_scale=0.05,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.45, 0, 0.07),
            parent=self.player_info_frame
        )
        self.player_hp_bar = DirectWaitBar(
            text="", range=poke.stats["hp"], value=poke.current_hp,
            barColor=(0.2, 0.8, 0.2, 1),
            frameColor=(0.3, 0.3, 0.3, 1),
            frameSize=(-0.4, 0.4, -0.01, 0.03),
            pos=(0, 0, -0.02),
            parent=self.player_info_frame
        )
        self.player_hp_text = DirectLabel(
            text=f"{poke.current_hp} / {poke.stats['hp']}",
            text_fg=(1, 1, 1, 1), text_scale=0.04,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.08),
            parent=self.player_info_frame
        )

    def _create_enemy_info(self):
        self.enemy_info_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.1, 0.8),
            frameSize=(-0.5, 0.5, -0.15, 0.15),
            pos=(-0.85, 0, 0.65)
        )
        poke = self.battle.active_enemy
        self.enemy_name_text = DirectLabel(
            text=f"{poke.name}  Nv.{poke.level}",
            text_fg=(1, 1, 1, 1), text_scale=0.05,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-0.45, 0, 0.07),
            parent=self.enemy_info_frame
        )
        self.enemy_hp_bar = DirectWaitBar(
            text="", range=poke.stats["hp"], value=poke.current_hp,
            barColor=(0.2, 0.8, 0.2, 1),
            frameColor=(0.3, 0.3, 0.3, 1),
            frameSize=(-0.4, 0.4, -0.01, 0.03),
            pos=(0, 0, -0.02),
            parent=self.enemy_info_frame
        )
        self.enemy_hp_text = DirectLabel(
            text=f"{poke.current_hp} / {poke.stats['hp']}",
            text_fg=(1, 1, 1, 1), text_scale=0.04,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.08),
            parent=self.enemy_info_frame
        )

    def _create_message_box(self):
        self.message_frame = DirectFrame(
            frameColor=(0.05, 0.05, 0.15, 0.9),
            frameSize=(-1.3, 1.3, -0.12, 0.12),
            pos=(0, 0, -0.85)
        )
        self.message_text = DirectLabel(
            text="",
            text_fg=(1, 1, 1, 1), text_scale=0.05,
            text_align=TextNode.ALeft,
            text_wordwrap=50,
            frameColor=(0, 0, 0, 0),
            pos=(-1.2, 0, -0.01),
            parent=self.message_frame
        )

    def _create_action_menu(self):
        self.action_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.2, 0.9),
            frameSize=(-0.55, 0.55, -0.28, 0.28),
            pos=(0.75, 0, -0.55)
        )
        self.action_frame.hide()

        btn_style = {
            "text_scale": 0.05,
            "frameSize": (-0.22, 0.22, -0.04, 0.06),
            "relief": 1,
            "text_fg": (1, 1, 1, 1),
        }
        DirectButton(
            text="Attaque", frameColor=(0.8, 0.3, 0.2, 1),
            pos=(-0.25, 0, 0.15), command=self.show_move_menu,
            parent=self.action_frame, **btn_style
        )
        DirectButton(
            text="Changer", frameColor=(0.2, 0.5, 0.8, 1),
            pos=(0.25, 0, 0.15), command=self.show_switch_menu,
            parent=self.action_frame, **btn_style
        )
        if self.battle.is_wild:
            DirectButton(
                text="Fuite", frameColor=(0.5, 0.5, 0.5, 1),
                pos=(0, 0, 0.02),
                command=lambda: self.scene.on_run(),
                parent=self.action_frame, **btn_style
            )

    def show_action_menu(self):
        self._hide_all_menus()
        self.action_frame.show()

    def show_move_menu(self):
        self._hide_all_menus()
        self.move_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.2, 0.9),
            frameSize=(-0.7, 0.7, -0.3, 0.3),
            pos=(0, 0, -0.55)
        )
        poke = self.battle.active_player
        type_colors = {
            "fire": (0.9, 0.3, 0.1, 1), "water": (0.2, 0.5, 1, 1),
            "grass": (0.2, 0.8, 0.3, 1), "electric": (0.9, 0.8, 0.1, 1),
            "normal": (0.6, 0.6, 0.5, 1), "poison": (0.6, 0.2, 0.7, 1),
            "psychic": (0.9, 0.3, 0.6, 1), "ice": (0.4, 0.7, 0.9, 1),
            "fighting": (0.7, 0.2, 0.15, 1), "ground": (0.7, 0.6, 0.3, 1),
            "flying": (0.5, 0.5, 0.8, 1), "bug": (0.5, 0.6, 0.2, 1),
            "rock": (0.6, 0.5, 0.3, 1), "ghost": (0.4, 0.3, 0.5, 1),
            "dragon": (0.4, 0.2, 0.8, 1), "dark": (0.3, 0.2, 0.2, 1),
            "steel": (0.5, 0.5, 0.6, 1), "fairy": (0.8, 0.4, 0.6, 1),
        }
        for i, move in enumerate(poke.moves):
            col = i % 2
            row = i // 2
            x = -0.32 + col * 0.64
            y = 0.15 - row * 0.2
            color = type_colors.get(move.type, (0.5, 0.5, 0.5, 1))
            idx = i
            DirectButton(
                text=f"{move.name}\nPP:{move.current_pp}/{move.max_pp}",
                text_scale=0.04, text_fg=(1, 1, 1, 1),
                frameColor=color,
                frameSize=(-0.28, 0.28, -0.06, 0.06),
                pos=(x, 0, y),
                command=self._on_move_selected, extraArgs=[idx],
                parent=self.move_frame
            )
        DirectButton(
            text="<- Retour", text_scale=0.04, text_fg=(1, 1, 1, 1),
            frameColor=(0.4, 0.4, 0.4, 1),
            frameSize=(-0.2, 0.2, -0.04, 0.04),
            pos=(0, 0, -0.2), command=self.show_action_menu,
            parent=self.move_frame
        )

    def show_switch_menu(self, forced=False):
        self._hide_all_menus()
        self.switch_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.2, 0.9),
            frameSize=(-0.8, 0.8, -0.4, 0.4),
            pos=(0, 0, 0)
        )
        label = "Choisissez un Pokemon !" if forced else "Choisissez un Pokemon"
        DirectLabel(
            text=label, text_fg=(1, 1, 1, 1), text_scale=0.06,
            frameColor=(0, 0, 0, 0), pos=(0, 0, 0.3),
            parent=self.switch_frame
        )
        for i, poke in enumerate(self.battle.team_player):
            y = 0.15 - i * 0.1
            status = "K.O." if poke.is_fainted() else f"PV:{poke.current_hp}/{poke.stats['hp']}"
            is_active = poke is self.battle.active_player
            color = ((0.3, 0.3, 0.3, 1) if poke.is_fainted()
                     else (0.2, 0.5, 0.8, 1) if is_active
                     else (0.3, 0.6, 0.3, 1))
            idx = i
            btn = DirectButton(
                text=f"{poke.name} Nv.{poke.level} - {status}",
                text_scale=0.04, text_fg=(1, 1, 1, 1),
                frameColor=color,
                frameSize=(-0.6, 0.6, -0.03, 0.05),
                pos=(0, 0, y),
                command=self._on_switch_selected, extraArgs=[idx],
                parent=self.switch_frame
            )
            if poke.is_fainted() or is_active:
                btn["state"] = 0
        if not forced:
            DirectButton(
                text="<- Retour", text_scale=0.04, text_fg=(1, 1, 1, 1),
                frameColor=(0.4, 0.4, 0.4, 1),
                frameSize=(-0.2, 0.2, -0.04, 0.04),
                pos=(0, 0, -0.3), command=self.show_action_menu,
                parent=self.switch_frame
            )

    def _on_move_selected(self, move_index):
        self._hide_all_menus()
        self.scene.on_attack(move_index)

    def _on_switch_selected(self, pokemon_index):
        poke = self.battle.team_player[pokemon_index]
        if poke.is_fainted() or poke is self.battle.active_player:
            return
        self._hide_all_menus()
        self.scene.on_switch(pokemon_index)

    def show_message(self, text):
        if self.message_text:
            self.message_text["text"] = text

    def update_display(self):
        p = self.battle.active_player
        e = self.battle.active_enemy
        if self.player_name_text:
            self.player_name_text["text"] = f"{p.name}  Nv.{p.level}"
        if self.player_hp_bar:
            self.player_hp_bar["range"] = p.stats["hp"]
            self.player_hp_bar["value"] = p.current_hp
            ratio = p.hp_fraction()
            if ratio > 0.5:
                self.player_hp_bar["barColor"] = (0.2, 0.8, 0.2, 1)
            elif ratio > 0.2:
                self.player_hp_bar["barColor"] = (0.9, 0.7, 0.1, 1)
            else:
                self.player_hp_bar["barColor"] = (0.9, 0.2, 0.1, 1)
        if self.player_hp_text:
            self.player_hp_text["text"] = f"{p.current_hp} / {p.stats['hp']}"
        if self.enemy_name_text:
            self.enemy_name_text["text"] = f"{e.name}  Nv.{e.level}"
        if self.enemy_hp_bar:
            self.enemy_hp_bar["range"] = e.stats["hp"]
            self.enemy_hp_bar["value"] = e.current_hp
            ratio = e.hp_fraction()
            if ratio > 0.5:
                self.enemy_hp_bar["barColor"] = (0.2, 0.8, 0.2, 1)
            elif ratio > 0.2:
                self.enemy_hp_bar["barColor"] = (0.9, 0.7, 0.1, 1)
            else:
                self.enemy_hp_bar["barColor"] = (0.9, 0.2, 0.1, 1)
        if self.enemy_hp_text:
            self.enemy_hp_text["text"] = f"{e.current_hp} / {e.stats['hp']}"

    def _hide_all_menus(self):
        if self.action_frame:
            self.action_frame.hide()
        if self.move_frame:
            self.move_frame.destroy()
            self.move_frame = None
        if self.switch_frame:
            self.switch_frame.destroy()
            self.switch_frame = None

    def cleanup(self):
        self._hide_all_menus()
        for widget in [self.player_info_frame, self.enemy_info_frame,
                       self.message_frame, self.action_frame]:
            if widget:
                widget.destroy()
