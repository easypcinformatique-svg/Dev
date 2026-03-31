#!/usr/bin/env python3
"""
Auto-Training Loop — Optimisation bayésienne des paramètres de trading.

Principe :
1. Lance un backtest avec les paramètres actuels
2. Analyse les métriques (Sharpe, win rate, PnL, drawdown)
3. Perturbe les paramètres dans la direction d'amélioration
4. Répète N fois
5. Garde les meilleurs paramètres trouvés

Inspiré des méthodes d'optimisation de Renaissance Technologies et Two Sigma.
"""

import sys
import time
import json
import copy
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, asdict

sys.path.insert(0, str(Path(__file__).parent))

from backtest.data_generator import generate_dataset
from backtest.engine import BacktestEngine, BacktestConfig
from backtest.strategies import AlphaCompositeStrategy


# ================================================================
#  PARAMÈTRES OPTIMISABLES
# ================================================================

@dataclass
class TrainableParams:
    """Paramètres de la stratégie à optimiser."""
    # AlphaComposite
    min_consensus: float = 0.35
    min_agreeing_strategies: int = 2
    spread_filter: float = 0.06
    volume_percentile_filter: float = 30.0
    max_price_extreme: float = 0.90
    min_price_extreme: float = 0.10
    # Risk
    stop_loss: float = 0.12
    take_profit: float = 0.40
    trailing_stop: float = 0.08
    max_position_pct: float = 0.03
    max_positions: int = 8
    # Backtest
    initial_capital: float = 100000.0

    def to_strategy(self) -> AlphaCompositeStrategy:
        strat = AlphaCompositeStrategy(
            min_consensus=self.min_consensus,
            min_agreeing_strategies=self.min_agreeing_strategies,
            spread_filter=self.spread_filter,
            volume_percentile_filter=self.volume_percentile_filter,
            max_price_extreme=self.max_price_extreme,
            min_price_extreme=self.min_price_extreme,
            stop_loss=self.stop_loss,
            take_profit=self.take_profit,
            trailing_stop=self.trailing_stop,
            max_position_pct=self.max_position_pct,
            max_positions=self.max_positions,
        )
        # Désactiver le sentiment pour le backtest (pas de réseau)
        strat.sentiment = None
        return strat


# ================================================================
#  SCORE COMPOSITE (objectif à maximiser)
# ================================================================

def compute_fitness(metrics) -> float:
    """
    Score de fitness multi-objectif.
    Combine rendement, risque, et qualité des trades.
    Inspiré de l'approche Sharpe-adjusted-return de AQR.
    """
    if metrics.total_trades < 5:
        return -100.0  # Pas assez de trades = mauvais

    # Composantes
    sharpe = max(-3, min(5, metrics.sharpe_ratio))
    sortino = max(-3, min(5, metrics.sortino_ratio))
    win_rate = metrics.win_rate
    profit_factor = min(5, metrics.profit_factor)
    max_dd = abs(metrics.max_drawdown)
    total_return = metrics.total_return
    n_trades = metrics.total_trades

    # Pénalités
    dd_penalty = max(0, max_dd - 0.15) * 5  # Pénalité si DD > 15%
    trade_penalty = max(0, 10 - n_trades) * 0.5  # Encourager un minimum de trades
    loss_penalty = max(0, 0.40 - win_rate) * 3  # Pénalité si win rate < 40%

    # Score composite pondéré
    fitness = (
        sharpe * 2.0 +           # Rendement ajusté au risque (le plus important)
        sortino * 1.0 +           # Pénalise la downside vol
        total_return * 3.0 +      # Rendement brut
        profit_factor * 0.5 +     # Ratio gains/pertes
        win_rate * 1.5 +          # Taux de réussite
        min(n_trades / 50, 1) * 0.5 -  # Bonus pour activité
        dd_penalty -
        trade_penalty -
        loss_penalty
    )

    return fitness


# ================================================================
#  PERTURBATION DES PARAMÈTRES
# ================================================================

def perturb_params(
    params: TrainableParams,
    rng: np.random.Generator,
    temperature: float = 1.0,
    best_params: TrainableParams = None,
) -> TrainableParams:
    """
    Perturbe les paramètres avec un recuit simulé.
    Temperature élevée = exploration, basse = exploitation.
    Si best_params fourni, on tend vers les meilleurs paramètres connus.
    """
    new = copy.deepcopy(params)

    # Facteur de perturbation (diminue avec la température)
    scale = 0.15 * temperature

    # Perturbation gaussienne pour chaque paramètre continu
    perturbations = {
        "min_consensus": (0.10, 0.60, scale),
        "spread_filter": (0.02, 0.15, scale * 0.5),
        "volume_percentile_filter": (5, 60, scale * 15),
        "max_price_extreme": (0.80, 0.98, scale * 0.05),
        "min_price_extreme": (0.02, 0.20, scale * 0.05),
        "stop_loss": (0.05, 0.25, scale * 0.5),
        "take_profit": (0.15, 0.80, scale * 0.5),
        "trailing_stop": (0.03, 0.20, scale * 0.5),
        "max_position_pct": (0.01, 0.08, scale * 0.3),
    }

    for param_name, (low, high, s) in perturbations.items():
        current_val = getattr(new, param_name)

        # Si on a un best_params, tendre vers lui (exploitation)
        if best_params is not None and rng.random() < 0.3:
            best_val = getattr(best_params, param_name)
            # Crossover vers le meilleur
            target = 0.7 * current_val + 0.3 * best_val
        else:
            target = current_val

        # Perturbation gaussienne
        noise = rng.normal(0, s)
        new_val = target + noise
        new_val = max(low, min(high, new_val))
        setattr(new, param_name, new_val)

    # Paramètres discrets
    if rng.random() < 0.15 * temperature:
        new.min_agreeing_strategies = int(rng.choice([1, 2, 3]))
    if rng.random() < 0.10 * temperature:
        new.max_positions = int(rng.choice([5, 6, 8, 10, 12]))

    return new


