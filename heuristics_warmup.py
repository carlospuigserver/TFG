# heuristics_warmup.py

import random
from poker_env import Action
from rangos import (
    get_open_range,
    get_call_range
)

# ----------------------------------------------------------------
# IMPORTS ADICIONALES NECESARIOS PARA MONTE CARLO (CÁLCULO DE EQUITY)
# ----------------------------------------------------------------
from treys import Card, Evaluator
from poker_env import rank_suit_to_str

# Creamos un Evaluator global para usarlo en la simulación
_evaluator = Evaluator()

# Para convertir hole cards (tupla o string) a notación como "AKs", "99", "72o"
_RANK_ORDER = "23456789TJQKA"

def hole_to_notation(hole):
    """
    hole: lista/tupla de dos cartas, cada carta puede ser
      - string "As", "Td", etc.  (ej.: 'Ah', 'Ks')
      - tupla (rank_int, suit_int), rank_int ∈ [2..14], suit_int ∈ [0..3]
    Devuelve "AKs", "99", "72o", etc.
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


# ------------------------------------------------------
# UTILIDADES PARA POSICIONES EN PÓKER 6-MÁX (NO CAMBIAN)
# ------------------------------------------------------
POSITIONS_6MAX = ["UTG", "EP", "MP", "HJ", "CO", "BTN"]

def get_position(gs):
    """
    Asume 6 jugadores. gs.dealer ∈ [0..5], gs.to_act ∈ [0..5] en orden secuencial de asientos.
    Retorna posición textual en POSITIONS_6MAX ordenado antihorario: [UTG, EP, MP, HJ, CO, BTN]
    """
    rel = (gs.to_act - ((gs.dealer + 3) % 6) + 6) % 6
    return POSITIONS_6MAX[rel]

def get_raiser_position(gs):
    """
    Identifica la posición textual del primer raiser en la mano preflop
    (solo para usar en rangos de defensa preflop).
    """
    if 'r' not in gs.history:
        return None
    idx_raise = gs.history.index('r')
    asiento_raiser = (gs.dealer + 1 + idx_raise) % 6

    class DummyGS:
        pass

    dgs = DummyGS()
    dgs.dealer = gs.dealer
    dgs.to_act = asiento_raiser
    return get_position(dgs)


# --------------------------------------------
# 1) PRE-FLOP HEURISTICS (Cubrimos TODOS los escenarios)
# --------------------------------------------
def preflop_heuristic_action(gs):
    pos_defender = get_position(gs)
    hole = gs.hole_cards[gs.to_act]
    hand_not = hole_to_notation(hole)

    # 1) Si no hay history: open-raise según rango
    if gs.history == "":
        open_pct, open_hands = get_open_range(pos_defender)
        if hand_not in open_hands:
            # En HU, usamos RAISE_LARGE si venimos de posiciones tempranas
            if pos_defender in ["UTG", "EP", "MP"]:
                return Action.RAISE_LARGE
            return Action.RAISE_MEDIUM
        else:
            return Action.FOLD

    # 2) Si ya hubo raise: defender según rangos de call
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
def evaluate_pocket_pair(hole, community, gs=None):
    """
    Si el jugador tiene pocket-pair preflop, detectamos si conectó set/trío:
      - hole es pocket-pair
      - en community (flop/turn) aparece alguna carta del mismo rank
    Entonces devolvemos True (set/trío).
    """
    if isinstance(hole[0], str):
        r1 = hole[0][0]
        r2 = hole[1][0]
    else:
        r1 = _RANK_ORDER[hole[0][0] - 2]
        r2 = _RANK_ORDER[hole[1][0] - 2]

    if r1 != r2:
        return False

    # Si es pocket-pair, chequeamos si muestra set/trío en board
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
    Detecta proyectos de color en flop/turn: 
    al menos 2 cartas del mismo palo entre hole y board.
    """
    def suit_val(card):
        return card[1] if isinstance(card, str) else card[1]

    suits_hole = [suit_val(hole[0]), suit_val(hole[1])]
    board_suits = [suit_val(c) for c in community]
    for s in suits_hole:
        if board_suits.count(s) >= 2:
            return True
    return False

