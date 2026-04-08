"""
Générateur de données historiques Polymarket simulées.

Simule des marchés de prédiction binaires avec des distributions réalistes :
- Courbes de probabilité avec mean-reversion et jumps
- Volumes suivant des distributions log-normales avec cycles journaliers
- Spreads bid/ask réalistes qui s'élargissent en basse liquidité
- Résolution des marchés avec convergence vers 0 ou 1
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class MarketConfig:
    """Configuration d'un marché de prédiction."""
    market_id: str
    question: str
    category: str
    start_date: datetime
    end_date: datetime
    resolution_date: datetime
    outcome: bool  # True = Yes wins, False = No wins
    initial_prob: float = 0.5
    volatility: float = 0.03
    mean_reversion_speed: float = 0.02
    jump_probability: float = 0.05
    jump_magnitude: float = 0.15
    base_volume: float = 50000.0
    volume_volatility: float = 0.8
    min_spread: float = 0.01
    max_spread: float = 0.08


# Templates de marchés réalistes par catégorie
MARKET_TEMPLATES = [
    {"category": "politics", "questions": [
        "Will {candidate} win the {year} presidential election?",
        "Will {party} win the Senate majority in {year}?",
        "Will {leader} resign before {date}?",
        "Will {country} hold elections before {date}?",
    ], "volatility_range": (0.02, 0.06), "volume_range": (100000, 5000000)},
    {"category": "crypto", "questions": [
        "Will Bitcoin exceed ${price}K by {date}?",
        "Will Ethereum merge to PoS by {date}?",
        "Will {token} reach $1 by {date}?",
    ], "volatility_range": (0.04, 0.10), "volume_range": (50000, 2000000)},
    {"category": "sports", "questions": [
        "Will {team} win the {league} championship {year}?",
        "Will {player} score {n}+ goals this season?",
    ], "volatility_range": (0.02, 0.05), "volume_range": (30000, 1000000)},
    {"category": "economics", "questions": [
        "Will US GDP growth exceed {pct}% in Q{q} {year}?",
        "Will the Fed raise rates in {month} {year}?",
        "Will inflation drop below {pct}% by {date}?",
    ], "volatility_range": (0.01, 0.04), "volume_range": (80000, 3000000)},
    {"category": "tech", "questions": [
        "Will {company} release {product} by {date}?",
        "Will AI pass {benchmark} by {date}?",
    ], "volatility_range": (0.02, 0.06), "volume_range": (40000, 1500000)},
    {"category": "geopolitics", "questions": [
        "Will {country} impose sanctions on {target} by {date}?",
        "Will {treaty} be signed by {date}?",
    ], "volatility_range": (0.03, 0.07), "volume_range": (60000, 2000000)},
]


def _clamp(value: float, low: float = 0.01, high: float = 0.99) -> float:
    return max(low, min(high, value))


