# graficar_desde_modelo.py

import os
import pickle
import numpy as np
import matplotlib.pyplot as plt

from sklearn.decomposition import PCA
from sklearn.metrics        import silhouette_score

from poker_env              import create_deck, GameState, INITIAL_STACK, Action
from bucket_features        import hand_to_features_enhanced
from cfr                    import CFRTrainer

def cargar_trainer(path='cfr_entrenado_completo.pkl'):
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Archivo '{path}' no encontrado. Entrena primero con entrenamiento_completo.py")
    with open(path, 'rb') as f:
        return pickle.load(f)

def evaluar_politica(trainer, phase, n_sims=2000):
    """Simula partidas heads-up usando la estrategia media final y devuelve (mean, std)."""
    km = trainer.kmeans_models[phase]
    payoffs = []
    for _ in range(n_sims):
        deck = create_deck(); np.random.shuffle(deck)
        hole0, hole1 = deck[:2], deck[2:4]
        community = trainer._deal(deck, phase)
        gs = GameState(hole0, hole1, community,
                       pot=10, to_act=0, history='',
                       phase=phase,
                       stack0=INITIAL_STACK, stack1=INITIAL_STACK,
                       current_bet=0, bet0=0, bet1=0,
                       dealer=0, deck=deck)
        # juego completo
        while not gs.is_terminal():
            feats  = hand_to_features_enhanced(
                        gs.hole_cards[gs.to_act],
                        gs.community_cards,
                        gs.pot, gs.history, gs.to_act)
            bucket = km.predict(feats.reshape(1,-1))[0]
            infoset = f"{phase}|{bucket}|{gs.history}"
            node    = trainer.nodes[phase].get(infoset, None)
            if node:
                strat = node.get_average_strategy()
            else:
                strat = np.ones(len(Action)) / len(Action)
            a = np.random.choice(len(strat), p=strat)
            gs = gs.apply_action(a)
        payoffs.append(gs.get_payoff(0) / INITIAL_STACK)
    return np.mean(payoffs), np.std(payoffs)

def graficar_metricas_desde_modelo(path_modelo='cfr_entrenado_completo.pkl'):
    trainer = cargar_trainer(path_modelo)
    fases = ['preflop','flop','turn','river']

    # --- 1) Regret promedio positivo final (bar chart) ---
    avg_regrets = {}
    for fase in fases:
        nodes = trainer.nodes[fase].values()
        total_pos = sum(np.sum(np.maximum(n.regret_sum,0)) for n in nodes)
        avg_regrets[fase] = total_pos / trainer.iterations_map[fase]

    plt.figure(figsize=(8,5))
    plt.bar(fases, [avg_regrets[f] for f in fases])
    plt.yscale('log')
    plt.title('Regret positivo promedio FINAL (log scale)')
    plt.ylabel('Average Positive Regret')
    plt.xlabel('Fase')
    plt.tight_layout()
    plt.show()

    # --- 2) Evaluación de la política media (mean & std payoff) ---
    means, stds = [], []
    for fase in fases:
        m, s = evaluar_politica(trainer, fase, n_sims=2000)
        print(f"[Evaluación] {fase:7s} → mean payoff = {m:.4f}, std = {s:.4f}")
        means.append(m); stds.append(s)

    x = np.arange(len(fases))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8,4))
    ax.bar(x - width/2, means, width, label='Mean payoff')
    ax.bar(x + width/2, stds,  width, label='Std payoff')
    ax.set_xticks(x); ax.set_xticklabels(fases)
    ax.set_ylabel('Valor normalizado')
    ax.set_title('Evaluación Monte Carlo de la política media')
    ax.legend()
    plt.tight_layout()
    plt.show()

def graficar_clusters(path_modelo='cfr_entrenado_completo.pkl', n_samples=2000):
    trainer = cargar_trainer(path_modelo)
    fases = ['preflop','flop','turn','river']

    for fase in fases:
        # 1) Generar muestras de features
        X = []
        for _ in range(n_samples):
            deck = create_deck(); np.random.shuffle(deck)
            hole = deck[:2]
            comm = trainer._deal(deck, fase)
            X.append(hand_to_features_enhanced(hole, comm, pot=10, history='', to_act=0))
        X = np.array(X)

        # 2) Predicción y métricas de calidad
        km     = trainer.kmeans_models[fase]
        labels = km.predict(X)
        inert  = km.inertia_
        sil    = silhouette_score(X, labels)
        print(f"[Clusters] {fase:7s} → inertia = {inert:.1f}, silhouette = {sil:.3f}")

        # 3) PCA a 2D y scatter
        X2  = PCA(n_components=2, random_state=42).fit_transform(X)
        plt.figure(figsize=(6,6))
        for c in np.unique(labels):
            idx = labels == c
            plt.scatter(X2[idx,0], X2[idx,1], s=10, alpha=0.6)
        plt.title(f'Clusters en fase {fase} (PCA 2D)')
        plt.xlabel('Componente 1')
        plt.ylabel('Componente 2')
        plt.tight_layout()
        plt.show()

if __name__ == '__main__':
    graficar_metricas_desde_modelo()
    graficar_clusters()
