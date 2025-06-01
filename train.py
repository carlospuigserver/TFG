# train_cfr.py

import pickle
import matplotlib.pyplot as plt
from cfr import CFRTrainer

def main():
    phases = ['preflop', 'flop', 'turn', 'river']

    # Instanciamos el CFRTrainer modificado
    trainer = CFRTrainer(
        iterations_map={'preflop': 20000, 'flop': 20000, 'turn': 20000, 'river': 20000},
        epsilon_map={'preflop': 0.05, 'flop': 0.01, 'turn': 0.02, 'river': 0.005}
    )

    # Para almacenar historial de mean, std y avg_regret
    history_mean = {phase: [] for phase in phases}
    history_std = {phase: [] for phase in phases}
    history_avg_regret = {phase: [] for phase in phases}

    def make_logger(phase):
        def logger(msg):
            print(msg)
            
            if msg.startswith("Iter") and "mean=" in msg and "std=" in msg and "avg_regret=" in msg:
                parts = msg.split()
                it = int(parts[1].strip(':'))

                mean_str = msg.split("mean=")[1].split(",")[0]
                mean_val = float(mean_str)

                std_str = msg.split("std=")[1].split(",")[0]
                std_val = float(std_str)

                avg_str = msg.split("avg_regret=")[1]
                avg_val = float(avg_str)

                history_mean[phase].append((it, mean_val))
                history_std[phase].append((it, std_val))
                history_avg_regret[phase].append((it, avg_val))
        return logger

    # Entrenamos fase por fase
    for phase in phases:
        trainer.train_phase(phase, st_logger=make_logger(phase))

    # Guardamos el modelo entrenado
    with open('cfr_entreno.pkl', 'wb') as f:
        pickle.dump(trainer, f)
    print('cfr_trainer.pkl actualizado')

    # --- Gráfica de Mean (payoff normalizado) vs Iteraciones ---
    plt.figure(figsize=(10, 6))
    for phase in phases:
        if history_mean[phase]:
            iters, means = zip(*history_mean[phase])
            plt.plot(iters, means, label=phase)
    plt.xlabel('Iteraciones')
    plt.ylabel('Mean (payoff normalizado)')
    plt.title('Mean por iteración para cada fase')
    plt.legend()
    plt.grid(True)
    plt.show()

    # --- Gráfica de Desviación Típica (payoff normalizado) vs Iteraciones ---
    plt.figure(figsize=(10, 6))
    for phase in phases:
        if history_std[phase]:
            iters, stds = zip(*history_std[phase])
            plt.plot(iters, stds, label=phase)
    plt.xlabel('Iteraciones')
    plt.ylabel('Desviación Típica (payoff normalizado)')
    plt.title('Desviación Típica por iteración para cada fase')
    plt.legend()
    plt.grid(True)
    plt.show()

    # --- Gráfica de Average Positive Regret (normalizado) vs Iteraciones (Escala Log) ---
    plt.figure(figsize=(10, 6))
    for phase in phases:
        if history_avg_regret[phase]:
            iters, regrets = zip(*history_avg_regret[phase])
            plt.plot(iters, regrets, label=phase)
    plt.xscale('log')
    plt.xlabel('Iteraciones')
    plt.ylabel('Average positive regret (normalizado)')
    plt.title('Convergencia de MCCFR (Escala Log) por fase')
    plt.legend()
    plt.grid(True, which='both', ls='--')
    plt.show()

if __name__ == '__main__':
    main()
