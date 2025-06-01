#poker_env.py

import random
import numpy as np
from itertools import combinations
from enum import Enum
from treys import Card, Evaluator

INITIAL_STACK = 1000
_evaluator = Evaluator()

class Action(Enum):
    FOLD = 0
    CALL = 1
    RAISE_SMALL = 2
    RAISE_MEDIUM = 3
    RAISE_LARGE = 4

NUM_ACTIONS = len(Action)

def create_deck():
    ranks = list(range(2, 15))  # 2..14 (14=As)
    suits = list(range(4))      # 0=spades, 1=hearts, 2=diamonds, 3=clubs
    return [(r, s) for s in suits for r in ranks]

def rank_suit_to_str(card):
    rank_map = {14: 'A', 13: 'K', 12: 'Q', 11: 'J', 10: 'T'}
    suit_map = {0: 's', 1: 'h', 2: 'd', 3: 'c'}
    r = rank_map.get(card[0], str(card[0]))
    s = suit_map[card[1]]
    return r + s

def cards_str(cards):
    return ' '.join(rank_suit_to_str(c) for c in cards)

def card_list_to_treys(cards):
    return [Card.new(rank_suit_to_str(c)) for c in cards]

def evaluate_hand(hole_cards, community_cards):
    board = card_list_to_treys(community_cards)
    hand = card_list_to_treys(hole_cards)
    return _evaluator.evaluate(board, hand)

def get_winner(gs):
    s0 = evaluate_hand(gs.hole_cards[0], gs.community_cards)
    s1 = evaluate_hand(gs.hole_cards[1], gs.community_cards)
    if s0 < s1:
        return 0
    if s1 < s0:
        return 1
    return -1

def hand_to_features(hole_cards, community_cards, bet_size, history, to_act, pot):
    f = []
    for c in hole_cards:
        f.extend(c)
    for i in range(5):
        if i < len(community_cards):
            f.extend(community_cards[i])
        else:
            f.extend([0, 0])
    f.append(bet_size)
    f.append(pot / INITIAL_STACK)
    f.append(to_act)
    f.append(history.count('r'))
    return np.array(f, dtype=float)

class GameState:
    def __init__(self, hole0, hole1, community=None,
                 pot=0, to_act=0, history='', phase='preflop',
                 stack0=INITIAL_STACK, stack1=INITIAL_STACK,
                 current_bet=0, bet0=0, bet1=0,
                 dealer=0, deck=None):
        self.hole_cards = {0: hole0, 1: hole1}
        self.community_cards = community or []
        self.pot = pot
        self.to_act = to_act
        self.history = history
        self.phase = phase
        self.stack = {0: stack0, 1: stack1}
        self.current_bet = current_bet
        self.bet = {0: bet0, 1: bet1}
        self.dealer = dealer
        self.deck = deck

    def is_terminal(self):
        if 'f' in self.history:
            return True
        if self.phase == 'river' and len(self.history) >= 4:
            return True
        return False

    def get_payoff(self, player):
        if 'f' in self.history:
            fold_player = (len(self.history) - 1) % 2
            winner = 1 - fold_player
        elif self.phase == 'river' and len(self.history) >= 4:
            winner = get_winner(self)
        else:
            return 0
        if winner == -1:
            return 0
        return self.pot if winner == player else -self.pot

    def legal_actions(self):
        return list(range(NUM_ACTIONS))

    def _is_betting_round_complete(self):
        if 'f' in self.history:
            return True
        if self.bet[0] == self.bet[1] and self.history.endswith(('c', 'r', 'f')):
            return True
        return False

    def _advance_phase(self):
        phases = ['preflop', 'flop', 'turn', 'river']
        idx = phases.index(self.phase)
        new_community = self.community_cards.copy()
        if idx < len(phases) - 1:
            next_phase = phases[idx + 1]
            if next_phase == 'flop' and len(new_community) < 3:
                new_community.extend(self.deck[4:7])
            elif next_phase == 'turn' and len(new_community) < 4:
                new_community.append(self.deck[7])
            elif next_phase == 'river' and len(new_community) < 5:
                new_community.append(self.deck[8])
            self.phase = next_phase
            self.community_cards = new_community
            self.bet = {0: 0, 1: 0}
            self.current_bet = 0
            self.history += '|'

    def apply_action(self, action_idx, raise_amount=None):
        raise_sizes = {
            2: int(self.pot * 0.5),
            3: int(self.pot * 1.0),
            4: self.stack[self.to_act]
        }
        action = Action(action_idx)
        if action == Action.FOLD:
            self.history += 'f'
            winner = 1 - self.to_act
            self.stack[winner] += self.pot
            self.pot = 0
            return self

        elif action == Action.CALL:
            to_call = self.current_bet - self.bet[self.to_act]
            to_call = min(to_call, self.stack[self.to_act])
            self.stack[self.to_act] -= to_call
            self.bet[self.to_act] += to_call
            self.pot += to_call
            self.history += 'c'

        elif action in [Action.RAISE_SMALL, Action.RAISE_MEDIUM, Action.RAISE_LARGE]:
            base_raise = raise_sizes[action_idx]
            if raise_amount is not None and raise_amount > base_raise:
                base_raise = min(raise_amount, self.stack[self.to_act])
            else:
                base_raise = min(base_raise, self.stack[self.to_act])
            to_call = self.current_bet - self.bet[self.to_act]
            total_bet = to_call + base_raise
            if total_bet > self.stack[self.to_act] + self.bet[self.to_act]:
                total_bet = self.stack[self.to_act] + self.bet[self.to_act]
            bet_increase = total_bet - self.bet[self.to_act]
            self.stack[self.to_act] -= bet_increase
            self.bet[self.to_act] = total_bet
            self.pot += bet_increase
            self.current_bet = total_bet
            self.history += 'r'

        self.to_act = 1 - self.to_act
        if self._is_betting_round_complete():
            self._advance_phase()
        return self

def get_bucket(kmeans_model, hole_cards, community_cards,
               bet_size, history='', to_act=0, pot=0):
    feats = hand_to_features(hole_cards, community_cards,
                              bet_size, history, to_act, pot)
    return kmeans_model.predict(feats.reshape(1, -1))[0]
