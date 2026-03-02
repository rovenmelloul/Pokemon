# gui/main_menu.py
import sys
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DirectSlider, DirectEntry
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui import DirectGuiGlobals as DGG
from panda3d.core import TransparencyAttrib, TextNode

from core.save_manager import SaveManager


class MainMenu:
    """
    Main menu UI for Panda3D.
    Does NOT inherit from ShowBase.
    Pass base (ShowBase instance) into constructor.
    """

    def __init__(self, base, background="game/gui/src/sprites/menu_background.png",
                 on_new_game=None, on_load_game=None):
        self.base = base
        self.background = background
        self.on_new_game = on_new_game
        self.on_load_game = on_load_game

        # UI containers
        self._root = None
        self._background_img = None
        self._buttons = []
        self._options_frame = None
        self._save_panel = None
        self._confirm_frame = None
        self._rename_frame = None

    def _play_click(self):
        sm = getattr(self.base, 'sound_manager', None)
        if sm:
            sm.play_sfx('menu_select')

    def _play_back(self):
        sm = getattr(self.base, 'sound_manager', None)
        if sm:
            sm.play_sfx('menu_back')

    def draw_main_menu(self):
        """Create and display the main menu."""
        if self._root:
            self.show()
            return

        # Root container (fullscreen)
        self._root = DirectFrame(
            frameSize=(-1.4, 1.4, -1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.base.aspect2d
        )

        # --- Background Image ---
        try:
            self._background_img = OnscreenImage(
                image=self.background,
                pos=(0, 0, 0),
                scale=(1.4, 1, 1),
                parent=self._root
            )
            self._background_img.setTransparency(TransparencyAttrib.MAlpha)
        except Exception as e:
            print(f"[MainMenu] Failed to load background '{self.background}': {e}")

        # --- Buttons ---
        self._create_button("Start Game", 0.15, self._on_start)
        self._create_button("Options", -0.05, self._on_options)
        self._create_button("Quit", -0.25, self._on_quit)

    def _create_button(self, text, y_pos, command):
        """Create a styled button with hover & press effects."""
        btn = DirectButton(
            text=text,
            scale=0.09,
            pos=(0, 0, y_pos),
            command=command,
            parent=self._root,

            frameSize=(-3.5, 3.5, -0.9, 0.9),
            frameColor=(0.12, 0.12, 0.12, 0.9),
            relief=DGG.FLAT,

            text_fg=(1, 1, 1, 1),
            text_scale=0.6,
        )

        btn.bind(DGG.ENTER, lambda _e, b=btn: b.__setitem__("frameColor", (0.22, 0.22, 0.22, 0.95)))
        btn.bind(DGG.EXIT, lambda _e, b=btn: b.__setitem__("frameColor", (0.12, 0.12, 0.12, 0.9)))
        btn.bind(DGG.B1PRESS, lambda _e, b=btn: b.__setitem__("frameColor", (0.06, 0.06, 0.06, 1.0)))

        btn.bind(DGG.ENTER, lambda _e, b=btn: b.setScale(0.095))
        btn.bind(DGG.EXIT, lambda _e, b=btn: b.setScale(0.09))

        self._buttons.append(btn)

    # ----------------------------
    # Save Slot Panel
    # ----------------------------

    def _show_save_panel(self):
        """Show the 3-slot save panel."""
        self._close_save_panel()

        # Hide main buttons
        for b in self._buttons:
            b.hide()

        slots = SaveManager.list_slots()

        self._save_panel = DirectFrame(
            frameSize=(-0.85, 0.85, -0.78, 0.58),
            frameColor=(0.05, 0.05, 0.05, 0.92),
            parent=self._root,
            pos=(0, 0, 0),
        )

        # Title
        DirectLabel(
            text="Sauvegardes",
            scale=0.07,
            pos=(0, 0, 0.45),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            parent=self._save_panel,
        )

        LEFT_X = -0.72  # left edge for text
        SLOT_SPACING = 0.32

        # 3 slot rows
        for i in range(3):
            slot_num = i + 1
            slot_data = slots[i]
            y = 0.28 - i * SLOT_SPACING

            if slot_data:
                save_name = slot_data.get("save_name", "")
                team_str = ", ".join(
                    f"{n} Nv.{l}" for n, l in
                    zip(slot_data["team_names"], slot_data["team_levels"])
                )
                if len(team_str) > 40:
                    team_str = team_str[:37] + "..."
                if save_name:
                    label = f"Partie {slot_num} - {save_name}"
                    sub_info = f"{team_str}  |  {slot_data['timestamp']}"
                else:
                    label = f"Partie {slot_num} - {team_str}"
                    sub_info = slot_data["timestamp"]
            else:
                label = f"Partie {slot_num} - Nouvelle Partie"
                sub_info = ""

            # Slot button (left-aligned text)
            btn = DirectButton(
                text=label,
                scale=0.055,
                pos=(0, 0, y),
                command=self._on_slot_click,
                extraArgs=[slot_num, slot_data is not None],
                parent=self._save_panel,
                frameSize=(-14, 10, -1.4, 1.4),
                frameColor=(0.15, 0.15, 0.15, 0.9),
                relief=DGG.FLAT,
                text_fg=(1, 1, 1, 1),
                text_scale=0.65,
                text_align=TextNode.ALeft,
                text_pos=(-13.5, -0.2),
            )
            btn.bind(DGG.ENTER, lambda _e, b=btn: b.__setitem__("frameColor", (0.25, 0.25, 0.25, 0.95)))
            btn.bind(DGG.EXIT, lambda _e, b=btn: b.__setitem__("frameColor", (0.15, 0.15, 0.15, 0.9)))

            # Sub-label (single line)
            if sub_info:
                DirectLabel(
                    text=sub_info,
                    scale=0.033,
                    pos=(LEFT_X, 0, y - 0.06),
                    frameColor=(0, 0, 0, 0),
                    text_fg=(0.5, 0.5, 0.5, 1),
                    text_align=TextNode.ALeft,
                    parent=self._save_panel,
                )

            # Rename + Delete buttons for occupied slots
            if slot_data:
                # Rename button (pen)
                ren_btn = DirectButton(
                    text="/",
                    scale=0.045,
                    pos=(0.64, 0, y),
                    command=self._on_rename_click,
                    extraArgs=[slot_num, slot_data.get("save_name", "")],
                    parent=self._save_panel,
                    frameSize=(-0.8, 0.8, -0.7, 0.7),
                    frameColor=(0.15, 0.4, 0.6, 0.9),
                    relief=DGG.FLAT,
                    text_fg=(1, 1, 1, 1),
                    text_scale=0.7,
                )
                ren_btn.bind(DGG.ENTER, lambda _e, b=ren_btn: b.__setitem__("frameColor", (0.2, 0.5, 0.75, 1)))
                ren_btn.bind(DGG.EXIT, lambda _e, b=ren_btn: b.__setitem__("frameColor", (0.15, 0.4, 0.6, 0.9)))

                # Delete button
                del_btn = DirectButton(
                    text="X",
                    scale=0.045,
                    pos=(0.74, 0, y),
                    command=self._on_delete_click,
                    extraArgs=[slot_num],
                    parent=self._save_panel,
                    frameSize=(-0.8, 0.8, -0.7, 0.7),
                    frameColor=(0.6, 0.15, 0.15, 0.9),
                    relief=DGG.FLAT,
                    text_fg=(1, 1, 1, 1),
                    text_scale=0.7,
                )
                del_btn.bind(DGG.ENTER, lambda _e, b=del_btn: b.__setitem__("frameColor", (0.8, 0.2, 0.2, 1)))
                del_btn.bind(DGG.EXIT, lambda _e, b=del_btn: b.__setitem__("frameColor", (0.6, 0.15, 0.15, 0.9)))

        # Retour button
        back_btn = DirectButton(
            text="Retour",
            scale=0.06,
            pos=(0, 0, -0.64),
            command=self._close_save_panel_and_show_main,
            parent=self._save_panel,
            frameSize=(-2.5, 2.5, -0.8, 0.8),
            frameColor=(0.12, 0.12, 0.12, 0.9),
            relief=DGG.FLAT,
            text_fg=(1, 1, 1, 1),
            text_scale=0.6,
        )
        back_btn.bind(DGG.ENTER, lambda _e, b=back_btn: b.__setitem__("frameColor", (0.22, 0.22, 0.22, 0.95)))
        back_btn.bind(DGG.EXIT, lambda _e, b=back_btn: b.__setitem__("frameColor", (0.12, 0.12, 0.12, 0.9)))

    def _on_slot_click(self, slot_num, has_save):
        """Called when a save slot is clicked."""
        if has_save:
            # Load existing game
            self.hide()
            if callable(self.on_load_game):
                self.on_load_game(slot_num)
        else:
            # New game
            self.hide()
            if callable(self.on_new_game):
                self.on_new_game(slot_num)

    def _on_rename_click(self, slot_num, current_name):
        """Show rename dialog for a save slot."""
        if self._rename_frame:
            self._rename_frame.destroy()
            self._rename_frame = None

        self._rename_frame = DirectFrame(
            frameSize=(-0.55, 0.55, -0.22, 0.22),
            frameColor=(0.1, 0.1, 0.1, 0.95),
            parent=self._root,
            pos=(0, 0, 0),
        )

        DirectLabel(
            text=f"Renommer Partie {slot_num}",
            scale=0.055,
            pos=(0, 0, 0.12),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            parent=self._rename_frame,
        )

        self._rename_entry = DirectEntry(
            scale=0.055,
            pos=(-0.35, 0, 0.01),
            width=12,
            initialText=current_name,
            numLines=1,
            parent=self._rename_frame,
            frameColor=(0.2, 0.2, 0.2, 1),
            text_fg=(1, 1, 1, 1),
            cursorKeys=True,
            focus=True,
        )

        DirectButton(
            text="OK",
            scale=0.05,
            pos=(-0.15, 0, -0.12),
            command=self._confirm_rename,
            extraArgs=[slot_num],
            parent=self._rename_frame,
            frameSize=(-2, 2, -0.8, 0.8),
            frameColor=(0.15, 0.5, 0.15, 0.9),
            relief=DGG.FLAT,
            text_fg=(1, 1, 1, 1),
            text_scale=0.6,
        )

        DirectButton(
            text="Annuler",
            scale=0.05,
            pos=(0.2, 0, -0.12),
            command=self._cancel_rename,
            parent=self._rename_frame,
            frameSize=(-2.5, 2.5, -0.8, 0.8),
            frameColor=(0.12, 0.12, 0.12, 0.9),
            relief=DGG.FLAT,
            text_fg=(1, 1, 1, 1),
            text_scale=0.6,
        )

    def _confirm_rename(self, slot_num):
        """Apply the new name to the save."""
        new_name = self._rename_entry.get().strip()
        SaveManager.rename(slot_num, new_name)
        if self._rename_frame:
            self._rename_frame.destroy()
            self._rename_frame = None
        self._show_save_panel()

    def _cancel_rename(self):
        """Close rename dialog."""
        if self._rename_frame:
            self._rename_frame.destroy()
            self._rename_frame = None

    def _on_delete_click(self, slot_num):
        """Show confirmation dialog for deleting a save."""
        if self._confirm_frame:
            self._confirm_frame.destroy()
            self._confirm_frame = None
        self._rename_frame = None

        self._confirm_frame = DirectFrame(
            frameSize=(-0.5, 0.5, -0.2, 0.2),
            frameColor=(0.1, 0.1, 0.1, 0.95),
            parent=self._root,
            pos=(0, 0, 0),
        )

        DirectLabel(
            text=f"Supprimer la Partie {slot_num} ?",
            scale=0.06,
            pos=(0, 0, 0.08),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            parent=self._confirm_frame,
        )

        DirectButton(
            text="Oui",
            scale=0.055,
            pos=(-0.18, 0, -0.07),
            command=self._confirm_delete,
            extraArgs=[slot_num],
            parent=self._confirm_frame,
            frameSize=(-2, 2, -0.8, 0.8),
            frameColor=(0.6, 0.15, 0.15, 0.9),
            relief=DGG.FLAT,
            text_fg=(1, 1, 1, 1),
            text_scale=0.6,
        )

        DirectButton(
            text="Non",
            scale=0.055,
            pos=(0.18, 0, -0.07),
            command=self._cancel_delete,
            parent=self._confirm_frame,
            frameSize=(-2, 2, -0.8, 0.8),
            frameColor=(0.12, 0.12, 0.12, 0.9),
            relief=DGG.FLAT,
            text_fg=(1, 1, 1, 1),
            text_scale=0.6,
        )

    def _confirm_delete(self, slot_num):
        """Delete the save and refresh the panel."""
        SaveManager.delete(slot_num)
        if self._confirm_frame:
            self._confirm_frame.destroy()
            self._confirm_frame = None
        self._rename_frame = None
        # Refresh save panel
        self._show_save_panel()

    def _cancel_delete(self):
        """Close delete confirmation."""
        if self._confirm_frame:
            self._confirm_frame.destroy()
            self._confirm_frame = None
        self._rename_frame = None

    def _close_save_panel(self):
        """Destroy the save panel."""
        if self._rename_frame:
            self._rename_frame.destroy()
            self._rename_frame = None
        if self._confirm_frame:
            self._confirm_frame.destroy()
            self._confirm_frame = None
        self._rename_frame = None
        if self._save_panel:
            self._save_panel.destroy()
            self._save_panel = None

    def _close_save_panel_and_show_main(self):
        """Close save panel and show main menu buttons."""
        self._close_save_panel()
        for b in self._buttons:
            b.show()

    # ----------------------------
    # Button Callbacks
    # ----------------------------

    def _on_start(self):
        """Called when Start is pressed -- show save panel."""
        self._show_save_panel()

    def _on_options(self):
        """Toggle options window."""
        if self._options_frame:
            self._options_frame.destroy()
            self._options_frame = None
            return

        self._options_frame = DirectFrame(
            frameSize=(-0.7, 0.7, -0.5, 0.5),
            frameColor=(0, 0, 0, 0.85),
            parent=self._root
        )

        DirectLabel(
            text="Options",
            scale=0.07,
            pos=(0, 0, 0.35),
            frameColor=(0, 0, 0, 0),
            parent=self._options_frame
        )

        DirectLabel(
            text="Master Volume",
            scale=0.05,
            pos=(0, 0, 0.1),
            frameColor=(0, 0, 0, 0),
            parent=self._options_frame
        )

        DirectSlider(
            range=(0, 1),
            value=0.5,
            pageSize=0.01,
            pos=(0, 0, -0.05),
            scale=0.6,
            parent=self._options_frame,
            command=self._on_volume_change
        )

        DirectButton(
            text="Close",
            scale=0.06,
            pos=(0, 0, -0.3),
            parent=self._options_frame,
            command=self._close_options
        )

    def _on_volume_change(self):
        """Volume slider changed."""
        pass

    def _close_options(self):
        if self._options_frame:
            self._options_frame.destroy()
            self._options_frame = None

    def _on_quit(self):
        """Exit the game safely."""
        try:
            self.base.userExit()
        except Exception:
            sys.exit(0)

    # ----------------------------
    # Visibility
    # ----------------------------

    def show(self):
        if self._root:
            self._root.show()
        for b in self._buttons:
            b.show()
        if self._options_frame:
            self._options_frame.show()
        if self._background_img:
            self._background_img.show()

    def hide(self):
        if self._root:
            self._root.hide()
        for b in self._buttons:
            b.hide()
        if self._options_frame:
            self._options_frame.hide()
        if self._background_img:
            self._background_img.hide()
        self._close_save_panel()

    def destroy(self):
        """Completely remove menu."""
        self._close_save_panel()

        if self._options_frame:
            self._options_frame.destroy()
            self._options_frame = None

        if self._background_img:
            self._background_img.destroy()
            self._background_img = None

        if self._root:
            self._root.destroy()
            self._root = None

        self._buttons = []