def generate_probability_path(
    config: MarketConfig,
    freq: str = "1h",
    rng: Optional[np.random.Generator] = None,
) -> pd.DataFrame:
    """
    Génère un chemin de probabilité réaliste pour un marché.

    Utilise un processus d'Ornstein-Uhlenbeck (mean-reverting) avec :
    - Bruit brownien pour la diffusion naturelle
    - Jumps de Poisson pour les événements news
    - Convergence finale vers le résultat réel
    - Cycles de volume intra-journaliers
    """
    if rng is None:
        rng = np.random.default_rng()

    timestamps = pd.date_range(
        start=config.start_date,
        end=config.resolution_date,
        freq=freq,
    )
    n = len(timestamps)
    if n < 2:
        raise ValueError("Le marché doit durer au moins 2 périodes")

    # --- Probabilité via processus O-U avec jumps ---
    prob = np.zeros(n)
    prob[0] = config.initial_prob

    # Le "vrai" prix converge progressivement vers le résultat
    final_target = 0.95 if config.outcome else 0.05
    convergence_targets = np.linspace(config.initial_prob, final_target, n)

    for i in range(1, n):
        # Fraction du temps écoulé (0 -> 1)
        t_frac = i / (n - 1)

        # Mean-reversion vers la cible convergente
        mean_rev = config.mean_reversion_speed * (convergence_targets[i] - prob[i - 1])

        # Volatilité décroissante en fin de marché
        vol = config.volatility * (1.0 - 0.5 * t_frac ** 2)

        # Bruit brownien
        dW = rng.normal(0, 1) * np.sqrt(1.0 / (24 if freq == "1h" else 1))
        diffusion = vol * dW

        # Jump de Poisson
        jump = 0.0
        if rng.random() < config.jump_probability / (24 if freq == "1h" else 1):
            direction = 1 if config.outcome else -1
            # 70% dans le sens du résultat, 30% contraire (faux signaux)
            if rng.random() > 0.7:
                direction *= -1
            jump = direction * config.jump_magnitude * rng.exponential(1.0)

        prob[i] = _clamp(prob[i - 1] + mean_rev + diffusion + jump)

    # Forcer la convergence finale
    n_final = max(1, n // 20)
    for i in range(n - n_final, n):
        alpha = (i - (n - n_final)) / n_final
        prob[i] = _clamp(prob[i] * (1 - alpha) + final_target * alpha)

    # --- Volume avec distribution log-normale et cycles ---
    hour_of_day = pd.Series(timestamps).dt.hour.values
    # Cycle journalier : pic à 14h-18h UTC (heures US)
    daily_cycle = 0.5 + 0.5 * np.exp(-0.5 * ((hour_of_day - 16) / 4) ** 2)
    # Effet week-end (volume réduit)
    day_of_week = pd.Series(timestamps).dt.dayofweek.values
    weekend_effect = np.where(day_of_week >= 5, 0.3, 1.0)
    # Volume de base log-normal
    log_vol = rng.normal(
        np.log(config.base_volume),
        config.volume_volatility,
        size=n,
    )
    raw_volume = np.exp(log_vol) * daily_cycle * weekend_effect
    # Volume augmente près de la résolution
    t_fracs = np.linspace(0, 1, n)
    resolution_boost = 1.0 + 2.0 * t_fracs ** 3
    # Volume augmente lors des jumps de probabilité
    prob_changes = np.abs(np.diff(prob, prepend=prob[0]))
    jump_boost = 1.0 + 10.0 * prob_changes
    volume = np.maximum(100, raw_volume * resolution_boost * jump_boost)

    # --- Spread bid/ask ---
    # Spread inversement proportionnel au volume, avec plancher
    normalized_vol = volume / np.median(volume)
    spread = config.min_spread + (config.max_spread - config.min_spread) / (
        1 + normalized_vol
    )
    # Bruit sur le spread
    spread *= 1 + 0.2 * rng.normal(0, 1, size=n)
    spread = np.clip(spread, config.min_spread, config.max_spread)

    bid = np.clip(prob - spread / 2, 0.01, 0.98)
    ask = np.clip(prob + spread / 2, 0.02, 0.99)

    # --- Nombre de trades ---
    avg_trade_size = rng.lognormal(np.log(500), 0.5, size=n)
    num_trades = np.maximum(1, (volume / avg_trade_size).astype(int))

    # --- Open interest cumulatif ---
    net_flow = rng.normal(0, volume * 0.1)
    open_interest = np.maximum(1000, np.cumsum(net_flow) + config.base_volume * 5)

    return pd.DataFrame({
        "timestamp": timestamps,
        "market_id": config.market_id,
        "mid_price": np.round(prob, 6),
        "bid_price": np.round(bid, 6),
        "ask_price": np.round(ask, 6),
        "spread": np.round(spread, 6),
        "volume_usd": np.round(volume, 2),
        "num_trades": num_trades,
        "open_interest": np.round(open_interest, 2),
    })


def generate_market_configs(
    n_markets: int = 50,
    start_date: datetime = datetime(2023, 1, 1),
    end_date: datetime = datetime(2025, 12, 31),
    rng: Optional[np.random.Generator] = None,
) -> list[MarketConfig]:
    """Génère N configurations de marchés réalistes."""
    if rng is None:
        rng = np.random.default_rng(42)

    configs = []
    for i in range(n_markets):
        template = MARKET_TEMPLATES[i % len(MARKET_TEMPLATES)]
        cat = template["category"]

        # Durée aléatoire entre 7 et 365 jours
        duration_days = int(rng.integers(7, 365))
        max_start = end_date - timedelta(days=duration_days + 1)
        if max_start <= start_date:
            max_start = start_date + timedelta(days=1)
        days_offset = int(rng.integers(0, max((max_start - start_date).days, 1)))
        m_start = start_date + timedelta(days=days_offset)
        m_end = m_start + timedelta(days=duration_days)
        m_resolution = m_end + timedelta(hours=int(rng.integers(1, 48)))

        vol_lo, vol_hi = template["volatility_range"]
        bv_lo, bv_hi = template["volume_range"]

        question = rng.choice(template["questions"])

        configs.append(MarketConfig(
            market_id=f"PM-{cat[:3].upper()}-{i:04d}",
            question=question,
            category=cat,
            start_date=m_start,
            end_date=m_end,
            resolution_date=m_resolution,
            outcome=bool(rng.random() > 0.45),  # Léger biais vers Yes
            initial_prob=float(_clamp(rng.beta(2, 2), 0.15, 0.85)),
            volatility=float(rng.uniform(vol_lo, vol_hi)),
            mean_reversion_speed=float(rng.uniform(0.005, 0.05)),
            jump_probability=float(rng.uniform(0.02, 0.10)),
            jump_magnitude=float(rng.uniform(0.05, 0.25)),
            base_volume=float(rng.uniform(bv_lo, bv_hi)),
            volume_volatility=float(rng.uniform(0.5, 1.2)),
            min_spread=float(rng.uniform(0.005, 0.02)),
            max_spread=float(rng.uniform(0.04, 0.12)),
        ))

    return configs


def generate_dataset(
    n_markets: int = 50,
    freq: str = "1h",
    seed: int = 42,
) -> tuple[pd.DataFrame, list[MarketConfig]]:
    """
    Génère un dataset complet de marchés Polymarket simulés.

    Returns:
        (DataFrame avec toutes les données OHLCV, liste des configs)
    """
    rng = np.random.default_rng(seed)
    configs = generate_market_configs(n_markets=n_markets, rng=rng)

    all_data = []
    for config in configs:
        df = generate_probability_path(config, freq=freq, rng=rng)
        df["category"] = config.category
        df["outcome"] = config.outcome
        df["question"] = config.question
        all_data.append(df)

    dataset = pd.concat(all_data, ignore_index=True)
    dataset = dataset.sort_values(["timestamp", "market_id"]).reset_index(drop=True)

    return dataset, configs
