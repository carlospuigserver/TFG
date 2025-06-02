# app.py

from flask import Flask, request, jsonify, render_template
import pickle

from practica import PokerGame
from poker_env import Action

# -----------------------------------------------------
# Configuramos Flask para servir archivos estáticos
# directamente desde la carpeta raíz y buscar plantillas
# también en la carpeta raíz.
# -----------------------------------------------------
app = Flask(
    __name__,
    static_folder='.',       # Sirve archivos estáticos desde el directorio actual
    static_url_path='',      # Sin prefijo; p. ej. /inicial.css servirá ./inicial.css
    template_folder='.'      # Las plantillas (render_template) se buscan en el directorio actual
)

# Cargamos el modelo CFR (pickle) una sola vez al iniciar la app
with open("cfr_entreno.pkl", "rb") as f:
    trainer = pickle.load(f)

# Almacén en memoria de partidas activas por session_id
games = {}

@app.route("/")
def index():
    # Al entrar a / devolvemos index.html (portada + loader + redirección)
    return render_template("index.html")

@app.route("/api/new_hand", methods=["POST"])
def new_hand():
    data = request.get_json()
    sid = data.get("session_id")
    if not sid:
        return jsonify({"error": "Falta session_id"}), 400

    # Creamos una nueva partida y guardamos el objeto PokerGame en el diccionario
    game = PokerGame()
    game.dealer = "player"  # El jugador es dealer la primera vez
    if not game.start_hand():
        return jsonify({"error": "No hay fichas para blinds"}), 400

    games[sid] = game

    return jsonify({
        "player_hole": game.player_hole,
        "community": [],
        "pot": game.pot,
        "player_chips": game.player_chips,
        "bot_chips": game.bot_chips,
        "current_bet": game.current_bet,
        "street_index": game.street_index,
        "history": game.history
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

    # Convertimos la cadena recibida a la enumeración Action correspondiente
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
        # El jugador se retiró (fold) o venció un all-in
        return jsonify({
            "result": "player_ended",
            "player_chips": game.player_chips,
            "bot_chips": game.bot_chips,
            "pot": game.pot
        })

    # 2) Ahora toca la acción del bot (usando el trainer cargado)
    bot_act, bot_raise_amt = game.bot_decide_action(trainer)
    termino_bot = game.apply_action("bot", bot_act, bot_raise_amt)
    if termino_bot:
        # El bot se retiró o ganó con all-in
        return jsonify({
            "result": "bot_ended",
            "bot_action": bot_act.name,
            "bot_raise_amount": bot_raise_amt,
            "player_chips": game.player_chips,
            "bot_chips": game.bot_chips,
            "pot": game.pot
        })

    # 3) La mano continúa; devolvemos estado parcial, incluidas las cartas comunitarias
    response = {
        "player_action": action_str,
        "bot_action": bot_act.name,
        "bot_raise_amount": bot_raise_amt,
        "pot": game.pot,
        "player_chips": game.player_chips,
        "bot_chips": game.bot_chips,
        "current_bet": game.current_bet,
        "street_index": game.street_index,
        "history": game.history
    }

    # Según en qué calle estemos, incluimos las cartas comunitarias
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
    # Ejecutamos el servidor en 0.0.0.0:5000 (visible en localhost)
    app.run(host="0.0.0.0", port=5000, debug=True)
