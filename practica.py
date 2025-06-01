# practica2.py

import random
import pickle
import numpy as np
from itertools import combinations
from poker_env import Action, NUM_ACTIONS, get_bucket, GameState
from poker_env import create_deck, rank_suit_to_str  # rank_suit_to_str para mostrar cartas


class PokerGame:
    def __init__(self, initial_stack=1000, small_blind=10, big_blind=20):
        self.initial_stack = initial_stack
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.game_state = None

    def start_hand(self):
        # 1) Preparamos y barajamos el deck
        deck = create_deck()
        random.shuffle(deck)
        hole0, hole1 = deck[:2], deck[2:4]

        # 2) Alternamos dealer (si no existe aún, dealer=0 → jugador)
        try:
            last_dealer = self.game_state.dealer
            dealer = 1 - last_dealer
        except (AttributeError, TypeError):
            dealer = 0

        # 3) Repartimos blinds / ajustamos stacks iniciales
        #    Dealer = 0 → jugador pone SB, bot pone BB, y BB (bot) actúa primero.
        #    Dealer = 1 → bot pone SB, jugador pone BB, y BB (jugador) actúa primero.
        community = []
        if dealer == 0:
            stack0 = self.initial_stack - self.small_blind
            stack1 = self.initial_stack - self.big_blind
            bet0, bet1 = self.small_blind, self.big_blind
            to_act = 1
        else:
            stack1 = self.initial_stack - self.small_blind
            stack0 = self.initial_stack - self.big_blind
            bet1, bet0 = self.small_blind, self.big_blind
            to_act = 0

        pot = self.small_blind + self.big_blind
        current_bet = self.big_blind

        self.game_state = GameState(
            hole0=hole0,
            hole1=hole1,
            community=community,
            pot=pot,
            to_act=to_act,
            history='',
            phase='preflop',
            stack0=stack0,
            stack1=stack1,
            current_bet=current_bet,
            bet0=bet0,
            bet1=bet1,
            dealer=dealer,
            deck=deck
        )

        # Mostrar mano inicial
        print("\n=== Nueva mano ===")
        print(f"Dealer: {'JUGADOR' if dealer == 0 else 'BOT'}")
        hc0 = rank_suit_to_str(hole0[0]) + rank_suit_to_str(hole0[1])
        print(f"Tus cartas: {rank_suit_to_str(hole0[0])} {rank_suit_to_str(hole0[1])}")

    def apply_human_action(self):
        """
        Pide acción al humano: fold/check/call/raise
        """
        gs = self.game_state
        while True:
            action_str = input("Tu acción (fold, check, call, raise): ").strip().lower()
            # FOLD
            if action_str == "fold":
                return Action.FOLD, None
            # CHECK → sólo si no hay nada que pagar (current_bet == bet[0])
            if action_str == "check" and gs.current_bet == gs.bet[0]:
                return Action.CALL, None  # en GameState usamos CALL como "check"
            # CALL → sólo si hay una apuesta pendiente
            if action_str == "call" and gs.current_bet > gs.bet[0]:
                return Action.CALL, None
            # RAISE
            if action_str == "raise":
                try:
                    amt = int(input("Monto de raise (>0): "))
                except:
                    print("Monto inválido, inténtalo de nuevo.")
                    continue
                if amt <= 0:
                    print("Monto debe ser mayor que 0.")
                    continue
                return Action.RAISE_MEDIUM, amt
            print("Acción no válida o no aplicable. Intenta de nuevo.")

    def bot_action(self, trainer):
        """
        El CFR + kmeans ya entrenado decide la acción del bot.
        """
        gs = self.game_state
        phase = gs.phase
        to_act = gs.to_act

        # Si no se entrenó esa fase, jugamos al azar
        if phase not in trainer.kmeans_models:
            action = random.choice(list(Action))
            return action, None

        # Construimos infoset → bucket
        history_for_bucket = gs.history
        hole = gs.hole_cards[to_act]
        bucket = get_bucket(
            trainer.kmeans_models[phase],
            hole,
            gs.community_cards,
            bet_size=gs.pot / self.initial_stack,
            history=history_for_bucket,
            to_act=to_act,
            pot=gs.pot
        )
        infoset = f"{phase}|{bucket}|{history_for_bucket}"
        if infoset in trainer.nodes[phase]:
            strat = trainer.nodes[phase][infoset].get_average_strategy()
        else:
            strat = np.ones(NUM_ACTIONS) / NUM_ACTIONS

        action_idx = np.random.choice(range(NUM_ACTIONS), p=strat)
        action = Action(action_idx)

        # Si decide subir, le damos raise_amount según convención
        if action in (Action.RAISE_SMALL, Action.RAISE_MEDIUM, Action.RAISE_LARGE):
            if action == Action.RAISE_SMALL:
                raise_amt = max(int(gs.pot * 0.6), 1)
            elif action == Action.RAISE_MEDIUM:
                raise_amt = max(int(gs.pot * 1.0), 1)
            else:
                # ALL-IN
                raise_amt = gs.stack[to_act]
            return action, raise_amt

        return action, None

    def play_hand(self, trainer):
        # 1) Arrancamos mano y repartimos blinds
        self.start_hand()

        # 2) Loop mientras no termine (ni fold ni showdown)
        while not self.game_state.is_terminal():
            gs = self.game_state
            to_act = gs.to_act

            # Mostramos estado ANTES de cada acción
            print(f"\nFase: {gs.phase.upper()}, Pot: {gs.pot}, Apuestas: {gs.bet[0]}|{gs.bet[1]}")
            print(f"Comunidad: {' '.join(rank_suit_to_str(c) for c in gs.community_cards)}")
            print(f"Stacks: Jugador={gs.stack[0]}, Bot={gs.stack[1]}")

            if to_act == 0:
                # Turno humano
                action, amt = self.apply_human_action()
                if amt is not None:
                    print(f"Jugador elige {action.name} de {amt}")
                else:
                    print(f"Jugador elige {action.name}")
                self.game_state = gs.apply_action(action.value, amt)
            else:
                # Turno bot
                action, amt = self.bot_action(trainer)
                if amt is not None:
                    print(f"Bot decide {action.name} con {amt}")
                else:
                    print(f"Bot decide {action.name}")
                self.game_state = gs.apply_action(action.value, amt)

            # (ahora vuelve al while y se imprimirá el estado actualizado)

        # 3) Mano terminada (fold o showdown)
        print("\n--- Showdown o Fold ---")
        gs = self.game_state

        # Si no hubo fold, imprimimos showdown completo
        if 'f' not in gs.history:
            print(f"Tus cartas: {' '.join(rank_suit_to_str(c) for c in gs.hole_cards[0])}, "
                  f"Comunidad: {' '.join(rank_suit_to_str(c) for c in gs.community_cards)}")
            print(f"Cartas bot: {' '.join(rank_suit_to_str(c) for c in gs.hole_cards[1])}, "
                  f"Comunidad: {' '.join(rank_suit_to_str(c) for c in gs.community_cards)}")

        payoff_p0 = gs.get_payoff(0)
        if payoff_p0 > 0:
            print(f"¡Ganas la mano y obtienes {payoff_p0} fichas!")
        elif payoff_p0 < 0:
            print(f"Pierdes la mano y pierdes {-payoff_p0} fichas.")
        else:
            print("Empate. No hay cambio de fichas.")

        print(f"Stacks finales de la mano: Jugador={gs.stack[0]}, Bot={gs.stack[1]}\n")
        return True

    def run(self, trainer):
        while True:
            # 1) Jugamos una mano completa
            done = self.play_hand(trainer)
            if not done:
                break

            # 2) Tras acabar la mano, comprobamos si alguien se quedó sin fichas
            gs = self.game_state
            if gs.stack[0] <= 0 or gs.stack[1] <= 0:
                print("Alguno de los dos se quedó sin fichas. Fin del match.")
                break

            # 3) Preguntamos si queremos otra mano
            cont = input("¿Jugar otra mano? (s/n): ").strip().lower()
            if cont != "s":
                break


def main():
    # Cargamos el trainer entrenado (cfr_trainer.pkl)
    with open("cfr_trainer.pkl", "rb") as f:
        trainer = pickle.load(f)

    game = PokerGame()
    game.run(trainer)


if __name__ == "__main__":
    main()
