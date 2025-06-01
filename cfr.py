# cfr.py

import numpy as np
import random
from sklearn.cluster import KMeans
from poker_env import create_deck, hand_to_features, GameState, get_bucket, INITIAL_STACK, Action

from heuristics_warmup import heuristic_action, monte_carlo_equity

NUM_ACTIONS = len(Action)


class Node:
    def __init__(self, info_set, num_actions=NUM_ACTIONS):
        self.info_set = info_set
        self.num_actions = num_actions
        self.regret_sum = np.zeros(num_actions)
        self.strategy_sum = np.zeros(num_actions)

    def get_strategy(self, epsilon=0.0):
        positive = np.maximum(self.regret_sum, 0)
        if positive.sum() > 0:
            strat = positive / positive.sum()
        else:
            strat = np.ones(self.num_actions) / self.num_actions

        if epsilon > 0:
            strat = (1 - epsilon) * strat + epsilon * (1.0 / self.num_actions)

        # Peso fijo = 1 en vez de weight variable
        self.strategy_sum += strat
        return strat

    def get_average_strategy(self):
        total = self.strategy_sum.sum()
        if total > 0:
            return self.strategy_sum / total
        return np.ones(self.num_actions) / self.num_actions


def cfr_phase(
    gs: GameState,
    p0: float,
    p1: float,
    nodes: dict,
    km: KMeans,
    phase: str,
    player: int = 0,
    max_depth: int = 15,
    epsilon: float = 0.0,
    iter_count: int = 1,
    total_iters: int = 1
) -> float:
    """
    CFR+ recursivo con Monte Carlo ligero en flop/river.
    """
    # 1) Nodo terminal o profundidad 0 → devolver payoff real (o aproximación MC si no hay showdown)
    if gs.is_terminal():
        return gs.get_payoff(player)
    if max_depth == 0:
        # Si no profundizamos más, aproximar payoff con Monte Carlo en función de fase
        deck = gs.deck.copy()
        # Equity del jugador actual vs rango uniforme
        hole = gs.hole_cards[gs.to_act]
        community = gs.community_cards.copy()
        equity = monte_carlo_equity(hole, community, deck, to_simulate=200)
        to_call = gs.current_bet - (gs.player_current_bet if gs.to_act == 0 else gs.bot_current_bet)
        return equity * gs.pot - (1 - equity) * to_call

    # 2) Construir infoset
    bucket = get_bucket(
        km,
        gs.hole_cards[gs.to_act],
        gs.community_cards,
        bet_size=gs.pot / INITIAL_STACK,
        history=gs.history,
        to_act=gs.to_act,
        pot=gs.pot
    )
    infoset = f"{phase}|{bucket}|{gs.history}"

    # 3) Crear nodo si no existe
    if infoset not in nodes:
        nodes[infoset] = Node(infoset)
    node = nodes[infoset]

    # 4) Estrategia actual con CFR+
    # ε con decaimiento exponencial suave
    lam = 1e-5
    eps = epsilon * np.exp(-lam * iter_count)
    strat = node.get_strategy(epsilon=eps)

    util = np.zeros(node.num_actions)
    node_util = 0.0

    legal_actions = gs.legal_actions()

    for a in legal_actions:
        action_enum = Action(a)

        # 5) Caso de all-in en flop/turn/river sin veto absoluto
        # Simplemente dejamos que recorra el resto
        # 6) Recursar o aproximar payoff con Monte Carlo
        nxt = gs.apply_action(a)

        # Determinar nuevo phase según gs.apply_action
        next_phase = nxt.phase

        if nxt.is_terminal():
            util[a] = nxt.get_payoff(player)
        else:
            util[a] = -cfr_phase(
                nxt,
                p0 * (strat[a] if gs.to_act == 0 else 1.0),
                p1 * (strat[a] if gs.to_act == 1 else 1.0),
                nodes,
                km,
                next_phase,
                player,
                max_depth - 1,
                epsilon,
                iter_count + 1,
                total_iters
            )

        node_util += strat[a] * util[a]

    # 7) Actualizar regrets
    for a in legal_actions:
        regret = util[a] - node_util
        if gs.to_act == 0:
            node.regret_sum[a] += p1 * regret
        else:
            node.regret_sum[a] += p0 * regret

    # Recocido suave de regrets (CFR+ clamp)
    node.regret_sum = np.maximum(node.regret_sum, 0)

    return node_util


