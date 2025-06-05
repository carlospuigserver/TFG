import re
import json
import pickle
import numpy as np

from practica2 import Action  # Solo para las constantes de acciones
from bucket_features import (
    hand_to_features_enhanced,
    real_equity_estimate
)

LOG_FILE = 'last_hand.log'
CFR_MODEL_FILE = 'cfr_entreno.pkl'

def _load_trainer():
    """
    Carga el modelo CFR entrenado, para poder extraer la estrategia de Nash
    en cada fase (preflop, flop, turn, river).
    """
    try:
        with open(CFR_MODEL_FILE, 'rb') as f:
            trainer = pickle.load(f)
        return trainer
    except FileNotFoundError:
        raise RuntimeError(f"No se encontró el fichero de CFR en '{CFR_MODEL_FILE}'")

def parse_last_hand():
    """
    Lee last_hand.log y devuelve un dict con la información extraída
    de la última mano: stacks iniciales, dealer, cartas, acciones por calle,
    showdown, ganador, stacks finales, etc.
    """
    # 1) Leer todas las líneas del fichero
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f.readlines()]
    except FileNotFoundError:
        raise RuntimeError(f"No se encontró el fichero de log: {LOG_FILE}")

    # 2) Encontrar índice donde aparece “=== Nueva mano ===”
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("=== Nueva mano ==="):
            start_idx = i
            break

    if start_idx is None:
        raise RuntimeError("No se encontró la marca '=== Nueva mano ===' en el log.")

    # Desde start_idx hacia abajo está la mano, hasta el final del fichero.
    mano_lines = lines[start_idx:]

    # Inicializamos variables de extracción
    info = {
        'stack_player_pre': None,
        'stack_bot_pre': None,
        'stack_player_post': None,
        'stack_bot_post': None,
        'dealer': None,
        'player_hole': None,
        'bot_hole': None,
        'community': [],      # iremos llenando flop, turn, river
        'acciones': {         # guardaremos cada acción con su fase y contexto
            'preflop': [],
            'flop': [],
            'turn': [],
            'river': [],
        },
        'showdown': {
            'tu_mejor': None,
            'bot_mejor': None,
            'winner': None,
            'pot_main': None,
            'pot_side': None,
        }
    }

    # Regex para extraer distintos bloques
    regex_dealer        = re.compile(r"Dealer:\s*(PLAYER|BOT)", re.IGNORECASE)
    regex_player_hole   = re.compile(r"Tus cartas:\s*\[(.*?)\]")
    regex_bot_hole      = re.compile(r"Cartas del bot:\s*\[(.*?)\]")
    regex_flop          = re.compile(r"Flop:\s*\[(.*?)\]")
    # AHORA capturamos TODO lo que esté entre corchetes y sacamos la última carta
    regex_turn          = re.compile(r"Turn:\s*\[(.*?)\]")
    regex_river         = re.compile(r"River:\s*\[(.*?)\]")
    regex_action_player = re.compile(r"Player hace (CALL|CHECK|FOLD|RAISE)(?: de (\d+) fichas)?", re.IGNORECASE)
    regex_action_bot    = re.compile(r"Bot hace (CALL|CHECK|FOLD|RAISE)(?: de (\d+) fichas)?", re.IGNORECASE)
    regex_showdown      = re.compile(r"Showdown!", re.IGNORECASE)
    regex_tu_mejor      = re.compile(r"Tu mejor jugada:\s*(.*)", re.IGNORECASE)
    regex_bot_mejor     = re.compile(r"Mejor jugada del bot:\s*(.*)", re.IGNORECASE)
    regex_winner        = re.compile(r"(¡Ganas la mano.*|El bot gana la mano.*|Empate.*)", re.IGNORECASE)
    regex_pot           = re.compile(r"-- Pot total:\s*(\d+) fichas \(Main Pot=(\d+), Side Pot=(\d+)\)")
    regex_final_stacks  = re.compile(r"Fichas\s*->\s*Tú:\s*(\d+)\s*\|\s*Bot:\s*(\d+)", re.IGNORECASE)

    # 3) Recorrer mano_lines línea a línea y extraer datos
    calle_actual = 'preflop'
    last_action  = None  # tupla (actor, tipo, monto) de la última acción en esta calle

    for line in mano_lines:
        # 3.1) Dealer
        m_dealer = regex_dealer.match(line)
        if m_dealer and info['dealer'] is None:
            info['dealer'] = m_dealer.group(1).lower()

        # 3.2) Cartas jugador y bot (hole cards)
        m_ph = regex_player_hole.search(line)
        if m_ph and info['player_hole'] is None:
            info['player_hole'] = [c.strip() for c in m_ph.group(1).split(',')]

        m_bh = regex_bot_hole.search(line)
        if m_bh and info['bot_hole'] is None:
            info['bot_hole'] = [c.strip() for c in m_bh.group(1).split(',')]

        # 3.3) Flop
        m_flop = regex_flop.search(line)
        if m_flop:
            # Tomamos la lista entera de flop, luego la convertimos a 3 cartas
            lista_flop = [c.strip().strip("'\"") for c in m_flop.group(1).split(',')]
            # Asegurarnos de quedarnos solo con las primeras 3 (por si hubiese ruido extra)
            lista_flop = lista_flop[:3]
            info['community'].append(lista_flop)
            calle_actual = 'flop'
            last_action  = None
            continue

        # 3.4) Turn (la línea viene con 4 cartas en total; extraemos la última)
        m_turn = regex_turn.search(line)
        if m_turn:
            todas = [c.strip().strip("'\"") for c in m_turn.group(1).split(',')]
            if todas:
                last_card = todas[-1]  # será la carta del turn
                info['community'].append([last_card])
            calle_actual = 'turn'
            last_action  = None
            continue

        # 3.5) River (la línea viene con 5 cartas en total; extraemos la última)
        m_river = regex_river.search(line)
        if m_river:
            todas = [c.strip().strip("'\"") for c in m_river.group(1).split(',')]
            if todas:
                last_card = todas[-1]  # será la carta del river
                info['community'].append([last_card])
            calle_actual = 'river'
            last_action  = None
            continue

        # 3.6) Acciones del jugador
        m_ap = regex_action_player.search(line)
        if m_ap:
            tipo  = m_ap.group(1).upper()       # 'CALL', 'CHECK', 'FOLD' o 'RAISE'
            monto = int(m_ap.group(2)) if m_ap.group(2) else 0

            # Si es CHECK y la última acción fue RAISE del bot, lo contamos como CALL
            if tipo == 'CHECK' and last_action and last_action[0] == 'bot' and last_action[1] == 'raise':
                tipo  = 'CALL'
                monto = last_action[2]

            info['acciones'][calle_actual].append({
                'actor': 'player',
                'tipo':  tipo.lower(),
                'monto': monto
            })

            # Actualizar last_action
            if tipo in ('RAISE', 'CALL', 'FOLD'):
                last_action = ('player', tipo.lower(), monto)
            else:
                last_action = ('player', tipo.lower(), 0)
            continue

        # 3.7) Acciones del bot
        m_ab = regex_action_bot.search(line)
        if m_ab:
            tipo  = m_ab.group(1).upper()
            monto = int(m_ab.group(2)) if m_ab.group(2) else 0

            # Si es CHECK y la última acción fue RAISE del jugador, lo contamos como CALL
            if tipo == 'CHECK' and last_action and last_action[0] == 'player' and last_action[1] == 'raise':
                tipo  = 'CALL'
                monto = last_action[2]

            info['acciones'][calle_actual].append({
                'actor': 'bot',
                'tipo':  tipo.lower(),
                'monto': monto
            })

            # Actualizar last_action
            if tipo in ('RAISE', 'CALL', 'FOLD'):
                last_action = ('bot', tipo.lower(), monto)
            else:
                last_action = ('bot', tipo.lower(), 0)
            continue

        # 3.8) Showdown (detectamos que llegó showdown)
        if regex_showdown.search(line):
            calle_actual = 'showdown'
            last_action  = None
            continue

        # 3.9) Descripción de manos en showdown
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
            m_pot = regex_pot.search(line)
            if m_pot:
                info['showdown']['pot_main'] = int(m_pot.group(2))
                info['showdown']['pot_side'] = int(m_pot.group(3))
                continue

    # 4) Extras: stacks finales (se buscan en reversa)
    for line in reversed(mano_lines):
        m_fs = regex_final_stacks.search(line)
        if m_fs:
            info['stack_player_post'] = int(m_fs.group(1))
            info['stack_bot_post']    = int(m_fs.group(2))
            break

    # 5) Para stack inicial (preflop), buscamos la primera ocurrencia
    for line in mano_lines:
        m_is = regex_final_stacks.search(line)
        if m_is:
            info['stack_player_pre'] = int(m_is.group(1))
            info['stack_bot_pre']    = int(m_is.group(2))
            break

    return info


