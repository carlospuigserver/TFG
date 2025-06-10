# practica.py
# raise entero controlado por equity y porcentaje del stack
import random
import pickle
import numpy as np
from itertools import combinations
from enum import Enum

from poker_env import Action, NUM_ACTIONS
from bucket_features import hand_to_features_enhanced  # Importamos la función mejorada
from bucket_features import real_equity_estimate       # Importamos la función de equity

class PokerGame:
    def __init__(self, player_chips=None, bot_chips=None, initial_stack=1000, small_blind=10, big_blind=20):
        self.initial_stack = initial_stack
        self.small_blind = small_blind
        self.big_blind = big_blind

        # Stacks
        # Si no se pasan stacks, usar el valor inicial por defecto
        self.player_chips = player_chips if player_chips is not None else initial_stack
        self.bot_chips    = bot_chips    if bot_chips    is not None else initial_stack

        # Pot y apuestas
        self.pot = 0
        self.current_bet = 0
        self.player_current_bet = 0
        self.bot_current_bet = 0

        # Contribuciones totales de fichas aportadas al pot por cada jugador
        self.player_contrib = 0
        self.bot_contrib = 0


        self.wins_player = 0
        self.wins_bot = 0


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
        # Dealer define quién pone SB/BB
        if self.dealer == "player":
            sb_player = self.small_blind
            bb_bot = self.big_blind

            if self.player_chips < sb_player or self.bot_chips < bb_bot:
                print("⚠️ Uno de los jugadores no puede cubrir las ciegas. All-in forzado.")

                # Ambos van all-in con lo que tengan (mínimo entre stacks)
                contrib = min(self.player_chips, self.bot_chips)

                self.player_contrib = self.player_chips
                self.bot_contrib = self.bot_chips
                self.player_current_bet = self.player_chips
                self.bot_current_bet = self.bot_chips

                self.pot = self.player_chips + self.bot_chips
                self.player_chips = 0
                self.bot_chips = 0

                return 'allin'

            # Asignación normal de blinds
            self.player_chips -= sb_player
            self.bot_chips -= bb_bot
            self.player_current_bet = sb_player
            self.bot_current_bet = bb_bot
            self.current_bet = bb_bot
            self.player_contrib = sb_player
            self.bot_contrib = bb_bot
            print(f"Dealer: Jugador -> SB={sb_player}, Bot -> BB={bb_bot}")

        else:
            sb_bot = self.small_blind
            bb_player = self.big_blind

            if self.bot_chips < sb_bot or self.player_chips < bb_player:
                print("⚠️ Uno de los jugadores no puede cubrir las ciegas. All-in forzado.")

                # Ambos van all-in con lo que tengan (mínimo entre stacks)
                contrib = min(self.player_chips, self.bot_chips)

                self.player_contrib = self.player_chips
                self.bot_contrib = self.bot_chips
                self.player_current_bet = self.player_chips
                self.bot_current_bet = self.bot_chips

                self.pot = self.player_chips + self.bot_chips
                self.player_chips = 0
                self.bot_chips = 0

                return 'allin'

            # Asignación normal de blinds
            self.bot_chips -= sb_bot
            self.player_chips -= bb_player
            self.bot_current_bet = sb_bot
            self.player_current_bet = bb_player
            self.current_bet = bb_player
            self.bot_contrib = sb_bot
            self.player_contrib = bb_player
            print(f"Dealer: Bot -> SB={sb_bot}, Jugador -> BB={bb_player}")

        self.pot = self.player_current_bet + self.bot_current_bet
        self.print_chip_counts()
        return True

            
    def force_allin_preflop(self):
        print("\n⚠️  All-in forzado en preflop por falta de fichas.")

        # Resetear apuestas previas
        self.current_bet = 0
        self.player_current_bet = 0
        self.bot_current_bet = 0

        # Ambos meten todo su stack
        contrib_player = self.player_chips
        contrib_bot = self.bot_chips

        self.player_contrib = contrib_player
        self.bot_contrib = contrib_bot

        self.player_current_bet = contrib_player
        self.bot_current_bet = contrib_bot

        self.player_chips = 0
        self.bot_chips = 0

        # ✅ Calcular el pot real (suma de contribuciones)
        self.pot = contrib_player + contrib_bot

        print(f"Tú vas all-in con {contrib_player} fichas.")
        print(f"Bot va all-in con {contrib_bot} fichas.")
        print(f"Pot total: {self.pot}")

        self.reveal_remaining_community_cards()
        self.showdown()



    # --- Inicia mano nueva ---
    def start_hand(self):
        # Reset del estado de la mano
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

        # Barajar y repartir
        self.shuffle_deck()
        self.deal_cards()

        # 👇⚠️ Check ciegas antes de arrancar
        result = self.post_blinds()
        self.player_contrib = self.player_current_bet  # ← Añadir esto
        self.bot_contrib = self.bot_current_bet 
        if result == 'allin':
            self.reveal_remaining_community_cards()
            self.showdown()
            return 'allin'

        
        # 🔍 Sanity check de integridad
        total_in_game = self.player_chips + self.bot_chips + self.pot
        if total_in_game != 2000:
            print(f"❗ ERROR: Total de fichas desajustado: {total_in_game}")
        else:
            print(f"✅ Total de fichas correcto: {total_in_game}")



        # ✅ NUEVA LÓGICA: si tras las ciegas uno queda sin fichas, showdown inmediato
        if self.player_chips == 0 or self.bot_chips == 0:
            print("Uno de los jugadores quedó sin fichas tras las ciegas. Se fuerza showdown.")
            self.reveal_remaining_community_cards()
            self.showdown()
            return 'allin'

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
            # Permitir raise si:
            # - Las apuestas no están igualadas (hay que igualar y subir)
            # - O las apuestas están igualadas pero no hubo raise previo en esta ronda (history no contiene 'r')
            if self.player_current_bet == self.bot_current_bet and 'r' in self.history:
                print(f"{actor.capitalize()} intenta hacer reraise pero las apuestas ya están igualadas y hubo raise previo en esta ronda. Acción inválida.")
                return False

            # Si no se pasa raise_amount explícito, lo calculamos por convención
            if raise_amount is None:
                if action == Action.RAISE_SMALL:
                    raise_amount = max(int(self.pot * 0.5), 1)
                elif action == Action.RAISE_MEDIUM:
                    raise_amount = max(int(self.pot * 1.0), 1)
                else:
                    # ALL-IN implícito: apostar todo su stack
                    raise_amount = stack

            # 🔒 Protección contra raises negativos o inválidos
            if raise_amount is None or raise_amount <= 0:
                print(f"⚠️ Raise inválido o nulo ({raise_amount}). Acción convertida a CALL.")
                action = Action.CALL
                raise_amount = None

            max_raise = stack - to_call
            if max_raise < 0:
                max_raise = 0

            raise_amount = min(raise_amount, max_raise)

            # 🔒 PARCHE NUEVO: limitar raise por stack del oponente también
            opponent_stack = self.bot_chips if actor == "player" else self.player_chips
            raise_amount = min(raise_amount, opponent_stack)

            total_put = to_call + raise_amount

            
            if stack < to_call:
                print(f"⚠️ {actor.capitalize()} no puede cubrir el CALL completo ({to_call}). Hace ALL-IN con {stack} fichas.")

                if actor == "player":
                    self.player_chips = 0
                    self.player_current_bet += stack
                    self.player_contrib += stack
                else:
                    self.bot_chips = 0
                    self.bot_current_bet += stack
                    self.bot_contrib += stack

                self.pot += stack
                self.history += 'c'
                return False




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
        
                # ✅ Si alguno se quedó sin fichas y las apuestas quedaron igualadas, forzar showdown
        #if (self.player_chips == 0 or self.bot_chips == 0) and \
         #  (self.player_current_bet == self.bot_current_bet):
          #  print("✅ Ambos all-in o igualaron con all-in. Se revela todo.")
           # return True  # Marca fin de la mano para que se active el showdown en app.py

        # ✅ Solo terminar si hay all-in Y apuestas igualadas
        if (self.player_chips == 0 or self.bot_chips == 0) and \
        (self.player_current_bet == self.bot_current_bet):
            print("✅ Ambos all-in o apuestas igualadas con all-in. Se revela todo.")
            return True



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

        # 1) Evaluar mejor mano de 7 cartas
        player_best = self.evaluate_hand7(self.player_hole + self.community_cards)
        bot_best = self.evaluate_hand7(self.bot_hole + self.community_cards)

        # 2) Mostrar jugadas
        print("Tu mejor jugada:", self.describe_hand(player_best))
        print("Mejor jugada del bot:", self.describe_hand(bot_best))

        # 3) Determinar pot real y distribuirlo sin inflar
        total_pot = self.pot
        main_contrib = min(self.player_contrib, self.bot_contrib)
        main_pot = main_contrib * 2

        # 🧠 Detectar si es un all-in forzado por ciegas (ambos metieron todo desde el inicio)
        allin_forzado = (
            self.player_chips == 0 or self.bot_chips == 0
        ) and (
            self.player_contrib + self.bot_contrib == self.initial_stack * 2
        ) and (
            self.player_contrib == self.player_current_bet and self.bot_contrib == self.bot_current_bet
        )

        side_pot = 0 if allin_forzado else total_pot - main_pot

        print(f"\n-- Reparto del pot: Main Pot={main_pot}, Side Pot={side_pot} (Pot total: {total_pot} fichas)")

        # 4) Comparar manos y repartir
        cmp = self.compare_hands(player_best, bot_best)

        if allin_forzado:
            if cmp > 0:
                print(f"¡Ganas la mano y te llevas el MAIN POT de {main_pot} fichas!")
                self.player_chips += main_pot
                print(f"El SIDE POT ({side_pot} fichas) lo gana el bot porque aportó más.")
                self.bot_chips += side_pot
            elif cmp < 0:
                print(f"El bot gana la mano y se lleva el MAIN POT de {main_pot} fichas.")
                self.bot_chips += main_pot
                print(f"El SIDE POT ({side_pot} fichas) lo gana el bot porque aportó más.")
                self.bot_chips += side_pot
            else:
                mitad = main_pot // 2
                print(f"Empate. Se reparte MAIN POT: cada uno recibe {mitad} fichas.")
                self.player_chips += mitad
                self.bot_chips += main_pot - mitad
                print(f"El SIDE POT ({side_pot} fichas) retorna al bot.")
                self.bot_chips += side_pot
        else:
            if cmp > 0:
                print(f"¡Ganas la mano y te llevas el MAIN POT de {main_pot} fichas!")
                self.player_chips += main_pot
                if side_pot > 0:
                    print(f"El SIDE POT ({side_pot} fichas) retorna al bot.")
                    self.bot_chips += side_pot
            elif cmp < 0:
                print(f"El bot gana la mano y se lleva el MAIN POT de {main_pot} fichas.")
                self.bot_chips += main_pot
                if side_pot > 0:
                    print(f"El SIDE POT ({side_pot} fichas) retorna a ti.")
                    self.player_chips += side_pot
            else:
                mitad = main_pot // 2
                print(f"Empate. Se reparte MAIN POT: cada uno recibe {mitad} fichas.")
                self.player_chips += mitad
                self.bot_chips += main_pot - mitad
                if side_pot > 0:
                    print(f"El SIDE POT ({side_pot} fichas) retorna al bot.")
                    self.bot_chips += side_pot




        # 5) Limpieza
        self.pot = 0
        self.print_chip_counts()
        return 

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
        rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
                    '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11,
                    'Q': 12, 'K': 13, 'A': 14}
        suit_map = {'s': 0, 'h': 1, 'd': 2, 'c': 3,
                    'S': 0, 'H': 1, 'D': 2, 'C': 3}

        def convert_cards(cards_str_list):
            return [(rank_map[c[0]], suit_map[c[1]]) for c in cards_str_list]

        phase_map = {0: 'preflop', 1: 'flop', 2: 'turn', 3: 'river'}
        phase = phase_map.get(self.street_index, 'river')

        # Obtener historial para bucket
        history_for_bucket = self.history.split('|')[-1] if '|' in self.history else self.history
        km = trainer.kmeans_models.get(phase)
        nodes = trainer.nodes.get(phase, {})

        # Convertir cartas a formato numérico
        hole_cards_numeric = convert_cards(self.bot_hole)
        if self.street_index == 0:
            community_numeric = []
        elif self.street_index == 1:
            community_numeric = convert_cards(self.community_cards[:3])
        elif self.street_index == 2:
            community_numeric = convert_cards(self.community_cards[:4])
        else:
            community_numeric = convert_cards(self.community_cards[:5])

        # Calcular cuánto debe pagar para hacer call
        to_call = self.current_bet - self.bot_current_bet
        pot_before = self.pot

        # =========================
        #  A) Si debe pagar (to_call > 0):
        # =========================
        if to_call > 0:
            # 1) Si la mesa está emparejada, forzamos equity = 0.50
            ranks_board = [r for (r, s) in community_numeric]
            if len(ranks_board) != len(set(ranks_board)):
                eq_bot = 0.50
            else:
                eq_bot = real_equity_estimate(
                    hole_cards_numeric,
                    community_numeric,
                    num_sim=500
                )

            # 2) Calcular pot odds
            if pot_before + to_call > 0:
                pot_odds = to_call / (pot_before + to_call)
            else:
                pot_odds = 1.0

            
            # 💥 PARCHE: permitir all-in parcial si no puede pagar completo
            if self.bot_chips > 0 and self.bot_chips < to_call:
                return Action.CALL, None  # all-in parcial permitido
            # 3) Si equity ≤ pot_odds → fold
            if eq_bot <= pot_odds:
                return Action.FOLD, None

            # 4) Si equity moderado → call
            if eq_bot < 0.65:
                return Action.CALL, None

            # 5) Equity alta → reraise proporcional
            if eq_bot < 0.90:
                desired_raise = max(int(pot_before * 1.0), 1)
                desired_raise = min(desired_raise, self.bot_chips - to_call)
                return Action.RAISE_MEDIUM, desired_raise
            else:
                # All-in reraise
                return Action.RAISE_LARGE, self.bot_chips - to_call

        # =========================
        #  B) Si to_call == 0 (abrir o check)
        # =========================
        if km is not None and nodes is not None:
            # 1) Bucketizar + estrategia CFR
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
        else:
            # Si no hay modelo CFR (fallback aleatorio)
            action = random.choice(list(Action))

        # 2) Convención de tamaños si decide abrir
        if action == Action.RAISE_SMALL:
            raise_amount = max(int(self.pot * 0.5), 1)
        elif action == Action.RAISE_MEDIUM:
            raise_amount = max(int(self.pot * 1.0), 1)
        elif action == Action.RAISE_LARGE:
            raise_amount = self.bot_chips
        else:
            raise_amount = None

        # =========================
        #  C) Si abre y su raise supera 40% del stack, revisar pot odds / equity
        # =========================
        if action in [Action.RAISE_SMALL, Action.RAISE_MEDIUM, Action.RAISE_LARGE] and raise_amount is not None:
            # Si sugerido > 40% del stack, forzamos revisión
            if raise_amount > self.bot_chips * 0.1:
                eq_bot = real_equity_estimate(
                    hole_cards_numeric,
                    community_numeric,
                    num_sim=2000
                )
                # Calcular “pot odds” aproximadas después de este raise
                candidate_raise = raise_amount
                if pot_before + candidate_raise > 0:
                    pot_odds_after = candidate_raise / (pot_before + candidate_raise)
                else:
                    pot_odds_after = 1.0

                # Si equity ≤ pot_odds_after → CALL
                if eq_bot <= pot_odds_after:
                    action = Action.CALL
                    raise_amount = None
                # Si equity moderada → reducir a RAISE_SMALL
                elif eq_bot < 0.70:
                    action = Action.RAISE_SMALL
                    raise_amount = max(int(pot_before * 0.5), 1)
                # Equity alta → RAISE_MEDIUM
                elif eq_bot < 0.90:
                    action = Action.RAISE_MEDIUM
                    raise_amount = max(int(pot_before * 1.0), 1)
                else:
                    # Equity muy alta → ALL‐IN
                    action = Action.RAISE_LARGE
                    raise_amount = self.bot_chips

        if action in [Action.RAISE_SMALL, Action.RAISE_MEDIUM, Action.RAISE_LARGE] and raise_amount is not None:
            to_call = self.current_bet - self.bot_current_bet
            opponent_stack = self.player_chips  # porque el bot está actuando
            max_legal_raise = min(self.bot_chips - to_call, opponent_stack)

            raise_amount = max(0, min(raise_amount, max_legal_raise))
