# heuristics_warmup.py

import random
from poker_env import Action
from rangos import (
    PRE_FLOP_OPEN_RANGES,
    PRE_FLOP_CALL_RANGES,
    BET_SIZING_RULES,
    RIVER_TIPS,
    HAND_READING_PRINCIPLES,
    get_open_range,
    get_call_range,
    suggest_bet_size
)
from bucket_features import real_equity_estimate

# --------------------------------------------
# Util para notación de manos “AKs”, “99”, “72o”
# --------------------------------------------
_RANK_ORDER = "23456789TJQKA"

def hole_to_notation(hole):
    """
    hole: lista/tupla de 2 cartas (string 'As' o tupla (14,1)).
    Devuelve “AKs”, “99”, “72o”, etc.
    """
    if isinstance(hole[0], str):
        r1, s1 = hole[0][0], hole[0][1]
        r2, s2 = hole[1][0], hole[1][1]
    else:
        rank_int1, suit_int1 = hole[0]
        rank_int2, suit_int2 = hole[1]
        r1 = _RANK_ORDER[rank_int1 - 2]
        r2 = _RANK_ORDER[rank_int2 - 2]
        s1 = suit_int1
        s2 = suit_int2

    if _RANK_ORDER.index(r1) > _RANK_ORDER.index(r2):
        high, low = r1, r2
        suited = (s1 == s2)
    elif _RANK_ORDER.index(r1) < _RANK_ORDER.index(r2):
        high, low = r2, r1
        suited = (s1 == s2)
    else:
        # Pocket pair
        return r1 + r2

    return f"{high}{low}" + ("s" if suited else "o")


# --------------------------------------------
# Posiciones 6-max
# --------------------------------------------
POSITIONS_6MAX = ["UTG", "EP", "MP", "HJ", "CO", "BTN"]

def get_position(gs):
    """
    gs.dealer ∈ [0..5], gs.to_act ∈ [0..5]; retorna la posición textual en 6-max.
    """
    rel = (gs.to_act - ((gs.dealer + 3) % 6) + 6) % 6
    return POSITIONS_6MAX[rel]

def get_raiser_position(gs):
    """
    Encuentra la posición textual del primer raiser preflop en gs.history.
    """
    if 'r' not in gs.history:
        return None
    idx_raise = gs.history.index('r')
    asiento_raiser = (gs.dealer + 1 + idx_raise) % 6

    class DummyGS: pass
    dgs = DummyGS()
    dgs.dealer = gs.dealer
    dgs.to_act = asiento_raiser
    return get_position(dgs)


# --------------------------------------------
# 1) PRE-FLOP HEURISTICS
# --------------------------------------------
def preflop_heuristic_action(gs):
    pos_defender = get_position(gs)
    hole = gs.hole_cards[gs.to_act]
    hand_not = hole_to_notation(hole)

    # 1) Sin history: open-raise según rango
    if gs.history == "":
        open_pct, open_hands = get_open_range(pos_defender)
        if hand_not in open_hands:
            if pos_defender in ["UTG", "EP", "MP"]:
                return Action.RAISE_LARGE
            return Action.RAISE_MEDIUM
        else:
            return Action.FOLD

    # 2) Ya hubo raise: defender según rangos de call
    pos_raiser = get_raiser_position(gs)
    if pos_raiser is None:
        return Action.FOLD

    scenario = None
    if pos_defender == "BTN" and pos_raiser in ["UTG", "EP"]:
        scenario = "BTN_vs_EP"
    elif pos_defender == "BTN" and pos_raiser in ["MP", "HJ"]:
        scenario = "BTN_vs_MP"
    elif pos_defender == "BB" and pos_raiser in ["UTG", "EP"]:
        scenario = "BB_vs_EP"
    elif pos_defender == "BB" and pos_raiser in ["MP", "HJ"]:
        scenario = "BB_vs_MP"
    elif pos_defender == "BB" and pos_raiser in ["CO", "BTN"]:
        scenario = "BB_vs_LP"
    else:
        return Action.FOLD

    call_pct, call_hands = get_call_range(scenario)
    if hand_not in call_hands:
        return Action.CALL
    else:
        return Action.FOLD


# --------------------------------------------
# 2) POSTFLOP HEURISTICS (FLOP y TURN)
# --------------------------------------------
def evaluate_pocket_pair(hole, community):
    """
    Devuelve True si hole es pocket-pair y hay al menos una carta del mismo rank en community.
    """
    if isinstance(hole[0], str):
        r1 = hole[0][0]
        r2 = hole[1][0]
    else:
        r1 = _RANK_ORDER[hole[0][0] - 2]
        r2 = _RANK_ORDER[hole[1][0] - 2]

    if r1 != r2:
        return False

    for c in community:
        if isinstance(c, str):
            if c[0] == r1:
                return True
        else:
            r_comm = _RANK_ORDER[c[0] - 2]
            if r_comm == r1:
                return True
    return False

