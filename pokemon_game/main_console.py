#!/usr/bin/env python3
"""
main_console.py — Test du combat Pokémon en console.
Combat 1v1 avec équipe de 6, capture, XP, Pokédex.
"""
import sys
import os

# Ajouter le dossier parent au path
sys.path.insert(0, os.path.dirname(__file__))

from core.pokemon import Pokemon
from core.battle import BattleSystem
from core.capture import CaptureSystem
from core.xp_system import XPSystem
from core.pokedex import Pokedex


def display_battle_state(battle: BattleSystem):
    """Affiche l'état du combat."""
    p = battle.active_player
    e = battle.active_enemy
    
    hp_bar_p = "█" * int(p.hp_fraction() * 20) + "░" * (20 - int(p.hp_fraction() * 20))
    hp_bar_e = "█" * int(e.hp_fraction() * 20) + "░" * (20 - int(e.hp_fraction() * 20))
    
    print("\n" + "═" * 50)
    print(f"  🔴 {e.name:15s} Lv.{e.level:3d}")
    print(f"     HP: [{hp_bar_e}] {e.current_hp}/{e.stats['hp']}")
    if e.status:
        print(f"     Statut: {e.status}")
    print()
    print(f"  🔵 {p.name:15s} Lv.{p.level:3d}")
    print(f"     HP: [{hp_bar_p}] {p.current_hp}/{p.stats['hp']}")
    if p.status:
        print(f"     Statut: {p.status}")
    
    alive_p = sum(1 for pk in battle.team_player if not pk.is_fainted())
    alive_e = sum(1 for pk in battle.team_enemy if not pk.is_fainted())
    print(f"\n  Équipe: {alive_p}/{len(battle.team_player)} vs {alive_e}/{len(battle.team_enemy)}")
    print("═" * 50)


def display_moves(pokemon: Pokemon):
    """Affiche les moves disponibles."""
    print("\n  Attaques :")
    for i, move in enumerate(pokemon.moves):
        type_str = move.type.upper()
        cat = "PHY" if move.category == "physical" else ("SPE" if move.category == "special" else "STA")
        print(f"    {i+1}. {move.name:20s} [{type_str:8s}] {cat} "
              f"PWR={move.power:3d} ACC={move.accuracy:3d} PP={move.current_pp}/{move.max_pp}")


def display_team(team: list[Pokemon]):
    """Affiche l'équipe."""
    print("\n  Équipe :")
    for i, p in enumerate(team):
        status = "K.O." if p.is_fainted() else f"HP={p.current_hp}/{p.stats['hp']}"
        types = "/".join(p.types)
        print(f"    {i+1}. {p.name:15s} Lv.{p.level} [{types}] {status}")


def get_player_action(battle: BattleSystem) -> dict:
    """Demande au joueur son action."""
    while True:
        print("\n  Que voulez-vous faire ?")
        print("    1. Attaquer")
        print("    2. Changer de Pokémon")
        if battle.is_wild:
            print("    3. Capturer")
            print("    4. Fuir")
        print("    5. Pokédex")
        
        try:
            choice = input("\n  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Au revoir !")
            sys.exit(0)
        
        if choice == "1":
            display_moves(battle.active_player)
            try:
                idx = int(input("  Choisir (1-4) : ").strip()) - 1
            except (ValueError, EOFError, KeyboardInterrupt):
                continue
            if 0 <= idx < len(battle.active_player.moves):
                return {"type": "attack", "move_index": idx}
            print("  ❌ Choix invalide !")
        
        elif choice == "2":
            switches = battle.get_available_switches()
            if not switches:
                print("  ❌ Aucun Pokémon disponible !")
                continue
            display_team(battle.team_player)
            try:
                idx = int(input("  Choisir : ").strip()) - 1
            except (ValueError, EOFError, KeyboardInterrupt):
                continue
            if any(i == idx for i, _ in switches):
                return {"type": "switch", "pokemon_index": idx}
            print("  ❌ Choix invalide !")
        
        elif choice == "3" and battle.is_wild:
            return {"type": "capture"}
        
        elif choice == "4" and battle.is_wild:
            return {"type": "run"}
        
        elif choice == "5":
            return {"type": "pokedex"}
        
        else:
            print("  ❌ Choix invalide !")


