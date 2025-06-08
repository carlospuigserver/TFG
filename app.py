#app.py
from flask import Flask, request, jsonify, send_from_directory
import pickle
import stats
from practica import PokerGame, Action

app = Flask(__name__, static_folder='.')

# Ciegas dinámicas
initial_sb = 10
initial_bb = 20
sb = initial_sb
bb = initial_bb
manos_desde_reset = 0
# Carga del trainer entrenado (CFR)
with open('cfr_entreno.pkl', 'rb') as f:
    trainer = pickle.load(f)

game = None
current_hand_logs = []  # Acumula todas las líneas de la mano en curso
last_dealer = "bot"  # el primero en repartir será el jugador


def action_str_to_enum(action_str):
    mapping = {
        "fold": Action.FOLD,
        "call": Action.CALL,
        "raise": Action.RAISE_MEDIUM,
    }
    return mapping.get(action_str)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/inicial.html')
def serve_inicial():
    return send_from_directory('.', 'inicial.html')

@app.route('/partida.html')
def serve_partida():
    return send_from_directory('.', 'partida.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

def format_chips():
    return f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}"

@app.route('/api/start_hand', methods=['POST'])
def start_hand():
    global game, current_hand_logs, last_dealer
    global sb, bb, manos_desde_reset


    # Crear una nueva partida y alternar el dealer manualmente
    # Heredar los stacks anteriores y alternar el dealer
    if game and game.player_chips > 0 and game.bot_chips > 0:
        player_stack = game.player_chips
        bot_stack = game.bot_chips
        manos_desde_reset += 1
        if manos_desde_reset % 4 == 0:
            sb *= 2
            bb *= 2
            current_hand_logs = [f"🔺 Ciegas aumentadas: SB={sb}, BB={bb}"]

    else:
        # Reset completo
        player_stack = 1000
        bot_stack = 1000
        sb = initial_sb
        bb = initial_bb
        manos_desde_reset = 0

    game = PokerGame(player_chips=player_stack, bot_chips=bot_stack, small_blind=sb, big_blind=bb)


    game.dealer = "bot" if last_dealer == "player" else "player"
    last_dealer = game.dealer  # Actualizar el global

    result = game.start_hand()

    if result == 'allin':
        logs = [
            "=== Mano forzada con all-in automático ===",
            f"Tus cartas: {game.player_hole}",
            f"Cartas del bot: {game.bot_hole}",
            f"Comunitarias: {game.community_cards}",
            format_chips(),
            "--- Showdown directo por falta de fichas ---"
        ]
        current_hand_logs[:] = logs
        return _resolve_showdown(current_hand_logs.copy())
    elif not result:
        return jsonify({'error': 'Error inesperado al iniciar la mano.'}), 400


    # Construir log inicial con claridad sobre quién paga cada ciega
    if game.dealer == "player":
        logs = [
            f"Dealer: JUGADOR -> SB={game.small_blind} (jugador), BB={game.big_blind} (bot)",
            "=== Nueva mano ===",
            "Dealer: PLAYER",
            f"Tus cartas: {game.player_hole}",
            format_chips(),
            f"--- Nueva ronda de apuestas (inicia: {game.get_first_actor().upper()}) ---"
        ]
    else:  # dealer == "bot"
        logs = [
            f"Dealer: BOT -> SB={game.small_blind} (bot), BB={game.big_blind} (jugador)",
            "=== Nueva mano ===",
            "Dealer: BOT",
            f"Tus cartas: {game.player_hole}",
            format_chips(),
            f"--- Nueva ronda de apuestas (inicia: {game.get_first_actor().upper()}) ---"
        ]

    current_hand_logs = logs.copy()

    
        
    player_allin = game.player_chips == 0
    bot_allin = game.bot_chips == 0
    bets_equal = game.player_current_bet == game.bot_current_bet
    if (player_allin or bot_allin) and bets_equal:
        current_hand_logs.append("Ambos jugadores están ALL IN o apuestas igualadas con all-in. Se revela todo y showdown.")
        return _resolve_showdown(current_hand_logs.copy())

        

    return jsonify({
        'player_hole': game.player_hole,
        'bot_hole': ["card_back", "card_back"],
        'community_cards': [],
        'pot': game.pot,
        'player_chips': game.player_chips,
        'bot_chips': game.bot_chips,
        'dealer': game.dealer,
        'street_index': game.street_index,
        'history': game.history,
        'to_act': game.get_first_actor(),
        'log': current_hand_logs.copy(),
        'hand_ended': False,
        'sb': game.small_blind,     # <--- AÑADIR
        'bb': game.big_blind        # <--- AÑADIR
        
    })


