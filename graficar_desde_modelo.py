# graficar_desde_modelo.py

import os
import pickle
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

def cargar_trainer(path='cfr_entrenado_completo.pkl'):
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Archivo '{path}' no encontrado. Entrena primero con entrenamiento_completo.py")
    with open(path, 'rb') as f:
        trainer = pickle.load(f)
    return trainer

def graficar_metricas_desde_modelo(path_modelo='cfr_entrenado_completo.pkl'):
    trainer = cargar_trainer(path_modelo)
    fases = ['preflop','flop','turn','river']

    # 1) Extraer métricas finales:
    mean_vals = {}
    std_vals = {}
    avg_regrets = {}
    for fase in fases:
        # recorremos todos los nodos de la fase
        nodes = trainer.nodes[fase].values()
        # para calcular media y std de payoff hemos de aproximar:
        #   el payoff medio lo estimamos por el fold_stats (no disponible),
        # pero podemos recuperar el avg positive regret final:
        total_pos_regret = np.sum([np.sum(np.maximum(n.regret_sum,0)) for n in nodes])
        # sacamos el avg_pos_regret aproximado dividiendo por iteraciones totales
        iters = trainer.iterations_map[fase]
        avg_regrets[fase] = total_pos_regret / iters
        # para mean/std no tenemos el historial: asignamos NaN
        mean_vals[fase] = np.nan
        std_vals[fase]  = np.nan

    # 2) Graficar average positive regret (única métrica que podemos extraer)
    plt.figure(figsize=(8,5))
    plt.bar(fases, [avg_regrets[f] for f in fases])
    plt.yscale('log')
    plt.ylabel('Average Positive Regret (log scale)')
    plt.title('Regret promedio positivo final por fase')
    plt.tight_layout()
    plt.show()

def graficar_clusters(path_modelo='cfr_entrenado_completo.pkl', n_samples=2000):
    trainer = cargar_trainer(path_modelo)
    from poker_env import create_deck
    from bucket_features import hand_to_features_enhanced

    fases = ['preflop','flop','turn','river']

    for fase in fases:
        # 1) Generar muestras de features
        X = []
        for _ in range(n_samples):
            deck = create_deck()
            np.random.shuffle(deck)
            hole = deck[:2]
            if fase=='preflop':
                comm = []
            elif fase=='flop':
                comm = deck[4:7]
            elif fase=='turn':
                comm = deck[4:8]
            else:
                comm = deck[4:9]
            feats = hand_to_features_enhanced(hole, comm, pot=10, history='', to_act=0)
            X.append(feats)
        X = np.array(X)

        # 2) Predecir clusters
        km = trainer.kmeans_models[fase]
        labels = km.predict(X)

        # 3) Reducir a 2D con PCA
        pca = PCA(n_components=2, random_state=42)
        X2 = pca.fit_transform(X)

        # 4) Scatter plot
        plt.figure(figsize=(6,6))
        for cluster in np.unique(labels):
            idx = labels==cluster
            plt.scatter(X2[idx,0], X2[idx,1], s=10, label=f'c{cluster}', alpha=0.6)
        plt.title(f'Clusters en fase {fase} (PCA 2D)')
        plt.xlabel('Componente 1')
        plt.ylabel('Componente 2')
        plt.legend(markerscale=2, fontsize='small', title='Cluster')
        plt.tight_layout()
        plt.show()

if __name__ == '__main__':
    # Solo regret promedio final (no hay historial completo)
    graficar_metricas_desde_modelo()
    # Scatter de clusters
    graficar_clusters()
