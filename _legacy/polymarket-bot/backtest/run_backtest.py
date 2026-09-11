#!/usr/bin/env python3
"""
Point d'entrée principal — 3 modes de fonctionnement :

1. BACKTEST SIMULE (défaut):
   python -m backtest.run_backtest --mode sim --strategy alpha

2. BACKTEST DONNEES REELLES POLYMARKET:
   python -m backtest.run_backtest --mode real --strategy alpha --top-markets 20

3. TRADING LIVE (paper ou real):
   python -m backtest.run_backtest --mode live --strategy alpha --capital 1000
   python -m backtest.run_backtest --mode live --strategy alpha --capital 1000 --real-money --private-key 0x...
"""

import argparse
import os
import time
import logging

from .data_generator import generate_dataset
from .strategies import (
    MomentumStrategy,
    MeanReversionStrategy,
    ValueStrategy,
    CompositeStrategy,
    SmartMoneyStrategy,
    ConvergenceStrategy,
    BayesianEdgeStrategy,
    AdaptiveMomentumStrategy,
    LiquidityEdgeStrategy,
    AlphaCompositeStrategy,
    InsuranceSellerStrategy,
)
from .engine import BacktestEngine, BacktestConfig
from .report import generate_report


STRATEGIES = {
    # --- Stratégies de base ---
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
    # --- Stratégies avancées ---
    "smart_money": lambda: SmartMoneyStrategy(
        lookback=36, volume_spike_threshold=1.8,
        max_position_pct=0.04, stop_loss=0.10, take_profit=0.25,
    ),
    "convergence": lambda: ConvergenceStrategy(
        min_market_progress=0.55, trend_lookback=48,
        max_position_pct=0.05, stop_loss=0.12, take_profit=0.30,
    ),
    "bayesian": lambda: BayesianEdgeStrategy(
        lookback=60, edge_threshold=0.05,
        max_position_pct=0.04, stop_loss=0.10, take_profit=0.25,
    ),
    "adaptive": lambda: AdaptiveMomentumStrategy(
        fast_lookback=12, slow_lookback=48, hurst_lookback=80,
        max_position_pct=0.04, stop_loss=0.10, take_profit=0.25,
    ),
    "liquidity": lambda: LiquidityEdgeStrategy(
        lookback=36, spread_contraction_threshold=0.45,
        max_position_pct=0.04, stop_loss=0.10, take_profit=0.25,
    ),
    # --- Stratégie Alpha (optimisée par auto-training 100 itérations) ---
    "alpha": lambda: AlphaCompositeStrategy(
        min_consensus=0.14, min_agreeing_strategies=2,
        spread_filter=0.10, volume_percentile_filter=28,
        max_price_extreme=0.89, min_price_extreme=0.09,
        stop_loss=0.25, take_profit=0.50, trailing_stop=0.17,
        max_position_pct=0.08, max_positions=12,
    ),
    # --- Alpha calibrée pour données réelles Polymarket ---
    "alpha_real": lambda: AlphaCompositeStrategy(
        min_consensus=0.14, min_agreeing_strategies=1,
        spread_filter=0.10, volume_percentile_filter=10,
        min_price_extreme=0.05, max_price_extreme=0.95,
        sentiment_weight=0.30,
        stop_loss=0.25, take_profit=0.50, trailing_stop=0.17,
        max_position_pct=0.08, max_positions=12,
    ),
    # --- Insurance Seller (inspirée anoin123 : $1.45M profit) ---
    "insurance": lambda: InsuranceSellerStrategy(
        max_no_price=0.35,
        min_yes_price=0.65,
        ideal_no_price=0.10,
        panic_threshold=-0.15,
        fear_multiplier=1.5,
        max_entries_per_market=5,
        entry_cooldown_bars=12,
        max_exposure_pct=0.15,
        hard_stop_loss=0.25,            # Resserré (était 0.40)
        stop_loss=0.25,                 # Aligné
        trailing_stop=0.10,             # Resserré (était 0.15)
    ),
}


