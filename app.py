from flask import Flask, request, jsonify, send_from_directory
import pickle
from practica import PokerGame, Action

app = Flask(__name__, static_folder='.')

with open('cfr_entreno.pkl', 'rb') as f:
    trainer = pickle.load(f)

game = None

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

    if action == Action.RAISE_MEDIUM and 'r' in game.history:
        return jsonify({'error': 'No se permite hacer reraise en esta ronda.'}), 400

    logs = []

    # Acción del jugador
    ended = game.apply_action("player", action, raise_amount=raise_amount)

    # Detectar all-in jugador
    if game.player_chips == 0 and not ended:
        logs.append("Player va ALL-IN!")

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

    # Acción del bot
    bot_action, bot_raise = game.bot_decide_action(trainer)

    if bot_action in [Action.RAISE_SMALL, Action.RAISE_MEDIUM, Action.RAISE_LARGE] and 'r' in game.history:
        bot_action = Action.CALL
        bot_raise = None

    to_call_bot = game.current_bet - game.bot_current_bet
    if bot_action == Action.FOLD and to_call_bot == 0:
        bot_action = Action.CALL
        bot_raise = None

    ended_bot = game.apply_action("bot", bot_action, raise_amount=bot_raise)

    # Detectar all-in bot
    if game.bot_chips == 0 and not ended_bot:
        logs.append("Bot va ALL-IN!")

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

    # --- Lógica de manejo de ALL-IN ---
    player_allin = (game.player_chips == 0)
    bot_allin = (game.bot_chips == 0)
    bets_equal = (game.player_current_bet == game.bot_current_bet)

    # Caso: ambos all-in o uno all-in con apuestas igualadas -> Revelar cartas y showdown
    if (player_allin and bot_allin) or ((player_allin or bot_allin) and bets_equal):
        logs.append("Ambos jugadores están ALL IN o apuestas igualadas con all-in. Se revela todo y showdown.")
        game.reveal_remaining_community_cards()
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

        logs.append("Showdown!")
        logs.append(f"Tus cartas: {game.player_hole} + Comunidad: {game.community_cards}")
        logs.append(f"Cartas del bot: {game.bot_hole} + Comunidad: {game.community_cards}")
        logs.append(f"Tu mejor jugada: {player_desc}")
        logs.append(f"Mejor jugada del bot: {bot_desc}")
        logs.append(f"-- Pot total: {game.pot} fichas (Main Pot={main_pot}, Side Pot={side_pot})")

        if cmp > 0:
            logs.append(f"¡Ganas la mano y te llevas el MAIN POT de {main_pot} fichas!")
            game.player_chips += main_pot
            if side_pot > 0:
                if contrib_player > contrib_bot:
                    logs.append(f"El SIDE POT ({side_pot} fichas) lo ganas tú porque aportaste más.")
                    game.player_chips += side_pot
                else:
                    logs.append(f"El SIDE POT ({side_pot} fichas) retorna al bot.")
                    game.bot_chips += side_pot
            winner = "player"
        elif cmp < 0:
            total_win = main_pot + side_pot
            logs.append(f"El bot gana la mano y se lleva MAIN+SIDE POT: {total_win} fichas.")
            game.bot_chips += total_win
            winner = "bot"
        else:
            half_main = main_pot // 2
            logs.append(f"Empate. Se reparte MAIN POT: cada uno recibe {half_main} fichas.")
            game.player_chips += half_main
            game.bot_chips += half_main
            if side_pot > 0:
                logs.append(f"El SIDE POT ({side_pot} fichas) va al que aportó más.")
                if contrib_bot > contrib_player:
                    game.bot_chips += side_pot
                else:
                    game.player_chips += side_pot
            winner = "tie"

        logs.append(format_chips())

        game.pot = 0

        return _end_hand_response(logs, show_bot_cards=True)

    # Continuar la mano normalmente
    bets_equal = (game.player_current_bet == game.bot_current_bet)
    both_acted = ('c' in game.history or 'r' in game.history)
    if bets_equal and both_acted:
        if game.street_index < 4:
            game.next_street()
            calles = ["Preflop", "Flop", "Turn", "River", "Showdown"]
            logs.append(f"Ronda de apuestas completada.")
            logs.append(format_chips())
            if game.street_index < 4:
                logs.append(f"{calles[game.street_index]}: "
                            f"{game.community_cards[:3] if game.street_index>=1 else []}"
                            f"{game.community_cards[3:4] if game.street_index>=2 else []}"
                            f"{game.community_cards[4:5] if game.street_index>=3 else []}")
            logs.append(format_chips())
            logs.append(f"--- Nueva ronda de apuestas (inicia: {game.get_first_actor().upper()}) ---")

    # Showdown normal en river si no hubo all-in
    if game.street_index == 4:
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

        logs.append("Showdown!")
        logs.append(f"Tus cartas: {game.player_hole} + Comunidad: {game.community_cards}")
        logs.append(f"Cartas del bot: {game.bot_hole} + Comunidad: {game.community_cards}")
        logs.append(f"Tu mejor jugada: {player_desc}")
        logs.append(f"Mejor jugada del bot: {bot_desc}")
        logs.append(f"-- Pot total: {game.pot} fichas (Main Pot={main_pot}, Side Pot={side_pot})")

        if cmp > 0:
            logs.append(f"¡Ganas la mano y te llevas el MAIN POT de {main_pot} fichas!")
            game.player_chips += main_pot
            if side_pot > 0:
                if contrib_player > contrib_bot:
                    logs.append(f"El SIDE POT ({side_pot} fichas) lo ganas tú porque aportaste más.")
                    game.player_chips += side_pot
                else:
                    logs.append(f"El SIDE POT ({side_pot} fichas) retorna al bot.")
                    game.bot_chips += side_pot
            winner = "player"
        elif cmp < 0:
            total_win = main_pot + side_pot
            logs.append(f"El bot gana la mano y se lleva MAIN+SIDE POT: {total_win} fichas.")
            game.bot_chips += total_win
            winner = "bot"
        else:
            half_main = main_pot // 2
            logs.append(f"Empate. Se reparte MAIN POT: cada uno recibe {half_main} fichas.")
            game.player_chips += half_main
            game.bot_chips += half_main
            if side_pot > 0:
                logs.append(f"El SIDE POT ({side_pot} fichas) va al que aportó más.")
                if contrib_bot > contrib_player:
                    game.bot_chips += side_pot
                else:
                    game.player_chips += side_pot
            winner = "tie"

        logs.append(format_chips())

        game.pot = 0

        return _end_hand_response(logs, show_bot_cards=True)

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
