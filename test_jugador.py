# test_bot_raise_forzado_allin.py

from practica import PokerGame, Action

def test_forzar_raise_excesivo_y_recorte():
    # Creamos juego con el bot limitado a 300 fichas
    game = PokerGame(player_chips=1000, bot_chips=300, small_blind=10, big_blind=20)
    game.dealer = "bot"  # El bot es SB

    game.shuffle_deck()
    game.deal_cards()
    game.post_blinds()

    print("=== TEST FORZADO: BOT INTENTA RAISE DE 600 CON SOLO 300 ===")
    print(f"Chips iniciales del bot: {game.bot_chips}")
    print(f"Contribución inicial SB: {game.bot_contrib}")

    # Forzamos al bot a intentar raise de 600 fichas
    forced_action = Action.RAISE_LARGE
    forced_raise_amount = 600

    game.apply_action("bot", forced_action, raise_amount=forced_raise_amount)

    total_contrib = game.bot_contrib
    print(f"Contribución final del bot tras raise forzado: {total_contrib}")
    print(f"Stack restante del bot: {game.bot_chips}")
    print(f"Historial: {game.history}")

    assert total_contrib == 300, f"El bot no fue recortado correctamente: contribuyó {total_contrib} con stack 300"
    assert game.bot_chips == 0, "El bot debería estar all-in"

    print("✅ El raise fue recortado correctamente al stack disponible (300 fichas).")

if __name__ == "__main__":
    test_forzar_raise_excesivo_y_recorte()
