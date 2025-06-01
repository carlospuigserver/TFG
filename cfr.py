# cfr.py

import numpy as np
import random
from sklearn.cluster import KMeans

from poker_env import (
    create_deck,
    GameState,
    INITIAL_STACK,
    Action
)

from bucket_features import (
    hand_to_features_enhanced,
    real_equity_estimate
)
from heuristics_warmup import heuristic_action

NUM_ACTIONS = len(Action)


class Node:
    def __init__(self, info_set, num_actions=NUM_ACTIONS):
        self.info_set = info_set
        self.num_actions = num_actions
        self.regret_sum = np.zeros(num_actions)
        self.strategy_sum = np.zeros(num_actions)

    def get_strategy(self, realization_weight, epsilon=0.0):
        """
        realization_weight: reach probability para este nodo.
        epsilon: probabilidad de explorar (ε-greedy).
        """
        positive = np.maximum(self.regret_sum, 0)
        if positive.sum() > 0:
            strat = positive / positive.sum()
        else:
            strat = np.ones(self.num_actions) / self.num_actions

        if epsilon > 0:
            strat = (1 - epsilon) * strat + epsilon * (1.0 / self.num_actions)

        self.strategy_sum += realization_weight * strat
        return strat

    def get_average_strategy(self):
        total = self.strategy_sum.sum()
        if total > 0:
            return self.strategy_sum / total
        return np.ones(self.num_actions) / self.num_actions