# =========================
            # Si después del límite no queda nada para subir, convierte a CALL
            if raise_amount <= 0:
                action = Action.CALL
                raise_amount = None

        return action, raise_amount

    # --- Obtener quién inicia la ronda de apuestas ---
    def get_first_actor(self):
        if self.street_index == 0:
            return self.dealer
        # Big Blind actúa primero (el que no es dealer)
        return "bot" if self.dealer == "player" else "player"

    # --- Ronda de apuestas con lógica all-in + check integrada 
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

            # ✅ CASO B PARCHEADO: uno está all-in, apuestas NO igualadas → que actúe el otro sólo si puede pagar
            if (player_allin or bot_allin) and not bets_equal:
                if current_turn == "player":
                    print("Estás contra un ALL IN y debes decidir call o fold.")
                    action_str = input("Tu acción (call, fold): ").strip().lower()
                    if action_str == "fold":
                        ended = self.apply_action("player", Action.FOLD)
                        return "fold"
                    elif action_str == "call":
                        ended = self.apply_action("player", Action.CALL)
                        return "all_in"
                    else:
                        print("Acción no válida.")
                        continue
                else:
                    # BOT está contra un all-in del jugador
                    to_call = self.current_bet - self.bot_current_bet
                    max_pay = min(to_call, self.bot_chips)

                    if max_pay > 0:
                        self.bot_chips -= max_pay
                        self.bot_current_bet += max_pay
                        self.bot_contrib += max_pay
                        self.pot += max_pay
                        print(f"Bot hace CALL de {max_pay} fichas para igualar el all-in.")
                    else:
                        print("Bot está all-in o no necesita igualar. CHECK forzado.")

                    return "all_in"

            # 3) Turno normal
            if current_turn == "player":
                action_str = input("Tu acción (fold, call, raise): ").strip().lower()
                if action_str == "fold":
                    ended = self.apply_action("player", Action.FOLD)
                    return "fold" if ended else "continue"
                elif action_str == "call":
                    ended = self.apply_action("player", Action.CALL)
                    return "fold" if ended else "continue"
                elif action_str == "raise":
                    try:
                        raise_amount = int(input("Monto de raise (>0): "))
                        if raise_amount <= 0:
                            raise ValueError
                    except:
                        print("Monto inválido, intenta de nuevo.")
                        continue
                    ended = self.apply_action("player", Action.RAISE_MEDIUM, raise_amount=raise_amount)
                    return "fold" if ended else "continue"
                else:
                    print("Acción no reconocida.")
                    continue

                has_acted["player"] = True
                current_turn = "bot"

            else:
                # Turno del BOT
                action, raise_amount = self.bot_decide_action(trainer)
                to_call_bot = self.current_bet - self.bot_current_bet

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
    def _check_and_update_wins(self):
        if self.player_chips == 0:
            self.wins_bot += 1
        elif self.bot_chips == 0:
            self.wins_player += 1


def main():
    # Cargar trainer entrenado (CFR)
    with open("cfr_entrenado_completo.pkl", "rb") as f:
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