def compute_metrics(parsed):
    """
    A partir de la información extraída (parsed), calcula las métricas:
    - Ganancia neta
    - VPIP, PFR
    - AF (aggression factor)
    - WTSD, W$SD
    - Conteo de fold/call/check/raise por calle
    Devuelve un diccionario con las métricas.
    """
    m = {}

    # 1) Stack inicial / final / ganancia neta
    sp_pre  = parsed['stack_player_pre']
    sb_pre  = parsed['stack_bot_pre']
    sp_post = parsed['stack_player_post']
    sb_post = parsed['stack_bot_post']
    m['stack_player_pre']  = sp_pre
    m['stack_player_post'] = sp_post
    m['stack_bot_pre']     = sb_pre
    m['stack_bot_post']    = sb_post
    m['net_player'] = sp_post - sp_pre
    m['net_bot']    = sb_post - sb_pre

    # 2) VPIP y PFR (preflop)
    acciones_pf = parsed['acciones']['preflop']
    vpip = any(a['actor'] == 'player' and a['tipo'] in ('call', 'raise') for a in acciones_pf)
    pfr  = any(a['actor'] == 'player' and a['tipo'] == 'raise' for a in acciones_pf)
    m['vpip'] = 1 if vpip else 0
    m['pfr']  = 1 if pfr  else 0

    # 3) AF (raises + bets) / calls
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

    # 4) WTSD y W$SD
    wtsd   = 1 if parsed['showdown']['tu_mejor'] else 0
    winner = parsed['showdown']['winner'] or ""
    wsd    = 1 if winner.lower().startswith("¡ganas") else 0
    m['wtsd'] = wtsd
    m['wsd']  = wsd

    # 5) Conteo de fold/call/check/raise por calle (solo acciones del jugador)
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


