from flask import Flask, request, jsonify, send_from_directory
import pickle
import stats
from practica2 import PokerGame, Action

app = Flask(__name__, static_folder='.')

# Carga del trainer entrenado (CFR)
with open('cfr_entreno.pkl', 'rb') as f:
    trainer = pickle.load(f)

game = None
current_hand_logs = []  # Acumula todas las líneas de la mano en curso

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
    global game, current_hand_logs
    game = PokerGame()
    started = game.start_hand()
    if not started:
        return jsonify({'error': 'No hay fichas para las blinds.'}), 400

    # Logs iniciales de la mano
    logs = [
        f"Dealer: {game.dealer} -> SB={game.small_blind}, BB={game.big_blind}",
        format_chips(),
        "=== Nueva mano ===",
        f"Dealer: {game.dealer.upper()}",
        f"Tus cartas: {game.player_hole}",
        format_chips(),
        f"--- Nueva ronda de apuestas (inicia: {game.get_first_actor().upper()}) ---"
    ]

    current_hand_logs = logs.copy()

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
        'hand_ended': False
    })

@app.route('/api/player_action', methods=['POST'])
def player_action():
    global game, current_hand_logs
    if game is None:
        return jsonify({'error': 'No hay juego activo.'}), 400

    data = request.json
    action_str = data.get('action')
    raise_amount = data.get('raise_amount')

    action = action_str_to_enum(action_str)
    if action is None:
        return jsonify({'error': 'Acción inválida'}), 400

    # 1) Acciones del jugador (usamos lista separada)
    player_logs = []
    ended = game.apply_action("player", action, raise_amount=raise_amount)

    if game.player_chips == 0 and not ended:
        player_logs.append("Player va ALL-IN!")

    if action == Action.CALL and (game.current_bet - game.player_current_bet) == 0:
        player_logs.append("Player hace CHECK.")
    elif action == Action.CALL:
        pay = game.current_bet - game.player_current_bet if game.current_bet - game.player_current_bet > 0 else 0
        player_logs.append(f"Player hace CALL de {pay} fichas.")
    elif action == Action.FOLD:
        player_logs.append("Player se retira (FOLD).")
    elif action == Action.RAISE_MEDIUM:
        total_raise = raise_amount + (game.current_bet - game.player_current_bet if game.current_bet - game.player_current_bet > 0 else 0)
        player_logs.append(f"Player hace RAISE de {total_raise} fichas (incluyendo call).")

    # Agregar solo los logs del jugador
    current_hand_logs.extend(player_logs)

    if ended:
        current_hand_logs.append("Jugador se retiró. Bot gana la mano.")
        return _end_hand_response(current_hand_logs.copy(), show_bot_cards=False)

    # 1.1) Detección de “check–check” en cualquier calle
    if game.current_bet == 0 and len(game.history) >= 2 and all(ch == 'c' for ch in game.history[-2:]):
        if game.street_index < 4:
            game.next_street()
            calles = ["Preflop", "Flop", "Turn", "River", "Showdown"]
            street_logs = [
                "Ronda de apuestas completada.",
                format_chips()
            ]
            if game.street_index < 4:
                street_logs.append(
                    f"{calles[game.street_index]}: "
                    f"{game.community_cards[:3] if game.street_index>=1 else []}"
                    f"{game.community_cards[3:4] if game.street_index>=2 else []}"
                    f"{game.community_cards[4:5] if game.street_index>=3 else []}"
                )
            street_logs.extend([
                format_chips(),
                f"--- Nueva ronda de apuestas (inicia: {game.get_first_actor().upper()}) ---"
            ])
            current_hand_logs.extend(street_logs)

        # Devolvemos estado actualizado sin invocar al bot esa ronda
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
            'to_act': "player",  # Aún le toca al jugador
            'log': current_hand_logs.copy(),
            'hand_ended': False
        })

    # --- Bloque a insertar: detección de CALL a RAISE del bot ---
    to_call = game.current_bet - game.player_current_bet
    if action == Action.CALL and to_call == 0 and game.history.endswith('r'):
        # Avanzar de ronda inmediatamente sin invocar al bot
        if game.street_index < 4:
            game.next_street()
            calles = ["Preflop", "Flop", "Turn", "River", "Showdown"]
            street_logs = [
                "Ronda de apuestas completada.",
                format_chips()
            ]
            if game.street_index < 4:
                street_logs.append(
                    f"{calles[game.street_index]}: "
                    f"{game.community_cards[:3] if game.street_index>=1 else []}"
                    f"{game.community_cards[3:4] if game.street_index>=2 else []}"
                    f"{game.community_cards[4:5] if game.street_index>=3 else []}"
                )
            street_logs.extend([
                format_chips(),
                f"--- Nueva ronda de apuestas (inicia: {game.get_first_actor().upper()}) ---"
            ])
            current_hand_logs.extend(street_logs)

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
            'hand_ended': False
        })
    # --- Fin bloque insertado ---

    # 2) Acción del bot (lista separada)
    bot_logs = []
    bot_action, bot_raise = game.bot_decide_action(trainer)

    bets_equal = (game.player_current_bet == game.bot_current_bet)
    if bot_action in [Action.RAISE_SMALL, Action.RAISE_MEDIUM, Action.RAISE_LARGE] and 'r' in game.history and bets_equal:
        bot_action = Action.CALL
        bot_raise = None

    to_call_bot = game.current_bet - game.bot_current_bet
    if bot_action == Action.FOLD and to_call_bot == 0:
        bot_action = Action.CALL
        bot_raise = None

    ended_bot = game.apply_action("bot", bot_action, raise_amount=bot_raise)

    if game.bot_chips == 0 and not ended_bot:
        bot_logs.append("Bot va ALL-IN!")

    if bot_action == Action.CALL and to_call_bot == 0:
        bot_logs.append("Bot hace CHECK.")
    elif bot_action == Action.CALL:
        pay = to_call_bot if to_call_bot > 0 else 0
        bot_logs.append(f"Bot hace CALL de {pay} fichas.")
    elif bot_action == Action.FOLD:
        bot_logs.append("Bot se retira (FOLD).")
    elif bot_action in [Action.RAISE_SMALL, Action.RAISE_MEDIUM, Action.RAISE_LARGE]:
        total_raise_bot = bot_raise if bot_raise else 0
        bot_logs.append(f"Bot hace RAISE de {total_raise_bot} fichas (incluyendo call).")

    # Agregar solo los logs del bot
    current_hand_logs.extend(bot_logs)

    if ended_bot:
        current_hand_logs.append("Bot se retira. Tú ganas la mano.")
        return _end_hand_response(current_hand_logs.copy(), show_bot_cards=False)

    # 3) Lógica de ALL-IN / avance de ronda tras acción del bot
    player_allin = (game.player_chips == 0)
    bot_allin = (game.bot_chips == 0)
    bets_equal = (game.player_current_bet == game.bot_current_bet)

    if (player_allin and bot_allin) or ((player_allin or bot_allin) and bets_equal):
        current_hand_logs.append("Ambos jugadores están ALL IN o apuestas igualadas con all-in. Se revela todo y showdown.")
        return _resolve_showdown(current_hand_logs.copy())

    # 3.2) Avanzar de ronda si bets igualadas y ambos han actuado (>= 2 acciones)
    bets_equal = (game.player_current_bet == game.bot_current_bet)
    if bets_equal and len(game.history) >= 2:
        if game.street_index < 4:
            game.next_street()
            calles = ["Preflop", "Flop", "Turn", "River", "Showdown"]
            street_logs = [
                "Ronda de apuestas completada.",
                format_chips()
            ]
            if game.street_index < 4:
                street_logs.append(
                    f"{calles[game.street_index]}: "
                    f"{game.community_cards[:3] if game.street_index>=1 else []}"
                    f"{game.community_cards[3:4] if game.street_index>=2 else []}"
                    f"{game.community_cards[4:5] if game.street_index>=3 else []}"
                )
            street_logs.extend([
                format_chips(),
                f"--- Nueva ronda de apuestas (inicia: {game.get_first_actor().upper()}) ---"
            ])
            current_hand_logs.extend(street_logs)

    # 4) Showdown normal en river si no hubo all-in
    if game.street_index == 4:
        return _resolve_showdown(current_hand_logs.copy())

    # 5) Si la mano continúa, devolvemos estado normal al frontend
    bot_cards_display = ["card_back", "card_back"]
    return jsonify({
        'player_hole': game.player_hole,
        'bot_hole': bot_cards_display,
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
        'hand_ended': False
    })

