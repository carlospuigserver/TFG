# ---------------------------------
# app.py (solo mostramos las rutas, con logs “a la consola” reconstruidos)
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

    # Creamos la nueva partida y alternamos dealer internamente
    game = PokerGame()
    game.dealer = "player"    # forzamos que empiece “player”, pero start_hand() invierte
    if not game.start_hand():
        return jsonify({"error": "No hay fichas para blinds"}), 400

    games[sid] = game

    # Reconstruimos en una lista “logs” todos los prints que `practica.py` habría hecho en consola:
    logs = []

    # 1) Mensaje de postura de blinds
    sb = game.small_blind
    bb = game.big_blind
    if game.dealer == "bot":
        # En práctica: “Dealer: Bot -> SB=10, Jugador -> BB=20”
        logs.append(f"Dealer: Bot -> SB={sb}, Jugador -> BB={bb}")
    else:
        # teórico en caso contrario (no ocurre la primera mano, pero lo dejamos por consistencia)
        logs.append(f"Dealer: Jugador -> SB={sb}, Bot -> BB={bb}")

    # 2) Chip counts tras blinds (print_chip_counts)
    logs.append(f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}")

    # 3) Inicio de mano
    logs.append("")  # línea en blanco para separar
    logs.append("=== Nueva mano ===")
    logs.append(f"Dealer: {game.dealer.upper()}")
    logs.append(f"Tus cartas: {game.player_hole}")

    # ¿Quién actúa primero?
    first_actor = game.get_first_actor()

    # Devolvemos la respuesta inicial, con logs, hole cards del jugador y zeros en comunidad
    return jsonify({
        "logs": logs,
        "player_hole": game.player_hole,
        "community": [],
        "pot": game.pot,
        "player_chips": game.player_chips,
        "bot_chips": game.bot_chips,
        "current_bet": game.current_bet,
        "street_index": game.street_index,
        "history": game.history,
        "dealer": game.dealer,
        "to_act": first_actor
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

    # Vamos a ir guardando en “logs” exactamente lo que, en modo consola, `practica.py` mostraba.
    logs = []

    # 0) Detectar si acabamos de iniciar una nueva ronda (preflop salvo blinds, o flop, o turn, o river).
    # En práctica, al empezar cada “betting_round” imprimen: 
    #     "\n--- Nueva ronda de apuestas (inicia: {WHO}) ---"
    # Nosotros diremos que arrancamos ronda cada vez que player_current_bet==0 y bot_current_bet==0:
    if game.player_current_bet == 0 and game.bot_current_bet == 0:
        starter = game.get_first_actor().upper()
        logs.append(f"--- Nueva ronda de apuestas (inicia: {starter}) ---")

    # 1) Convertimos la cadena a la enumeración Action
    if action_str == "fold":
        act = Action.FOLD
    elif action_str == "call":
        act = Action.CALL
    elif action_str == "raise":
        act = Action.RAISE_MEDIUM
    else:
        return jsonify({"error": "Acción inválida"}), 400

    # 2) Primero, “loguear” la acción del jugador (tal cual se haría en consola).
    #    Para reproducir “Player hace CHECK/CALL/RAISE” como lo hace `practica.py.apply_action`.
    to_call_p = game.current_bet - game.player_current_bet  # cuánto debe pagar para igualar
    if act == Action.FOLD:
        logs.append("Player se retira (FOLD).")
    elif act == Action.CALL:
        pay = min(to_call_p, game.player_chips)
        if pay == 0:
            logs.append("Player hace CHECK.")
        else:
            logs.append(f"Player hace CALL de {pay} fichas.")
    else:  # Action.RAISE_MEDIUM (en tu front siempre lo llamas como “raise” con monto explícito)
        # En práctica: total_put = to_call + raise_amount; cap al stack
        total_put = to_call_p + (raise_amt if raise_amt is not None else 0)
        total_put = min(total_put, game.player_chips)
        logs.append(f"Player hace RAISE de {total_put} fichas (incluyendo call).")

    # 3) Aplicamos la acción del jugador
    termino = game.apply_action("player", act, raise_amt)
    if termino:
        # El jugador se plegó o el all-in terminó la mano. En práctica retorna inmediatamente “player_ended”.
        # Retrasmitimos logs y devolvemos resultado final:
        return jsonify({
            "logs": logs,
            "result": "player_ended",
            "player_chips": game.player_chips,
            "bot_chips": game.bot_chips,
            "pot": game.pot,
            "dealer": game.dealer,
            "bot_hole": game.bot_hole
        })

    # 4) Ahora, “turno del bot”. Primero calculamos qué decide el bot:
    bot_act, bot_raise_amt = game.bot_decide_action(trainer)

    # 5) Log “Bot decide X con raise_amount=Y”
    logs.append(f"Bot decide {bot_act.name} con raise_amount={bot_raise_amt}")

    #    Para reproducir “Bot hace CHECK/CALL/RAISE” como lo hace apply_action:
    to_call_b = game.current_bet - game.bot_current_bet
    if bot_act == Action.FOLD:
        # Si decide fold y no hay nada que pagar, en consola haría “Bot decide FOLD pero es CHECK (no hay nada que pagar).” 
        # Para simplificar, asumimos “Bot hace CHECK.” si to_call_b==0, o “Bot se retira (FOLD).” si to_call_b>0
        if to_call_b == 0:
            logs.append("Bot hace CHECK.")
        else:
            logs.append("Bot se retira (FOLD).")
    elif bot_act == Action.CALL:
        pay_b = min(to_call_b, game.bot_chips)
        if pay_b == 0:
            logs.append("Bot hace CHECK.")
        else:
            logs.append(f"Bot hace CALL de {pay_b} fichas.")
    else:
        # RAISE_SMALL, RAISE_MEDIUM o RAISE_LARGE: 
        total_put_b = to_call_b + (bot_raise_amt if bot_raise_amt is not None else 0)
        total_put_b = min(total_put_b, game.bot_chips)
        logs.append(f"Bot hace RAISE de {total_put_b} fichas (incluyendo call).")

    # 6) Aplicamos la acción del bot
    termino_bot = game.apply_action("bot", bot_act, bot_raise_amt)
    if termino_bot:
        # El bot se plegó o ganó con all-in
        return jsonify({
            "logs": logs,
            "result": "bot_ended",
            "bot_action": bot_act.name,
            "bot_raise_amount": bot_raise_amt,
            "player_chips": game.player_chips,
            "bot_chips": game.bot_chips,
            "pot": game.pot,
            "dealer": game.dealer,
            "bot_hole": game.bot_hole
        })

    # 7) Ahora, justo después de aplicar ambas acciones, comprobamos si ambas apuestas se han igualado.
    #    En práctica, al igualarse se imprime “Ronda de apuestas completada.” + chip counts, y luego se invoca next_street()
    if game.player_current_bet == game.bot_current_bet:
        logs.append("Ronda de apuestas completada.")
        logs.append(f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}")

        # Avanzamos de calle
        game.next_street()

        # Dependiendo de la nueva street_index, sacamos flop/turn/river o showdown
        si = game.street_index
        if si == 1:
            # Flop
            logs.append(f"Flop: {game.community_cards[:3]}")
            logs.append(f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}")
        elif si == 2:
            # Turn
            logs.append(f"Turn: {game.community_cards[3]}")
            logs.append(f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}")
        elif si == 3:
            # River
            logs.append(f"River: {game.community_cards[4]}")
            logs.append(f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}")
        elif si == 4:
            # Showdown
            logs.append("Showdown!")
            # ------------- Reconstruir showdown EXACTO de práctica.py -------------
            # 1) Describir manos de 7 cartas
            player_best = game.evaluate_hand7(game.player_hole + game.community_cards)
            bot_best = game.evaluate_hand7(game.bot_hole + game.community_cards)

            logs.append(f"Tus cartas: {game.player_hole} + Comunidad: {game.community_cards}")
            logs.append(f"Cartas del bot: {game.bot_hole} + Comunidad: {game.community_cards}")
            logs.append(f"Tu mejor jugada: {game.describe_hand(player_best)}")
            logs.append(f"Mejor jugada del bot: {game.describe_hand(bot_best)}")

            # 2) Contribuciones y pots
            contrib_p = game.player_contrib
            contrib_b = game.bot_contrib
            main_contrib = min(contrib_p, contrib_b)
            main_pot = main_contrib * 2
            side_pot = (contrib_p + contrib_b) - main_pot
            logs.append(f"-- Pot total: {game.pot} fichas (Main Pot={main_pot}, Side Pot={side_pot})")

            # 3) Quién gana
            cmp = game.compare_hands(player_best, bot_best)
            if cmp > 0:
                # Player gana main pot
                logs.append(f"¡Ganas la mano y te llevas el MAIN POT de {main_pot} fichas!")
                game.player_chips += main_pot
                if side_pot > 0:
                    if contrib_p > contrib_b:
                        logs.append(f"El SIDE POT ({side_pot} fichas) lo ganas tú porque aportaste más.")
                        game.player_chips += side_pot
                    else:
                        logs.append(f"El SIDE POT ({side_pot} fichas) retorna al bot.")
                        game.bot_chips += side_pot
            elif cmp < 0:
                total_win = main_pot + side_pot
                logs.append(f"El bot gana la mano y se lleva MAIN+SIDE POT: {total_win} fichas.")
                game.bot_chips += total_win
            else:
                half_main = main_pot // 2
                logs.append(f"Empate. Se reparte MAIN POT: cada uno recibe {half_main} fichas.")
                game.player_chips += half_main
                game.bot_chips += half_main
                if side_pot > 0:
                    logs.append(f"El SIDE POT ({side_pot} fichas) va al que aportó más.")
                    if contrib_b > contrib_p:
                        game.bot_chips += side_pot
                    else:
                        game.player_chips += side_pot

            # 4) Limpiar pot y mostrar stacks finales
            game.pot = 0
            logs.append(f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}")
            # ------------------------------------------------------------------------

    # 8) A estas alturas, la mano sigue (o acabamos de hacer showdown). Construimos la respuesta.
    next_actor = game.get_first_actor()

    # Según la calle en que estemos (0=preflop,1=flop,2=turn,3=river,4=showdown),
    # devolvemos el array apropiado de comunidad.
    if game.street_index == 1:
        comm = game.community_cards[:3]
    elif game.street_index == 2:
        comm = game.community_cards[:4]
    elif game.street_index == 3:
        comm = game.community_cards[:5]
    else:
        comm = []  # en showdown dejamos vacío (ya mostramos todo en logs)

    response = {
        "logs": logs,
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
        "to_act": next_actor,
        "community": comm
    }

    # Si acabamos de hacer showdown, conviene enviar también las hole cards del bot:
    if game.street_index == 4:
        response["bot_hole"] = game.bot_hole

    return jsonify(response)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
