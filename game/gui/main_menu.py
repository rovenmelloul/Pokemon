# gui/main_menu.py
import sys
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DirectSlider
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui import DirectGuiGlobals as DGG
from panda3d.core import TransparencyAttrib


class MainMenu:
    """
    Main menu UI for Panda3D.
    Does NOT inherit from ShowBase.
    Pass base (ShowBase instance) into constructor.
    """

    def __init__(self, base, background="game/gui/src/sprites/menu_background.png", on_start=None):
        self.base = base
        self.background = background
        self.on_start_callback = on_start

        # UI containers
        self._root = None
        self._background_img = None
        self._buttons = []
        self._options_frame = None

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
            # OnscreenImage scales better for full-screen backgrounds than frameTexture
            self._background_img = OnscreenImage(
                image=self.background,
                pos=(0, 0, 0),
                scale=(1.4, 1, 1),
                parent=self._root
            )
            self._background_img.setTransparency(TransparencyAttrib.MAlpha)
        except Exception as e:
            print(f"[MainMenu] Failed to load background '{self.background}': {e}")

        # --- Title ---

        # --- Buttons ---
        # nicer spacing and styles
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

            # Button visual states (frameSize units tuned for the scale)
            frameSize=(-3.5, 3.5, -0.9, 0.9),
            frameColor=(0.12, 0.12, 0.12, 0.9),
            relief=DGG.FLAT,

            text_fg=(1, 1, 1, 1),
            text_scale=0.6,
        )

        # Bind events: use __setitem__ to change DirectButton options from callbacks
        btn.bind(DGG.ENTER, lambda _e, b=btn: b.__setitem__("frameColor", (0.22, 0.22, 0.22, 0.95)))
        btn.bind(DGG.EXIT, lambda _e, b=btn: b.__setitem__("frameColor", (0.12, 0.12, 0.12, 0.9)))
        btn.bind(DGG.B1PRESS, lambda _e, b=btn: b.__setitem__("frameColor", (0.06, 0.06, 0.06, 1.0)))

        # Optionally add a subtle scale animation on hover (works without external libs)
        btn.bind(DGG.ENTER, lambda _e, b=btn: b.setScale(0.095))
        btn.bind(DGG.EXIT, lambda _e, b=btn: b.setScale(0.09))

        self._buttons.append(btn)

    # ----------------------------
    # Button Callbacks
    # ----------------------------

    def _on_start(self):
        """Called when Start is pressed."""
        self.hide()
        if callable(self.on_start_callback):
            try:
                self.on_start_callback()
            except Exception as e:
                print(f"[MainMenu] Start callback error: {e}")

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

    def _on_volume_change(self, value):
        """Volume slider changed."""
        print(f"Volume set to: {value}")

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
            # OnscreenImage uses a NodePath; ensure it's visible too
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

    def destroy(self):
        """Completely remove menu."""
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