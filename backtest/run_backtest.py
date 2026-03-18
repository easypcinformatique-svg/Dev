#!/usr/bin/env python3
"""
Point d'entrée principal du moteur de backtesting Polymarket.

Usage:
    python -m backtest.run_backtest [options]

    --strategy    Stratégie à utiliser: momentum, mean_reversion, value, composite (défaut: composite)
    --markets     Nombre de marchés à simuler (défaut: 30)
    --capital     Capital initial en USD (défaut: 100000)
    --freq        Fréquence des données: 1h, 4h, 1D (défaut: 4h)
    --seed        Seed aléatoire pour reproductibilité (défaut: 42)
    --output      Chemin du rapport HTML (défaut: backtest_report.html)
    --no-report   Ne pas générer le rapport HTML
"""

import argparse
import sys
import time

from .data_generator import generate_dataset
from .strategies import (
    MomentumStrategy,
    MeanReversionStrategy,
    ValueStrategy,
    CompositeStrategy,
)
from .engine import BacktestEngine, BacktestConfig
from .report import generate_report


STRATEGIES = {
    "momentum": lambda: MomentumStrategy(
        lookback=24, momentum_threshold=0.05, volume_filter=1.2,
        max_position_pct=0.05, stop_loss=0.15, take_profit=0.30,
    ),
    "mean_reversion": lambda: MeanReversionStrategy(
        lookback=48, z_score_threshold=1.5,
        max_position_pct=0.04, stop_loss=0.12, take_profit=0.25,
    ),
    "value": lambda: ValueStrategy(
        lookback=72, edge_threshold=0.08,
        max_position_pct=0.05, stop_loss=0.15, take_profit=0.35,
    ),
    "composite": lambda: CompositeStrategy(
        consensus_threshold=0.4,
        max_position_pct=0.05, max_positions=10,
        stop_loss=0.15, take_profit=0.30,
    ),
}


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Backtesting Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--strategy", choices=list(STRATEGIES.keys()),
        default="composite", help="Stratégie de trading",
    )
    parser.add_argument("--markets", type=int, default=30, help="Nombre de marchés")
    parser.add_argument("--capital", type=float, default=100000, help="Capital initial ($)")
    parser.add_argument("--freq", default="4h", help="Fréquence des données")
    parser.add_argument("--seed", type=int, default=42, help="Seed aléatoire")
    parser.add_argument("--output", default="backtest_report.html", help="Fichier rapport")
    parser.add_argument("--no-report", action="store_true", help="Skip le rapport HTML")
    args = parser.parse_args()

    print("=" * 60)
    print("  POLYMARKET BACKTESTING ENGINE")
    print("=" * 60)
    print()

    # 1. Générer les données
    print(f"[1/4] Generation de {args.markets} marches simules ({args.freq})...")
    t0 = time.time()
    dataset, configs = generate_dataset(
        n_markets=args.markets,
        freq=args.freq,
        seed=args.seed,
    )
    dt = time.time() - t0
    print(f"      -> {len(dataset):,} barres generees en {dt:.1f}s")
    print(f"      -> Categories: {dataset['category'].nunique()}")
    print(f"      -> Periode: {dataset['timestamp'].min()} -> {dataset['timestamp'].max()}")
    print()

    # 2. Initialiser la stratégie
    print(f"[2/4] Initialisation strategie: {args.strategy}")
    strategy = STRATEGIES[args.strategy]()
    print(f"      -> {strategy.name}")
    print(f"      -> Max positions: {strategy.max_positions}")
    print(f"      -> Stop-loss: {strategy.stop_loss:.0%} | Take-profit: {strategy.take_profit:.0%}")
    print()

    # 3. Exécuter le backtest
    print(f"[3/4] Execution du backtest (capital: ${args.capital:,.0f})...")
    bt_config = BacktestConfig(
        initial_capital=args.capital,
        transaction_fee_pct=0.002,
        slippage_pct=0.001,
    )
    engine = BacktestEngine(strategy=strategy, config=bt_config)

    t0 = time.time()
    result = engine.run(dataset, configs)
    dt = time.time() - t0
    print(f"      -> Backtest termine en {dt:.1f}s")
    print()

    # 4. Afficher les résultats
    print(result.metrics.summary())
    print()

    # 5. Générer le rapport
    if not args.no_report:
        print(f"[4/4] Generation du rapport interactif...")
        report_path = generate_report(result, output_path=args.output)
        print(f"      -> Rapport sauvegarde: {report_path}")
        print()
        print(f"Ouvrir le rapport: file://{report_path}")
    else:
        print("[4/4] Rapport HTML skipe (--no-report)")

    print()
    print("Done.")

    return result


if __name__ == "__main__":
    main()
