import re
import json
import pickle

from practica2 import Action  # Solo para constantes de acciones
from bucket_features import real_equity_estimate

LOG_FILE = 'last_hand.log'
CFR_MODEL_FILE = 'cfr_entreno.pkl'

def parse_last_hand():
    """
    Lee last_hand.log y devuelve un dict con la información extraída
    de la última mano: stacks iniciales, dealer, cartas, acciones por calle,
    showdown, ganador, stacks finales, y el pot inicial tras blinds.
    """
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = [l.rstrip() for l in f.readlines()]
    except FileNotFoundError:
        raise RuntimeError(f"No se encontró el fichero de log: {LOG_FILE}")

    # 1) Buscar "=== Nueva mano ==="
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("=== Nueva mano ==="):
            start_idx = i
            break

    if start_idx is None:
        raise RuntimeError("No se encontró la marca '=== Nueva mano ===' en el log.")

    mano_lines = lines[start_idx:]

    info = {
        'stack_player_pre':  None,
        'stack_bot_pre':     None,
        'stack_player_post': None,
        'stack_bot_post':    None,
        'initial_pot':       0,      # Pot tras blinds
        'dealer':            None,
        'player_hole':       None,
        'bot_hole':          None,
        'community':         [],     # [[flop3],[turn1],[river1]]
        'acciones': {
            'preflop': [],
            'flop':    [],
            'turn':    [],
            'river':   [],
        },
        'showdown': {
            'tu_mejor': None,
            'bot_mejor': None,
            'winner':    None,
            'pot_main':  None,
            'pot_side':  None,
        }
    }

    regex_dealer         = re.compile(r"Dealer:\s*(PLAYER|BOT)", re.IGNORECASE)
    regex_player_hole    = re.compile(r"Tus cartas:\s*\[(.*?)\]")
    regex_bot_hole       = re.compile(r"Cartas del bot:\s*\[(.*?)\]")
    regex_flop           = re.compile(r"Flop:\s*\[(.*?)\]")
    regex_turn           = re.compile(r"Turn:\s*\[(.*?)\]")
    regex_river          = re.compile(r"River:\s*\[(.*?)\]")
    regex_action_player  = re.compile(r"Player hace (CALL|CHECK|FOLD|RAISE)(?: de (\d+) fichas)?", re.IGNORECASE)
    regex_action_bot     = re.compile(r"Bot hace (CALL|CHECK|FOLD|RAISE)(?: de (\d+) fichas)?", re.IGNORECASE)
    regex_showdown       = re.compile(r"Showdown!", re.IGNORECASE)
    regex_tu_mejor       = re.compile(r"Tu mejor jugada:\s*(.*)", re.IGNORECASE)
    regex_bot_mejor      = re.compile(r"Mejor jugada del bot:\s*(.*)", re.IGNORECASE)
    regex_winner         = re.compile(r"(¡Ganas la mano.*|El bot gana la mano.*|Empate.*)", re.IGNORECASE)
    regex_pot_showdown   = re.compile(r"-- Pot total:\s*(\d+)\s+fichas\s+\(Main Pot=(\d+), Side Pot=(\d+)\)")
    regex_stacks         = re.compile(r"Fichas\s*->\s*Tú:\s*(\d+)\s*\|\s*Bot:\s*(\d+)", re.IGNORECASE)
    regex_pot_status     = re.compile(r"Pot:\s*(\d+)", re.IGNORECASE)

    calle_actual = 'preflop'
    last_action  = None
    found_initial_pot = False

    for idx, line in enumerate(mano_lines):
        if not found_initial_pot:
            m_pot = regex_pot_status.search(line)
            if m_pot:
                info['initial_pot'] = int(m_pot.group(1))
                found_initial_pot = True

        m_dealer = regex_dealer.match(line)
        if m_dealer and info['dealer'] is None:
            info['dealer'] = m_dealer.group(1).lower()

        m_ph = regex_player_hole.search(line)
        if m_ph and info['player_hole'] is None:
            info['player_hole'] = [c.strip().strip("'\"") for c in m_ph.group(1).split(',')]

        m_bh = regex_bot_hole.search(line)
        if m_bh and info['bot_hole'] is None:
            info['bot_hole'] = [c.strip().strip("'\"") for c in m_bh.group(1).split(',')]

        m_flop = regex_flop.search(line)
        if m_flop:
            lista_flop = [c.strip().strip("'\"") for c in m_flop.group(1).split(',')]
            lista_flop = lista_flop[:3]
            info['community'].append(lista_flop)
            calle_actual = 'flop'
            last_action  = None
            continue

        m_turn = regex_turn.search(line)
        if m_turn:
            todas = [c.strip().strip("'\"") for c in m_turn.group(1).split(',')]
            if todas:
                last_card = todas[-1]
                info['community'].append([last_card])
            calle_actual = 'turn'
            last_action  = None
            continue

        m_river = regex_river.search(line)
        if m_river:
            todas = [c.strip().strip("'\"") for c in m_river.group(1).split(',')]
            if todas:
                last_card = todas[-1]
                info['community'].append([last_card])
            calle_actual = 'river'
            last_action  = None
            continue

        m_ap = regex_action_player.search(line)
        if m_ap:
            tipo  = m_ap.group(1).upper()
            monto = int(m_ap.group(2)) if m_ap.group(2) else 0

            if tipo == 'CHECK' and last_action and last_action[0] == 'bot' and last_action[1] == 'raise':
                tipo  = 'CALL'
                monto = last_action[2]

            info['acciones'][calle_actual].append({
                'actor': 'player',
                'tipo':  tipo.lower(),
                'monto': monto
            })

            if tipo in ('RAISE', 'CALL', 'FOLD'):
                last_action = ('player', tipo.lower(), monto)
            else:
                last_action = ('player', tipo.lower(), 0)
            continue

        m_ab = regex_action_bot.search(line)
        if m_ab:
            tipo  = m_ab.group(1).upper()
            monto = int(m_ab.group(2)) if m_ab.group(2) else 0

            if tipo == 'CHECK' and last_action and last_action[0] == 'player' and last_action[1] == 'raise':
                tipo  = 'CALL'
                monto = last_action[2]

            info['acciones'][calle_actual].append({
                'actor': 'bot',
                'tipo':  tipo.lower(),
                'monto': monto
            })

            if tipo in ('RAISE', 'CALL', 'FOLD'):
                last_action = ('bot', tipo.lower(), monto)
            else:
                last_action = ('bot', tipo.lower(), 0)
            continue

        if regex_showdown.search(line):
            calle_actual = 'showdown'
            last_action  = None
            continue

        if calle_actual == 'showdown':
            m_tm = regex_tu_mejor.search(line)
            if m_tm:
                info['showdown']['tu_mejor'] = m_tm.group(1).strip()
                continue
            m_bm = regex_bot_mejor.search(line)
            if m_bm:
                info['showdown']['bot_mejor'] = m_bm.group(1).strip()
                continue
            m_wr = regex_winner.search(line)
            if m_wr:
                info['showdown']['winner'] = m_wr.group(1).strip()
                continue
            m_pot = regex_pot_showdown.search(line)
            if m_pot:
                info['showdown']['pot_main'] = int(m_pot.group(2))
                info['showdown']['pot_side'] = int(m_pot.group(3))
                continue

    for line in reversed(mano_lines):
        m_fs = regex_stacks.search(line)
        if m_fs:
            info['stack_player_post'] = int(m_fs.group(1))
            info['stack_bot_post']    = int(m_fs.group(2))
            break

    for line in mano_lines:
        m_is = regex_stacks.search(line)
        if m_is:
            info['stack_player_pre'] = int(m_is.group(1))
            info['stack_bot_pre']    = int(m_is.group(2))
            break

    return info