def compute_nash_recs(parsed):
    """
    Genera recomendaciones basadas en Nash, fase a fase.
    Por cada calle (preflop, flop, turn, river) toma la PRIMERA acción del jugador
    y genera UNA SOLA recomendación para esa calle. Así obtenemos hasta 4 recomendaciones,
    evitando repeticiones múltiples en el caso de que el jugador hiciera varios "call/check" en la misma calle.
    """
    recs = []
    trainer = _load_trainer()

    # Mapeo de la enum Action a índices usados en CFR:
    action_to_idx = {
        Action.FOLD:          0,
        Action.CALL:          1,
        Action.RAISE_SMALL:   2,
        Action.RAISE_MEDIUM:  3,
        Action.RAISE_LARGE:   4
    }

    for calle in ('preflop', 'flop', 'turn', 'river'):
        # Filtrar solo las acciones del jugador en esta calle
        acciones_calle = [a for a in parsed['acciones'][calle] if a['actor'] == 'player']
        if not acciones_calle:
            continue

        # Tomamos únicamente la PRIMERA acción del jugador en esa calle
        primera_accion = acciones_calle[0]
        idx_a = parsed['acciones'][calle].index(primera_accion)

        # --- 1) Preparamos hole y board como listas de tuplas ---
        hole_str  = parsed['player_hole'][:]
        if calle == 'preflop':
            board_str = []
        elif calle == 'flop':
            board_str = parsed['community'][0]
        elif calle == 'turn':
            board_str = parsed['community'][0] + parsed['community'][1]
        else:  # 'river'
            board_str = parsed['community'][0] + parsed['community'][1] + parsed['community'][2]

        # Mapeo de cartas de string a tupla (rank_int, suit_int)
        rank_map = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
            '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11,
            'Q': 12, 'K': 13, 'A': 14
        }
        suit_map = {
            's': 0, 'h': 1, 'd': 2, 'c': 3,
            'S': 0, 'H': 1, 'D': 2, 'C': 3
        }
        def convert_cards(cards_list):
            clean = [c.strip().strip("'\"") for c in cards_list]
            return [(rank_map[c[0]], suit_map[c[1]]) for c in clean]

        hole_num_list  = convert_cards(hole_str)
        board_num_list = convert_cards(board_str)

        # --- 2) Calculamos equity real en este momento ---
        eq_player = real_equity_estimate(hole_num_list, board_num_list, num_sim=500)

        # --- 3) Construir el info-set para este momento ---
        phase_map = {'preflop': 'preflop', 'flop': 'flop', 'turn': 'turn', 'river': 'river'}
        phase = phase_map[calle]

        # Historial simplificado: concatenamos acciones previas en esta calle
        history_for_bucket = ""
        for prev in parsed['acciones'][calle][:idx_a]:
            if prev['tipo'] in ('call', 'check'):
                history_for_bucket += 'c'
            elif prev['tipo'] == 'raise':
                history_for_bucket += 'r'
            elif prev['tipo'] == 'fold':
                history_for_bucket += 'f'

        # Bucketizar usando kmeans del trainer
        km    = trainer.kmeans_models.get(phase, None)
        nodes = trainer.nodes.get(phase, {})

        if km is not None and nodes is not None:
            feats = hand_to_features_enhanced(
                hole_num_list,
                board_num_list,
                pot=0,            # Se podría pasar el pot real si estuviera disponible
                history=history_for_bucket,
                to_act=1          # 1 porque es el jugador el que está actuando
            )
            bucket = int(km.predict(feats.reshape(1, -1))[0])
            info_set = f"{phase}|{bucket}|{history_for_bucket}"
            if info_set in nodes:
                strat = nodes[info_set].get_average_strategy()
            else:
                # Si no existe ese info-set en el árbol CFR, usamos uniforme
                N = len(Action)
                strat = np.ones(N) / N
        else:
            # Si no hay modelo kmeans/nodos, estrategia uniforme
            N = len(Action)
            strat = np.ones(N) / N

        # --- 4) Analizar la acción que tomó el jugador ---
        accion_jugador = primera_accion['tipo']       # 'call', 'check', 'fold' o 'raise'
        # Tratamos 'check' como 'call' para poder mapearlo
        if accion_jugador == 'check':
            accion_jugador = 'call'
        monto_jugador  = primera_accion['monto']      # importe del call/raise (0 si fue check)

        # Convertir el string a la constante Enum Action correspondiente
        try:
            enum_acc   = Action[accion_jugador.upper()]
            idx_action = action_to_idx.get(enum_acc, None)
        except KeyError:
            idx_action = None

        # Si no podemos mapear la acción, saltamos esta calle
        if idx_action is None:
            continue

        prob_nash = strat[idx_action]

        # Encontrar la acción de Nash con mayor probabilidad
        idx_max = int(np.argmax(strat))
        action_from_idx = {v: k for k, v in action_to_idx.items()}
        accion_nash = action_from_idx.get(idx_max, None)

        # --- 5) Construir la frase de recomendación para esta calle ---
        umbral = 0.10

        if prob_nash < umbral:
            texto = (
                f"En {calle.upper()}, tuviste {hole_str} con board {board_str} → "
                f"tu equity ≈ {eq_player:.1%}. Nash juega “{accion_nash.name.lower()}” "
                f"con frecuencia {strat[idx_max]:.0%}, pero tú hiciste “{accion_jugador}”. "
                f"Recomendado: “{accion_nash.name.lower()}”."
            )
            recs.append(texto)
        else:
            texto = (
                f"En {calle.upper()}, tu acción (“{accion_jugador}”) coincide con Nash "
                f"({prob_nash:.0%}). Tu equity ≈ {eq_player:.1%}, ¡bien jugado!"
            )
            recs.append(texto)

    return recs


def get_last_stats():
    """
    Función de conveniencia para ejecutar desde Flask:
    - Parsear la última mano
    - Calcular métricas
    - Calcular recomendaciones de Nash
    - Devolver todo en un JSON único
    """
    parsed  = parse_last_hand()
    metrics = compute_metrics(parsed)
    recs    = compute_nash_recs(parsed)

    response = metrics.copy()
    response['recommendations'] = recs
    return response


if __name__ == '__main__':
    parsed          = parse_last_hand()
    metrics         = compute_metrics(parsed)
    recommendations = compute_nash_recs(parsed)
    output = {
        'metrics':        metrics,
        'recommendations': recommendations
    }
    print(json.dumps(output, indent=2))
