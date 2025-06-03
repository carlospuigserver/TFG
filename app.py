# ---------------------------------
# app.py (sin reraise, reinicio de stacks, rotación de dealer, CHECK–CHECK detectado correctamente)
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

# Almacenaremos las partidas activas en memoria, indexadas por session_id
games = {}

# Stack inicial para ambos jugadores
INITIAL_STACK = 1000

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/new_hand", methods=["POST"])
def new_hand():
    data = request.get_json()
    sid = data.get("session_id")
    if not sid:
        return jsonify({"error": "Falta session_id"}), 400

    # Si es la primera mano de esta sesión, creamos el PokerGame y forzamos dealer="player"
    if sid not in games:
        game = PokerGame()
        game.dealer = "player"
        games[sid] = game
    else:
        game = games[sid]
        # Si alguno llegó a 0 fichas, reiniciamos ambos stacks a 1000
        if game.player_chips == 0 or game.bot_chips == 0:
            game.player_chips = INITIAL_STACK
            game.bot_chips = INITIAL_STACK
        # En cualquier otro caso, reutilizamos la misma instancia (se arrastran las pilas restantes)

    # Llamamos start_hand() para alternar dealer, barajar, repartir y publicar blinds
    if not game.start_hand():
        return jsonify({"error": "No hay fichas para blinds"}), 400

    # Reconstruimos “logs” tal cual lo imprimiría practica.py
    logs = []
    sb = game.small_blind
    bb = game.big_blind
    if game.dealer == "bot":
        logs.append(f"Dealer: Bot -> SB={sb}, Jugador -> BB={bb}")
    else:
        logs.append(f"Dealer: Jugador -> SB={sb}, Bot -> BB={bb}")

    logs.append(f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}")
    logs.append("")
    logs.append("=== Nueva mano ===")
    logs.append(f"Dealer: {game.dealer.upper()}")
    logs.append(f"Tus cartas: {game.player_hole}")

    first_actor = game.get_first_actor()

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
    logs = []

    # 0) Si arrancamos una nueva ronda de apuestas (player_current_bet == bot_current_bet == 0)
    if game.player_current_bet == 0 and game.bot_current_bet == 0:
        starter = game.get_first_actor().upper()
        logs.append(f"--- Nueva ronda de apuestas (inicia: {starter}) ---")

    # 1) Convertimos la string a la enumeración Action
    if action_str == "fold":
        act = Action.FOLD
    elif action_str == "call":
        act = Action.CALL
    elif action_str == "raise":
        act = Action.RAISE_MEDIUM
    else:
        return jsonify({"error": "Acción inválida"}), 400

    # 2) Loguear texto exacto de la acción del jugador
    to_call_p = game.current_bet - game.player_current_bet
    if act == Action.FOLD:
        player_action_str = "FOLD"
        logs.append("Player se retira (FOLD).")
    elif act == Action.CALL:
        pay = min(to_call_p, game.player_chips)
        if pay == 0:
            player_action_str = "CHECK"
            logs.append("Player hace CHECK.")
        else:
            player_action_str = "CALL"
            logs.append(f"Player hace CALL de {pay} fichas.")
    else:  # Action.RAISE_MEDIUM
        total_put = to_call_p + (raise_amt if raise_amt is not None else 0)
        total_put = min(total_put, game.player_chips)
        player_action_str = "RAISE"
        logs.append(f"Player hace RAISE de {total_put} fichas (incluyendo call).")

    # 3) Aplicar la acción del jugador
    termino = game.apply_action("player", act, raise_amt)
    if termino:
        # El jugador se plegó o hizo all-in que terminó la mano
        pot_before = game.pot
        response = {
            "logs": logs,
            "result": "player_ended",
            "player_chips": game.player_chips,
            "bot_chips": game.bot_chips,
            "pot": pot_before,
            "dealer": game.dealer,
            "bot_hole": game.bot_hole
        }
        game.pot = 0
        return jsonify(response)

    # 4) Detectar cierre de ronda en caso de “player hizo CALL a un bet abierto (to_call_p > 0)”
    #    o bien “player hizo CHECK (to_call_p == 0) pero el bot más adelante también haga CHECK”.
    #    Aquí, primero comprobamos si el jugador igualó un bet abierto:
    if act == Action.CALL and to_call_p > 0:
        logs.append("Ronda de apuestas completada.")
        logs.append(f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}")

        game.next_street()
        si = game.street_index

        if si <= 3:
            if si == 1:
                logs.append(f"Flop: {game.community_cards[:3]}")
            elif si == 2:
                logs.append(f"Turn: {game.community_cards[3]}")
            elif si == 3:
                logs.append(f"River: {game.community_cards[4]}")
            logs.append(f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}")

            response = {
                "logs": logs,
                "result": "new_street",
                "pot": game.pot,
                "player_chips": game.player_chips,
                "bot_chips": game.bot_chips,
                "current_bet": game.current_bet,
                "street_index": game.street_index,
                "history": game.history,
                "dealer": game.dealer,
                "to_act": game.get_first_actor(),
                "community": game.community_cards[: (3 if si == 1 else 4 if si == 2 else 5)]
            }
            return jsonify(response)
        else:
            # showdown (si == 4)
            logs.append("Showdown!")
            player_best = game.evaluate_hand7(game.player_hole + game.community_cards)
            bot_best = game.evaluate_hand7(game.bot_hole + game.community_cards)

            logs.append(f"Tus cartas: {game.player_hole} + Comunidad: {game.community_cards}")
            logs.append(f"Cartas del bot: {game.bot_hole} + Comunidad: {game.community_cards}")
            logs.append(f"Tu mejor jugada: {game.describe_hand(player_best)}")
            logs.append(f"Mejor jugada del bot: {game.describe_hand(bot_best)}")

            contrib_p = game.player_contrib
            contrib_b = game.bot_contrib
            main_contrib = min(contrib_p, contrib_b)
            main_pot = main_contrib * 2
            side_pot = (contrib_p + contrib_b) - main_pot
            logs.append(f"-- Pot total: {game.pot} fichas (Main Pot={main_pot}, Side Pot={side_pot})")

            cmp = game.compare_hands(player_best, bot_best)
            if cmp > 0:
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

            pot_before = game.pot
            game.pot = 0
            logs.append(f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}")

            response = {
                "logs": logs,
                "result": "showdown",
                "player_chips": game.player_chips,
                "bot_chips": game.bot_chips,
                "pot": pot_before,
                "dealer": game.dealer,
                "bot_hole": game.bot_hole
            }
            return jsonify(response)

    # 5) Si el jugador hizo “CHECK” (CALL de 0) **y no igualó un bet**, entonces es turno del bot
    to_call_b_pre = game.current_bet - game.bot_current_bet
    bot_act, bot_raise_amt = game.bot_decide_action(trainer)

    logs.append(f"Bot decide {bot_act.name} con raise_amount={bot_raise_amt}")

    # 6) Loguear la acción exacta del bot (distinción CALL vs. CHECK)
    if bot_act == Action.FOLD:
        # Si no hay nada que pagar, interpretamos FOLD como CHECK
        if to_call_b_pre == 0:
            bot_action_str = "CHECK"
            logs.append("Bot hace CHECK.")
        else:
            bot_action_str = "FOLD"
            logs.append("Bot se retira (FOLD).")
    elif bot_act == Action.CALL:
        pay_b = min(to_call_b_pre, game.bot_chips)
        if pay_b == 0:
            bot_action_str = "CHECK"
            logs.append("Bot hace CHECK.")
        else:
            bot_action_str = "CALL"
            logs.append(f"Bot hace CALL de {pay_b} fichas.")
    else:
        # RAISE_SMALL, RAISE_MEDIUM, RAISE_LARGE
        total_put_b = to_call_b_pre + (bot_raise_amt if bot_raise_amt is not None else 0)
        total_put_b = min(total_put_b, game.bot_chips)
        bot_action_str = "RAISE"
        logs.append(f"Bot hace RAISE de {total_put_b} fichas (incluyendo call).")

    # 7) Aplicar la acción del bot
    termino_bot = game.apply_action("bot", bot_act, bot_raise_amt)
    if termino_bot:
        # Si el bot hizo “FOLD” real (y había un to_call_b_pre > 0), cerramos la mano
        if bot_act == Action.FOLD and to_call_b_pre > 0:
            response = {
                "logs": logs,
                "result": "bot_folded",
                "pot": game.pot,
                "player_chips": game.player_chips,
                "bot_chips": game.bot_chips,
                "dealer": game.dealer
            }
            game.pot = 0
            return jsonify(response)

        # Si el bot ganó por all-in o porque el jugador ya se había retirado
        pot_before = game.pot
        response = {
            "logs": logs,
            "result": "bot_ended",
            "bot_action": bot_action_str,
            "bot_raise_amount": bot_raise_amt,
            "player_chips": game.player_chips,
            "bot_chips": game.bot_chips,
            "pot": pot_before,
            "dealer": game.dealer,
            "bot_hole": game.bot_hole
        }
        game.pot = 0
        return jsonify(response)

    # 8) Detectar cierre de ronda en “raise→call” o en “check–check (CHECK del player + CHECK del bot)”:

    # ¿Fue “player hizo CHECK” (to_call_p == 0) y luego “bot hizo CHECK” (to_call_b_pre == 0)?
    is_check_check = (player_action_str == "CHECK" and bot_action_str == "CHECK")

    # ¿Fue “bot hizo CALL” a un bet abierto? (to_call_b_pre > 0 en el momento de la llamada)
    is_call_to_bet = (bot_act == Action.CALL and to_call_b_pre > 0)

    if is_call_to_bet or is_check_check:
        logs.append("Ronda de apuestas completada.")
        logs.append(f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}")

        game.next_street()
        si = game.street_index

        if si <= 3:
            if si == 1:
                logs.append(f"Flop: {game.community_cards[:3]}")
            elif si == 2:
                logs.append(f"Turn: {game.community_cards[3]}")
            elif si == 3:
                logs.append(f"River: {game.community_cards[4]}")
            logs.append(f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}")

            response = {
                "logs": logs,
                "result": "new_street",
                "pot": game.pot,
                "player_chips": game.player_chips,
                "bot_chips": game.bot_chips,
                "current_bet": game.current_bet,
                "street_index": game.street_index,
                "history": game.history,
                "dealer": game.dealer,
                "to_act": game.get_first_actor(),
                "community": game.community_cards[: (3 if si == 1 else 4 if si == 2 else 5)]
            }
            return jsonify(response)
        else:
            # showdown (si == 4)
            logs.append("Showdown!")
            player_best = game.evaluate_hand7(game.player_hole + game.community_cards)
            bot_best = game.evaluate_hand7(game.bot_hole + game.community_cards)

            logs.append(f"Tus cartas: {game.player_hole} + Comunidad: {game.community_cards}")
            logs.append(f"Cartas del bot: {game.bot_hole} + Comunidad: {game.community_cards}")
            logs.append(f"Tu mejor jugada: {game.describe_hand(player_best)}")
            logs.append(f"Mejor jugada del bot: {game.describe_hand(bot_best)}")

            contrib_p = game.player_contrib
            contrib_b = game.bot_contrib
            main_contrib = min(contrib_p, contrib_b)
            main_pot = main_contrib * 2
            side_pot = (contrib_p + contrib_b) - main_pot
            logs.append(f"-- Pot total: {game.pot} fichas (Main Pot={main_pot}, Side Pot={side_pot})")

            cmp = game.compare_hands(player_best, bot_best)
            if cmp > 0:
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

            pot_before = game.pot
            game.pot = 0
            logs.append(f"Fichas -> Tú: {game.player_chips} | Bot: {game.bot_chips} | Pot: {game.pot}")

            response = {
                "logs": logs,
                "result": "showdown",
                "player_chips": game.player_chips,
                "bot_chips": game.bot_chips,
                "pot": pot_before,
                "dealer": game.dealer,
                "bot_hole": game.bot_hole
            }
            return jsonify(response)

    # 9) Si llegamos hasta aquí, significa que no se cerró la ronda (p.ej. player CHECK + bot RAISE,
    #    o player RAISE + bot >CALL (reraise prohibido), o player RAISE + bot hizo CALL parcial (pero sin igualar completamente el bet),
    #    etc.). Devolvemos el estado “tal cual” para que el jugador u otro actor siga actuando.
    next_actor = game.get_first_actor()
    if game.street_index == 1:
        comm = game.community_cards[:3]
    elif game.street_index == 2:
        comm = game.community_cards[:4]
    elif game.street_index == 3:
        comm = game.community_cards[:5]
    else:
        comm = []

    response = {
        "logs": logs,
        "player_action": player_action_str,
        "bot_action": bot_action_str,
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
    return jsonify(response)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