# ================================================================
#  BOUCLE D'ENTRAÎNEMENT
# ================================================================

def run_single_backtest(params: TrainableParams, dataset, configs) -> dict:
    """Lance un seul backtest et retourne les résultats."""
    strategy = params.to_strategy()
    bt_config = BacktestConfig(
        initial_capital=params.initial_capital,
        transaction_fee_pct=0.002,
        slippage_pct=0.001,
    )
    engine = BacktestEngine(strategy=strategy, config=bt_config)
    result = engine.run(dataset, configs)

    fitness = compute_fitness(result.metrics)

    return {
        "fitness": fitness,
        "metrics": result.metrics,
        "n_trades": result.metrics.total_trades,
        "sharpe": result.metrics.sharpe_ratio,
        "return": result.metrics.total_return,
        "win_rate": result.metrics.win_rate,
        "max_dd": result.metrics.max_drawdown,
        "profit_factor": result.metrics.profit_factor,
        "sortino": result.metrics.sortino_ratio,
        "pnl": result.metrics.cumulative_pnl,
    }


def train(
    n_iterations: int = 100,
    n_markets: int = 20,
    seeds: list[int] = None,
):
    """
    Boucle d'entraînement principale.

    Utilise plusieurs seeds pour éviter l'overfitting sur un seul dataset.
    """
    if seeds is None:
        seeds = [42, 123, 256, 789, 1337]

    rng = np.random.default_rng(2024)

    # Générer les datasets (plusieurs pour robustesse)
    print("=" * 70)
    print("  AUTO-TRAINING LOOP — OPTIMISATION DES PARAMETRES")
    print("=" * 70)
    print(f"\n  Iterations : {n_iterations}")
    print(f"  Marchés    : {n_markets} par seed")
    print(f"  Seeds      : {seeds}")
    print()

    print("[1/3] Génération des datasets d'entraînement...")
    datasets = []
    for seed in seeds:
        ds, cfgs = generate_dataset(n_markets=n_markets, freq="1D", seed=seed)
        datasets.append((ds, cfgs))
        print(f"  Seed {seed}: {len(ds):,} barres, {len(cfgs)} marchés")
    print()

    # Paramètres initiaux
    current_params = TrainableParams()
    best_params = copy.deepcopy(current_params)
    best_fitness = -999.0
    best_metrics = None

    # Historique
    history = []

    print("[2/3] Lancement de la boucle d'optimisation...\n")
    print(f"{'Iter':>4} | {'Fitness':>8} | {'Best':>8} | {'Sharpe':>7} | {'Return':>8} | "
          f"{'WinRate':>7} | {'MaxDD':>7} | {'Trades':>6} | {'PF':>6} | Action")
    print("-" * 105)

    start_time = time.time()

    for iteration in range(1, n_iterations + 1):
        # Température de recuit simulé (décroît avec les itérations)
        temperature = max(0.1, 1.0 - iteration / n_iterations * 0.8)

        # Perturber les paramètres
        if iteration == 1:
            candidate = current_params
        else:
            candidate = perturb_params(current_params, rng, temperature, best_params)

        # Évaluer sur TOUS les datasets (moyenne pour robustesse = anti-overfitting)
        fitness_scores = []
        all_results = []
        for ds, cfgs in datasets:
            try:
                result = run_single_backtest(candidate, ds, cfgs)
                fitness_scores.append(result["fitness"])
                all_results.append(result)
            except Exception as e:
                fitness_scores.append(-100)

        avg_fitness = np.mean(fitness_scores)
        min_fitness = np.min(fitness_scores)

        # Fitness robuste : moyenne pondérée avec pénalité pour la pire seed
        robust_fitness = 0.7 * avg_fitness + 0.3 * min_fitness

        # Métriques moyennes pour le log
        if all_results:
            avg_sharpe = np.mean([r["sharpe"] for r in all_results])
            avg_return = np.mean([r["return"] for r in all_results])
            avg_wr = np.mean([r["win_rate"] for r in all_results])
            avg_dd = np.mean([r["max_dd"] for r in all_results])
            avg_trades = np.mean([r["n_trades"] for r in all_results])
            avg_pf = np.mean([r["profit_factor"] for r in all_results])
        else:
            avg_sharpe = avg_return = avg_wr = avg_dd = avg_trades = avg_pf = 0

        # Décision : accepter ou rejeter
        action = ""
        if robust_fitness > best_fitness:
            # Nouveau meilleur !
            improvement = robust_fitness - best_fitness
            best_fitness = robust_fitness
            best_params = copy.deepcopy(candidate)
            best_metrics = all_results
            current_params = copy.deepcopy(candidate)
            action = f"*** BEST (+{improvement:.2f}) ***"
        elif robust_fitness > avg_fitness * 0.9:
            # Metropolis-Hastings : accepter parfois les solutions moins bonnes
            # pour éviter les minima locaux
            accept_prob = np.exp((robust_fitness - best_fitness) / max(temperature, 0.01))
            if rng.random() < accept_prob * 0.3:
                current_params = copy.deepcopy(candidate)
                action = f"accept (p={accept_prob:.2f})"
            else:
                action = "reject"
        else:
            action = "reject"

        # Log
        print(f"{iteration:4d} | {robust_fitness:8.2f} | {best_fitness:8.2f} | "
              f"{avg_sharpe:7.3f} | {avg_return:7.2%} | {avg_wr:6.1%} | "
              f"{avg_dd:6.2%} | {avg_trades:6.0f} | {avg_pf:5.2f} | {action}")

        # Sauvegarder l'historique
        history.append({
            "iteration": iteration,
            "fitness": robust_fitness,
            "best_fitness": best_fitness,
            "sharpe": avg_sharpe,
            "return": avg_return,
            "win_rate": avg_wr,
            "max_dd": avg_dd,
            "trades": avg_trades,
            "profit_factor": avg_pf,
            "temperature": temperature,
            "action": action.split(" ")[0] if action else "reject",
        })

    elapsed = time.time() - start_time

    # ================================================================
    #  RÉSULTATS FINAUX
    # ================================================================
    print("\n" + "=" * 70)
    print("  RÉSULTATS DE L'ENTRAÎNEMENT")
    print("=" * 70)
    print(f"\n  Durée totale : {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  Itérations   : {n_iterations}")
    print(f"  Best fitness : {best_fitness:.4f}")

    # Compter les améliorations
    improvements = sum(1 for h in history if "BEST" in h["action"])
    print(f"  Améliorations: {improvements}/{n_iterations}")

    # Meilleurs paramètres
    print(f"\n  --- MEILLEURS PARAMETRES TROUVÉS ---")
    print(f"  min_consensus           : {best_params.min_consensus:.4f}")
    print(f"  min_agreeing_strategies : {best_params.min_agreeing_strategies}")
    print(f"  spread_filter           : {best_params.spread_filter:.4f}")
    print(f"  volume_percentile_filter: {best_params.volume_percentile_filter:.1f}")
    print(f"  max_price_extreme       : {best_params.max_price_extreme:.4f}")
    print(f"  min_price_extreme       : {best_params.min_price_extreme:.4f}")
    print(f"  stop_loss               : {best_params.stop_loss:.4f}")
    print(f"  take_profit             : {best_params.take_profit:.4f}")
    print(f"  trailing_stop           : {best_params.trailing_stop:.4f}")
    print(f"  max_position_pct        : {best_params.max_position_pct:.4f}")
    print(f"  max_positions           : {best_params.max_positions}")

    if best_metrics:
        print(f"\n  --- MÉTRIQUES MOYENNES (sur {len(seeds)} seeds) ---")
        avg_sharpe = np.mean([r["sharpe"] for r in best_metrics])
        avg_return = np.mean([r["return"] for r in best_metrics])
        avg_wr = np.mean([r["win_rate"] for r in best_metrics])
        avg_dd = np.mean([r["max_dd"] for r in best_metrics])
        avg_pf = np.mean([r["profit_factor"] for r in best_metrics])
        avg_pnl = np.mean([r["pnl"] for r in best_metrics])
        print(f"  Sharpe Ratio    : {avg_sharpe:.3f}")
        print(f"  Return total    : {avg_return:.2%}")
        print(f"  Win Rate        : {avg_wr:.1%}")
        print(f"  Max Drawdown    : {avg_dd:.2%}")
        print(f"  Profit Factor   : {avg_pf:.3f}")
        print(f"  PnL moyen       : ${avg_pnl:,.2f}")

    # Sauvegarder les résultats
    results = {
        "best_params": asdict(best_params),
        "best_fitness": best_fitness,
        "n_iterations": n_iterations,
        "n_improvements": improvements,
        "elapsed_seconds": elapsed,
        "history": history,
    }

    output_path = Path("training_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Résultats sauvegardés dans {output_path}")

    print("\n" + "=" * 70)

    return best_params, history


# ================================================================
#  MAIN
# ================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Auto-Training Loop")
    parser.add_argument("--iterations", type=int, default=100, help="Nombre d'itérations")
    parser.add_argument("--markets", type=int, default=20, help="Marchés par seed")
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 123, 256, 789, 1337],
                        help="Seeds pour les datasets")
    args = parser.parse_args()

    best_params, history = train(
        n_iterations=args.iterations,
        n_markets=args.markets,
        seeds=args.seeds,
    )