def compute_metrics(parsed):
    """
    Calcula métricas globales a partir de parsed.
    """
    m = {}

    sp_pre   = parsed['stack_player_pre']
    sb_pre   = parsed['stack_bot_pre']
    sp_post  = parsed['stack_player_post']
    sb_post  = parsed['stack_bot_post']
    m['stack_player_pre']  = sp_pre
    m['stack_player_post'] = sp_post
    m['stack_bot_pre']     = sb_pre
    m['stack_bot_post']    = sb_post
    m['net_player'] = sp_post - sp_pre
    m['net_bot']    = sb_post - sb_pre

    acciones_pf = parsed['acciones']['preflop']
    vpip = any(a['actor'] == 'player' and a['tipo'] in ('call', 'raise') for a in acciones_pf)
    pfr  = any(a['actor'] == 'player' and a['tipo'] == 'raise' for a in acciones_pf)
    m['vpip'] = 1 if vpip else 0
    m['pfr']  = 1 if pfr  else 0

    total_raises = 0
    total_calls  = 0
    for calle in ('preflop', 'flop', 'turn', 'river'):
        for a in parsed['acciones'][calle]:
            if a['actor'] == 'player':
                if a['tipo'] == 'raise':
                    total_raises += 1
                elif a['tipo'] == 'call':
                    total_calls += 1
    m['af'] = (total_raises / total_calls) if total_calls > 0 else None

    wtsd   = 1 if parsed['showdown']['tu_mejor'] else 0
    winner = parsed['showdown']['winner'] or ""
    wsd    = 1 if winner.lower().startswith("¡ganas") else 0
    m['wtsd'] = wtsd
    m['wsd']  = wsd

    m['counts_per_street'] = {}
    for calle in ('preflop', 'flop', 'turn', 'river'):
        folds  = sum(1 for a in parsed['acciones'][calle] if a['actor'] == 'player' and a['tipo'] == 'fold')
        calls  = sum(1 for a in parsed['acciones'][calle] if a['actor'] == 'player' and a['tipo'] == 'call')
        checks = sum(1 for a in parsed['acciones'][calle] if a['actor'] == 'player' and a['tipo'] == 'check')
        raises = sum(1 for a in parsed['acciones'][calle] if a['actor'] == 'player' and a['tipo'] == 'raise')
        m['counts_per_street'][calle] = {
            'folds': folds,
            'calls': calls,
            'checks': checks,
            'raises': raises
        }

    return m