def run_sim_backtest(args):
    """Mode 1 : Backtest sur données simulées."""
    print("=" * 60)
    print("  POLYMARKET BACKTEST — DONNEES SIMULEES")
    print("=" * 60)
    print()

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

    strategy = STRATEGIES[args.strategy]()
    print(f"[2/4] Strategie: {strategy.name}")
    print(f"      -> Stop-loss: {strategy.stop_loss:.0%} | Take-profit: {strategy.take_profit:.0%}")
    print()

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

    print(result.metrics.summary())

    if not args.no_report:
        print(f"\n[4/4] Generation du rapport...")
        report_path = generate_report(result, output_path=args.output)
        print(f"      -> {report_path}")

    return result


def run_real_backtest(args):
    """Mode 2 : Backtest sur données réelles Polymarket."""
    from .polymarket_client import PolymarketClient

    print("=" * 60)
    print("  POLYMARKET BACKTEST — DONNEES REELLES")
    print("=" * 60)
    print()

    client = PolymarketClient()

    # 1. Récupérer les marchés
    print(f"[1/5] Recuperation des top {args.top_markets} marches Polymarket...")
    markets = client.get_all_active_markets(
        min_volume=args.min_volume,
        min_liquidity=args.min_liquidity,
        max_markets=args.top_markets,
    )
    print(f"      -> {len(markets)} marches trouves")
    for m in markets[:5]:
        print(f"         - {m.question[:60]} (vol=${m.volume:,.0f})")
    if len(markets) > 5:
        print(f"         ... et {len(markets) - 5} autres")
    print()

    # 2. Télécharger les historiques
    print(f"[2/5] Telechargement des historiques de prix...")
    import pandas as pd
    all_data = []
    for i, market in enumerate(markets):
        print(f"      [{i+1}/{len(markets)}] {market.question[:50]}...", end=" ")
        try:
            df = client.get_market_history_for_backtest(
                market,
                fidelity=args.fidelity,
            )
            if len(df) > 30:
                all_data.append(df)
                print(f"OK ({len(df)} barres)")
            else:
                print("SKIP (pas assez de donnees)")
        except Exception as e:
            print(f"ERREUR ({e})")

    if not all_data:
        print("Aucune donnee recuperee. Verifiez votre connexion.")
        return None

    dataset = pd.concat(all_data, ignore_index=True)
    dataset = dataset.sort_values(["timestamp", "market_id"]).reset_index(drop=True)
    print(f"\n      -> {len(dataset):,} barres totales")
    print(f"      -> {len(all_data)} marches avec donnees")
    print()

    # 3. Stratégie
    strategy = STRATEGIES[args.strategy]()
    print(f"[3/5] Strategie: {strategy.name}")
    print()

    # 4. Backtest
    # On crée des MarketConfig factices (pas de résolution pour les marchés actifs)
    from .data_generator import MarketConfig
    from datetime import datetime, timedelta

    configs = []
    for market in markets:
        if any(market.condition_id == d["market_id"].iloc[0] for d in [df for df in all_data] if len(d) > 0):
            configs.append(MarketConfig(
                market_id=market.condition_id,
                question=market.question,
                category=market.category,
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2026, 12, 31),
                resolution_date=datetime(2027, 1, 1),  # Pas de résolution
                outcome=True,
                initial_prob=market.yes_price,
            ))

    print(f"[4/5] Execution du backtest (capital: ${args.capital:,.0f})...")
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

    print(result.metrics.summary())

    if not args.no_report:
        print(f"\n[5/5] Generation du rapport...")
        report_path = generate_report(result, output_path=args.output)
        print(f"      -> {report_path}")

    return result