@app.route('/api/player_action', methods=['POST'])
def player_action():
    global game, current_hand_logs
    if game is None:
        return jsonify({'error': 'No hay juego activo.'}), 400

    data = request.get_json()
    actor = data.get('actor', 'player')

    def actuar_bot_si_toca():
        bot_action, bot_raise = game.bot_decide_action(trainer)
        to_call_bot = game.current_bet - game.bot_current_bet

        if bot_action == Action.FOLD and to_call_bot == 0:
            bot_action = Action.CALL
            bot_raise = None

        ended_bot = game.apply_action("bot", bot_action, raise_amount=bot_raise)

        if bot_action == Action.CALL and to_call_bot == 0:
            current_hand_logs.append("Bot hace CHECK.")
        elif bot_action == Action.CALL:
            current_hand_logs.append(f"Bot hace CALL de {to_call_bot} fichas.")
        elif bot_action == Action.FOLD:
            current_hand_logs.append("Bot se retira (FOLD).")
        elif bot_action in [Action.RAISE_SMALL, Action.RAISE_MEDIUM, Action.RAISE_LARGE]:
            current_hand_logs.append(f"Bot hace RAISE de {bot_raise} fichas (incluyendo call).")

        if ended_bot:
            current_hand_logs.append("Bot se retira. Tú ganas la mano.")
            return _end_hand_response(current_hand_logs.copy(), show_bot_cards=False)

        if (game.player_chips == 0 or game.bot_chips == 0) and \
           (game.player_current_bet == game.bot_current_bet):
            current_hand_logs.append("Ambos jugadores están ALL IN o apuestas igualadas con all-in. Se revela todo y showdown.")
            return _resolve_showdown(current_hand_logs.copy())

        return None

    if actor == 'bot':
        respuesta = actuar_bot_si_toca()
        if respuesta:
            return respuesta

        return jsonify({
            'player_hole': game.player_hole,
            'bot_hole': ["card_back", "card_back"],
            'community_cards': (
                (game.community_cards[:3] if game.street_index >= 1 else []) +
                (game.community_cards[3:4] if game.street_index >= 2 else []) +
                (game.community_cards[4:5] if game.street_index >= 3 else [])
            ),
            'pot': game.pot,
            'player_chips': game.player_chips,
            'bot_chips': game.bot_chips,
            'dealer': game.dealer,
            'street_index': game.street_index,
            'history': game.history,
            'to_act': "player",
            'log': current_hand_logs.copy(),
            'hand_ended': False,
            'sb': game.small_blind,
            'bb': game.big_blind
        })

    # Si actúa el jugador
    action_str = data.get('action')
    raise_amount = data.get('raise_amount')
    action = action_str_to_enum(action_str)
    if action is None:
        return jsonify({'error': 'Acción inválida'}), 400

    to_call = game.current_bet - game.player_current_bet
    player_logs = []
    ended = game.apply_action("player", action, raise_amount=raise_amount)

    if action == Action.CALL:
        if to_call == 0:
            player_logs.append("Player hace CHECK.")
        else:
            player_logs.append(f"Player hace CALL de {to_call} fichas.")
    elif action == Action.FOLD:
        player_logs.append("Player se retira (FOLD).")
    elif action in [Action.RAISE_SMALL, Action.RAISE_MEDIUM, Action.RAISE_LARGE]:
        total_raise = (to_call if to_call > 0 else 0) + raise_amount
        player_logs.append(f"Player hace RAISE de {total_raise} fichas (incluyendo call).")

    current_hand_logs.extend(player_logs)

    if ended:
        current_hand_logs.append("Jugador se retiró. Bot gana la mano.")
        return _end_hand_response(current_hand_logs.copy(), show_bot_cards=False)

    if (game.player_chips == 0 or game.bot_chips == 0) and \
       (game.player_current_bet == game.bot_current_bet):
        current_hand_logs.append("Ambos jugadores están ALL IN o apuestas igualadas con all-in. Se revela todo y showdown.")
        return _resolve_showdown(current_hand_logs.copy())

    def avanzar_street_y_posible_acción_bot():
        game.next_street()
        logs = ["Ronda de apuestas completada."]
        if game.street_index == 1:
            logs.append(f"Flop: {game.community_cards[:3]}")
        elif game.street_index == 2:
            logs.append(f"Turn: {game.community_cards[:4]}")
        elif game.street_index == 3:
            logs.append(f"River: {game.community_cards[:5]}")
        logs.append(format_chips())
        logs.append(f"--- Nueva ronda de apuestas (inicia: {game.get_first_actor().upper()}) ---")
        current_hand_logs.extend(logs)

        if (game.player_chips == 0 or game.bot_chips == 0) and \
           (game.player_current_bet == game.bot_current_bet):
            current_hand_logs.append("Ambos jugadores están ALL IN o apuestas igualadas con all-in. Se revela todo y showdown.")
            return _resolve_showdown(current_hand_logs.copy())

        if game.get_first_actor() == "bot":
            respuesta = actuar_bot_si_toca()
            if respuesta:
                return respuesta

        return jsonify({
            'player_hole': game.player_hole,
            'bot_hole': ["card_back", "card_back"],
            'community_cards': (
                (game.community_cards[:3] if game.street_index >= 1 else []) +
                (game.community_cards[3:4] if game.street_index >= 2 else []) +
                (game.community_cards[4:5] if game.street_index >= 3 else [])
            ),
            'pot': game.pot,
            'player_chips': game.player_chips,
            'bot_chips': game.bot_chips,
            'dealer': game.dealer,
            'street_index': game.street_index,
            'history': game.history,
            'to_act': "player",
            'log': current_hand_logs.copy(),
            'hand_ended': False,
            'sb': game.small_blind,
            'bb': game.big_blind
        })

    # ✅ DOBLE CHECK: avanzar si historia termina en 'cc' y no hay apuestas
    if game.current_bet == 0 and game.history.endswith('cc'):
        if game.street_index < 3:
            return avanzar_street_y_posible_acción_bot()
        else:
            current_hand_logs.append("Ronda de apuestas completada.")
            return _resolve_showdown(current_hand_logs.copy())

    # ✅ También cubrir CHECK-CHECK con CALL de 0
    # ✅ Avanza si se cumple: CHECK (CALL de 0) + otro CHECK anterior → fin de ronda
    # ✅ Avanza si:
