# practica2.py

import random
import pickle
import numpy as np
from itertools import combinations
from enum import Enum

from poker_env import Action, NUM_ACTIONS
from bucket_features import hand_to_features_enhanced  # Importamos la función mejorada
from bucket_features import real_equity_estimate       # Importamos la función de equity

class PokerGame:
    def __init__(self, initial_stack=1000, small_blind=10, big_blind=20):
        self.initial_stack = initial_stack
        self.small_blind = small_blind
        self.big_blind = big_blind

        # Stacks
        self.player_chips = initial_stack
        self.bot_chips = initial_stack

        # Pot y apuestas
        self.pot = 0
        self.current_bet = 0
        self.player_current_bet = 0
        self.bot_current_bet = 0

        # Contribuciones totales de fichas aportadas al pot por cada jugador
        self.player_contrib = 0
        self.bot_contrib = 0

        # Dealer alterna cada mano: 'player' o 'bot'
        self.dealer = "player"

        # Baraja y cartas
        self.deck = []
        self.player_hole = []
        self.bot_hole = []
        self.community_cards = []

        # Ronda actual: 0=preflop, 1=flop, 2=turn, 3=river, 4=showdown
        self.street_index = 0

        # Historial de acciones simplificado para info sets: 'f', 'c', 'r'
        self.history = ""

    # --- Construye y baraja ---
    def build_deck(self):
        suits = ["H", "D", "C", "S"]
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
        return [r + s for s in suits for r in ranks]

    def shuffle_deck(self):
        self.deck = self.build_deck()
        random.shuffle(self.deck)

    # --- Reparto de cartas ---
    def deal_cards(self):
        self.player_hole = [self.deck.pop(), self.deck.pop()]
        self.bot_hole = [self.deck.pop(), self.deck.pop()]
        self.community_cards = [self.deck.pop() for _ in range(5)]

    # --- Publicar blinds ---
    def post_blinds(self):
        if self.dealer == "player":
            sb = self.small_blind
            bb = self.big_blind
            if self.player_chips < sb or self.bot_chips < bb:
                print("No hay fichas para las blinds.")
                return False
            # El jugador hace SB, el bot hace BB
            self.player_chips -= sb
            self.bot_chips -= bb
            self.player_current_bet = sb
            self.bot_current_bet = bb
            self.current_bet = bb
            # Actualizamos contribuciones
            self.player_contrib = sb
            self.bot_contrib = bb
            print(f"Dealer: Jugador -> SB={sb}, Bot -> BB={bb}")
        else:
            sb = self.small_blind
            bb = self.big_blind
            if self.bot_chips < sb or self.player_chips < bb:
                print("No hay fichas para las blinds.")
                return False
            # El bot hace SB, el jugador hace BB
            self.bot_chips -= sb
            self.player_chips -= bb
            self.bot_current_bet = sb
            self.player_current_bet = bb
            self.current_bet = bb
            # Actualizamos contribuciones
            self.bot_contrib = sb
            self.player_contrib = bb
            print(f"Dealer: Bot -> SB={sb}, Jugador -> BB={bb}")

        self.pot = self.player_current_bet + self.bot_current_bet
        self.print_chip_counts()
        return True

    # --- Inicia mano nueva ---
    def start_hand(self):
        # Reseteamos contribuciones y apuestas
        self.player_contrib = 0
        self.bot_contrib = 0
        self.street_index = 0
        self.pot = 0
        self.current_bet = 0
        self.player_current_bet = 0
        self.bot_current_bet = 0
        self.history = ""

        # Alternamos dealer
        self.dealer = "bot" if self.dealer == "player" else "player"

        # Reparto
        self.shuffle_deck()
        self.deal_cards()

        if not self.post_blinds():
            return False

        print("\n=== Nueva mano ===")
        print(f"Dealer: {self.dealer.upper()}")
        print("Tus cartas:", self.player_hole)
        return True

    # --- Aplicar acción de jugador o bot ---
    def apply_action(self, actor, action: Action, raise_amount=None):
        # Si se retira
        if action == Action.FOLD:
            print(f"{actor.capitalize()} se retira (FOLD).")
            # El oponente se queda con todo el pot; no hay side pot en fold.
            if actor == "player":
                self.bot_chips += self.pot
                print("Bot gana la mano.")
            else:
                self.player_chips += self.pot
                print("Jugador gana la mano.")
            self.pot = 0
            return True  # Indica que la mano terminó por fold

        # Determinamos cuánto hay que pagar para llamar
        if actor == "player":
            to_call = self.current_bet - self.player_current_bet
            stack = self.player_chips
        else:
            to_call = self.current_bet - self.bot_current_bet
            stack = self.bot_chips

        # CALL / CHECK
        if action == Action.CALL:
            pay = min(to_call, stack)
            if actor == "player":
                self.player_chips -= pay
                self.player_current_bet += pay
                self.player_contrib += pay  # Actualizamos contribución
            else:
                self.bot_chips -= pay
                self.bot_current_bet += pay
                self.bot_contrib += pay  # Actualizamos contribución
            self.pot += pay
            if pay == 0:
                print(f"{actor.capitalize()} hace CHECK.")
            else:
                print(f"{actor.capitalize()} hace CALL de {pay} fichas.")
            self.history += 'c'

        # RAISE (pequeño, medio o grande)
        elif action in [Action.RAISE_SMALL, Action.RAISE_MEDIUM, Action.RAISE_LARGE]:
            # Si no se pasa raise_amount explícito, lo calculamos por convención
            if raise_amount is None:
                if action == Action.RAISE_SMALL:
                    raise_amount = max(int(self.pot * 0.5), 1)
                elif action == Action.RAISE_MEDIUM:
                    raise_amount = max(int(self.pot * 1.0), 1)
                else:
                    # ALL-IN implícito: apostar todo su stack
                    raise_amount = stack

            total_put = to_call + raise_amount
            total_put = min(total_put, stack)

            if actor == "player":
                self.player_chips -= total_put
                self.player_current_bet += total_put
                self.player_contrib += total_put  # Actualizamos contribución
            else:
                self.bot_chips -= total_put
                self.bot_current_bet += total_put
                self.bot_contrib += total_put  # Actualizamos contribución

            self.pot += total_put
            self.current_bet = max(
                self.current_bet,
                self.player_current_bet if actor == "player" else self.bot_current_bet
            )
            print(f"{actor.capitalize()} hace RAISE de {total_put} fichas (incluyendo call).")
            self.history += 'r'

        else:
            print("Acción no reconocida.")
            return False

        return False  # Indica que la mano continúa

    # --- Mostrar stacks ---
    def print_chip_counts(self):
        print(f"Fichas -> Tú: {self.player_chips} | Bot: {self.bot_chips} | Pot: {self.pot}")

    # --- Avanzar calle ---
    def next_street(self):
        self.street_index += 1
        self.current_bet = 0
        self.player_current_bet = 0
        self.bot_current_bet = 0
        self.history = ""

        if self.street_index == 1:
            print("\nFlop:", self.community_cards[:3])
        elif self.street_index == 2:
            print("\nTurn:", self.community_cards[3])
        elif self.street_index == 3:
            print("\nRiver:", self.community_cards[4])
        elif self.street_index == 4:
            print("\nShowdown!")

        self.print_chip_counts()

    # --- Evaluación simple de manos ---
    def get_rank(self, card):
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
                       '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11,
                       'Q': 12, 'K': 13, 'A': 14}
        return rank_values[card[0]]

    def get_suit(self, card):
        return card[-1]

    def evaluate_five_card_hand(self, cards):
        ranks = sorted([self.get_rank(c) for c in cards], reverse=True)
        suits = [self.get_suit(c) for c in cards]
        rank_counts = {}
        for r in ranks:
            rank_counts[r] = rank_counts.get(r, 0) + 1
        counts = sorted(
            [(r, cnt) for r, cnt in rank_counts.items()],
            key=lambda x: (x[1], x[0]), reverse=True
        )
        is_flush = all(s == suits[0] for s in suits)
        unique_ranks = sorted(set(ranks), reverse=True)
        is_straight = False
        straight_high = None
        if len(unique_ranks) >= 5:
            for i in range(len(unique_ranks) - 4):
                if unique_ranks[i] - unique_ranks[i + 4] == 4:
                    is_straight = True
                    straight_high = unique_ranks[i]
                    break
            if not is_straight and {14, 5, 4, 3, 2}.issubset(unique_ranks):
                is_straight = True
                straight_high = 5
        if is_flush and is_straight:
            return {"handRank": 9, "tiebreakers": [straight_high]}
        if counts[0][1] == 4:
            fourRank = counts[0][0]
            kicker = max(r for r in ranks if r != fourRank)
            return {"handRank": 8, "tiebreakers": [fourRank, kicker]}
        if counts[0][1] == 3 and len(counts) > 1 and counts[1][1] >= 2:
            return {"handRank": 7, "tiebreakers": [counts[0][0], counts[1][0]]}
        if is_flush:
            flush_ranks = sorted(
                [self.get_rank(c) for c in cards if self.get_suit(c) == suits[0]],
                reverse=True
            )
            return {"handRank": 6, "tiebreakers": flush_ranks[:5]}
        if is_straight:
            return {"handRank": 5, "tiebreakers": [straight_high]}
        if counts[0][1] == 3:
            triple = counts[0][0]
            kickers = sorted([r for r in ranks if r != triple], reverse=True)[:2]
            return {"handRank": 4, "tiebreakers": [triple] + kickers}
        if counts[0][1] == 2 and len(counts) > 1 and counts[1][1] == 2:
            highPair = max(counts[0][0], counts[1][0])
            lowPair = min(counts[0][0], counts[1][0])
            kicker = max(r for r in ranks if r != highPair and r != lowPair)
            return {"handRank": 3, "tiebreakers": [highPair, lowPair, kicker]}
        if counts[0][1] == 2:
            pair = counts[0][0]
            kickers = sorted([r for r in ranks if r != pair], reverse=True)[:3]
            return {"handRank": 2, "tiebreakers": [pair] + kickers}
        return {"handRank": 1, "tiebreakers": ranks[:5]}

    def evaluate_hand7(self, cards):
        best_eval = None
        for combo in combinations(cards, 5):
            eval_combo = self.evaluate_five_card_hand(list(combo))
            if best_eval is None or self.compare_hands(eval_combo, best_eval) > 0:
                best_eval = eval_combo
        return best_eval

    def compare_hands(self, handA, handB):
        if handA["handRank"] > handB["handRank"]:
            return 1
        if handA["handRank"] < handB["handRank"]:
            return -1
        for a, b in zip(handA["tiebreakers"], handB["tiebreakers"]):
            if a > b:
                return 1
            if a < b:
                return -1
        return 0

    def describe_hand(self, best_eval):
        ts = best_eval["tiebreakers"]
        hr = best_eval["handRank"]
        if hr == 9:
            return f"Escalera de color a la {ts[0]}"
        elif hr == 8:
            return f"Poker de {ts[0]} con kicker {ts[1]}"
        elif hr == 7:
            return f"Full House: triple de {ts[0]} y pareja de {ts[1]}"
        elif hr == 6:
            return f"Color con {', '.join(map(str, ts))}"
        elif hr == 5:
            return f"Escalera a la {ts[0]}"
        elif hr == 4:
            return f"Trío de {ts[0]} con kickers {ts[1]}, {ts[2]}"
        elif hr == 3:
            return f"Dobles parejas de {ts[0]} y {ts[1]} con kicker {ts[2]}"
        elif hr == 2:
            return f"Pareja de {ts[0]} con kickers {', '.join(map(str, ts[1:]))}"
        elif hr == 1:
            return f"Carta alta {ts[0]} con kickers {', '.join(map(str, ts[1:]))}"
        return ""

    def showdown(self):
        print("\n--- Showdown ---")
        print("Tus cartas:", self.player_hole, "+ Comunidad:", self.community_cards)
        print("Cartas del bot:", self.bot_hole, "+ Comunidad:", self.community_cards)

        # 1) Evaluar mejor mano de 7 cartas para cada jugador
        player_best = self.evaluate_hand7(self.player_hole + self.community_cards)
        bot_best = self.evaluate_hand7(self.bot_hole + self.community_cards)

        print("Tu mejor jugada:", self.describe_hand(player_best))
        print("Mejor jugada del bot:", self.describe_hand(bot_best))

        # 2) Contribuciones ya acumuladas a lo largo de la mano
        contrib_player = self.player_contrib
        contrib_bot = self.bot_contrib

        # 3) Determinar main pot y side pot correctamente
        main_contrib = min(contrib_player, contrib_bot)
        main_pot = main_contrib * 2
        side_pot = (contrib_player + contrib_bot) - main_pot

        print(f"\n-- Pot total: {self.pot} fichas (Main Pot={main_pot}, Side Pot={side_pot})")

        # 4) Comparar manos y repartir
        cmp = self.compare_hands(player_best, bot_best)
        if cmp > 0:
            # El jugador gana el main pot; el side pot (si existe) va al que aportó más
            print(f"¡Ganas la mano y te llevas el MAIN POT de {main_pot} fichas!")
            self.player_chips += main_pot
            if side_pot > 0:
                # Quien aportó más al side pot lo gana
                if contrib_player > contrib_bot:
                    print(f"El SIDE POT ({side_pot} fichas) lo ganas tú porque aportaste más.")
                    self.player_chips += side_pot
                else:
                    print(f"El SIDE POT ({side_pot} fichas) retorna al bot.")
                    self.bot_chips += side_pot
        elif cmp < 0:
            # El bot gana main + side (o solo main si no hubo side)
            total_win = main_pot + side_pot
            print(f"El bot gana la mano y se lleva MAIN+SIDE POT: {total_win} fichas.")
            self.bot_chips += total_win
        else:
            # Empate: dividir el main pot; el side pot va al que aportó más
            half_main = main_pot // 2
            print(f"Empate. Se reparte MAIN POT: cada uno recibe {half_main} fichas.")
            self.player_chips += half_main
            self.bot_chips += half_main
            if side_pot > 0:
                print(f"El SIDE POT ({side_pot} fichas) va al que aportó más.")
                if contrib_bot > contrib_player:
                    self.bot_chips += side_pot
                else:
                    self.player_chips += side_pot

        # 5) Limpiar pot y mostrar stacks finales
        self.pot = 0
        self.print_chip_counts()

    # --- Revelar cartas restantes en all-in ---
    def reveal_remaining_community_cards(self):
        while self.street_index < 3:
            self.street_index += 1
            if self.street_index == 1:
                print("\nFlop:", self.community_cards[:3])
            elif self.street_index == 2:
                print("\nTurn:", self.community_cards[3])
            elif self.street_index == 3:
                print("\nRiver:", self.community_cards[4])
        self.print_chip_counts()

    # --- Decide acción bot basado en modelo entrenado (con cap de tamaño según equity) ---
    def bot_decide_action(self, trainer):
        # Map para convertir "As" → (14,1), etc.
        rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
                    '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11,
                    'Q': 12, 'K': 13, 'A': 14}
        suit_map = {'s': 0, 'h': 1, 'd': 2, 'c': 3,
                    'S': 0, 'H': 1, 'D': 2, 'C': 3}

        def convert_cards(cards_str_list):
            return [(rank_map[c[0]], suit_map[c[1]]) for c in cards_str_list]

        phase_map = {0: 'preflop', 1: 'flop', 2: 'turn', 3: 'river'}
        phase = phase_map.get(self.street_index, 'river')

        history_for_bucket = self.history.split('|')[-1] if '|' in self.history else self.history
        km = trainer.kmeans_models.get(phase)
        nodes = trainer.nodes.get(phase, {})

        if km is None or nodes is None:
            # Si no hay modelo entrenado, elige acción aleatoria
            action = random.choice(list(Action))
            raise_amount = None
            return action, raise_amount

        # Convertir las cartas del bot y la comunidad a tupla (rank, suit)
        hole_cards_numeric = convert_cards(self.bot_hole)
        if self.street_index == 0:
            community_numeric = []
        elif self.street_index == 1:
            community_numeric = convert_cards(self.community_cards[:3])
        elif self.street_index == 2:
            community_numeric = convert_cards(self.community_cards[:4])
        else:
            community_numeric = convert_cards(self.community_cards[:5])

        # Calcular features para bucketizar
        feats = hand_to_features_enhanced(
            hole_cards_numeric,
            community_numeric,
            pot=self.pot,
            history=history_for_bucket,
            to_act=1
        )
        bucket = km.predict(feats.reshape(1, -1))[0]

        info_set = f"{phase}|{bucket}|{history_for_bucket}"
        if info_set in nodes:
            strat = nodes[info_set].get_average_strategy()
        else:
            strat = np.ones(NUM_ACTIONS) / NUM_ACTIONS

        action_idx = np.random.choice(range(NUM_ACTIONS), p=strat)
        action = Action(action_idx)

        # Determinar raise_amount según convención
        if action == Action.RAISE_SMALL:
            raise_amount = max(int(self.pot * 0.5), 1)
        elif action == Action.RAISE_MEDIUM:
            raise_amount = max(int(self.pot * 1.0), 1)
        elif action == Action.RAISE_LARGE:
            # ALL-IN puro: apostará todo lo que le queda
            raise_amount = self.bot_chips
        else:
            raise_amount = None

        # ======== BLOQUE NUEVO: CAPEAR raise_large SEGÚN equity del bot ========
        if action == Action.RAISE_LARGE and raise_amount is not None:
            # 1) Calcular equity real de la mano del bot vs. rival aleatorio
            eq_bot = real_equity_estimate(
                hole_cards_numeric,
                community_numeric,
                num_sim=500  # ajustable (más sims → mayor precisión, pero tarde)
            )

            # 2) Obtener tamaño del bote antes de apostar
            pot_before = self.pot

            # 3) Definir umbrales de equity para cap:
            #    - eq_bot < 0.40 → no all-in (CALL)
            #    - 0.40 ≤ eq_bot < 0.50 → RAISE_MEDIUM
            #    - 0.50 ≤ eq_bot < 0.60 → RAISE_MEDIUM (intermedio)
            #    - eq_bot ≥ 0.60 → ALL-IN completo
            if eq_bot < 0.40:
                # Demasiado baja equity: hacemos CALL en vez de all-in
                action = Action.CALL
                raise_amount = None

            elif eq_bot < 0.50:
                # Equity moderada: capeo a raise mediano (≈1× bote)
                action = Action.RAISE_MEDIUM
                raise_amount = max(int(pot_before * 1.0), 1)

            elif eq_bot < 0.70:
                # Equity decente pero no alta: capeo también a raise mediano
                action = Action.RAISE_MEDIUM
                raise_amount = max(int(pot_before * 1.0), 1)

            else:
                # Equity alta (≥0.60): permitimos full all-in
                action = Action.RAISE_LARGE
                raise_amount = self.bot_chips
        # ======== FIN DEL BLOQUE DE CAPEO ========

        return action, raise_amount

    # --- Obtener quién inicia la ronda de apuestas ---
    def get_first_actor(self):
        # Big Blind actúa primero (el que no es dealer)
        return "bot" if self.dealer == "player" else "player"

    # --- Ronda de apuestas con lógica all-in + check integrada ---
    def betting_round(self, starter, trainer):
        has_acted = {"player": False, "bot": False}
        current_turn = starter
        print(f"\n--- Nueva ronda de apuestas (inicia: {current_turn.upper()}) ---")

        while True:
            # 1) Si ambos han actuado e igualaron apuestas → acaba esta ronda
            if has_acted["player"] and has_acted["bot"] and \
               self.player_current_bet == self.bot_current_bet:
                print("Ronda de apuestas completada.")
                self.print_chip_counts()
                return "continue"

            # 2) Condición ALL-IN
            player_allin = (self.player_chips == 0)
            bot_allin = (self.bot_chips == 0)
            bets_equal = (self.player_current_bet == self.bot_current_bet)

            # Caso A: ambos ALL-IN o uno ALL-IN y apuestas igualadas → showdown
            if (player_allin and bot_allin) or ((player_allin or bot_allin) and bets_equal):
                print("Ambos jugadores están ALL IN o apuestas igualadas con all-in. Se revela todo y showdown.")
                return "all_in"

            # Caso B: uno está ALL-IN y las apuestas NO están igualadas → el otro debe CALL o FOLD
            if (player_allin or bot_allin) and not bets_equal:
                if current_turn == "player":
                    print("Estás contra un ALL IN y debes decidir call o fold.")
                    action_str = input("Tu acción (call, fold): ").strip().lower()
                    if action_str == "fold":
                        ended = self.apply_action("player", Action.FOLD)
                        if ended:
                            return "fold"
                    elif action_str == "call":
                        ended = self.apply_action("player", Action.CALL)
                        if ended:
                            return "fold"
                    else:
                        print("Acción no válida.")
                        continue
                    return "all_in"
                else:
                    # Turno del bot contra all-in
                    to_call = self.current_bet - self.bot_current_bet
                    if to_call > 0:
                        paid = min(to_call, self.bot_chips)
                        self.bot_chips -= paid
                        self.bot_current_bet += paid
                        self.bot_contrib += paid
                        self.pot += paid
                        if paid == 0:
                            print("Bot quiere igualar pero está ALL IN con 0 fichas.")
                        else:
                            print(f"Bot hace CALL de {paid} fichas para igualar el all-in.")
                    else:
                        print("Bot hace CHECK contra un all-in.")
                    return "all_in"

            # 3) Turno normal (no ALL-IN)
            if current_turn == "player":
                action_str = input("Tu acción (fold, call, raise): ").strip().lower()
                if action_str == "fold":
                    ended = self.apply_action("player", Action.FOLD)
                    if ended:
                        return "fold"
                elif action_str == "call":
                    ended = self.apply_action("player", Action.CALL)
                    if ended:
                        return "fold"
                elif action_str == "raise":
                    try:
                        raise_amount = int(input("Monto de raise (>0): "))
                    except:
                        print("Monto inválido, intenta de nuevo.")
                        continue
                    if raise_amount <= 0:
                        print("Monto debe ser mayor que 0.")
                        continue
                    ended = self.apply_action("player", Action.RAISE_MEDIUM, raise_amount=raise_amount)
                    if ended:
                        return "fold"
                else:
                    print("Acción no reconocida.")
                    continue

                has_acted["player"] = True
                current_turn = "bot"

            else:
                # Turno del BOT
                action, raise_amount = self.bot_decide_action(trainer)

                # Calculamos cuánto necesita para call
                to_call_bot = self.current_bet - self.bot_current_bet

                # Si el bot decide FOLD pero no hay nada que pagar (to_call_bot == 0), interpretamos como CHECK
                if action == Action.FOLD and to_call_bot == 0:
                    print("Bot decide FOLD pero es CHECK (no hay nada que pagar).")
                    print("Bot hace CHECK.")
                    has_acted["bot"] = True
                    current_turn = "player"
                    print(f"Apuestas -> Tú: {self.player_current_bet} | Bot: {self.bot_current_bet} | Pot: {self.pot}")
                    continue

                print(f"Bot decide {action.name} con raise_amount={raise_amount}")
                ended = self.apply_action("bot", action, raise_amount=raise_amount)
                if ended:
                    return "fold"
                has_acted["bot"] = True
                current_turn = "player"

            print(f"Apuestas -> Tú: {self.player_current_bet} | Bot: {self.bot_current_bet} | Pot: {self.pot}")

    # --- Juego completo con integración all-in + check ---
    def play_hand(self, trainer):
        if not self.start_hand():
            return False

        for _ in range(4):  # máximo 4 calles: preflop, flop, turn, river
            starter = self.get_first_actor()
            result = self.betting_round(starter, trainer)

            if result == "fold":
                return True
            if result == "all_in":
                # Revela las cartas restantes antes del showdown
                self.reveal_remaining_community_cards()
                self.showdown()
                return True

            self.next_street()

        # Después de la última calle (river) → showdown normal
        self.showdown()
        return True


def main():
    # Cargar trainer entrenado (CFR)
    with open("cfr_entreno.pkl", "rb") as f:
        trainer = pickle.load(f)

    game = PokerGame()
    while game.player_chips > 0 and game.bot_chips > 0:
        done = game.play_hand(trainer)
        if done:
            cont = input("\n¿Jugar otra mano? (s/n): ").strip().lower()
            if cont != "s":
                break

    print("\nFin de la partida.")
    print(f"Stacks finales -> Tú: {game.player_chips}, Bot: {game.bot_chips}")


if __name__ == "__main__":
    main()
