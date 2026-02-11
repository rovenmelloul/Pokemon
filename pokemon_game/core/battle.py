"""
BattleSystem — Système de combat 1v1 complet.
Formule de dégâts Gen 5+, STAB, critiques, précision, switch, KO.
"""
import random
from .pokemon import Pokemon
from .move import Move
from .type_chart import TypeChart


class BattleSystem:
    """
    Gère un combat Pokémon 1v1 tour par tour.
    
    Supporte :
    - Formule de dégâts officielle Gen 5+
    - STAB (Same Type Attack Bonus) × 1.5
    - Coups critiques (1/16 chance, ×1.5 dégâts)
    - Précision / esquive
    - Efficacité des types (0×, 0.5×, 1×, 2×, 4× etc.)
    - Switch Pokémon (team de 6)
    - Détection de victoire
    - Effets de statut basiques
    """

    def __init__(self, team_player: list[Pokemon], team_enemy: list[Pokemon],
                 is_wild: bool = True):
        self.team_player = team_player
        self.team_enemy = team_enemy
        self.active_player: Pokemon = team_player[0]
        self.active_enemy: Pokemon = team_enemy[0]
        self.is_wild = is_wild
        self.battle_log: list[str] = []
        self.is_over = False
        self.winner: str | None = None  # "player" ou "enemy"
        self.turn_count = 0

    def log(self, message: str):
        """Ajoute un message au log de combat."""
        self.battle_log.append(message)

    # ─────────── Formule de dégâts ───────────

    def calculate_damage(self, attacker: Pokemon, defender: Pokemon, move: Move) -> tuple[int, bool, float]:
        """
        Calcule les dégâts d'une attaque.
        Retourne (dégâts, is_critical, effectiveness_multiplier).
        
        Formule Gen 5+:
        damage = ((2*level/5 + 2) * power * A/D) / 50 + 2
        damage *= targets * weather * critical * random * STAB * type * burn
        """
        if not move.is_damaging():
            return 0, False, 1.0

        level = attacker.level

        # Attaque / Défense selon catégorie
        if move.category == "physical":
            atk_stat = attacker.stats["attack"]
            def_stat = defender.stats["defense"]
        else:  # special
            atk_stat = attacker.stats["sp_attack"]
            def_stat = defender.stats["sp_defense"]

        # Formule de base
        base_damage = ((2 * level / 5 + 2) * move.power * atk_stat / def_stat) / 50 + 2

        # Critique (1/16 chance)
        is_critical = random.randint(1, 16) == 1
        critical_mult = 1.5 if is_critical else 1.0

        # Random (85% à 100%)
        random_mult = random.randint(85, 100) / 100.0

        # STAB (Same Type Attack Bonus)
        stab = 1.5 if move.type in attacker.types else 1.0

        # Type effectiveness
        type_mult = TypeChart.get_effectiveness(move.type, defender.types)

        # Burn penalty (attaque physique sous brûlure)
        burn_mult = 0.5 if (attacker.status == "burn" and move.category == "physical") else 1.0

        # Calcul final
        total = int(base_damage * critical_mult * random_mult * stab * type_mult * burn_mult)
        total = max(1, total) if type_mult > 0 else 0

        return total, is_critical, type_mult

    # ─────────── Précision ───────────

    def accuracy_check(self, move: Move) -> bool:
        """Vérifie si l'attaque touche."""
        if move.accuracy >= 100:
            return True
        return random.randint(1, 100) <= move.accuracy

    # ─────────── Tour de combat ───────────

    def execute_turn(self, player_action: dict, enemy_action: dict) -> list[str]:
        """
        Exécute un tour complet.
        
        Actions possibles :
        - {"type": "attack", "move_index": int}
        - {"type": "switch", "pokemon_index": int}
        - {"type": "run"} (combat sauvage uniquement)
        - {"type": "item", "item": str} (Pokéball, etc.)
        
        Retourne la liste des messages du tour.
        """
        self.turn_count += 1
        self.battle_log = []
        self.log(f"\n══════ Tour {self.turn_count} ══════")

        # Résoudre les switches d'abord (priorité)
        if player_action["type"] == "switch":
            self._do_switch("player", player_action["pokemon_index"])
        if enemy_action["type"] == "switch":
            self._do_switch("enemy", enemy_action["pokemon_index"])

        # Fuite
        if player_action["type"] == "run":
            if self.is_wild:
                self.log("Vous avez fui le combat !")
                self.is_over = True
                return self.battle_log
            else:
                self.log("Impossible de fuir un combat dresseur !")

        # Déterminer l'ordre d'attaque
        actions = []
        if player_action["type"] == "attack":
            move = self.active_player.moves[player_action["move_index"]]
            actions.append(("player", self.active_player, self.active_enemy, move))
        if enemy_action["type"] == "attack":
            move = self.active_enemy.moves[enemy_action["move_index"]]
            actions.append(("enemy", self.active_enemy, self.active_player, move))

        # Tri par priorité puis vitesse
        actions.sort(key=lambda a: (
            -a[3].priority,
            -a[1].stats["speed"],
            -random.random()
        ))

        # Exécuter les attaques
        for side, attacker, defender, move in actions:
            if attacker.is_fainted():
                continue
            self._execute_attack(side, attacker, defender, move)
            
            # Vérifier KO
            if defender.is_fainted():
                side_name = "ennemi" if side == "player" else "votre"
                self.log(f"  → {defender.name} {side_name} est K.O. !")
                self._handle_faint(side)
                if self.is_over:
                    break

        # Effets de statut en fin de tour
        if not self.is_over:
            self._apply_status_damage(self.active_player, "player")
            self._apply_status_damage(self.active_enemy, "enemy")

        return self.battle_log

    def _execute_attack(self, side: str, attacker: Pokemon, defender: Pokemon,
                        move: Move):
        """Exécute une attaque."""
        owner = "Votre" if side == "player" else "L'ennemi"
        self.log(f"{owner} {attacker.name} utilise {move.name} !")

        # Vérifier PP
        if not move.use():
            self.log(f"  Plus de PP pour {move.name} !")
            return

        # Paralysie (25% chance de ne pas bouger)
        if attacker.status == "paralysis" and random.randint(1, 4) == 1:
            self.log(f"  {attacker.name} est paralysé et ne peut pas bouger !")
            return

        # Sleep
        if attacker.status == "sleep":
            if random.randint(1, 3) == 1:  # 33% chance de se réveiller
                attacker.clear_status()
                self.log(f"  {attacker.name} se réveille !")
            else:
                self.log(f"  {attacker.name} dort profondément...")
                return

        # Freeze
        if attacker.status == "freeze":
            if random.randint(1, 5) == 1:  # 20% chance de dégeler
                attacker.clear_status()
                self.log(f"  {attacker.name} dégèle !")
            else:
                self.log(f"  {attacker.name} est gelé et ne peut pas bouger !")
                return

        # Précision
        if not self.accuracy_check(move):
            self.log(f"  L'attaque a échoué !")
            return

        # Dégâts
        if move.is_damaging():
            damage, is_critical, type_mult = self.calculate_damage(attacker, defender, move)
            defender.take_damage(damage)

            self.log(f"  → {damage} dégâts à {defender.name} ! "
                     f"(HP: {defender.current_hp}/{defender.stats['hp']})")
            if is_critical:
                self.log(f"  ★ Coup critique !")
            eff_msg = TypeChart.get_effectiveness_message(type_mult)
            if eff_msg:
                self.log(f"  {eff_msg}")
        
        # Effets de statut des attaques
        if move.effect and not defender.is_fainted():
            if move.effect in ("poison", "burn", "paralysis", "sleep", "freeze"):
                if defender.status is None:
                    defender.set_status(move.effect)
                    status_names = {
                        "poison": "empoisonné",
                        "burn": "brûlé",
                        "paralysis": "paralysé",
                        "sleep": "endormi",
                        "freeze": "gelé"
                    }
                    self.log(f"  {defender.name} est {status_names[move.effect]} !")

    def _apply_status_damage(self, pokemon: Pokemon, side: str):
        """Applique les dégâts de statut en fin de tour."""
        if pokemon.is_fainted() or pokemon.status is None:
            return
        
        if pokemon.status == "poison":
            dmg = max(1, pokemon.stats["hp"] // 8)
            pokemon.take_damage(dmg)
            self.log(f"  💀 {pokemon.name} souffre du poison ! (-{dmg} HP)")
        elif pokemon.status == "burn":
            dmg = max(1, pokemon.stats["hp"] // 16)
            pokemon.take_damage(dmg)
            self.log(f"  🔥 {pokemon.name} souffre de sa brûlure ! (-{dmg} HP)")

        if pokemon.is_fainted():
            self.log(f"  → {pokemon.name} est K.O. à cause de son statut !")
            self._handle_faint(side)

    # ─────────── Switch ───────────

    def _do_switch(self, side: str, pokemon_index: int):
        """Switch le Pokémon actif."""
        if side == "player":
            team = self.team_player
            old = self.active_player
        else:
            team = self.team_enemy
            old = self.active_enemy

        if pokemon_index < 0 or pokemon_index >= len(team):
            return
        new_pokemon = team[pokemon_index]
        if new_pokemon.is_fainted():
            self.log(f"  {new_pokemon.name} est K.O. et ne peut pas combattre !")
            return

        if side == "player":
            self.active_player = new_pokemon
            self.log(f"  {old.name}, reviens ! Go, {new_pokemon.name} !")
        else:
            self.active_enemy = new_pokemon
            self.log(f"  L'ennemi rappelle {old.name} et envoie {new_pokemon.name} !")

    def switch_player_pokemon(self, pokemon_index: int) -> bool:
        """Switch côté joueur (utilisé pour switch forcé au KO)."""
        if pokemon_index < 0 or pokemon_index >= len(self.team_player):
            return False
        poke = self.team_player[pokemon_index]
        if poke.is_fainted():
            return False
        self.active_player = poke
        self.log(f"  Go, {poke.name} !")
        return True

    # ─────────── Gestion KO ───────────

    def _handle_faint(self, attacking_side: str):
        """Gère le KO : vérifie victoire ou force un switch."""
        if attacking_side == "player":
            # L'ennemi est KO
            alive_enemy = [p for p in self.team_enemy if not p.is_fainted()]
            if not alive_enemy:
                self.is_over = True
                self.winner = "player"
                self.log("🎉 Vous avez gagné le combat !")
            else:
                # L'IA switch automatiquement
                next_idx = self.team_enemy.index(alive_enemy[0])
                self.active_enemy = alive_enemy[0]
                self.log(f"  L'ennemi envoie {alive_enemy[0].name} !")
        else:
            # Le joueur est KO
            alive_player = [p for p in self.team_player if not p.is_fainted()]
            if not alive_player:
                self.is_over = True
                self.winner = "enemy"
                self.log("💀 Vous avez perdu le combat...")
            # Sinon, le joueur devra choisir manuellement (switch_player_pokemon)

    # ─────────── Utilitaires ───────────

    def get_available_switches(self, side: str = "player") -> list[tuple[int, Pokemon]]:
        """Retourne les Pokémons disponibles pour un switch."""
        team = self.team_player if side == "player" else self.team_enemy
        active = self.active_player if side == "player" else self.active_enemy
        return [
            (i, p) for i, p in enumerate(team)
            if not p.is_fainted() and p is not active
        ]

    def player_needs_switch(self) -> bool:
        """Vérifie si le joueur doit choisir un nouveau Pokémon."""
        return (self.active_player.is_fainted() and 
                not self.is_over and
                any(not p.is_fainted() for p in self.team_player))

    def get_enemy_action(self) -> dict:
        """IA basique : choisit l'attaque la plus puissante avec des PP."""
        available_moves = [
            (i, m) for i, m in enumerate(self.active_enemy.moves)
            if m.current_pp > 0
        ]
        if not available_moves:
            # Struggle (attaque désespérée)
            return {"type": "attack", "move_index": 0}

        # Choisit la meilleure attaque en tenant compte de l'efficacité
        best_idx = 0
        best_score = -1
        for i, move in available_moves:
            if move.is_damaging():
                eff = TypeChart.get_effectiveness(move.type, self.active_player.types)
                stab = 1.5 if move.type in self.active_enemy.types else 1.0
                score = move.power * eff * stab
            else:
                score = 10  # Les attaques de statut ont un score bas
            if score > best_score:
                best_score = score
                best_idx = i
        
        return {"type": "attack", "move_index": best_idx}

    def get_battle_state(self) -> dict:
        """Retourne l'état courant du combat pour l'UI."""
        return {
            "turn": self.turn_count,
            "player": {
                "active": self.active_player,
                "team": self.team_player,
                "alive_count": sum(1 for p in self.team_player if not p.is_fainted())
            },
            "enemy": {
                "active": self.active_enemy,
                "team": self.team_enemy,
                "alive_count": sum(1 for p in self.team_enemy if not p.is_fainted())
            },
            "is_over": self.is_over,
            "winner": self.winner
        }