# - Se han hecho dos CHECKs seguidos ('cc')
# - O el dealer es el bot y el jugador hace un CALL de 0 para igualar la BB
    if action == Action.CALL and to_call == 0 and game.current_bet == 0:
        is_check_check = len(game.history) >= 2 and game.history[-2:] == 'cc'
        is_bot_dealer_preflop = game.street_index == 0 and game.dealer == 'bot' and game.history == 'c'

        if is_check_check or is_bot_dealer_preflop:
            if game.street_index < 3:
                return avanzar_street_y_posible_acción_bot()
            else:
                current_hand_logs.append("Ronda de apuestas completada.")
                return _resolve_showdown(current_hand_logs.copy())



        # ✅ NO dejar que el bot actúe si preflop ya está cerrado correctamente
    preflop_cerrado_y_equilibrado = (
        game.street_index == 0 and
        game.dealer == "bot" and
        game.history == "cc" and
        game.player_current_bet == game.bot_current_bet
    )
    if preflop_cerrado_y_equilibrado:
        return avanzar_street_y_posible_acción_bot()

    respuesta = actuar_bot_si_toca()
    if respuesta:
        return respuesta

    if game.player_current_bet == game.bot_current_bet and len(game.history) >= 2:
        if game.street_index < 3:
            return avanzar_street_y_posible_acción_bot()
        else:
            current_hand_logs.append("Ronda de apuestas completada.")
            return _resolve_showdown(current_hand_logs.copy())

    if game.street_index == 4:
        return _resolve_showdown(current_hand_logs.copy())

    return jsonify({
        'player_hole': game.player_hole,
        'bot_hole': ["card_back", "card_back"],
        'community_cards': (
            (game.community_cards[:3] if game.street_index >= 1 else []) +
            (game.community_cards[3:4] if game.street_index >= 2 else []) +
            (game.community_cards[4:5] if game.street_index >= 3 else [])
        ),
        'pot': game.pot,
        'player_chips': game.player_chips,
        'bot_chips': game.bot_chips,
        'dealer': game.dealer,
        'street_index': game.street_index,
        'history': game.history,
        'to_act': "player",
        'log': current_hand_logs.copy(),
        'hand_ended': False,
        'sb': game.small_blind,
        'bb': game.big_blind
    })