def _convertir_cartas(cards_list):
    rank_map = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'T':10,'J':11,'Q':12,'K':13,'A':14}
    suit_map = {'s':0,'h':1,'d':2,'c':3,'S':0,'H':1,'D':2,'C':3}
    resultado = []
    for c in cards_list:
        c = c.strip().strip("'\"")
        if len(c) >= 2:
            r = rank_map.get(c[0], None)
            s = suit_map.get(c[1], None)
            if r is not None and s is not None:
                resultado.append((r,s))
    return resultado


def _cartas_y_tablero(parsed, calle):
    hole = parsed['player_hole'][:]
    if calle == 'preflop':
        board = []
    elif calle == 'flop':
        board = parsed['community'][0][:]
    elif calle == 'turn':
        board = parsed['community'][0][:] + parsed['community'][1][:]
    else:  # 'river'
        board = parsed['community'][0][:] + parsed['community'][1][:] + parsed['community'][2][:]
    return hole, board


def _get_pot_before(parsed, calle):
    pot = parsed['initial_pot']
    for c_prev in ('preflop', 'flop', 'turn', 'river'):
        if c_prev == calle:
            break
        for a in parsed['acciones'][c_prev]:
            pot += a['monto']
    acciones_calle = parsed['acciones'][calle]
    idx_primera = None
    for idx, a in enumerate(acciones_calle):
        if a['actor'] == 'player':
            idx_primera = idx
            break
    if idx_primera is not None:
        for i in range(idx_primera):
            pot += acciones_calle[i]['monto']
    return pot