class CFRTrainer:
    def __init__(
        self,
        iterations_map=None,
        samples_map=None,
        depth=20,
        epsilon_map=None
    ):
        self.iterations_map = iterations_map or {
            'preflop': 50000,
            'flop': 30000,
            'turn': 30000,
            'river': 15000
        }
        self.samples_map = samples_map or {
            'preflop': 30000,
            'flop': 15000,
            'turn': 15000,
            'river': 10000
        }
        self.depth = depth
        self.epsilon_map = epsilon_map or {
            'preflop': 0.05,
            'flop': 0.03,
            'turn': 0.05,
            'river': 0.01
        }

        self.kmeans_models = {}
        self.nodes = {}

    @staticmethod
    def _deal(deck, phase):
        """
        Muestreo realista de cartas comunitarias:
        - Preflop: []
        - Flop: quemar 1 carta, tomar 3
        - Turn: quemar 1 carta, tomar 1
        - River: quemar 1 carta, tomar 1
        """
        d = deck.copy()
        if phase == 'preflop':
            return []
        if phase == 'flop':
            # quemar d[0], flop = d[1:4]
            return d[1:4]
        if phase == 'turn':
            # quemar d[4], turn = d[5]
            return d[1:5] + [d[5]]
        # River
        return d[1:5] + [d[5]] + [d[7]]

    def prefill_regrets(self, phase, km: KMeans, num_sims=20000, epsilon=0.01):
        from collections import defaultdict

        count_actions = defaultdict(
            lambda: np.zeros(Node(info_set="", num_actions=NUM_ACTIONS).num_actions)
        )
        sum_utilities = defaultdict(
            lambda: np.zeros(Node(info_set="", num_actions=NUM_ACTIONS).num_actions)
        )

        for _ in range(num_sims):
            deck = create_deck()
            random.shuffle(deck)
            hole0, hole1 = deck[:2], deck[2:4]
            community = self._deal(deck, phase)
            pot = 10
            to_act = 0
            history = ""
            stack0, stack1 = INITIAL_STACK, INITIAL_STACK

            gs = GameState(
                hole0,
                hole1,
                community,
                pot,
                to_act,
                history,
                phase=phase,
                stack0=stack0,
                stack1=stack1,
                current_bet=0,
                bet0=0,
                bet1=0,
                dealer=0,
                deck=deck
            )

            gs.player_current_bet = gs.bet[0]
            gs.bot_current_bet = gs.bet[1]

            path = []
            while not gs.is_terminal():
                comm = self._deal(gs.deck, gs.phase)
                gs.community_cards = comm

                gs.player_current_bet = gs.bet[0]
                gs.bot_current_bet = gs.bet[1]

                bucket = get_bucket(
                    km,
                    gs.hole_cards[gs.to_act],
                    gs.community_cards,
                    bet_size=gs.pot / INITIAL_STACK,
                    history=gs.history,
                    to_act=gs.to_act,
                    pot=gs.pot
                )
                infoset = f"{phase}|{bucket}|{gs.history}"

                # Acción heurística inicial
                action_enum = heuristic_action(gs)

                a_idx = action_enum.value
                count_actions[infoset][a_idx] += 1
                path.append((infoset, a_idx, gs.to_act))

                try:
                    gs = gs.apply_action(a_idx)
                except OverflowError:
                    break

                if gs.is_terminal():
                    break

            payoff_p0 = gs.get_payoff(0)
            payoff_p1 = -payoff_p0
            for infoset, a_idx, player in path:
                util = payoff_p0 if player == 0 else payoff_p1
                sum_utilities[infoset][a_idx] += util

        self.nodes[phase] = {}
        for infoset, node_counts in count_actions.items():
            if infoset not in self.nodes[phase]:
                self.nodes[phase][infoset] = Node(infoset)
            node = self.nodes[phase][infoset]

            avg_util = np.zeros(node.num_actions)
            for a in range(node.num_actions):
                if node_counts[a] > 0:
                    avg_util[a] = sum_utilities[infoset][a] / node_counts[a]
                else:
                    avg_util[a] = -1.0  # acción no probada

            best_util = np.max(avg_util)
            for a in range(node.num_actions):
                node.regret_sum[a] = max(0.0, best_util - avg_util[a])

            if node.regret_sum.sum() == 0:
                node.regret_sum[:] = epsilon

        print(f"[Warm-up] Prefill completo en fase '{phase}'. Nodos iniciales: {len(self.nodes[phase])}")

    def train_phase(self, phase, st_logger=print):
        st_logger(f"--- Entrenando {phase} CFR+ ---")
        n_samp = self.samples_map[phase]
        iters = self.iterations_map[phase]
        eps0 = self.epsilon_map[phase]

        # 1) Clustering KMeans
        samples = []
        for _ in range(n_samp):
            deck = create_deck()
            random.shuffle(deck)
            hole, comm = deck[:2], self._deal(deck, phase)
            samples.append(
                hand_to_features(
                    hole,
                    comm,
                    bet_size=10 / self.depth,
                    history='',
                    to_act=0,
                    pot=10
                )
            )
        km = KMeans(n_clusters=max(2, int(n_samp**0.5)), random_state=42).fit(np.array(samples))
        self.kmeans_models[phase] = km

        # 2) Warm-up
        self.prefill_regrets(phase, km=km, num_sims=n_samp, epsilon=eps0)

        # 3) CFR puro / CFR+
        utils_block = []
        for i in range(1, iters + 1):
            deck = create_deck()
            random.shuffle(deck)
            hole0, hole1 = deck[:2], deck[2:4]
            comm = self._deal(deck, phase)
            gs = GameState(
                hole0,
                hole1,
                comm,
                pot=10,
                to_act=0,
                history='',
                phase=phase,
                stack0=INITIAL_STACK,
                stack1=INITIAL_STACK,
                current_bet=0,
                bet0=0,
                bet1=0,
                dealer=0,
                deck=deck
            )

            gs.player_current_bet = gs.bet[0]
            gs.bot_current_bet = gs.bet[1]

            val = cfr_phase(
                gs,
                1.0,
                1.0,
                self.nodes[phase],
                km,
                phase,
                player=0,
                max_depth=self.depth,
                epsilon=eps0,
                iter_count=i,
                total_iters=iters
            )
            utils_block.append(val)

            if i % 500 == 0:
                mean = np.mean(utils_block)
                std = np.std(utils_block)
                total_pos = sum(
                    np.sum(np.maximum(n.regret_sum, 0)) for n in self.nodes[phase].values()
                )
                avg_reg = total_pos / i
                st_logger(f"Iter {i:5d}: mean={mean:.4f}, std={std:.4f}, avg_regret={avg_reg:.4f}")
                utils_block = []

        total_pos = sum(
            np.sum(np.maximum(n.regret_sum, 0)) for n in self.nodes[phase].values()
        )
        avg_regret = total_pos / iters
        st_logger(f"*** Average positive regret en {phase}: {avg_regret:.6f} ***")
