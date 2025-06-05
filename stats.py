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
    regex_final_stacks = re.compile(r"Fichas\s*->\s*Tú:\s*(\d+)\s*\|\s*Bot:\s*(\d+)", re.IGNORECASE)

    # 3) Recorrer mano_lines línea a línea y extraer datos
    calle_actual = 'preflop'
    last_action = None  # tuple (actor, tipo, monto) de la última acción en esta calle

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

        # 3.3) Flop / Turn / River (para saber en qué ronda estamos)
        m_flop = regex_flop.search(line)
        if m_flop:
            info['community'].append([c.strip() for c in m_flop.group(1).split(',')])
            calle_actual = 'flop'
            last_action = None
            continue

        m_turn = regex_turn.search(line)
        if m_turn:
            info['community'].append([m_turn.group(1).strip()])
            calle_actual = 'turn'
            last_action = None
            continue

        m_river = regex_river.search(line)
        if m_river:
            info['community'].append([m_river.group(1).strip()])
            calle_actual = 'river'
            last_action = None
            continue

        # 3.4) Acciones del jugador
        m_ap = regex_action_player.search(line)
        if m_ap:
            tipo = m_ap.group(1).upper()       # 'CALL', 'CHECK', 'FOLD' o 'RAISE'
            monto = int(m_ap.group(2)) if m_ap.group(2) else 0

            # Si es CHECK y la última acción fue RAISE del bot, lo contamos como CALL
            if tipo == 'CHECK' and last_action and last_action[0] == 'bot' and last_action[1] == 'raise':
                tipo = 'CALL'
                monto = last_action[2]

            info['acciones'][calle_actual].append({
                'actor': 'player',
                'tipo': tipo.lower(),
                'monto': monto
            })

            # Actualizar last_action
            if tipo in ('RAISE', 'CALL', 'FOLD'):
                last_action = ('player', tipo.lower(), monto)
            else:
                last_action = ('player', tipo.lower(), 0)
            continue

        # 3.5) Acciones del bot
        m_ab = regex_action_bot.search(line)
        if m_ab:
            tipo = m_ab.group(1).upper()
            monto = int(m_ab.group(2)) if m_ab.group(2) else 0

            # Si es CHECK y la última acción fue RAISE del jugador, lo contamos como CALL
            if tipo == 'CHECK' and last_action and last_action[0] == 'player' and last_action[1] == 'raise':
                tipo = 'CALL'
                monto = last_action[2]

            info['acciones'][calle_actual].append({
                'actor': 'bot',
                'tipo': tipo.lower(),
                'monto': monto
            })

            # Actualizar last_action
            if tipo in ('RAISE', 'CALL', 'FOLD'):
                last_action = ('bot', tipo.lower(), monto)
            else:
                last_action = ('bot', tipo.lower(), 0)
            continue

        # 3.6) Showdown (detectamos que llegó showdown)
        if regex_showdown.search(line):
            calle_actual = 'showdown'
            last_action = None
            continue

        # 3.7) Descripción de manos en showdown
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

    # 4) Extras: stacks finales
    for line in reversed(mano_lines):
        m_fs = regex_final_stacks.search(line)
        if m_fs:
            info['stack_player_post'] = int(m_fs.group(1))
            info['stack_bot_post'] = int(m_fs.group(2))
            break

    # 5) Para stack inicial (preflop), buscamos la primera ocurrencia
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
    - Conteo de fold/call/check/raise por calle
    - Pot odds simples en cada call (placeholder)
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
    vpip = any(a['actor'] == 'player' and a['tipo'] in ('call', 'raise') for a in acciones_pf)
    pfr = any(a['actor'] == 'player' and a['tipo'] == 'raise' for a in acciones_pf)
    m['vpip'] = 1 if vpip else 0
    m['pfr'] = 1 if pfr else 0

    # 3) AF (raises + bets) / calls
    total_raises = 0
    total_calls = 0
    for calle in ('preflop', 'flop', 'turn', 'river'):
        for a in parsed['acciones'][calle]:
            if a['actor'] == 'player':
                if a['tipo'] == 'raise':
                    total_raises += 1
                elif a['tipo'] == 'call':
                    total_calls += 1
    m['af'] = total_raises / total_calls if total_calls > 0 else None

    # 4) WTSD y W$SD
    wtsd = 1 if parsed['showdown']['tu_mejor'] else 0
    winner = parsed['showdown']['winner'] or ""
    wsd = 1 if winner.lower().startswith("¡ganas") else 0
    m['wtsd'] = wtsd
    m['wsd'] = wsd

    # 5) Conteo de fold/call/check/raise por calle (solo acciones del jugador)
    m['counts_per_street'] = {}
    for calle in ('preflop', 'flop', 'turn', 'river'):
        folds = sum(1 for a in parsed['acciones'][calle] if a['actor'] == 'player' and a['tipo'] == 'fold')
        calls = sum(1 for a in parsed['acciones'][calle] if a['actor'] == 'player' and a['tipo'] == 'call')
        checks = sum(1 for a in parsed['acciones'][calle] if a['actor'] == 'player' and a['tipo'] == 'check')
        raises = sum(1 for a in parsed['acciones'][calle] if a['actor'] == 'player' and a['tipo'] == 'raise')
        m['counts_per_street'][calle] = {
            'folds': folds,
            'calls': calls,
            'checks': checks,
            'raises': raises
        }

    # 6) Pot odds: placeholder (se podría mejorar)
    m['pot_odds'] = None

    return m


