"""
PokedexUI -- Pokedex interface with PokeAPI sprite images.
"""
import os
from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton, DirectScrolledList, DGG,
)
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TextNode, TransparencyAttrib, Vec4, Texture, PNMImage, Filename
from core.pokedex import Pokedex

SPRITES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "sprites")

# Type colors for placeholder backgrounds
TYPE_COLORS = {
    "fire": (0.9, 0.3, 0.1), "water": (0.2, 0.5, 1.0),
    "grass": (0.2, 0.8, 0.3), "electric": (0.9, 0.8, 0.1),
    "normal": (0.6, 0.6, 0.5), "poison": (0.6, 0.2, 0.7),
    "psychic": (0.9, 0.3, 0.6), "ice": (0.4, 0.7, 0.9),
    "fighting": (0.7, 0.2, 0.15), "ground": (0.7, 0.6, 0.3),
    "flying": (0.5, 0.5, 0.8), "bug": (0.5, 0.6, 0.2),
    "rock": (0.6, 0.5, 0.3), "ghost": (0.4, 0.3, 0.5),
    "dragon": (0.4, 0.2, 0.8), "dark": (0.3, 0.2, 0.2),
    "steel": (0.5, 0.5, 0.6), "fairy": (0.8, 0.4, 0.6),
}


class PokedexUI:
    def __init__(self, base, pokedex, on_close_callback):
        self.base = base
        self.pokedex = pokedex
        self.on_close = on_close_callback
        self.frame = None
        self.detail_frame = None
        self._sprite_images = []

    def show(self):
        self.frame = DirectFrame(
            frameColor=(0.05, 0.05, 0.1, 0.92),
            frameSize=(-1.5, 1.5, -1, 1),
            pos=(0, 0, 0),
        )

        # Title
        DirectLabel(
            parent=self.frame,
            text="POKEDEX",
            scale=0.1,
            pos=(0, 0, 0.85),
            text_fg=(1, 0.85, 0.2, 1),
            frameColor=(0, 0, 0, 0),
        )

        # Stats
        seen = self.pokedex.get_seen_count()
        caught = self.pokedex.get_caught_count()
        total = self.pokedex.get_total_count()
        DirectLabel(
            parent=self.frame,
            text=f"Seen: {seen}  |  Caught: {caught}  |  Total: {total}",
            scale=0.04,
            pos=(0, 0, 0.75),
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
        )

        # Build scrollable Pokemon list
        self._create_pokemon_grid()

        # Close button
        DirectButton(
            parent=self.frame,
            text="Close [P]",
            scale=0.05,
            pos=(0, 0, -0.9),
            command=self.hide,
            frameSize=(-3, 3, -1, 1),
            text_fg=(1, 1, 1, 1),
            frameColor=(0.4, 0.2, 0.2, 1),
        )

    def _create_pokemon_grid(self):
        """Create a scrolled list of Pokemon entries with sprites."""
        entries = self.pokedex.get_entries_list()
        items = []

        for entry in entries:
            item_frame = DirectFrame(
                frameColor=(0.15, 0.15, 0.2, 0.8),
                frameSize=(-0.6, 0.6, -0.05, 0.05),
            )

            # Status indicator
            if entry["status"] == "caught":
                status_text = "[C]"
                status_color = (0.2, 0.8, 0.2, 1)
            elif entry["status"] == "seen":
                status_text = "[S]"
                status_color = (0.8, 0.8, 0.2, 1)
            else:
                status_text = "[ ]"
                status_color = (0.4, 0.4, 0.4, 1)

            DirectLabel(
                parent=item_frame,
                text=status_text,
                text_fg=status_color,
                text_scale=0.04,
                pos=(-0.52, 0, -0.01),
                frameColor=(0, 0, 0, 0),
            )

            # Sprite image (if available and caught/seen)
            sprite_loaded = False
            if entry["status"] != "unknown":
                sprite_path = os.path.join(SPRITES_DIR, f"{entry['id']}.png")
                if os.path.exists(sprite_path):
                    try:
                        img = OnscreenImage(
                            image=sprite_path,
                            pos=(-0.4, 0, 0),
                            scale=0.04,
                            parent=item_frame,
                        )
                        img.setTransparency(TransparencyAttrib.MAlpha)
                        self._sprite_images.append(img)
                        sprite_loaded = True
                    except Exception:
                        pass

            # Pokemon info text
            types_str = "/".join(entry["types"])
            name_text = f"#{entry['id']:03d} {entry['name']:12s}"
            if entry["status"] == "caught":
                name_text += f"  [{types_str}]"

            DirectLabel(
                parent=item_frame,
                text=name_text,
                text_fg=(1, 1, 1, 1) if entry["status"] == "caught" else (0.6, 0.6, 0.6, 1),
                text_scale=0.04,
                text_align=TextNode.ALeft,
                pos=(-0.3, 0, -0.01),
                frameColor=(0, 0, 0, 0),
            )

            items.append(item_frame)

        # Scrolled list
        self.scrolled_list = DirectScrolledList(
            parent=self.frame,
            decButton_pos=(0.65, 0, 0.55),
            decButton_text="UP",
            decButton_text_scale=0.04,
            decButton_borderWidth=(0.005, 0.005),
            incButton_pos=(0.65, 0, -0.65),
            incButton_text="DOWN",
            incButton_text_scale=0.04,
            incButton_borderWidth=(0.005, 0.005),
            frameSize=(-0.7, 0.7, -0.7, 0.65),
            frameColor=(0.08, 0.08, 0.12, 0.5),
            pos=(0, 0, 0),
            numItemsVisible=10,
            forceHeight=0.12,
            itemFrame_frameSize=(-0.65, 0.65, -0.6, 0.6),
            itemFrame_pos=(0, 0, 0.55),
            items=items,
        )

    def hide(self):
        callback = self.on_close
        self.on_close = None
        self._destroy_frame()
        if callback:
            callback()

    def _destroy_frame(self):
        for img in self._sprite_images:
            try:
                img.destroy()
            except Exception:
                pass
        self._sprite_images = []
        if self.frame:
            self.frame.destroy()
            self.frame = None

    def cleanup(self):
        self.on_close = None
        self._destroy_frame()