def run_live(args):
    """Mode 3 : Trading live sur Polymarket."""
    from .live_trader import LiveTrader, LiveTraderConfig

    print("=" * 60)
    if args.real_money:
        print("  POLYMARKET LIVE TRADER — REAL MONEY")
    else:
        print("  POLYMARKET LIVE TRADER — PAPER TRADING")
    print("=" * 60)
    print()

    strategy = STRATEGIES[args.strategy]()
    print(f"Strategie: {strategy.name}")
    print(f"Capital: ${args.capital:,.0f}")
    print()

    config = LiveTraderConfig(
        initial_capital=args.capital,
        max_position_pct=0.05,
        max_total_exposure_pct=0.30,
        max_positions=8,
        min_market_volume=args.min_volume,
        min_market_liquidity=args.min_liquidity,
        scan_interval_seconds=args.scan_interval,
        dry_run=not args.real_money,
    )

    private_key = args.private_key or os.environ.get("POLYMARKET_PRIVATE_KEY")
    if args.real_money and not private_key:
        print("ERREUR: --private-key ou POLYMARKET_PRIVATE_KEY requis pour le live trading")
        return None

    trader = LiveTrader(
        strategy=strategy,
        config=config,
        private_key=private_key,
    )

    print("Demarrage du trader...")
    print("Ctrl+C pour arreter\n")

    trader.run(max_iterations=args.max_iterations)

    summary = trader.get_summary()
    print("\n--- RESUME ---")
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")

    return trader


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Trading Bot — Backtest & Live",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Backtest simule
  python -m backtest.run_backtest --mode sim --strategy alpha --markets 30

  # Backtest donnees reelles Polymarket
  python -m backtest.run_backtest --mode real --strategy alpha --top-markets 20

  # Paper trading live
  python -m backtest.run_backtest --mode live --strategy alpha --capital 1000

  # Real money trading
  python -m backtest.run_backtest --mode live --strategy alpha --capital 1000 --real-money --private-key 0x...
        """,
    )

    # Mode
    parser.add_argument(
        "--mode", choices=["sim", "real", "live"],
        default="sim", help="Mode: sim=simulated, real=real data backtest, live=live trading",
    )

    # Stratégie
    parser.add_argument(
        "--strategy", choices=list(STRATEGIES.keys()),
        default="alpha", help="Strategie de trading (defaut: alpha)",
    )

    # Capital
    parser.add_argument("--capital", type=float, default=100000, help="Capital initial ($)")

    # Backtest sim
    parser.add_argument("--markets", type=int, default=30, help="[sim] Nombre de marches")
    parser.add_argument("--freq", default="4h", help="[sim] Frequence: 1h, 4h, 1D")
    parser.add_argument("--seed", type=int, default=42, help="[sim] Seed aleatoire")

    # Backtest real
    parser.add_argument("--top-markets", type=int, default=20, help="[real] Nombre de top marches")
    parser.add_argument("--fidelity", type=int, default=60, help="[real] Granularite en minutes")
    parser.add_argument("--min-volume", type=float, default=50000, help="[real/live] Volume minimum")
    parser.add_argument("--min-liquidity", type=float, default=5000, help="[real/live] Liquidite minimum")

    # Live
    parser.add_argument("--real-money", action="store_true", help="[live] Trading reel (ATTENTION!)")
    parser.add_argument("--private-key", help="[live] Cle privee du wallet (ou env POLYMARKET_PRIVATE_KEY)")
    parser.add_argument("--scan-interval", type=int, default=300, help="[live] Intervalle scan en secondes")
    parser.add_argument("--max-iterations", type=int, default=0, help="[live] Max iterations (0=infini)")

    # Output
    parser.add_argument("--output", default="backtest_report.html", help="Fichier rapport HTML")
    parser.add_argument("--no-report", action="store_true", help="Ne pas generer le rapport")

    args = parser.parse_args()

    if args.mode == "sim":
        return run_sim_backtest(args)
    elif args.mode == "real":
        return run_real_backtest(args)
    elif args.mode == "live":
        return run_live(args)


if __name__ == "__main__":
    main()
