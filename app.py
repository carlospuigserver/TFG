from flask import Flask, request, jsonify, send_from_directory
import pickle
from practica import PokerGame, Action

app = Flask(__name__, static_folder='.')

with open('cfr_entreno.pkl', 'rb') as f:
    trainer = pickle.load(f)

game = None  # estado global simple (mejor usar sesiones en producción)

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
    global game
    game = PokerGame()
    started = game.start_hand()
    if not started:
        return jsonify({'error': 'No hay fichas para las blinds.'}), 400

    logs = [
        f"Dealer: {game.dealer} -> SB={game.small_blind}, BB={game.big_blind}",
        format_chips(),
        "=== Nueva mano ===",
        f"Dealer: {game.dealer.upper()}",
        f"Tus cartas: {game.player_hole}",
        format_chips(),
        f"--- Nueva ronda de apuestas (inicia: {game.get_first_actor().upper()}) ---"
    ]

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
        'log': logs,
        'hand_ended': False
    })

@app.route('/api/player_action', methods=['POST'])
def player_action():
    global game
    if game is None:
        return jsonify({'error': 'No hay juego activo.'}), 400

    data = request.json
    action_str = data.get('action')
    raise_amount = data.get('raise_amount')

    action = action_str_to_enum(action_str)
    if action is None:
        return jsonify({'error': 'Acción inválida'}), 400

    # Bloquear re-raises del jugador en la ronda actual (solo un raise permitido)
    if action == Action.RAISE_MEDIUM and 'r' in game.history:
        return jsonify({'error': 'No se permite hacer reraise en esta ronda.'}), 400

    logs = []

    # Acción jugador
    ended = game.apply_action("player", action, raise_amount=raise_amount)
    if action == Action.CALL and (game.current_bet - game.player_current_bet) == 0:
        logs.append(f"Player hace CHECK.")
    elif action == Action.CALL:
        pay = game.current_bet - game.player_current_bet if game.current_bet - game.player_current_bet > 0 else 0
        logs.append(f"Player hace CALL de {pay} fichas.")
    elif action == Action.FOLD:
        logs.append("Player se retira (FOLD).")
    elif action == Action.RAISE_MEDIUM:
        total_raise = raise_amount + (game.current_bet - game.player_current_bet if game.current_bet - game.player_current_bet > 0 else 0)
        logs.append(f"Player hace RAISE de {total_raise} fichas (incluyendo call).")

    if ended:
        logs.append("Jugador se retiró. Bot gana la mano.")
        return _end_hand_response(logs, show_bot_cards=False)

    # Acción bot
    bot_action, bot_raise = game.bot_decide_action(trainer)

    # Bloquear re-raises del bot si ya hubo raise en ronda actual
    if bot_action in [Action.RAISE_SMALL, Action.RAISE_MEDIUM, Action.RAISE_LARGE] and 'r' in game.history:
        bot_action = Action.CALL
        bot_raise = None

    # Permitir check al bot (call de 0 fichas)
    to_call_bot = game.current_bet - game.bot_current_bet
    if bot_action == Action.FOLD and to_call_bot == 0:
        bot_action = Action.CALL
        bot_raise = None

    ended_bot = game.apply_action("bot", bot_action, raise_amount=bot_raise)

    if bot_action == Action.CALL and to_call_bot == 0:
        logs.append("Bot hace CHECK.")
    elif bot_action == Action.CALL:
        pay = to_call_bot if to_call_bot > 0 else 0
        logs.append(f"Bot hace CALL de {pay} fichas.")
    elif bot_action == Action.FOLD:
        logs.append("Bot se retira (FOLD).")
    elif bot_action in [Action.RAISE_SMALL, Action.RAISE_MEDIUM, Action.RAISE_LARGE]:
        total_raise_bot = bot_raise if bot_raise else 0
        logs.append(f"Bot hace RAISE de {total_raise_bot} fichas (incluyendo call).")

    if ended_bot:
        logs.append("Bot se retiró. Tú ganas la mano.")
        return _end_hand_response(logs, show_bot_cards=False)

    # Verificar si ronda de apuestas terminó: ambos actuaron e igualaron apuestas
    bets_equal = (game.player_current_bet == game.bot_current_bet)
    both_acted = ('c' in game.history or 'r' in game.history)  # al menos un call o raise
    if bets_equal and both_acted:
        # Avanzar calle si no estamos en showdown
        if game.street_index < 4:
            game.next_street()
            calles = ["Preflop", "Flop", "Turn", "River", "Showdown"]
            logs.append(f"Ronda de apuestas completada.")
            logs.append(format_chips())
            if game.street_index < 4:
                logs.append(f"{calles[game.street_index]}: {game.community_cards[:3] if game.street_index>=1 else []}{game.community_cards[3:4] if game.street_index>=2 else []}{game.community_cards[4:5] if game.street_index>=3 else []}")
            logs.append(format_chips())
            logs.append(f"--- Nueva ronda de apuestas (inicia: {game.get_first_actor().upper()}) ---")

    # Showdown
    if game.street_index == 4:
        game.showdown()
        logs.append("Showdown!")
        logs.append(f"Tus cartas: {game.player_hole}")
        logs.append(f"Cartas bot: {game.bot_hole}")
        return _end_hand_response(logs, show_bot_cards=True)

    # Mostrar cartas bot tapadas salvo showdown y fold
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
        'log': logs,
        'hand_ended': False
    })

def _end_hand_response(logs, show_bot_cards=True):
    global game
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
        'log': logs,
        'hand_ended': True
    }
    game = None
    return jsonify(resp)

if __name__ == '__main__':
    app.run(debug=True)