def run_battle(team_player: list[Pokemon], team_enemy: list[Pokemon], 
               pokedex: Pokedex, is_wild: bool = True):
    """Lance un combat complet en console."""
    battle = BattleSystem(team_player, team_enemy, is_wild=is_wild)
    
    # Marquer le Pokémon ennemi comme vu
    pokedex.mark_seen(battle.active_enemy.id)
    
    print("\n" + "🔥" * 25)
    if is_wild:
        print(f"  Un {battle.active_enemy.name} sauvage apparaît !")
    else:
        print(f"  Combat de dresseur !")
    print("🔥" * 25)
    
    captured_pokemon = None
    
    while not battle.is_over:
        display_battle_state(battle)
        
        # Switch forcé si KO
        if battle.player_needs_switch():
            print("\n  ⚠️  Votre Pokémon est K.O. ! Choisissez-en un autre !")
            display_team(team_player)
            while True:
                try:
                    idx = int(input("  Choisir : ").strip()) - 1
                except (ValueError, EOFError, KeyboardInterrupt):
                    continue
                if battle.switch_player_pokemon(idx):
                    break
                print("  ❌ Choix invalide !")
            continue
        
        # Action du joueur
        action = get_player_action(battle)
        
        if action["type"] == "pokedex":
            print(pokedex.display())
            continue
        
        if action["type"] == "capture":
            # Tenter la capture
            print("\n  🎯 Lancer de Pokéball !")
            result = CaptureSystem.attempt_capture(battle.active_enemy, "pokeball")
            for i in range(result["shakes"]):
                print(f"    ... shake {i+1} ...")
            print(f"  {result['message']}")
            if result["success"]:
                pokedex.mark_caught(battle.active_enemy.id)
                captured_pokemon = battle.active_enemy
                battle.is_over = True
                battle.winner = "player"
                break
            else:
                # L'ennemi attaque quand même
                enemy_action = battle.get_enemy_action()
                logs = battle.execute_turn(
                    {"type": "attack", "move_index": 0},  # dummy, le joueur a lancé une ball
                    enemy_action
                )
                # On affiche uniquement l'attaque ennemie
                for line in logs:
                    if "ennemi" in line.lower() or "enemy" in line.lower() or "L'" in line:
                        print(line)
                continue
        
        # Action de l'ennemi
        enemy_action = battle.get_enemy_action()
        
        # Exécuter le tour
        logs = battle.execute_turn(action, enemy_action)
        for line in logs:
            print(line)
    
    # XP et résultats
    if battle.winner == "player" and not captured_pokemon:
        print("\n  📊 Résultats :")
        for pokemon in team_player:
            if not pokemon.is_fainted():
                xp = XPSystem.calculate_xp_gain(pokemon, team_enemy[0], is_wild)
                events = XPSystem.award_xp(pokemon, xp)
                messages = XPSystem.format_events(events)
                print(f"\n  {pokemon.name} :")
                for msg in messages:
                    print(msg)
    
    if captured_pokemon:
        print(f"\n  {captured_pokemon.name} a été ajouté à votre équipe !")
        if len(team_player) < 6:
            captured_pokemon.full_restore()
            team_player.append(captured_pokemon)
    
    return battle.winner, captured_pokemon


def main():
    """Point d'entrée console."""
    print("╔══════════════════════════════════════╗")
    print("║     🎮 POKÉMON BATTLE CONSOLE 🎮     ║")
    print("╚══════════════════════════════════════╝")
    
    # Créer l'équipe du joueur
    print("\n  Création de votre équipe...")
    team_player = [
        Pokemon.create(1, 15),   # Bulbasaur Lv.15
        Pokemon.create(4, 15),   # Charmander Lv.15
        Pokemon.create(7, 15),   # Squirtle Lv.15
        Pokemon.create(10, 15),  # Pikachu Lv.15
        Pokemon.create(18, 14),  # Gastly Lv.14
        Pokemon.create(21, 14),  # Eevee Lv.14
    ]
    
    # Pokédex
    pokedex = Pokedex()
    for p in team_player:
        pokedex.mark_caught(p.id)
    
    print("  Équipe prête !")
    display_team(team_player)
    
    # Boucle de combats
    while True:
        print("\n" + "─" * 50)
        print("  Menu principal :")
        print("    1. Combat sauvage aléatoire")
        print("    2. Combat dresseur")
        print("    3. Voir l'équipe")
        print("    4. Pokédex")
        print("    5. Soigner l'équipe")
        print("    6. Quitter")
        
        try:
            choice = input("\n  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if choice == "1":
            # Combat sauvage
            import random
            wild_ids = [12, 13, 14, 23, 30]  # Pokémons sauvages courants
            wild_id = random.choice(wild_ids)
            wild_level = random.randint(
                max(5, team_player[0].level - 5),
                team_player[0].level + 2
            )
            wild = Pokemon.create(wild_id, wild_level)
            team_enemy = [wild]
            run_battle(team_player, team_enemy, pokedex, is_wild=True)
        
        elif choice == "2":
            # Combat dresseur
            team_enemy = [
                Pokemon.create(15, 16),  # Machop
                Pokemon.create(14, 16),  # Geodude
                Pokemon.create(29, 17),  # Onix
            ]
            run_battle(team_player, team_enemy, pokedex, is_wild=False)
        
        elif choice == "3":
            display_team(team_player)
            input("  Appuyez sur Entrée pour continuer...")
        
        elif choice == "4":
            print(pokedex.display())
            input("  Appuyez sur Entrée pour continuer...")
        
        elif choice == "5":
            for p in team_player:
                p.full_restore()
            print("  ✅ Toute l'équipe est soignée !")
        
        elif choice == "6":
            break
    
    print("\n  👋 À bientôt, Dresseur !")


if __name__ == "__main__":
    main()