def has_flush_draw(hole, community):
    """
    Detecta proyecto de color: al menos 2 del mismo palo en hole y ≥2 en community.
    """
    suits_h = [c[1] for c in hole]
    suits_b = [c[1] for c in community]
    for s in suits_h:
        if suits_b.count(s) >= 2:
            return True
    return False

def determine_board_texture(community):
    """
    Retorna 'dry', 'wet' o 'neutral' según las primeras 3 cartas del board.
    """
    if len(community) < 3:
        return "neutral"
    ranks = []
    suits = []
    for c in community[:3]:
        if isinstance(c, str):
            ranks.append(_RANK_ORDER.index(c[0]))
            suits.append(c[1])
        else:
            ranks.append(c[0] - 2)
            suits.append(c[1])
    unique_suits = set(suits)
    for s in unique_suits:
        if suits.count(s) >= 2:
            return "wet"
    sorted_ranks = sorted(ranks)
    if sorted_ranks[2] - sorted_ranks[0] <= 4:
        return "wet"
    return "dry"

def postflop_heuristic_action(gs):
    hole = gs.hole_cards[gs.to_act]
    community = gs.community_cards

    # 1) Si es pocket-pair y conectó set/trío
    if evaluate_pocket_pair(hole, community):
        in_3bet_pot = ('r' in gs.history and gs.history.count('r') >= 2)
        texture = determine_board_texture(community)
        bs_low, bs_high = suggest_bet_size(
            texture,
            "turn" if len(community) == 4 else "flop",
            in_3bet_pot
        )
        if bs_low >= 0.55:
            return Action.RAISE_MEDIUM
        return Action.RAISE_SMALL

    # 2) Flush draw
    if has_flush_draw(hole, community):
        to_call = gs.current_bet - (
            gs.player_current_bet if gs.to_act == 0 else gs.bot_current_bet
        )
        if to_call > 0:
            eq = real_equity_estimate(hole, community, num_sim=20)
            pot = gs.pot
            pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1.0
            if eq >= pot_odds:
                return Action.CALL
            return Action.FOLD
        else:
            return Action.RAISE_SMALL

    # 3) Caso genérico: fold/call según equity real vs pot odds
    to_call = gs.current_bet - (
        gs.player_current_bet if gs.to_act == 0 else gs.bot_current_bet
    )
    if to_call > 0:
        eq = real_equity_estimate(hole, community, num_sim=20)
        pot = gs.pot
        pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1.0
        if eq >= pot_odds:
            return Action.CALL
        else:
            return Action.FOLD
    else:
        return Action.CALL  # CHECK


# --------------------------------------------
# 3) RIVER HEURISTICS
# --------------------------------------------
def compute_pot_odds(villain_bet, current_pot):
    total_if_called = current_pot + villain_bet + villain_bet
    return (villain_bet / total_if_called) * 100 if total_if_called > 0 else 0.0

def has_nut_blocker(hole, community):
    """
    True si el board ya tiene 4 cartas de un mismo palo y hole contiene As de ese palo.
    """
    suits_community = [c[1] for c in community]
    for c in hole:
        if isinstance(c, str):
            r, s = c[0], c[1]
        else:
            r = _RANK_ORDER[c[0] - 2]
            s = c[1]
        if suits_community.count(s) == 4 and r == "A":
            return True
    return False

def river_heuristic_action(gs):
    hole = gs.hole_cards[gs.to_act]
    community = gs.community_cards
    to_call = gs.current_bet - (
        gs.player_current_bet if gs.to_act == 0 else gs.bot_current_bet
    )
    pot = gs.pot

    # 1) Equity real en river
    eq = real_equity_estimate(hole, community, num_sim=30)

    if to_call > 0:
        pot_odds_pct = compute_pot_odds(to_call, pot)
        if (eq * 100) >= pot_odds_pct:
            return Action.CALL
        else:
            return Action.FOLD

    # 2) Si no hay que pagar: raise si bloqueador de nut flush
    if has_nut_blocker(hole, community):
        return Action.RAISE_LARGE

    # 3) Bluff razonable si equity ≥ 0.3
    if eq >= 0.3:
        return Action.RAISE_MEDIUM

    # 4) En otro caso: check/call
    return Action.CALL


# --------------------------------------------
# Función unificada de heurística según fase
# --------------------------------------------
def heuristic_action(gs):
    if gs.phase == "preflop":
        return preflop_heuristic_action(gs)
    elif gs.phase in ("flop", "turn"):
        return postflop_heuristic_action(gs)
    else:
        return river_heuristic_action(gs)
