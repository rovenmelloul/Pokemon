"""
BattleSystem -- Systeme de combat tour par tour (formule Gen 5+).
"""
import random
from .pokemon_stats import PokemonStats
from .move import Move
from .type_chart import TypeChart


class BattleSystem:
    def __init__(self, team_player, team_enemy, is_wild=True):
        self.team_player = team_player
        self.team_enemy = team_enemy
        self.active_player = team_player[0]
        for p in team_player:
            if not p.is_fainted():
                self.active_player = p
                break
        self.active_enemy = team_enemy[0]
        self.is_wild = is_wild
        self.battle_log = []
        self.is_over = False
        self.winner = None
        self.turn_count = 0

    def log(self, message):
        self.battle_log.append(message)

    def calculate_damage(self, attacker, defender, move):
        if not move.is_damaging():
            return 0, False, 1.0
        level = attacker.level
        if move.category == "physical":
            atk_stat = attacker.stats["attack"]
            def_stat = defender.stats["defense"]
        else:
            atk_stat = attacker.stats["sp_attack"]
            def_stat = defender.stats["sp_defense"]
        base_damage = ((2 * level / 5 + 2) * move.power * atk_stat / def_stat) / 50 + 2
        is_critical = random.randint(1, 16) == 1
        critical_mult = 1.5 if is_critical else 1.0
        random_mult = random.randint(85, 100) / 100.0
        stab = 1.5 if move.type in attacker.types else 1.0
        type_mult = TypeChart.get_effectiveness(move.type, defender.types)
        burn_mult = 0.5 if (attacker.status == "burn" and move.category == "physical") else 1.0
        total = int(base_damage * critical_mult * random_mult * stab * type_mult * burn_mult)
        total = max(1, total) if type_mult > 0 else 0
        return total, is_critical, type_mult

    def accuracy_check(self, move):
        if move.accuracy >= 100:
            return True
        return random.randint(1, 100) <= move.accuracy

    def execute_turn(self, player_action, enemy_action):
        self.turn_count += 1
        self.battle_log = []
        self.log(f"\n====== Tour {self.turn_count} ======")

        if player_action["type"] == "switch":
            self._do_switch("player", player_action["pokemon_index"])
        if enemy_action["type"] == "switch":
            self._do_switch("enemy", enemy_action["pokemon_index"])

        if player_action["type"] == "run":
            if self.is_wild:
                self.log("Vous avez fui le combat !")
                self.is_over = True
                return self.battle_log
            else:
                self.log("Impossible de fuir un combat dresseur !")

        actions = []
        if player_action["type"] == "attack":
            move = self.active_player.moves[player_action["move_index"]]
            actions.append(("player", self.active_player, self.active_enemy, move))
        if enemy_action["type"] == "attack":
            move = self.active_enemy.moves[enemy_action["move_index"]]
            actions.append(("enemy", self.active_enemy, self.active_player, move))

        actions.sort(key=lambda a: (-a[3].priority, -a[1].stats["speed"], -random.random()))

        for side, attacker, defender, move in actions:
            if attacker.is_fainted():
                continue
            self._execute_attack(side, attacker, defender, move)
            if defender.is_fainted():
                opp = "ennemi" if side == "player" else "allie"
                self.log(f"  -> {defender.name} ({opp}) est K.O. !")
                self._handle_faint(side)
                if self.is_over:
                    break

        if not self.is_over:
            self._apply_status_damage(self.active_player, "player")
            self._apply_status_damage(self.active_enemy, "enemy")

        return self.battle_log

    def _execute_attack(self, side, attacker, defender, move):
        owner = "Votre" if side == "player" else "L'ennemi"
        self.log(f"{owner} {attacker.name} utilise {move.name} !")

        if not move.use():
            self.log(f"  Plus de PP pour {move.name} !")
            return

        if attacker.status == "paralysis" and random.randint(1, 4) == 1:
            self.log(f"  {attacker.name} est paralyse et ne peut pas bouger !")
            return
        if attacker.status == "sleep":
            if random.randint(1, 3) == 1:
                attacker.clear_status()
                self.log(f"  {attacker.name} se reveille !")
            else:
                self.log(f"  {attacker.name} dort profondement...")
                return
        if attacker.status == "freeze":
            if random.randint(1, 5) == 1:
                attacker.clear_status()
                self.log(f"  {attacker.name} degele !")
            else:
                self.log(f"  {attacker.name} est gele !")
                return

        if not self.accuracy_check(move):
            self.log(f"  L'attaque a echoue !")
            return

        if move.is_damaging():
            damage, is_critical, type_mult = self.calculate_damage(attacker, defender, move)
            defender.take_damage(damage)
            self.log(f"  -> {damage} degats a {defender.name} ! "
                     f"(PV: {defender.current_hp}/{defender.stats['hp']})")
            if is_critical:
                self.log(f"  * Coup critique !")
            eff_msg = TypeChart.get_effectiveness_message(type_mult)
            if eff_msg:
                self.log(f"  {eff_msg}")

        if move.effect and not defender.is_fainted():
            if move.effect in ("poison", "burn", "paralysis", "sleep", "freeze"):
                if defender.status is None:
                    defender.set_status(move.effect)
                    status_names = {
                        "poison": "empoisonne",
                        "burn": "brule",
                        "paralysis": "paralyse",
                        "sleep": "s'est endormi",
                        "freeze": "gele"
                    }
                    self.log(f"  {defender.name} est {status_names[move.effect]} !")

    def _apply_status_damage(self, pokemon, side):
        if pokemon.is_fainted() or pokemon.status is None:
            return
        if pokemon.status == "poison":
            dmg = max(1, pokemon.stats["hp"] // 8)
            pokemon.take_damage(dmg)
            self.log(f"  {pokemon.name} souffre du poison ! (-{dmg} PV)")
        elif pokemon.status == "burn":
            dmg = max(1, pokemon.stats["hp"] // 16)
            pokemon.take_damage(dmg)
            self.log(f"  {pokemon.name} souffre de la brulure ! (-{dmg} PV)")
        if pokemon.is_fainted():
            self.log(f"  -> {pokemon.name} est K.O. a cause du statut !")
            self._handle_faint(side)

    def _do_switch(self, side, pokemon_index):
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

    def switch_player_pokemon(self, pokemon_index):
        if pokemon_index < 0 or pokemon_index >= len(self.team_player):
            return False
        poke = self.team_player[pokemon_index]
        if poke.is_fainted():
            return False
        self.active_player = poke
        self.log(f"  Go, {poke.name} !")
        return True

    def _handle_faint(self, attacking_side):
        if attacking_side == "player":
            alive_enemy = [p for p in self.team_enemy if not p.is_fainted()]
            if not alive_enemy:
                self.is_over = True
                self.winner = "player"
                self.log("Vous avez gagne le combat !")
            else:
                self.active_enemy = alive_enemy[0]
                self.log(f"  L'ennemi envoie {alive_enemy[0].name} !")
        else:
            alive_player = [p for p in self.team_player if not p.is_fainted()]
            if not alive_player:
                self.is_over = True
                self.winner = "enemy"
                self.log("Vous avez perdu le combat...")

    def get_available_switches(self, side="player"):
        team = self.team_player if side == "player" else self.team_enemy
        active = self.active_player if side == "player" else self.active_enemy
        return [(i, p) for i, p in enumerate(team) if not p.is_fainted() and p is not active]

    def player_needs_switch(self):
        return (self.active_player.is_fainted() and
                not self.is_over and
                any(not p.is_fainted() for p in self.team_player))

    def get_enemy_action(self):
        available_moves = [(i, m) for i, m in enumerate(self.active_enemy.moves) if m.current_pp > 0]
        if not available_moves:
            return {"type": "attack", "move_index": 0}
        best_idx = 0
        best_score = -1
        for i, move in available_moves:
            if move.is_damaging():
                eff = TypeChart.get_effectiveness(move.type, self.active_player.types)
                stab = 1.5 if move.type in self.active_enemy.types else 1.0
                score = move.power * eff * stab
            else:
                score = 10
            if score > best_score:
                best_score = score
                best_idx = i
        return {"type": "attack", "move_index": best_idx}

    def get_battle_state(self):
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
