"""Backtest : parier sur le favori de chaque match de Ligue 1 2025-26.

Capital 50 000 EUR, 2 000 EUR par match. Favori = equipe avec la cote la plus basse
(cotes Bet365 de cloture, repli : moyenne marche). Les matchs d'un meme jour sont
mises en meme temps : on ne joue que les matchs que le capital du matin peut couvrir.
Usage : python favorites.py [chemin_csv]
"""
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

CAPITAL = 50_000
STAKE = 2_000
CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("F1_2025-26.csv")


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("FTR")]
    for r in rows:
        r["dt"] = datetime.strptime(f"{r['Date']} {r['Time']}", "%d/%m/%Y %H:%M")
        h = float(r["B365CH"] or r["AvgCH"])
        a = float(r["B365CA"] or r["AvgCA"])
        r["fav"], r["odd"] = ("H", h) if h <= a else ("A", a)
    return sorted(rows, key=lambda r: r["dt"])


def main():
    rows = load(CSV)
    by_day = defaultdict(list)
    for r in rows:
        by_day[r["dt"].date()].append(r)

    capital, peak, low, max_dd = CAPITAL, CAPITAL, CAPITAL, 0.0
    bets = wins = 0
    odds = []
    month = defaultdict(float)
    buckets = defaultdict(lambda: [0, 0, 0.0])  # tranche de cote -> paris, gagnes, gain
    for day in sorted(by_day):
        n = min(len(by_day[day]), int(capital // STAKE))
        for r in by_day[day][:n]:
            won = r["FTR"] == r["fav"]
            pnl = STAKE * (r["odd"] - 1) if won else -STAKE
            capital += pnl
            bets += 1
            wins += won
            odds.append(r["odd"])
            month[day.strftime("%Y-%m")] += pnl
            b = "< 1.40" if r["odd"] < 1.4 else "1.40-1.80" if r["odd"] < 1.8 else ">= 1.80"
            buckets[b][0] += 1; buckets[b][1] += won; buckets[b][2] += pnl
        peak = max(peak, capital)
        low = min(low, capital)
        max_dd = max(max_dd, peak - capital)

    print(f"Capital {CAPITAL:,} EUR | {STAKE:,} EUR par match | favori de chaque match\n")
    print(f"Paris : {bets} | favoris gagnants : {wins} ({wins / bets:.1%}) | cote moyenne : {sum(odds) / len(odds):.2f}")
    print(f"Total mise : {bets * STAKE:,} EUR")
    print(f"Capital final : {capital:,.0f} EUR (resultat {capital - CAPITAL:+,.0f} EUR, "
          f"ROI sur mises {(capital - CAPITAL) / (bets * STAKE):+.1%})")
    print(f"Capital au plus bas : {low:,.0f} EUR | au plus haut : {peak:,.0f} EUR | drawdown max : {max_dd:,.0f} EUR")
    print("\nPar mois :")
    for k, v in sorted(month.items()):
        print(f"  {k} : {v:+,.0f}")
    print("\nPar tranche de cote :")
    for k in ["< 1.40", "1.40-1.80", ">= 1.80"]:
        n, w, p = buckets[k]
        print(f"  {k:10} {n:>4} paris | {w / n:.1%} gagnes | {p:+,.0f} EUR | ROI {p / (n * STAKE):+.1%}")


if __name__ == "__main__":
    main()