def generate_recommendations(parsed, metrics):
    """
    Genera una lista de recomendaciones basadas en las "parsed" y las "metrics".
    Cada elemento de la lista es una frase de consejo de Nash.
    """
    recs = []

    # 1) Preflop: si no hubo VPIP (vpip == 0) y tenías un par alto o cartas fuertes,
    #    recomendar ser más agresivo.
    #    Ejemplo muy simplificado: si tu mano inicial era pareja alta, sugerir raise.
    hole = parsed['player_hole']
    vpip = metrics['vpip']
    if vpip == 0:
        # Vamos a distinguir pares altos si la "hole" muestra dos mismas letras.
        if hole[0][0] == hole[1][0]:  
            recs.append(
                f"En preflop, tu mano inicial fue {hole}. Nash sugeriría abrir con raise con pareja."
            )
        else:
            recs.append(
                f"En preflop, tuviste {hole}. Nash habría recomendado al menos un call, pero igualaste fotos."
            )

    # 2) Flop: si hiciste muchos calls pero no raise y tenías posibilidad de proyecto,
    #    sugerir ser más agresivo.
    calls_flop = metrics['counts_per_street']['flop']['calls']
    raises_flop = metrics['counts_per_street']['flop']['raises']
    if calls_flop > 0 and raises_flop == 0:
        recs.append(
            f"En el flop hiciste {calls_flop} call(s) pero ningún raise. Nash recomendaría más agresión en el flop."
        )

    # 3) Turn: si hiciste fold con equity decente (por ejemplo, si tienes par medio),
    #    recomendar revisar pot odds. Para simplificar, asumimos que si fold=1, sugerimos.
    folds_turn = metrics['counts_per_street']['turn']['folds']
    if folds_turn > 0:
        recs.append(
            f"En el turn te retiraste (fold). Si tu equity era > 40%, Nash indicaría al menos un call."
        )

    # 4) River: si llegaste a showdown y perdiste, agregar consejo sobre valor.
    if metrics['wtsd'] == 1 and metrics['wsd'] == 0:
        recs.append(
            "Llegaste al showdown pero perdiste. En river, revisar si tu apuesta de valor fue óptima según Nash."
        )

    # 5) Agregar mensaje general si no hay recomendaciones específicas.
    if len(recs) == 0:
        recs.append("Movimiento muy cercano a Nash. ¡Buen trabajo!")
    
    return recs


if __name__ == '__main__':
    parsed = parse_last_hand()
    metrics = compute_metrics(parsed)
    recommendations = generate_recommendations(parsed, metrics)

    # Imprimimos JSON con métricas y recomendaciones
    output = {
        'metrics': metrics,
        'recommendations': recommendations
    }
    print(json.dumps(output, indent=2))
