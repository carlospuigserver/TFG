# test_jugador.py
from practica import PokerGame

def test_allin_ciegas_simetrico():
    print("\n=== TEST: ALL-IN FORZADO EN CIEGAS (Jugador sin fichas) ===")
    game1 = PokerGame(player_chips=5, bot_chips=1995, small_blind=10, big_blind=20)
    game1.dealer = "bot"  # Bot reparte → jugador es BB
    result1 = game1.start_hand()

    total_fichas1 = game1.player_chips + game1.bot_chips + game1.pot
    assert total_fichas1 == 2000, f"❌ ERROR: Fichas tras showdown (jugador sin stack): {total_fichas1}"
    print(f"🎯 Fichas tras showdown (jugador sin stack): {total_fichas1}")

    print("\n=== TEST: ALL-IN FORZADO EN CIEGAS (Bot sin fichas) ===")
    game2 = PokerGame(player_chips=1995, bot_chips=5, small_blind=10, big_blind=20)
    game2.dealer = "player"  # Jugador reparte → bot es BB
    result2 = game2.start_hand()

    total_fichas2 = game2.player_chips + game2.bot_chips + game2.pot
    assert total_fichas2 == 2000, f"❌ ERROR: Fichas tras showdown (bot sin stack): {total_fichas2}"
    print(f"🎯 Fichas tras showdown (bot sin stack): {total_fichas2}")

    print("\n✅ Test completado: los all-ins forzados en ciegas funcionan y no inflan fichas.")

if __name__ == "__main__":
    test_allin_ciegas_simetrico()