def compute_recommendations(parsed):
    """
    Genera recomendaciones basadas en equity vs pot odds + tamaño del raise,
    e incluye las cartas del jugador y del board en cada calle.
    """
    recs = []

    for calle in ('preflop', 'flop', 'turn', 'river'):
        acciones_calle = parsed['acciones'][calle]
        acciones_player = [a for a in acciones_calle if a['actor'] == 'player']
        if not acciones_player:
            continue

        primera = acciones_player[0]
        tipo    = primera['tipo']   # 'call', 'check', 'fold' o 'raise'
        monto   = primera['monto']

        hole_str, board_str = _cartas_y_tablero(parsed, calle)
        hole_display  = "[" + ", ".join(hole_str) + "]"
        board_display = "[" + ", ".join(board_str) + "]"

        # 1) CALL o CHECK
        if tipo in ('call', 'check'):
            pot_before = _get_pot_before(parsed, calle)
            call_amt   = monto
            pot_after  = pot_before + call_amt
            pot_odds   = (call_amt / pot_after) if pot_after > 0 else 0.0

            hole_nums  = _convertir_cartas(hole_str)
            board_nums = _convertir_cartas(board_str)
            eq_player  = real_equity_estimate(hole_nums, board_nums, num_sim=500)

            texto = (
                f"En {calle.upper()}, tenías {hole_display} con board {board_display}. "
                f"Pagaste {call_amt} fichas; pot odds ≈ {pot_odds:.0%}, equity ≈ {eq_player:.0%}. "
                f"{'Deberías haber FOLD.' if eq_player < pot_odds else 'Correcto hacer CALL.'}"
            )
            recs.append(texto)
            continue

        # 2) RAISE
        if tipo == 'raise':
            hole_nums  = _convertir_cartas(hole_str)
            board_nums = _convertir_cartas(board_str)
            eq_player  = real_equity_estimate(hole_nums, board_nums, num_sim=500)

            pre_stack  = parsed['stack_player_pre'] or 0
            porcentaje = (monto / pre_stack) if pre_stack > 0 else 0.0

            if porcentaje > 0.40:
                if eq_player < 0.30:
                    texto = (
                        f"En {calle.upper()}, tenías {hole_display} con board {board_display}. "
                        f"Hiciste un RAISE grande ({porcentaje:.0%} del stack) con equity ≈ {eq_player:.0%}. "
                        f"Mejor FOLD o raise más pequeño."
                    )
                elif eq_player < 0.65:
                    texto = (
                        f"En {calle.upper()}, tenías {hole_display} con board {board_display}. "
                        f"Raise grande ({porcentaje:.0%} del stack) con equity ≈ {eq_player:.0%}. "
                        f"Podrías haber hecho raise más pequeño o un simple CALL."
                    )
                else:
                    texto = (
                        f"En {calle.upper()}, tenías {hole_display} con board {board_display}. "
                        f"Raise grande ({porcentaje:.0%}) con equity alta ≈ {eq_player:.0%}. "
                        f"Raise coherente."
                    )
            else:
                texto = (
                    f"En {calle.upper()}, tenías {hole_display} con board {board_display}. "
                    f"Raise moderado ({porcentaje:.0%} del stack) con equity ≈ {eq_player:.0%}. "
                    f"Raise coherente."
                )
            recs.append(texto)
            continue

        # 3) FOLD
        if tipo == 'fold':
            texto = (
                f"En {calle.upper()}, tenías {hole_display} con board {board_display}. "
                f"Te retiraste sin apostar. No hay recomendación adicional."
            )
            recs.append(texto)
            continue

    return recs


def get_last_stats():
    """
    Función para Flask: parsea mano, calcula métricas y recomendaciones.
    """
    parsed          = parse_last_hand()
    metrics         = compute_metrics(parsed)
    recommendations = compute_recommendations(parsed)

    response = metrics.copy()
    response['recommendations'] = recommendations
    return response


if __name__ == '__main__':
    parsed          = parse_last_hand()
    metrics         = compute_metrics(parsed)
    recommendations = compute_recommendations(parsed)
    output = {
        'metrics':         metrics,
        'recommendations': recommendations
    }
    print(json.dumps(output, indent=2))