class CFRTrainer:
    def __init__(
        self,
        iterations_map=None,
        samples_map=None,
        depth=15,
        epsilon_map=None
    ):
        # Número de iteraciones por fase
        self.iterations_map = iterations_map or {
            'preflop': 30000,
            'flop':   50000,
            'turn':   30000,
            'river':  10000
        }
        # Muestras para clustering
        self.samples_map = samples_map or {
            'preflop': 20000,
            'flop':   10000,
            'turn':   20000,
            'river':  10000
        }
        self.depth = depth
        # Epsilon para exploración que decae linealmente
        self.epsilon_map = epsilon_map or {
            'preflop': 0.10,
            'flop':   0.05,
            'turn':   0.10,
            'river':  0.02
        }

        # Almacenarán KMeans y nodos por fase
        self.kmeans_models = {}
        self.nodes = {}

        # Estadísticas fold-equity empírica: fase -> {'RS': [int attempts, int folds], 'RM': [...]}
        self.fold_stats = {
            'preflop': {'RS': [1, 1], 'RM': [1, 1]},
            'flop':    {'RS': [1, 1], 'RM': [1, 1]},
            'turn':    {'RS': [1, 1], 'RM': [1, 1]},
            'river':   {'RS': [1, 1], 'RM': [1, 1]},
        }

    @staticmethod
    def _deal(deck, phase):
        """
        Genera la lista parcial de cartas comunitarias según fase:
          - preflop: []
          - flop: deck[4:7]
          - turn: deck[4:8]
          - river: deck[4:9]
        """
        if phase == 'preflop':
            return []
        if phase == 'flop':
            return deck[4:7]
        if phase == 'turn':
            return deck[4:8]
        return deck[4:9]

    def prefill_regrets(self, phase, km: KMeans, num_sims=10000, epsilon=0.01):
        """
        Warm-up con heurísticas:
          - Simula num_sims veces estados aleatorios.
          - En cada estado, usa heuristic_action (que ahora emplea equity real en flop/river).
          - Si la acción es RAISE_LARGE y equity_real < 0.85, se reemplaza por CALL.
          - Genera regret inicial normalizado (= payoff / INITIAL_STACK).
          - Registra estadísticas de fold-equity en raises RS/RM.
        """
        from collections import defaultdict

        # count_actions[infoset][a] = cuántas veces elegimos acción a en ese infoset
        count_actions = defaultdict(
            lambda: np.zeros(Node(info_set="", num_actions=NUM_ACTIONS).num_actions)
        )
        # sum_utilities[infoset][a] = suma de utilidades (normalizadas) obtenidas cuando hicimos acción a
        sum_utilities = defaultdict(
            lambda: np.zeros(Node(info_set="", num_actions=NUM_ACTIONS).num_actions)
        )

        for _ in range(num_sims):
            deck = create_deck()
            random.shuffle(deck)
            hole0, hole1 = deck[:2], deck[2:4]
            community = self._deal(deck, phase)
            pot = 10
            gs = GameState(
                hole0=hole0,
                hole1=hole1,
                community=community,
                pot=pot,
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

            path = []
            while not gs.is_terminal():
                gs.player_current_bet = gs.bet[0]
                gs.bot_current_bet = gs.bet[1]

                # --- REEMPLAZO de get_bucket por hand_to_features_enhanced --- #
                hole = gs.hole_cards[gs.to_act]
                community_now = gs.community_cards
                feats = hand_to_features_enhanced(
                    hole,
                    community_now,
                    pot=gs.pot,
                    history=gs.history,
                    to_act=gs.to_act
                )
                bucket = km.predict(feats.reshape(1, -1))[0]
                infoset = f"{phase}|{bucket}|{gs.history}"
                # ------------------------------------------------------------- #

                # 1) Acción heurística
                action_enum = heuristic_action(gs)

                # 2) Si es RAISE_LARGE y equity_real < 0.85, cambiamos a CALL
                equity_now = real_equity_estimate(hole, community_now, num_sim=20)
                if action_enum == Action.RAISE_LARGE and equity_now < 0.85:
                    action_enum = Action.CALL

                a_idx = action_enum.value
                count_actions[infoset][a_idx] += 1
                path.append((infoset, a_idx, gs.to_act, phase, action_enum))

                # 3) Registrar fold-equity empírica si es raise_small o raise_medium
                if action_enum in (Action.RAISE_SMALL, Action.RAISE_MEDIUM):
                    key = 'RS' if action_enum == Action.RAISE_SMALL else 'RM'
                    self.fold_stats[phase][key][0] += 1

                prev_hist = gs.history
                # --- Aquí envolvemos en try/except OverflowError ---
                try:
                    gs = gs.apply_action(a_idx)
                except OverflowError:
                    # Si la apuesta escala demasiado, interrumpimos este camino de warm-up
                    break

                if action_enum in (Action.RAISE_SMALL, Action.RAISE_MEDIUM):
                    # Si justo después de ese raise hubo fold (historia añade 'f'), contamos
                    if 'f' in gs.history and gs.history.replace('|','').startswith(prev_hist.replace('|','') + 'r'):
                        key = 'RS' if action_enum == Action.RAISE_SMALL else 'RM'
                        self.fold_stats[phase][key][1] += 1

                if gs.is_terminal():
                    break

            # 4) Payoff al final de la mano (jugador 0), normalizado
            payoff_p0 = gs.get_payoff(0)
            util_norm_p0 = payoff_p0 / INITIAL_STACK
            util_norm_p1 = -util_norm_p0

            for infoset, a_idx, player, ph, _ in path:
                util = util_norm_p0 if player == 0 else util_norm_p1
                sum_utilities[infoset][a_idx] += util

        # 5) Construir nodos y fijar regret_sum inicial según heurísticas
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
                    avg_util[a] = -1.0  # acción no tomada → utility muy baja

            best_util = np.max(avg_util)
            for a in range(node.num_actions):
                node.regret_sum[a] = max(0.0, best_util - avg_util[a])

            if node.regret_sum.sum() == 0:
                node.regret_sum[:] = epsilon

        # Si algún nodo quedó con regrets = 0, le damos epsilon pequeño
        for infoset, node in self.nodes[phase].items():
            if node.regret_sum.sum() == 0:
                node.regret_sum[:] = epsilon

        print(f"[Warm-up] Prefill completo en fase '{phase}'. Nodos iniciales: {len(self.nodes[phase])}")


    def sample_trajectory(self, phase, km, iter_count, total_iters):
        """
        MCCFR por outcome sampling:
          - Se muestrea una sola trayectoria (chance + acciones).
          - En cada infoset, se muestrea UNA acción según la estrategia actual.
          - Al llegar a terminal, calculamos payoff normalizado y retropropagamos regrets.
        """
        deck = create_deck()
        random.shuffle(deck)
        hole0, hole1 = deck[:2], deck[2:4]
        community = self._deal(deck, phase)
        gs = GameState(
            hole0=hole0,
            hole1=hole1,
            community=community,
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

        trajectory = []
        reach_prob = 1.0

        while not gs.is_terminal():
            # --- REEMPLAZO de get_bucket por hand_to_features_enhanced --- #
            hole = gs.hole_cards[gs.to_act]
            community_now = gs.community_cards
            feats = hand_to_features_enhanced(
                hole,
                community_now,
                pot=gs.pot,
                history=gs.history,
                to_act=gs.to_act
            )
            bucket = km.predict(feats.reshape(1, -1))[0]
            infoset = f"{phase}|{bucket}|{gs.history}"
            if infoset not in self.nodes[phase]:
                self.nodes[phase][infoset] = Node(infoset)
            node = self.nodes[phase][infoset]
            # ------------------------------------------------------------- #

            eps = self.epsilon_map[phase] * (1 - iter_count / total_iters)
            strat = node.get_strategy(reach_prob, epsilon=eps)

            # Muestreamos una acción
            a_idx = np.random.choice(range(NUM_ACTIONS), p=strat)
            action_enum = Action(a_idx)

            trajectory.append((infoset, a_idx, strat[a_idx], gs.to_act, phase, action_enum))

            # Registrar fold-equity empírica si es RS o RM
            if action_enum in (Action.RAISE_SMALL, Action.RAISE_MEDIUM):
                key = 'RS' if action_enum == Action.RAISE_SMALL else 'RM'
                self.fold_stats[phase][key][0] += 1

            prev_hist = gs.history
            gs = gs.apply_action(a_idx)

            if action_enum in (Action.RAISE_SMALL, Action.RAISE_MEDIUM):
                if 'f' in gs.history and gs.history.replace('|','').startswith(prev_hist.replace('|','') + 'r'):
                    key = 'RS' if action_enum == Action.RAISE_SMALL else 'RM'
                    self.fold_stats[phase][key][1] += 1

            reach_prob *= strat[a_idx]

        payoff_p0 = gs.get_payoff(0)
        util_norm_p0 = payoff_p0 / INITIAL_STACK

        # Retropropagar regrets
        for infoset, a_idx, prob_a, player, ph, _ in reversed(trajectory):
            node = self.nodes[phase][infoset]
            util = util_norm_p0 if player == 0 else -util_norm_p0
            node.regret_sum[a_idx] += util / (prob_a + 1e-12)

        return util_norm_p0


    def train_phase(self, phase, st_logger=print):
        """
        1) Clustering con features enriquecidos.
        2) Warm-up con heurísticas mejoradas (equity real).
        3) MCCFR outcome sampling con payoffs normalizados.
        """
        st_logger(f"--- Entrenando {phase} con MCCFR (payoff normalizado) ---")

        n_samp  = self.samples_map[phase]
        iters   = self.iterations_map[phase]
        eps0    = self.epsilon_map[phase]

        # 1) Clustering KMeans sobre hand_to_features_enhanced
        samples = []
        for _ in range(n_samp):
            deck = create_deck()
            random.shuffle(deck)
            hole = deck[:2]
            comm = self._deal(deck, phase)
            feats = hand_to_features_enhanced(
                hole,
                comm,
                pot=10,
                history='',
                to_act=0
            )
            samples.append(feats)
        X = np.array(samples)
        km = KMeans(n_clusters=max(2, n_samp // 10), random_state=42).fit(X)
        self.kmeans_models[phase] = km

        # 2) Warm-up
        self.prefill_regrets(phase, km=km, num_sims=n_samp, epsilon=eps0)

        # 3) MCCFR (outcome sampling)
        utils_block = []
        for i in range(1, iters + 1):
            util = self.sample_trajectory(phase, km, i, iters)
            utils_block.append(util)

            if i % 500 == 0:
                mean = np.mean(utils_block)
                std = np.std(utils_block)
                total_pos = sum(
                    np.sum(np.maximum(n.regret_sum, 0))
                    for n in self.nodes[phase].values()
                )
                avg_reg = total_pos / i
                st_logger(f"Iter {i:6d}: mean={mean:.4f}, std={std:.4f}, avg_regret={avg_reg:.4f}")
                utils_block = []

        # Mostrar fold-equity empírica
        foldeos_RS = self.fold_stats[phase]['RS'][1]
        tot_RS     = self.fold_stats[phase]['RS'][0]
        foldeos_RM = self.fold_stats[phase]['RM'][1]
        tot_RM     = self.fold_stats[phase]['RM'][0]
        fe_RS = foldeos_RS / tot_RS if tot_RS > 0 else 0.0
        fe_RM = foldeos_RM / tot_RM if tot_RM > 0 else 0.0
        st_logger(f"[Fold-equity empírica en {phase}] RS: {fe_RS:.2%}, RM: {fe_RM:.2%}")

        total_pos = sum(
            np.sum(np.maximum(n.regret_sum, 0))
            for n in self.nodes[phase].values()
        )
        avg_regret_final = total_pos / iters
        st_logger(f"*** Average positive regret en {phase}: {avg_regret_final:.6f} ***")