@app.route('/api/last_stats', methods=['GET'])
def get_last_stats_api():
    """
    Llamamos a stats.get_last_stats() para:
      1) Leer y parsear last_hand.log,
      2) Calcular métricas,
      3) Generar recomendaciones de Nash.
    """
    try:
        response = stats.get_last_stats()
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _end_hand_response(all_logs, show_bot_cards=True):
    """
    Guarda el log completo de la mano en 'last_hand.log' y devuelve
    la respuesta JSON al frontend indicando que la mano ha terminado.
    """
    global game, current_hand_logs

    # Guardar 'last_hand.log' con todas las líneas de la mano
    try:
        with open('last_hand.log', 'w', encoding='utf-8') as f:
            for line in all_logs:
                f.write(line + "\n")
    except Exception as e:
        print("ERROR al guardar last_hand.log:", e)

    bot_cards = game.bot_hole if show_bot_cards else ["card_back", "card_back"]
    resp = {
        'player_hole': game.player_hole,
        'bot_hole': bot_cards,
        'community_cards': game.community_cards,
        'pot': game.pot,
        'player_chips': game.player_chips,
        'bot_chips': game.bot_chips,
        'dealer': game.dealer,
        'street_index': game.street_index,
        'history': game.history,
        'to_act': None,
        'log': all_logs,
        'hand_ended': True,
        'sb': game.small_blind,   # ✅ AÑADIR AQUÍ
        'bb': game.big_blind     
    }

    # Reiniciar variables para la próxima mano
    current_hand_logs = []
    return jsonify(resp)

def _resolve_showdown(logs_before):
    """
    Lógica común para resolver showdown (ya sea all-in o calle 4):
    - Revela comunitarias
    - Evalúa manos
    - Asigna fichas
    - Completa logs y responde
    """
    global game, current_hand_logs

    # 1) Revelar comunitarias restantes si hay
    if game.street_index < 3:
        game.reveal_remaining_community_cards()

    # 2) Evaluar manos
    player_best = game.evaluate_hand7(game.player_hole + game.community_cards)
    bot_best = game.evaluate_hand7(game.bot_hole + game.community_cards)

    player_desc = game.describe_hand(player_best)
    bot_desc = game.describe_hand(bot_best)

    contrib_player = game.player_contrib
    contrib_bot = game.bot_contrib
    main_contrib = min(contrib_player, contrib_bot)
    main_pot = main_contrib * 2
    side_pot = abs(contrib_player - contrib_bot)
    total_pot = main_pot + side_pot


    cmp = game.compare_hands(player_best, bot_best)

    showdown_logs = [
        "Showdown!",
        f"Tus cartas: {game.player_hole} + Comunidad: {game.community_cards}",
        f"Cartas del bot: {game.bot_hole} + Comunidad: {game.community_cards}",
        f"Tu mejor jugada: {player_desc}",
        f"Mejor jugada del bot: {bot_desc}",
        f"-- Reparto del pot: Main Pot={main_pot}, Side Pot={side_pot} (Total repartido: {main_pot + side_pot} fichas)"

    ]

    if cmp > 0:
        showdown_logs.append(f"¡Ganas la mano y te llevas el MAIN POT de {main_pot} fichas!")
        game.player_chips += main_pot
        if side_pot > 0:
            if contrib_player > contrib_bot:
                showdown_logs.append(f"El SIDE POT ({side_pot} fichas) lo ganas tú porque aportaste más.")
                game.player_chips += side_pot
            else:
                showdown_logs.append(f"El SIDE POT ({side_pot} fichas) retorna al bot.")
                game.bot_chips += side_pot
    elif cmp < 0:
        total_win = main_pot + side_pot
        showdown_logs.append(f"El bot gana la mano y se lleva MAIN+SIDE POT: {total_win} fichas.")
        game.bot_chips += total_win
    else:
        half_main = main_pot // 2
        showdown_logs.append(f"Empate. Se reparte MAIN POT: cada uno recibe {half_main} fichas.")
        game.player_chips += half_main
        game.bot_chips += half_main
        if side_pot > 0:
            showdown_logs.append(f"El SIDE POT ({side_pot} fichas) va al que aportó más.")
            if contrib_bot > contrib_player:
                game.bot_chips += side_pot
            else:
                game.player_chips += side_pot

    
    game.pot = 0
    showdown_logs.append(format_chips())
    current_hand_logs = logs_before + showdown_logs

    # Limpiar pot
    return _end_hand_response(current_hand_logs.copy(), show_bot_cards=True)

if __name__ == '__main__':
    app.run(debug=True)