def determine_board_texture(community):
    """
    Clasifica textura del board en 'dry', 'wet' o 'neutral' (solo para flop).
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

    # 1) Si es pocket-pair y conectó set/trío, hacemos un RAISE_MEDIUM
    if evaluate_pocket_pair(hole, community):
        return Action.RAISE_MEDIUM

    # 2) Si hay flush draw, pagamos o hacemos RAISE_SMALL
    if has_flush_draw(hole, community):
        to_call = gs.current_bet - (gs.player_current_bet if gs.to_act == 0 else gs.bot_current_bet)
        if to_call > 0:
            return Action.CALL
        return Action.RAISE_SMALL

    # 3) Caso genérico: fold/call según pot odds simplificado
    to_call = gs.current_bet - (gs.player_current_bet if gs.to_act == 0 else gs.bot_current_bet)
    if to_call > 0:
        if to_call <= gs.pot * 0.2:
            return Action.CALL
        return Action.FOLD
    else:
        return Action.CALL  # check


# --------------------------------------------
# 3) RIVER HEURISTICS
# --------------------------------------------
def compute_pot_odds(villain_bet, current_pot):
    total_if_called = current_pot + villain_bet + villain_bet
    if total_if_called <= 0:
        return 0.0
    return (villain_bet / total_if_called) * 100

def compute_bluff_odds(bluff_bet, current_pot):
    total_with_bluff = current_pot + bluff_bet
    if total_with_bluff <= 0:
        return 0.0
    return (bluff_bet / total_with_bluff) * 100

def has_nut_blocker(hole, community):
    """
    Detecta bloqueadores de nut flush en el river: 
    Si board ya tiene 4 cartas de un mismo palo y hole contenga As de ese palo.
    """
    def suit_val(card):
        return card[1] if isinstance(card, str) else card[1]

    suits_community = [suit_val(c) for c in community]
    for c in hole:
        if isinstance(c, str):
            r, s = c[0], c[1]
        else:
            r = _RANK_ORDER[c[0] - 2]
            s = c[1]
        if suits_community.count(s) == 4 and r == "A":
            return True
    return False

def simple_equity_estimate(hole, community):
    """
    Estimación MUY simplificada de equity en river y también para FLOP (cuando la uses ahí):
      - Si evaluate_pocket_pair(...) retorna True → equity 0.85 (trío o mejor).
      - Si hay alguna carta de hole igual a comunidad → equity 0.50 (pair medio).
      - En cualquier otro caso → equity 0.10.
    """
    if evaluate_pocket_pair(hole, community):
        return 0.85

    hole_ranks = set()
    for c in hole:
        if isinstance(c, str):
            hole_ranks.add(c[0])
        else:
            hole_ranks.add(_RANK_ORDER[c[0] - 2])
    comm_ranks = set()
    for c in community:
        if isinstance(c, str):
            comm_ranks.add(c[0])
        else:
            comm_ranks.add(_RANK_ORDER[c[0] - 2])
    if hole_ranks & comm_ranks:
        return 0.5

    return 0.1

def river_heuristic_action(gs):
    hole = gs.hole_cards[gs.to_act]
    community = gs.community_cards  # 5 cartas en river
    to_call = gs.current_bet - (gs.player_current_bet if gs.to_act == 0 else gs.bot_current_bet)
    pot = gs.pot

    equity = simple_equity_estimate(hole, community)

    # 1) Si hay que pagar
    if to_call > 0:
        pot_odds_pct = compute_pot_odds(to_call, pot)
        if (equity * 100) >= pot_odds_pct:
            return Action.CALL
        else:
            return Action.FOLD

    # 2) Si no hay que pagar, y hay bloqueador de nut‐flush, vamos ALL‐IN
    if has_nut_blocker(hole, community):
        return Action.RAISE_LARGE

    # 3) Caso genérico: check
    return Action.CALL


# --------------------------------------------------
# MONTE CARLO EQUITY (USANDO treys/Evaluator)
# --------------------------------------------------
def monte_carlo_equity(hole, community, to_simulate=1000):
    """
    Simula rivales aleatorios y calcula equity aproximada usando 'treys'.
    hole       : lista de 2 cartas propias, cada carta como string "As", "Td", etc.
    community  : lista de cartas comunitarias (0..5 cartas), cada carta como string.
    to_simulate: número de iteraciones Monte Carlo.
    Devuelve (ganas + empates * 0.5) / total_simulaciones.
    """
    # 1) Construir mazo completo y quitar las cartas conocidas
    full_deck = []
    suits = ["H", "D", "C", "S"]
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
    for r in ranks:
        for s in suits:
            full_deck.append(r + s)

    known = set(hole + community)
    remaining = [c for c in full_deck if c not in known]

    wins = 0
    ties = 0
    total = to_simulate

    for _ in range(to_simulate):
        random.shuffle(remaining)
        opp_hole = remaining[:2]
        cards_needed = 5 - len(community)
        board_extra = remaining[2 : 2 + cards_needed]
        final_board = community + board_extra

        # Convertir a treys para evaluación
        own_board_treys = [Card.new(rank_suit_to_str(c)) for c in final_board]
        own_hand_treys  = [Card.new(rank_suit_to_str(c)) for c in hole]
        opp_board_treys = [Card.new(rank_suit_to_str(c)) for c in final_board]
        opp_hand_treys  = [Card.new(rank_suit_to_str(c)) for c in opp_hole]

        own_score = _evaluator.evaluate(own_board_treys, own_hand_treys)
        opp_score = _evaluator.evaluate(opp_board_treys, opp_hand_treys)

        # En Treys, score más bajo = mejor mano
        if own_score < opp_score:
            wins += 1
        elif own_score == opp_score:
            ties += 1

    return (wins + ties * 0.5) / total


# --------------------------------------------------
# Función unificada de heurística según fase
# --------------------------------------------------
def heuristic_action(gs):
    if gs.phase == "preflop":
        return preflop_heuristic_action(gs)
    elif gs.phase in ("flop", "turn"):
        return postflop_heuristic_action(gs)
    else:
        return river_heuristic_action(gs)
