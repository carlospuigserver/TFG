import unittest
from practica import PokerGame, Action  # Asegurate de que el nombre 'practica.py' sea correcto

class TestPokerGame(unittest.TestCase):
    
    def setUp(self):
        self.game = PokerGame(player_chips=100, bot_chips=100)
        self.game.shuffle_deck()
        self.game.deal_cards()

        self.game.pot = 0
        self.game.current_bet = 0
        self.game.player_current_bet = 0
        self.game.bot_current_bet = 0
        self.game.player_contrib = 0
        self.game.bot_contrib = 0
        self.game.community_cards = ['AS', 'KH', '3D', '7C']  # Simulamos hasta el turn
        self.game.street_index = 2

    def test_bot_raise_limited_by_player_stack(self):
        # Simulamos situación: jugador tiene 50, bot tiene 500
        self.game.player_chips = 50
        self.game.bot_chips = 500

        # 🔧 Forzamos raise manual del bot por 100 (aunque se va a recortar a 50)
        action = Action.RAISE_LARGE
        intended_raise = 100

        result = self.game.apply_action('bot', action, raise_amount=intended_raise)

        # ✅ Raise real debería ser de 50
        self.assertEqual(self.game.bot_current_bet, 50)
        self.assertEqual(self.game.bot_chips, 450)
        self.assertEqual(self.game.current_bet, 50)

        # 🎯 El jugador paga todo (all-in)
        result2 = self.game.apply_action('player', Action.CALL)

        # Jugador sin fichas → all-in completo
        self.assertEqual(self.game.player_chips, 0)
        self.assertEqual(self.game.player_current_bet, 50)

        # 💥 Ambos están all-in, se fuerza showdown
        self.assertTrue(result2)

class MockTrainer:
    def __init__(self):
        self.kmeans_models = {}
        self.nodes = {}

if __name__ == '__main__':
    unittest.main()
