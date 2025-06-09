# entrenamiento_completo.py


import pickle
import numpy as np
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt


from poker_env import create_deck
from bucket_features import hand_to_features_enhanced
from cfr import CFRTrainer


def entrenamiento_completo(n_samples=10000):
    trainer = CFRTrainer()


    fases = ['preflop', 'flop', 'turn', 'river']


    history_mean = {fase: [] for fase in fases}
    history_std = {fase: [] for fase in fases}
    history_avg_regret = {fase: [] for fase in fases}


    def make_logger(fase):
        def logger(msg):
            print(msg)
            if msg.startswith("Iter") and "mean=" in msg and "std=" in msg and "avg_regret=" in msg:
                parts = msg.split()
                it = int(parts[1].strip(':'))


                mean_val = float(msg.split("mean=")[1].split(",")[0])
                std_val = float(msg.split("std=")[1].split(",")[0])
                avg_val = float(msg.split("avg_regret=")[1])


                history_mean[fase].append((it, mean_val))
                history_std[fase].append((it, std_val))
                history_avg_regret[fase].append((it, avg_val))
        return logger


    for fase in fases:
        print(f"\n--- Recalculando clusters y entrenando para fase: {fase} ---")
        muestras = []


        for _ in range(n_samples):
            deck = create_deck()
            np.random.shuffle(deck)
            hole = deck[:2]


            if fase == 'preflop':
                comm = []
            elif fase == 'flop':
                comm = deck[4:7]
            elif fase == 'turn':
                comm = deck[4:8]
            else:
                comm = deck[4:9]


            feats = hand_to_features_enhanced(
                hole, comm, pot=10, history='', to_act=0
            )
            muestras.append(feats)


        X = np.array(muestras)
        k = max(2, len(muestras) // 10)
        kmeans = KMeans(n_clusters=k, random_state=42).fit(X)
        trainer.kmeans_models[fase] = kmeans


        print(f"✅ Clustering hecho ({k} clusters). Ahora entrenando MCCFR...")
        trainer.train_phase(fase, st_logger=make_logger(fase))


    # Guardamos modelo entrenado con nodos y clusters
    with open('cfr_entrenado_completo.pkl', 'wb') as f:
        pickle.dump(trainer, f)
    print("\n💾 Entrenamiento completo guardado en 'cfr_entrenado_completo.pkl'")


    # Guardamos historiales por separado
    with open('historico_metricas.pkl', 'wb') as f:
        pickle.dump({
            'mean': history_mean,
            'std': history_std,
            'regret': history_avg_regret
        }, f)
    print("📊 Historial de métricas guardado en 'historico_metricas.pkl'")


if __name__ == '__main__':
    entrenamiento_completo()
