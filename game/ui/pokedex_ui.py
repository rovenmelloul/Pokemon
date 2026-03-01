"""
PokedexUI -- Interface Pokedex avec pagination et filtre.
Supporte un mode swap pour echanger un Pokemon de l'equipe.
"""
import os
from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton, DGG,
)
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode, TransparencyAttrib, Filename
from core.pokedex import Pokedex

SPRITES_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "sprites"))
ITEMS_PER_PAGE = 10

TYPE_COLORS = {
    "fire": (1, 0.4, 0.1, 1), "water": (0.3, 0.55, 1, 1),
    "grass": (0.3, 0.75, 0.3, 1), "electric": (1, 0.85, 0.15, 1),
    "poison": (0.65, 0.25, 0.8, 1), "normal": (0.65, 0.65, 0.55, 1),
    "ghost": (0.45, 0.35, 0.65, 1), "fighting": (0.75, 0.3, 0.2, 1),
    "rock": (0.7, 0.6, 0.35, 1), "ground": (0.72, 0.6, 0.3, 1),
    "flying": (0.55, 0.6, 0.9, 1), "bug": (0.55, 0.7, 0.15, 1),
    "ice": (0.55, 0.8, 0.9, 1), "dragon": (0.45, 0.35, 0.9, 1),
    "dark": (0.35, 0.25, 0.2, 1), "steel": (0.6, 0.6, 0.7, 1),
    "fairy": (0.9, 0.5, 0.7, 1), "psychic": (1, 0.35, 0.65, 1),
    "???": (0.4, 0.4, 0.4, 1),
}


