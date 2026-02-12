"""
main_menu.py — Menu principal du jeu Pokémon (Panda3D).
Affiche les options de jeu au lancement.
"""
from panda3d.core import Vec4, TextNode, TransparencyAttrib
from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectLabel
)
from direct.gui.OnscreenText import OnscreenText


class MainMenu:
    """
    Menu principal avec les options :
    - Exploration
    - Combat Sauvage
    - Combat Dresseur
    - Pokédex
    - Soigner l'équipe
    - Quitter
    """

    def __init__(self, app, callbacks: dict):
        """
        Args:
            app: l'instance ShowBase
            callbacks: dict avec les clés:
                'exploration', 'wild_battle', 'trainer_battle',
                'pokedex', 'heal', 'quit'
        """
        self.app = app
        self.callbacks = callbacks

        # UI Elements
        self.root_frame = None
        self.title_text = None
        self.subtitle_text = None
        self.buttons = []
        self.message_text = None

    def setup(self):
        """Crée le menu principal."""
        # Fond plein écran semi-transparent
        self.root_frame = DirectFrame(
            frameColor=(0.05, 0.05, 0.12, 0.95),
            frameSize=(-2, 2, -1.5, 1.5),
            pos=(0, 0, 0)
        )

        # Titre
        self.title_text = OnscreenText(
            text="POKÉMON GAME",
            pos=(0, 0.6),
            scale=0.15,
            fg=(1, 0.85, 0.2, 1),
            shadow=(0.2, 0.1, 0, 1),
            font=None,
            align=TextNode.ACenter,
            parent=self.root_frame
        )

        # Sous-titre
        self.subtitle_text = OnscreenText(
            text="Panda3D Edition",
            pos=(0, 0.45),
            scale=0.06,
            fg=(0.7, 0.7, 0.8, 1),
            align=TextNode.ACenter,
            parent=self.root_frame
        )

        # Définition des boutons
        menu_items = [
            ("Exploration", "exploration", (0.2, 0.6, 0.3, 1)),
            ("Combat Sauvage", "wild_battle", (0.8, 0.3, 0.2, 1)),
            ("Combat Dresseur", "trainer_battle", (0.7, 0.4, 0.2, 1)),
            ("Pokedex", "pokedex", (0.3, 0.4, 0.7, 1)),
            ("Soigner l'equipe", "heal", (0.2, 0.7, 0.5, 1)),
            ("Quitter", "quit", (0.5, 0.5, 0.5, 1)),
        ]

        for i, (label, key, color) in enumerate(menu_items):
            y = 0.25 - i * 0.12
            btn = DirectButton(
                text=label,
                text_scale=0.055,
                text_fg=(1, 1, 1, 1),
                text_align=TextNode.ACenter,
                frameColor=color,
                frameSize=(-0.4, 0.4, -0.04, 0.06),
                relief=1,
                pos=(0, 0, y),
                command=self._on_click,
                extraArgs=[key],
                parent=self.root_frame
            )
            self.buttons.append(btn)

        # Zone de message (feedback soigner, etc.)
        self.message_text = OnscreenText(
            text="",
            pos=(0, -0.55),
            scale=0.05,
            fg=(0.5, 1, 0.5, 1),
            align=TextNode.ACenter,
            parent=self.root_frame
        )

    def _on_click(self, key: str):
        """Callback quand un bouton est cliqué."""
        callback = self.callbacks.get(key)
        if callback:
            callback()

    def show_message(self, text: str):
        """Affiche un message temporaire."""
        if self.message_text:
            self.message_text.setText(text)
            # Effacer après 2 secondes
            self.app.taskMgr.doMethodLater(
                2.0, self._clear_message, "clear_menu_msg"
            )

    def _clear_message(self, task):
        """Efface le message."""
        if self.message_text:
            self.message_text.setText("")
        return task.done

    def show(self):
        """Affiche le menu."""
        if self.root_frame:
            self.root_frame.show()

    def hide(self):
        """Cache le menu."""
        if self.root_frame:
            self.root_frame.hide()

    def cleanup(self):
        """Nettoie le menu."""
        for btn in self.buttons:
            btn.destroy()
        self.buttons = []
        if self.title_text:
            self.title_text.destroy()
        if self.subtitle_text:
            self.subtitle_text.destroy()
        if self.message_text:
            self.message_text.destroy()
        if self.root_frame:
            self.root_frame.destroy()
