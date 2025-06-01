# bucket_features.py

import random
import numpy as np
from poker_env import INITIAL_STACK
from treys import Card as TreysCard, Evaluator as TreysEvaluator

_evaluator = TreysEvaluator()

# --------------------------------------------------------
# 1) FUNCIÓN PARA SIMULAR EQUITY REAL
# --------------------------------------------------------
def real_equity_estimate(hole, community, num_sim=100):
    """
    Estima la equity real de `hole` frente a un rival con hole aleatorio.
    - hole: lista de 2 tuplas (rank_int, suit_int)
    - community: lista de 0..5 tuplas (rank_int, suit_int)
    - num_sim: número de simulaciones Monte Carlo
    Devuelve un float ∈ [0..1].
    """
    # Construir baraja completa
    ranks = list(range(2, 15))
    suits = list(range(4))
    full_deck = [(r, s) for s in suits for r in ranks]

    # Filtrar las cartas que ya están en uso (hole + community)
    used = set(hole + community)
    deck = [c for c in full_deck if c not in used]

    wins = 0
    ties = 0
    losses = 0

    for _ in range(num_sim):
        random.shuffle(deck)

        # Repartir hole del rival: primeras 2 cartas de deck
        opp_hole = deck[0:2]

        # Completar el board hasta 5 cartas
        missing = 5 - len(community)
        board = community.copy()
        board.extend(deck[2:2 + missing])

        # Convertir a Treys
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


def _card_to_str(card):
    """
    Convierte (rank_int, suit_int) a notación Treys: 'As', 'Kd', etc.
    rank_int ∈ [2..14], suit_int ∈ [0..3] con 0=spades,1=hearts,2=diamonds,3=clubs.
    """
    rank_map = {14: 'A', 13: 'K', 12: 'Q', 11: 'J', 10: 'T'}
    suit_map = {0: 's', 1: 'h', 2: 'd', 3: 'c'}
    r = rank_map.get(card[0], str(card[0]))
    s = suit_map.get(card[1], 's')
    return r + s


# --------------------------------------------------------
# 2) FEATURES “ENRIQUECIDAS” PARA BUCKETIZACIÓN AVANZADA
# --------------------------------------------------------
def has_flush_draw(hole, community):
    """
    Indica 1 si hay proyecto de color: al menos 2 mismas suits en hole + ≥2 en community.
    """
    suits_h = [c[1] for c in hole]
    suits_b = [c[1] for c in community]
    for s in set(suits_h):
        if suits_b.count(s) >= 2:
            return 1
    return 0


def has_straight_draw(hole, community):
    """
    Indica 1 si hay proyecto de escalera: alguna secuencia de 4 valores entre hole∪community.
    """
    ranks = set([c[0] for c in hole + community])
    for r in range(2, 11):
        if all([(r + i) in ranks for i in range(4)]):
            return 1
    # Proyecto wheel A-2-3-4
    if {14, 2, 3, 4}.issubset(ranks):
        return 1
    return 0


def board_connectedness(community):
    """
    ∈ [0..1]: cuántos pares en el board están consecutivos (para medir “conectividad”).
    """
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
    """
    Proxy de EHS: simplemente invoca real_equity_estimate con un solo oponente aleatorio.
    """
    return real_equity_estimate(hole, community, num_sim=num_mc)


def hand_to_features_enhanced(hole, community, pot, history, to_act):
    """
    Vector 1-D con features:
      1) Codificación lineal básica: (hole ×2) + (up to 5 community) + pot_norm + to_act + count('r')
      2) + has_flush_draw, has_straight_draw, board_connectedness
      3) + EHS estimate, + pot_ratio
    """
    f = []

    # 1) Basico: hole cards
    for c in hole:
        f.extend(c)

    # Community: hasta 5 cartas
    for i in range(5):
        if i < len(community):
            f.extend(community[i])
        else:
            f.extend([0, 0])

    # pot normalizado
    f.append(pot / INITIAL_STACK)

    # to_act (0 o 1)
    f.append(to_act)

    # número de 'r' en history
    f.append(history.count('r'))

    # 2) Discretas/proxies
    fd = has_flush_draw(hole, community)
    f.append(fd)

    sd = has_straight_draw(hole, community)
    f.append(sd)

    bc = board_connectedness(community)
    f.append(bc)

    # 3) EHS y pot_ratio
    ehs = effective_hand_strength(hole, community, num_mc=20)
    f.append(ehs)

    pot_ratio = pot / (pot + 2 * INITIAL_STACK)
    f.append(pot_ratio)

    return np.array(f, dtype=float)