class PokedexUI(DirectObject):
    def __init__(self, base, pokedex, on_close_callback,
                 swap_mode=False, on_swap_select=None):
        super().__init__()
        self.base = base
        self.pokedex = pokedex
        self.on_close = on_close_callback
        self.swap_mode = swap_mode
        self.on_swap_select = on_swap_select
        self.frame = None
        self._sprite_images = []
        self._card_nodes = []
        self._empty_label = None
        self.filter_unlocked = True
        self.current_page = 0
        self._all_entries = []
        self._page_label = None

    def show(self):
        self.frame = DirectFrame(
            frameColor=(0.05, 0.05, 0.1, 0.92),
            frameSize=(-1.5, 1.5, -1, 1),
            pos=(0, 0, 0),
        )

        # Title (different in swap mode)
        if self.swap_mode:
            DirectLabel(
                parent=self.frame,
                text="CHOISIR UN POKEMON",
                scale=0.07,
                pos=(-0.5, 0, 0.92),
                text_fg=(0.3, 0.85, 0.5, 1),
                frameColor=(0, 0, 0, 0),
            )
        else:
            # Top bar: filter + counters
            self.filter_btn = DirectButton(
                parent=self.frame,
                text="Filtre: Debloques",
                scale=0.04,
                pos=(-1.05, 0, 0.92),
                command=self._toggle_filter,
                text_fg=(1, 1, 1, 1),
                frameColor=(0.3, 0.5, 0.3, 1),
                frameSize=(-3.5, 3.5, -0.7, 1.1),
            )

        seen = self.pokedex.get_seen_count()
        caught = self.pokedex.get_caught_count()
        total = self.pokedex.get_total_count()
        DirectLabel(
            parent=self.frame,
            text=f"Vus: {seen} | Captures: {caught} | Total: {total}",
            scale=0.035,
            pos=(0.65, 0, 0.93),
            text_fg=(0.7, 0.7, 0.7, 1),
            frameColor=(0, 0, 0, 0),
        )

        # Page navigation (bottom)
        self.prev_btn = DirectButton(
            parent=self.frame,
            text="< Prec",
            scale=0.04,
            pos=(-0.6, 0, -0.88),
            command=self._prev_page,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.25, 0.25, 0.35, 1),
            frameSize=(-3, 3, -0.7, 1.1),
        )
        self.next_btn = DirectButton(
            parent=self.frame,
            text="Suiv >",
            scale=0.04,
            pos=(0.6, 0, -0.88),
            command=self._next_page,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.25, 0.25, 0.35, 1),
            frameSize=(-3, 3, -0.7, 1.1),
        )
        self._page_label = DirectLabel(
            parent=self.frame,
            text="",
            scale=0.035,
            pos=(0, 0, -0.87),
            text_fg=(0.6, 0.6, 0.6, 1),
            frameColor=(0, 0, 0, 0),
        )

        # Close button
        close_text = "Annuler" if self.swap_mode else "Fermer [P]"
        DirectButton(
            parent=self.frame,
            text=close_text,
            scale=0.045,
            pos=(0, 0, -0.95),
            command=self.hide,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.4, 0.2, 0.2, 1),
            frameSize=(-3, 3, -0.7, 1.1),
        )

        # Mouse wheel scroll
        self.accept("wheel_up", self._prev_page)
        self.accept("wheel_down", self._next_page)

        self._refresh_entries()
        self._render_page()

    def _toggle_filter(self):
        if self.swap_mode:
            return
        self.filter_unlocked = not self.filter_unlocked
        if self.filter_unlocked:
            self.filter_btn["text"] = "Filtre: Debloques"
            self.filter_btn["frameColor"] = (0.3, 0.5, 0.3, 1)
        else:
            self.filter_btn["text"] = "Filtre: Tous"
            self.filter_btn["frameColor"] = (0.4, 0.3, 0.5, 1)
        self.current_page = 0
        self._refresh_entries()
        self._render_page()

    def _refresh_entries(self):
        entries = self.pokedex.get_entries_list()
        if self.swap_mode:
            entries = [e for e in entries if e["status"] == "caught"]
        elif self.filter_unlocked:
            entries = [e for e in entries if e["status"] in ("seen", "caught")]
        self._all_entries = entries

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._render_page()

    def _next_page(self):
        max_page = max(0, (len(self._all_entries) - 1) // ITEMS_PER_PAGE)
        if self.current_page < max_page:
            self.current_page += 1
            self._render_page()

    def _render_page(self):
        for img in self._sprite_images:
            try:
                img.destroy()
            except Exception:
                pass
        self._sprite_images = []
        for node in self._card_nodes:
            try:
                node.destroy()
            except Exception:
                pass
        self._card_nodes = []
        if self._empty_label:
            self._empty_label.destroy()
            self._empty_label = None

        total = len(self._all_entries)
        max_page = max(0, (total - 1) // ITEMS_PER_PAGE) if total > 0 else 0
        start = self.current_page * ITEMS_PER_PAGE
        end = min(start + ITEMS_PER_PAGE, total)
        page_entries = self._all_entries[start:end]

        if total > 0:
            self._page_label["text"] = f"Page {self.current_page + 1}/{max_page + 1} ({total} Pokemon)"
        else:
            self._page_label["text"] = ""

        self.prev_btn["state"] = DGG.NORMAL if self.current_page > 0 else DGG.DISABLED
        self.next_btn["state"] = DGG.NORMAL if self.current_page < max_page else DGG.DISABLED

        if not page_entries:
            empty_text = "Aucun Pokemon capture." if self.swap_mode else "Aucun Pokemon decouvert."
            self._empty_label = DirectLabel(
                parent=self.frame,
                text=empty_text,
                scale=0.05,
                pos=(0, 0, 0.1),
                text_fg=(0.5, 0.5, 0.5, 1),
                frameColor=(0, 0, 0, 0),
            )
            return

        card_h = 0.16
        top_y = 0.75
        for i, entry in enumerate(page_entries):
            y = top_y - i * card_h
            card = self._create_pokemon_card(entry, y)
            self._card_nodes.append(card)

    def _create_pokemon_card(self, entry, y_pos):
        is_caught = entry["status"] == "caught"
        is_seen = entry["status"] == "seen"
        is_unknown = entry["status"] == "unknown"

        if is_caught:
            bg_color = (0.12, 0.12, 0.18, 0.9)
        elif is_seen:
            bg_color = (0.1, 0.1, 0.14, 0.85)
        else:
            bg_color = (0.06, 0.06, 0.08, 0.7)

        card = DirectFrame(
            parent=self.frame,
            frameColor=bg_color,
            frameSize=(-1.3, 1.3, -0.07, 0.07),
            pos=(0, 0, y_pos),
        )

        if is_caught:
            ind_color = (0.2, 0.8, 0.2, 1)
        elif is_seen:
            ind_color = (0.9, 0.8, 0.2, 1)
        else:
            ind_color = (0.2, 0.2, 0.2, 1)

        DirectFrame(
            parent=card,
            frameColor=ind_color,
            frameSize=(-0.01, 0.01, -0.06, 0.06),
            pos=(-1.27, 0, 0),
        )

        # Sprite
        sprite_id = entry.get("sprite_id", entry["id"])
        sprite_path = os.path.join(SPRITES_DIR, f"{sprite_id}.png")
        if os.path.exists(sprite_path):
            panda_path = Filename.fromOsSpecific(sprite_path).getFullpath()
            try:
                img = DirectFrame(
                    parent=card,
                    image=panda_path,
                    image_scale=0.06,
                    frameColor=(0, 0, 0, 0),
                    frameSize=(-0.07, 0.07, -0.07, 0.07),
                    pos=(-1.1, 0, 0),
                )
                img.setTransparency(TransparencyAttrib.MAlpha)
                if is_unknown:
                    img.setColorScale(0.15, 0.15, 0.2, 0.9)
                elif is_seen:
                    img.setColorScale(0.6, 0.6, 0.6, 0.9)
                self._sprite_images.append(img)
            except Exception as e:
                print(f"[Pokedex] Sprite error {sprite_id}: {e}")

        # Number + Name
        num_str = f"#{entry['id']:03d}"
        if is_caught:
            name_fg = (1, 1, 1, 1)
        elif is_seen:
            name_fg = (0.7, 0.7, 0.7, 1)
        else:
            name_fg = (0.3, 0.3, 0.35, 1)

        name_text = f"{num_str}  {entry['name']}"
        if self.swap_mode and is_caught:
            level = entry.get("level", 0)
            name_text += f"  Nv.{level}"
            if entry.get("is_shiny"):
                name_text = f"[*] {name_text}"
                name_fg = (1, 0.84, 0, 1)

        DirectLabel(
            parent=card,
            text=name_text,
            text_fg=name_fg,
            text_scale=0.045,
            text_align=TextNode.ALeft,
            pos=(-0.95, 0, 0.02),
            frameColor=(0, 0, 0, 0),
        )

        # Types
        if not is_unknown:
            types = entry.get("types", ["???"])
            x_offset = -0.95
            for t in types:
                t_color = TYPE_COLORS.get(t, (0.5, 0.5, 0.5, 1))
                DirectFrame(
                    parent=card,
                    frameColor=(t_color[0], t_color[1], t_color[2], 0.7),
                    frameSize=(-0.08, 0.08, -0.014, 0.016),
                    pos=(x_offset + 0.08, 0, -0.03),
                )
                DirectLabel(
                    parent=card,
                    text=t.upper(),
                    text_fg=(1, 1, 1, 0.9),
                    text_scale=0.022,
                    pos=(x_offset + 0.08, 0, -0.032),
                    frameColor=(0, 0, 0, 0),
                )
                x_offset += 0.2

        # Swap mode: "Choisir" button
        if self.swap_mode and is_caught:
            DirectButton(
                parent=card,
                text="Choisir",
                text_fg=(1, 1, 1, 1),
                scale=0.045,
                frameColor=(0.2, 0.6, 0.3, 1),
                frameSize=(-2, 2, -0.6, 0.8),
                pos=(1.05, 0, 0),
                command=self._select_for_swap,
                extraArgs=[entry["id"], entry.get("level", 5), entry.get("is_shiny", False)],
            )
        else:
            if is_caught and entry.get("base_stats"):
                stats = entry["base_stats"]
                parts = []
                for label, key in [("PV","hp"),("ATQ","attack"),("DEF","defense"),
                                    ("AtS","sp_attack"),("DeS","sp_defense"),("VIT","speed")]:
                    parts.append(f"{label}:{stats.get(key,0)}")
                DirectLabel(
                    parent=card,
                    text="  ".join(parts),
                    text_fg=(0.5, 0.5, 0.55, 1),
                    text_scale=0.02,
                    text_align=TextNode.ARight,
                    pos=(1.25, 0, -0.03),
                    frameColor=(0, 0, 0, 0),
                )

            if is_caught:
                DirectLabel(
                    parent=card, text="CAPTURE",
                    text_fg=(0.3, 0.85, 0.3, 1), text_scale=0.025,
                    pos=(1.1, 0, 0.03), frameColor=(0, 0, 0, 0),
                )
            elif is_seen:
                DirectLabel(
                    parent=card, text="VU",
                    text_fg=(0.9, 0.8, 0.2, 1), text_scale=0.025,
                    pos=(1.1, 0, 0.03), frameColor=(0, 0, 0, 0),
                )

        return card

    def _select_for_swap(self, pokedex_id, level, is_shiny):
        """Select a Pokemon for swap - cleanup without triggering on_close."""
        if self.on_swap_select:
            callback = self.on_swap_select
            self.on_swap_select = None
            self.on_close = None
            self.ignoreAll()
            self._destroy_frame()
            callback(pokedex_id, level, is_shiny)

    def hide(self):
        self.ignoreAll()
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
        for node in self._card_nodes:
            try:
                node.destroy()
            except Exception:
                pass
        self._card_nodes = []
        if self._empty_label:
            self._empty_label.destroy()
            self._empty_label = None
        if self.frame:
            self.frame.destroy()
            self.frame = None

    def cleanup(self):
        self.ignoreAll()
        self.on_close = None
        self.on_swap_select = None
        self._destroy_frame()
