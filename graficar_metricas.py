import pickle
import matplotlib.pyplot as plt
import os


def cargar_metricas(path='historico_metricas.pkl'):
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Archivo '{path}' no encontrado. Entrena primero con entrenamiento_completo.py")


    with open(path, 'rb') as f:
        data = pickle.load(f)


    return data['mean'], data['std'], data['regret']


def graficar_metricas():
    history_mean, history_std, history_avg_regret = cargar_metricas()


    fases = ['preflop', 'flop', 'turn', 'river']


    # --- Mean (payoff normalizado) ---
    plt.figure(figsize=(10, 6))
    for fase in fases:
        if history_mean[fase]:
            iters, means = zip(*history_mean[fase])
            plt.plot(iters, means, label=fase)
    plt.xlabel('Iteraciones')
    plt.ylabel('Mean (payoff normalizado)')
    plt.title('Media del payoff por iteración')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


    # --- Desviación típica ---
    plt.figure(figsize=(10, 6))
    for fase in fases:
        if history_std[fase]:
            iters, stds = zip(*history_std[fase])
            plt.plot(iters, stds, label=fase)
    plt.xlabel('Iteraciones')
    plt.ylabel('Desviación Típica')
    plt.title('Desviación típica del payoff por iteración')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


    # --- Average positive regret (en log-scale) ---
    plt.figure(figsize=(10, 6))
    for fase in fases:
        if history_avg_regret[fase]:
            iters, regrets = zip(*history_avg_regret[fase])
            plt.plot(iters, regrets, label=fase)
    plt.xscale('log')
    plt.xlabel('Iteraciones (escala log)')
    plt.ylabel('Average Positive Regret')
    plt.title('Convergencia de MCCFR (regret promedio positivo)')
    plt.legend()
    plt.grid(True, which='both', linestyle='--')
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    graficar_metricas()



