import random
import numpy as np
from poker_env import INITIAL_STACK
from treys import Card as TreysCard, Evaluator as TreysEvaluator

_evaluator = TreysEvaluator()

# ------------------------------------------
# Función para convertir (rank, suit) → Treys
# ------------------------------------------
def _card_to_str(card):
    rank_map = {14: 'A', 13: 'K', 12: 'Q', 11: 'J', 10: 'T'}
    suit_map = {0: 's', 1: 'h', 2: 'd', 3: 'c'}
    r = rank_map.get(card[0], str(card[0]))
    s = suit_map.get(card[1], 's')
    return r + s

# --------------------------------------------------------
# 1) SIMULACIÓN DE EQUITY REAL CON PERFIL DE OPONENTE
# --------------------------------------------------------
def is_hand_in_range(card1, card2, profile="balanced"):
    ranks_sorted = sorted([card1[0], card2[0]], reverse=True)
    suits_list = [card1[1], card2[1]]
    gap = abs(ranks_sorted[0] - ranks_sorted[1])
    same_suit = suits_list[0] == suits_list[1]

    high_card = ranks_sorted[0]
    low_card = ranks_sorted[1]

    is_pair = high_card == low_card
    is_suited = same_suit
    is_connector = gap <= 1
    both_high = high_card >= 11 and low_card >= 10  # QJ, KQ, AJ...

    if profile == "tight":
        if is_pair and high_card >= 9:
            return True
        if both_high and is_suited:
            return True
        if is_connector and is_suited and high_card >= 10:
            return True
        return False

    elif profile == "loose":
        if is_pair:
            return True
        if is_connector:
            return True
        if is_suited and high_card >= 6:
            return True
        if high_card >= 10:
            return True
        return False

    else:  # "balanced"
        if is_pair and high_card >= 7:
            return True
        if both_high:
            return True
        if is_connector and is_suited:
            return True
        if is_connector:
            return True
        return False

def real_equity_estimate(hole, community, num_sim=100, profile="balanced"):
    ranks = list(range(2, 15))
    suits = list(range(4))
    full_deck = [(r, s) for s in suits for r in ranks]

    used = set(hole + community)
    deck = [c for c in full_deck if c not in used]

    # Generar posibles manos del oponente
    possible_opp_hands = []
    for i in range(len(deck)):
        for j in range(i + 1, len(deck)):
            c1, c2 = deck[i], deck[j]
            if is_hand_in_range(c1, c2, profile=profile):
                possible_opp_hands.append((c1, c2))

    # Si ninguna mano pasó el filtro, usar todas
    if not possible_opp_hands:
        for i in range(len(deck)):
            for j in range(i + 1, len(deck)):
                possible_opp_hands.append((deck[i], deck[j]))

    wins = 0
    ties = 0
    losses = 0

    for _ in range(num_sim):
        random.shuffle(possible_opp_hands)
        opp_hole = possible_opp_hands[0]

        missing = 5 - len(community)
        board = community.copy()

        used_sim = set(hole + community + list(opp_hole))
        deck_sim = [c for c in full_deck if c not in used_sim]
        random.shuffle(deck_sim)
        board.extend(deck_sim[:missing])

        treys_board = [TreysCard.new(_card_to_str(c)) for c in board]
        treys_hand0 = [TreysCard.new(_card_to_str(c)) for c in hole]
        treys_hand1 = [TreysCard.new(_card_to_str(c)) for c in opp_hole]

        score0 = _evaluator.evaluate(treys_board, treys_hand0)
        score1 = _evaluator.evaluate(treys_board, treys_hand1)

        if score0 < score1:
            wins += 1
        elif score0 == score1:
            ties += 1
        else:
            losses += 1

    total = wins + ties + losses
    if total == 0:
        return 0.0
    return (wins + ties / 2) / total

# --------------------------------------------------------
# 2) FEATURES “ENRIQUECIDAS” PARA BUCKETIZACIÓN AVANZADA
# --------------------------------------------------------
def has_flush_draw(hole, community):
    suits_h = [c[1] for c in hole]
    suits_b = [c[1] for c in community]
    for s in set(suits_h):
        if suits_b.count(s) >= 2:
            return 1
    return 0

def has_straight_draw(hole, community):
    ranks = set([c[0] for c in hole + community])
    for r in range(2, 11):
        if all([(r + i) in ranks for i in range(4)]):
            return 1
    if {14, 2, 3, 4}.issubset(ranks):
        return 1
    return 0

def board_connectedness(community):
    if len(community) < 3:
        return 0.0
    rs = sorted(set([c[0] for c in community]))
    pairs = 0
    total_pairs = len(rs) - 1
    for i in range(total_pairs):
        if rs[i + 1] - rs[i] == 1:
            pairs += 1
    return pairs / total_pairs if total_pairs > 0 else 0.0

def effective_hand_strength(hole, community, num_mc=50):
    return real_equity_estimate(hole, community, num_sim=num_mc)

def hand_to_features_enhanced(hole, community, pot, history, to_act):
    f = []

    # 1) Cartas propias
    for c in hole:
        f.extend(c)

    # 2) Cartas comunitarias (rellenar hasta 5)
    for i in range(5):
        if i < len(community):
            f.extend(community[i])
        else:
            f.extend([0, 0])

    # 3) Pot normalizado
    f.append(pot / INITIAL_STACK)

    # 4) To act (0 o 1)
    f.append(to_act)

    # 5) Número de raises
    f.append(history.count('r'))

    # 6) Flags
    f.append(has_flush_draw(hole, community))
    f.append(has_straight_draw(hole, community))
    f.append(board_connectedness(community))

    # 7) EHS y pot ratio
    f.append(effective_hand_strength(hole, community, num_mc=20))
    f.append(pot / (pot + 2 * INITIAL_STACK))

    return np.array(f, dtype=float)
