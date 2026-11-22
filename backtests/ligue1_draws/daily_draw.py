"""Backtest : capital 100 000 EUR, 5 000 EUR max par jour sur le nul du match le plus important du jour.

Un seul pari par jour de match (la mise se libere le soir meme).
"Match le plus important" selon deux definitions :
  - equilibre : le match le plus serre du jour (cote du nul la plus basse = nul le plus probable)
  - affiche   : le match entre les deux equipes les mieux classees au moment du match
Ligue 1 2025-26, cotes Bet365 de cloture (repli : moyenne marche).
Usage : python daily_draw.py [chemin_csv]
"""
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

CAPITAL = 100_000
STAKE = 5_000
CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("F1_2025-26.csv")


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("FTR")]
    for r in rows:
        r["dt"] = datetime.strptime(f"{r['Date']} {r['Time']}", "%d/%m/%Y %H:%M")
        r["odd"] = float(r["B365CD"] or r["AvgCD"])
    return sorted(rows, key=lambda r: r["dt"])


def rank_key(table, team):
    pts, gd, gf = table[team]
    return (pts, gd, gf)


def run(rows, pick):
    table = defaultdict(lambda: [0, 0, 0])  # points, diff, buts pour (avant le jour)
    by_day = defaultdict(list)
    for r in rows:
        by_day[r["dt"].date()].append(r)

    capital, peak, max_dd, low = CAPITAL, CAPITAL, 0.0, CAPITAL
    bets = wins = 0
    log = []
    for day in sorted(by_day):
        matches = by_day[day]
        if capital >= STAKE:
            m = pick(matches, table)
            won = m["FTR"] == "D"
            pnl = STAKE * (m["odd"] - 1) if won else -STAKE
            capital += pnl
            bets += 1
            wins += won
            peak = max(peak, capital)
            low = min(low, capital)
            max_dd = max(max_dd, peak - capital)
            log.append((day, m, pnl, capital))
        for r in matches:  # mise a jour du classement apres la journee
            hg, ag = int(r["FTHG"]), int(r["FTAG"])
            h, a = table[r["HomeTeam"]], table[r["AwayTeam"]]
            h[0] += 3 if hg > ag else 1 if hg == ag else 0
            a[0] += 3 if ag > hg else 1 if hg == ag else 0
            h[1] += hg - ag; a[1] += ag - hg
            h[2] += hg; a[2] += ag
    return dict(bets=bets, wins=wins, capital=capital, max_dd=max_dd, low=low, log=log)


def most_balanced(matches, table):
    return min(matches, key=lambda r: r["odd"])


def top_fixture(matches, table):
    teams = sorted(table, key=lambda t: rank_key(table, t), reverse=True)
    pos = {t: i for i, t in enumerate(teams)}
    worst = len(pos) + 1
    return min(matches, key=lambda r: pos.get(r["HomeTeam"], worst) + pos.get(r["AwayTeam"], worst))


def main():
    rows = load(CSV)
    print(f"Capital {CAPITAL:,} EUR | mise {STAKE:,} EUR | 1 pari max par jour de match\n")
    for name, pick in [("Match le plus serre", most_balanced), ("Affiche (meilleurs classes)", top_fixture)]:
        s = run(rows, pick)
        print(f"== {name} ==")
        print(f"  Paris : {s['bets']} | nuls gagnes : {s['wins']} ({s['wins'] / s['bets']:.1%})")
        print(f"  Capital final : {s['capital']:,.0f} EUR  (resultat {s['capital'] - CAPITAL:+,.0f} EUR, "
              f"{(s['capital'] - CAPITAL) / CAPITAL:+.1%})")
        print(f"  Capital au plus bas : {s['low']:,.0f} EUR | drawdown max : {s['max_dd']:,.0f} EUR")
        month = defaultdict(float)
        for day, m, pnl, cap in s["log"]:
            month[day.strftime("%Y-%m")] += pnl
        print("  Par mois : " + " | ".join(f"{k} {v:+,.0f}" for k, v in sorted(month.items())))
        print()


if __name__ == "__main__":
    main()