@app.route('/api/last_stats', methods=['GET'])
def get_last_stats():
    try:
        parsed = stats.parse_last_hand()
        metrics = stats.compute_metrics(parsed)
        recs    = stats.generate_recommendations(parsed, metrics)
        response = metrics.copy()
        response['recommendations'] = recs
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
        'hand_ended': True
    }

    # Reiniciar variables para la próxima mano
    game = None
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

    # 1) Revelar comunitarias restantes
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
    side_pot = (contrib_player + contrib_bot) - main_pot

    cmp = game.compare_hands(player_best, bot_best)

    showdown_logs = [
        "Showdown!",
        f"Tus cartas: {game.player_hole} + Comunidad: {game.community_cards}",
        f"Cartas del bot: {game.bot_hole} + Comunidad: {game.community_cards}",
        f"Tu mejor jugada: {player_desc}",
        f"Mejor jugada del bot: {bot_desc}",
        f"-- Pot total: {game.pot} fichas (Main Pot={main_pot}, Side Pot={side_pot})"
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

    showdown_logs.append(format_chips())
    current_hand_logs = logs_before + showdown_logs

    # Limpiar pot
    game.pot = 0
    return _end_hand_response(current_hand_logs.copy(), show_bot_cards=True)

if __name__ == '__main__':
    app.run(debug=True)
