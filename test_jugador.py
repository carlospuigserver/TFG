from practica import PokerGame, Action
import pickle

class MockTrainer:
    def __init__(self):
        self.kmeans_models = {}
        self.nodes = {}

def test_manual_raise_input():
    game = PokerGame(player_chips=500, bot_chips=50)
    trainer = MockTrainer()

    game.shuffle_deck()
    game.deal_cards()

    # Salteamos blinds
    game.pot = 0
    game.current_bet = 0
    game.player_current_bet = 0
    game.bot_current_bet = 0
    game.player_contrib = 0
    game.bot_contrib = 0
    game.community_cards = ['AS', 'KH', '3D', '7C']
    game.street_index = 2  # Turn

    print("=== TEST INTERACTIVO ===")
    print(f"Tus fichas: {game.player_chips}")
    print(f"Fichas del bot: {game.bot_chips}")
    print("Cartas comunitarias:", game.community_cards)

    # Te toca hablar a vos
    action_str = input("Tu acción (call, raise, fold): ").strip().lower()
    
    if action_str == "fold":
        game.apply_action("player", Action.FOLD)
        return
    elif action_str == "call":
        game.apply_action("player", Action.CALL)
    elif action_str == "raise":
        try:
            amount = int(input("¿Cuánto querés subir?: "))
            game.apply_action("player", Action.RAISE_LARGE, raise_amount=amount)
        except:
            print("Monto inválido.")
            return
    else:
        print("Acción no válida.")
        return

    # Le toca al bot decidir si iguala
    to_call = game.current_bet - game.bot_current_bet
    max_pay = min(to_call, game.bot_chips)

    if max_pay > 0:
        print(f"\nBot iguala con {max_pay} (all-in)")
        game.bot_chips -= max_pay
        game.bot_current_bet += max_pay
        game.bot_contrib += max_pay
        game.pot += max_pay
    else:
        print("\nBot no necesita pagar nada (CHECK)")

    # Forzar showdown
    game.reveal_remaining_community_cards()
    game.showdown()

if __name__ == "__main__":
    test_manual_raise_input()
