from direct.gui.DirectGui import (
    DirectFrame,
    DirectLabel,
    DirectButton,
    DirectScrolledList,
    DGG,
)
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TextNode, TransparencyAttrib, Vec4
from core.pokedex import Pokedex


class PokedexUI:
    def __init__(self, base, pokedex: Pokedex, on_close_callback):
        self.base = base
        self.pokedex = pokedex
        self.on_close = on_close_callback
        self.frame = None
        self.font = None  # Utiliser la police par défaut

    def show(self):
        """Affiche l'interface du Pokédex."""
        # Fond semi-transparent
        self.frame = DirectFrame(
            frameColor=(0, 0, 0, 0.8),
            frameSize=(-1.5, 1.5, -1, 1),
            pos=(0, 0, 0),
        )

        # Titre
        DirectLabel(
            parent=self.frame,
            text="POKÉDEX",
            scale=0.1,
            pos=(0, 0, 0.8),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
        )

        # Liste des Pokémons
        self._create_scroll_list()

        # Bouton Fermer
        DirectButton(
            parent=self.frame,
            text="Fermer",
            scale=0.05,
            pos=(0, 0, -0.85),
            command=self.hide,
            frameSize=(-3, 3, -1, 1),
        )

    def _create_scroll_list(self):
        """Crée la liste défilante des Pokémon."""
        # Items de la liste
        items = []
        
        # Récupérer tous les Pokémon connus (vus ou capturés)
        import os, json
        # On utilise une méthode interne pour lister les entrées connues
        # Pokedex stocke tout dans self.entries
        known_entries = [
            (pid, data) 
            for pid, data in self.pokedex.entries.items() 
            if data["status"] in ("seen", "caught")
        ]
        # Trier par ID
        known_entries.sort(key=lambda x: x[0])
        
        if not known_entries:
            DirectLabel(
                parent=self.frame,
                text="Aucun Pokémon rencontré pour le moment.",
                scale=0.06,
                pos=(0, 0, 0),
                text_fg=(0.8, 0.8, 0.8, 1),
                frameColor=(0, 0, 0, 0),
            )
            return

        for pid, data in known_entries:
            status = "Capturé" if data["status"] == "caught" else "Vu"
            name = data["name"]
                
            color = (1, 1, 1, 1) if status == "Capturé" else (0.7, 0.7, 0.7, 1)
            icon_text = "🔴" if status == "Capturé" else "👁️"
            
            # Création du label pour l'item
            lbl = DirectLabel(
                text=f"#{pid:03d} {name} - {status}",
                text_scale=0.05,
                text_pos=(-0.4, 0),
                text_fg=color,
                frameColor=(0, 0, 0, 0),
                frameSize=(-0.5, 0.5, -0.05, 0.05)
            )
            items.append(lbl)

        # ScrolledList
        self.scrolled_list = DirectScrolledList(
            parent=self.frame,
            decButton_pos=(0.35, 0, 0.53),
            decButton_text="▲",
            decButton_text_scale=0.04,
            decButton_borderWidth=(0.005, 0.005),
            
            incButton_pos=(0.35, 0, -0.53),
            incButton_text="▼",
            incButton_text_scale=0.04,
            incButton_borderWidth=(0.005, 0.005),
            
            frameSize=(-0.5, 0.5, -0.6, 0.6),
            frameColor=(0.1, 0.1, 0.1, 0.5),
            pos=(0, 0, 0),
            numItemsVisible=10,
            forceHeight=0.11,
            itemFrame_frameSize=(-0.45, 0.45, -0.55, 0.55),
            itemFrame_pos=(0, 0, 0.5),
            items=items
        )

    def hide(self):
        """Cache l'interface et appelle le callback de fermeture."""
        callback = self.on_close
        self.on_close = None # Prevent recursion if callback calls cleanup
        self._destroy_frame()
        if callback:
            callback()

    def _destroy_frame(self):
        if self.frame:
            self.frame.destroy()
            self.frame = None

    def cleanup(self):
        """Détruit l'interface sans appeler le callback."""
        self.on_close = None
        self._destroy_frame()
