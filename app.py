# ---------------------------------
# app.py (solo mostramos las rutas)
# ---------------------------------
from flask import Flask, request, jsonify, render_template
import pickle

from practica import PokerGame
from poker_env import Action

app = Flask(
    __name__,
    static_folder='.',
    static_url_path='',
    template_folder='.'
)

# Cargamos el trainer CFR al comienzo
with open("cfr_entreno.pkl", "rb") as f:
    trainer = pickle.load(f)

# Almacenaremos las partidas en memoria, indexadas por session_id
games = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/new_hand", methods=["POST"])
def new_hand():
    data = request.get_json()
    sid = data.get("session_id")
    if not sid:
        return jsonify({"error": "Falta session_id"}), 400

    game = PokerGame()
    game.dealer = "player"    # Empezamos con el jugador como dealer
    if not game.start_hand():
        return jsonify({"error": "No hay fichas para blinds"}), 400

    games[sid] = game

    # Determinar quién actúa primero en esta mano
    first_actor = game.get_first_actor()

    return jsonify({
        "player_hole": game.player_hole,
        "community": [],
        "pot": game.pot,
        "player_chips": game.player_chips,
        "bot_chips": game.bot_chips,
        "current_bet": game.current_bet,
        "street_index": game.street_index,
        "history": game.history,
        "dealer": game.dealer,           # le indicamos al front-end quién es dealer
        "to_act": first_actor            # y quién comienza la ronda
    })

@app.route("/api/player_action", methods=["POST"])
def player_action():
    data = request.get_json()
    sid = data.get("session_id")
    action_str = data.get("action")
    raise_amt = data.get("raise_amount")

    if sid not in games:
        return jsonify({"error": "Sesión no encontrada"}), 404

    game = games[sid]

    # Convertimos la cadena a la enumeración Action
    if action_str == "fold":
        act = Action.FOLD
    elif action_str == "call":
        act = Action.CALL
    elif action_str == "raise":
        act = Action.RAISE_MEDIUM
    else:
        return jsonify({"error": "Acción inválida"}), 400

    # 1) Aplica la acción del jugador
    termino = game.apply_action("player", act, raise_amt)
    if termino:
        # El jugador se plegó o el all-in terminó la mano
        return jsonify({
            "result": "player_ended",
            "player_chips": game.player_chips,
            "bot_chips": game.bot_chips,
            "pot": game.pot,
            "dealer": game.dealer,
            # En este caso final de mano, podemos revelar las hole cards del bot
            "bot_hole": game.bot_hole
        })

    # 2) Toca al bot (usando el trainer CFR)
    bot_act, bot_raise_amt = game.bot_decide_action(trainer)
    termino_bot = game.apply_action("bot", bot_act, bot_raise_amt)
    if termino_bot:
        # El bot se plegó o ganó con all-in
        return jsonify({
            "result": "bot_ended",
            "bot_action": bot_act.name,
            "bot_raise_amount": bot_raise_amt,
            "player_chips": game.player_chips,
            "bot_chips": game.bot_chips,
            "pot": game.pot,
            "dealer": game.dealer,
            "bot_hole": game.bot_hole
        })

    # 3) La mano continúa: devolvemos estado parcial + cartas comunitarias si pasamos a flop/turn/river
    #    También informamos “dealer” y “to_act” (quién actúa a continuación)
    next_actor = game.get_first_actor()

    response = {
        "player_action": action_str,
        "bot_action": bot_act.name,
        "bot_raise_amount": bot_raise_amt,
        "pot": game.pot,
        "player_chips": game.player_chips,
        "bot_chips": game.bot_chips,
        "current_bet": game.current_bet,
        "street_index": game.street_index,
        "history": game.history,
        "dealer": game.dealer,
        "to_act": next_actor
    }

    # Si estamos en flop/turn/river, incluimos las cartas comunitarias correspondientes
    if game.street_index == 1:
        response["community"] = game.community_cards[:3]
    elif game.street_index == 2:
        response["community"] = game.community_cards[:4]
    elif game.street_index == 3:
        response["community"] = game.community_cards[:5]
    else:
        response["community"] = []

    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
