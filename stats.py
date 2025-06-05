import re
import json

LOG_FILE = 'last_hand.log'

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
        'acciones': {
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

    # Regex para capturar diferentes líneas
    regex_blinds = re.compile(r"Dealer:\s*(\w+)\s*→\s*SB=(\d+),\s*BB=(\d+)", re.IGNORECASE)
    regex_dealer = re.compile(r"Dealer:\s*(PLAYER|BOT)", re.IGNORECASE)
    regex_player_hole = re.compile(r"Tus cartas:\s*\[(.*?)\]")
    regex_bot_hole = re.compile(r"Cartas del bot:\s*\[(.*?)\]")
    regex_flop = re.compile(r"Flop:\s*\[(.*?)\]")
    regex_turn = re.compile(r"Turn:\s*(\w+)")
    regex_river = re.compile(r"River:\s*(\w+)")
    regex_action_player = re.compile(r"Player hace (CALL|CHECK|FOLD|RAISE)(?: de (\d+) fichas)?", re.IGNORECASE)
    regex_action_bot = re.compile(r"Bot hace (CALL|CHECK|FOLD|RAISE)(?: de (\d+) fichas)?", re.IGNORECASE)
    regex_showdown = re.compile(r"Showdown!", re.IGNORECASE)
    regex_tu_mejor = re.compile(r"Tu mejor jugada:\s*(.*)", re.IGNORECASE)
    regex_bot_mejor = re.compile(r"Mejor jugada del bot:\s*(.*)", re.IGNORECASE)
    regex_winner = re.compile(r"(¡Ganas la mano.*|El bot gana la mano.*|Empate.*)", re.IGNORECASE)
    regex_pot = re.compile(r"-- Pot total:\s*(\d+) fichas \(Main Pot=(\d+), Side Pot=(\d+)\)")

    # 3) Recorrer mano_lines línea a línea y extraer datos
    calle_actual = 'preflop'
    for line in mano_lines:
        # 3.1) Stacks preflop (podría aparecer justo antes de “=== Nueva mano ===”)
        m_blinds = regex_blinds.search(line)
        if m_blinds and info['stack_player_pre'] is None:
            # El dealer indica quién paga SB/BB; pero lo que queremos es el total inicial de stacks
            # Para simplificar, podemos leer valores anteriores al “=== Nueva mano ===”
            # Por ejemplo, si Dealer: Player → SB=10, BB=20, asumimos que antes ambos tenían initial_stack.
            # En este ejemplo no capturamos el initial_stack original, pero podemos inferir:
            #    stack_player_pre = stack_player_post + contribuciones + (si ganó, sumó pot)
            # Mejor idea: directamente tomar el valor de “Fichas -> Tú: X | Bot: Y” en la línea previa al flop.
            continue

        # 3.2) Dealer
        m_dealer = regex_dealer.match(line)
        if m_dealer and info['dealer'] is None:
            info['dealer'] = m_dealer.group(1).lower()

        # 3.3) Cartas jugador y bot (hole cards)
        m_ph = regex_player_hole.search(line)
        if m_ph and info['player_hole'] is None:
            # Ejemplo de captura: "[As, Kd]" → lista ['As', 'Kd']
            info['player_hole'] = [c.strip() for c in m_ph.group(1).split(',')]

        m_bh = regex_bot_hole.search(line)
        if m_bh and info['bot_hole'] is None:
            info['bot_hole'] = [c.strip() for c in m_bh.group(1).split(',')]

        # 3.4) Flop / Turn / River (para saber en qué ronda estamos)
        m_flop = regex_flop.search(line)
        if m_flop:
            info['community'].append([c.strip() for c in m_flop.group(1).split(',')])
            calle_actual = 'flop'
            continue

        m_turn = regex_turn.search(line)
        if m_turn:
            info['community'].append([m_turn.group(1).strip()])
            calle_actual = 'turn'
            continue

        m_river = regex_river.search(line)
        if m_river:
            info['community'].append([m_river.group(1).strip()])
            calle_actual = 'river'
            continue

        # 3.5) Acciones del jugador
        m_ap = regex_action_player.search(line)
        if m_ap:
            tipo = m_ap.group(1).upper()       # 'CALL', 'CHECK', 'FOLD' o 'RAISE'
            monto = m_ap.group(2) or '0'
            info['acciones'][calle_actual].append({
                'actor': 'player',
                'tipo': tipo.lower(),
                'monto': int(monto)
            })
            continue

        # 3.6) Acciones del bot
        m_ab = regex_action_bot.search(line)
        if m_ab:
            tipo = m_ab.group(1).upper()
            monto = m_ab.group(2) or '0'
            info['acciones'][calle_actual].append({
                'actor': 'bot',
                'tipo': tipo.lower(),
                'monto': int(monto)
            })
            continue

        # 3.7) Showdown (detectamos que llegó showdown)
        if regex_showdown.search(line):
            # A partir de aquí, esperamos líneas con “Tu mejor jugada: ...” y “Mejor jugada del bot: ...”
            calle_actual = 'showdown'
            continue

        # 3.8) Descripción de manos en showdown
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
                # group(2) es Main Pot, group(3) es Side Pot
                info['showdown']['pot_main'] = int(m_pot.group(2))
                info['showdown']['pot_side'] = int(m_pot.group(3))
                continue

    # 4) Extras: stacks finales
    # Buscamos la última línea que empiece por "Fichas -> Tú: X | Bot: Y"
    regex_final_stacks = re.compile(r"Fichas\s*->\s*Tú:\s*(\d+)\s*\|\s*Bot:\s*(\d+)", re.IGNORECASE)
    for line in reversed(mano_lines):
        m_fs = regex_final_stacks.search(line)
        if m_fs:
            info['stack_player_post'] = int(m_fs.group(1))
            info['stack_bot_post'] = int(m_fs.group(2))
            break

    # 5) Para stack inicial (preflop), buscamos la **primera** ocurrencia de esa misma regex
    for line in mano_lines:
        m_is = regex_final_stacks.search(line)
        if m_is:
            info['stack_player_pre'] = int(m_is.group(1))
            info['stack_bot_pre'] = int(m_is.group(2))
            break

    return info


def compute_metrics(parsed):
    """
    A partir de la información extraída (parsed), calcula las métricas:
    - Ganancia neta
    - VPIP, PFR
    - AF
    - WTSD, W$SD
    - Conteo de fold/call/raise por calle
    - Pot odds simples en cada call
    Devuelve un diccionario con las métricas.
    """
    m = {}

    # 1) Stack inicial / final / ganancia neta
    sp_pre = parsed['stack_player_pre']
    sb_pre = parsed['stack_bot_pre']
    sp_post = parsed['stack_player_post']
    sb_post = parsed['stack_bot_post']
    m['stack_player_pre'] = sp_pre
    m['stack_player_post'] = sp_post
    m['stack_bot_pre'] = sb_pre
    m['stack_bot_post'] = sb_post
    m['net_player'] = sp_post - sp_pre
    m['net_bot'] = sb_post - sb_pre

    # 2) VPIP y PFR (preflop)
    acciones_pf = parsed['acciones']['preflop']
    vpip = any(a['actor']=='player' and a['tipo'] in ('call','raise') for a in acciones_pf)
    pfr = any(a['actor']=='player' and a['tipo']=='raise' for a in acciones_pf)
    m['vpip'] = 1 if vpip else 0
    m['pfr'] = 1 if pfr else 0

    # 3) AF (raises + bets) / calls
    total_raises = 0
    total_calls = 0
    for calle in ('preflop','flop','turn','river'):
        for a in parsed['acciones'][calle]:
            if a['actor']=='player':
                if a['tipo']=='raise':
                    total_raises += 1
                elif a['tipo']=='call':
                    total_calls += 1
    m['af'] = total_raises / total_calls if total_calls>0 else None

    # 4) WTSD y W$SD
    # WTSD = 1 si el jugador llega a showdown (aparece parsed['showdown']['tu_mejor'])
    wtsd = 1 if parsed['showdown']['tu_mejor'] else 0
    # W$SD = 1 si gana en showdown
    winner = parsed['showdown']['winner'] or ""
    wsd = 1 if winner.lower().startswith("¡ganas") else 0
    m['wtsd'] = wtsd
    m['wsd'] = wsd

    # 5) Conteo de fold/call/raise por calle (solo acciones del jugador)
    m['counts_per_street'] = {}
    for calle in ('preflop','flop','turn','river'):
        folds = sum(1 for a in parsed['acciones'][calle] if a['actor']=='player' and a['tipo']=='fold')
        calls = sum(1 for a in parsed['acciones'][calle] if a['actor']=='player' and a['tipo']=='call')
        raises = sum(1 for a in parsed['acciones'][calle] if a['actor']=='player' and a['tipo']=='raise')
        m['counts_per_street'][calle] = {
            'folds': folds,
            'calls': calls,
            'raises': raises
        }

    # 6) Pot odds simples: para cada call del jugador, calculamos (monto_call / pot_antes)
    #    Pero necesitamos extraer del log la información del pot justo antes de cada call.
    #    Simplificaremos: si en la línea “Player hace CALL de X fichas” está, 
    #    buscamos inmediatamente la línea previa que indique “Pot: Y” en el statusBar.
    #    Sin embargo, el cliente no imprime “Pot:” en cada ronda dentro del log.
    #    Nueva estrategia: podemos aproximar pot_antes como la suma de contribuciones previas.
    #    Para no complicar, lo dejaremos en null o hacemos un placeholder.
    m['pot_odds'] = None

    return m

if __name__ == '__main__':
    parsed = parse_last_hand()
    metrics = compute_metrics(parsed)
    print(json.dumps(metrics, indent=2))
