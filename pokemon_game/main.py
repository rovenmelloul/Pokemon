#!/usr/bin/env python3
"""
main.py — Point d'entrée du jeu Pokémon (Panda3D).
Lance l'application graphique complète.
"""
import sys
import os

# Ajouter le dossier courant au path
sys.path.insert(0, os.path.dirname(__file__))

from engine.game_app import GameApp


def main():
    print("╔══════════════════════════════════════╗")
    print("║       🎮 POKÉMON GAME 3D 🎮          ║")
    print("║   Panda3D | Python | OOP             ║")
    print("╚══════════════════════════════════════╝")
    print()
    print("  Contrôles :")
    print("    ZQSD / Flèches : Se déplacer")
    print("    P : Pokédex")
    print("    Échap : Pause")
    print()

    app = GameApp()
    app.run()


if __name__ == "__main__":
    main()
