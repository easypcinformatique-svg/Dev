"""Backtest : miser 10 000 EUR sur le match nul a chaque match de Ligue 1 2025-26.

Source des donnees : football-data.co.uk (F1_2025-26.csv).
Usage : python backtest.py [chemin_csv]
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

STAKE = 10_000
CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("F1_2025-26.csv")

# colonne de cote "nul" -> libelle
BOOKS = {
    "B365D": "Bet365 (ouverture)",
    "PSD": "Pinnacle (ouverture)",
    "AvgD": "Moyenne marche (ouverture)",
    "MaxD": "Meilleure cote (ouverture)",
    "B365CD": "Bet365 (cloture)",
    "PSCD": "Pinnacle (cloture)",
    "AvgCD": "Moyenne marche (cloture)",
    "MaxCD": "Meilleure cote (cloture)",
}


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r.get("FTR")]


def run(rows, col):
    staked = profit = 0.0
    bets = wins = 0
    bankroll, peak, max_dd = 0.0, 0.0, 0.0
    by_month = defaultdict(float)
    for r in rows:
        odd = r.get(col)
        if not odd:
            continue
        odd = float(odd)
        pnl = STAKE * (odd - 1) if r["FTR"] == "D" else -STAKE
        bets += 1
        wins += r["FTR"] == "D"
        staked += STAKE
        profit += pnl
        bankroll += pnl
        peak = max(peak, bankroll)
        max_dd = max(max_dd, peak - bankroll)
        d, m, y = r["Date"].split("/")
        by_month[f"{y}-{m}"] += pnl
    return dict(bets=bets, wins=wins, staked=staked, profit=profit, max_dd=max_dd, by_month=by_month)


def main():
    rows = load(CSV)
    draws = sum(r["FTR"] == "D" for r in rows)
    print(f"Matchs : {len(rows)} | Nuls : {draws} ({draws / len(rows):.1%})\n")
    print(f"{'Bookmaker':30} {'Paris':>5} {'Gagnes':>6} {'Mise totale':>13} {'Gain net':>12} {'ROI':>7} {'Drawdown max':>13}")
    for col, label in BOOKS.items():
        s = run(rows, col)
        print(f"{label:30} {s['bets']:>5} {s['wins']:>6} {s['staked']:>13,.0f} {s['profit']:>12,.0f} "
              f"{s['profit'] / s['staked']:>7.1%} {s['max_dd']:>13,.0f}")

    s = run(rows, "B365CD")
    print("\nP&L par mois (Bet365 cloture) :")
    cum = 0.0
    for month in sorted(s["by_month"]):
        cum += s["by_month"][month]
        print(f"  {month} : {s['by_month'][month]:>10,.0f}  (cumul {cum:>10,.0f})")


if __name__ == "__main__":
    main()
