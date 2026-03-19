#!/usr/bin/env python3
"""Rapport horaire du Insurance Seller Bot."""

import json
import os
import requests
from datetime import datetime, timedelta

STATE_FILE = "logs/insurance_bot/state.json"
REPORT_DIR = "logs/insurance_bot/reports"
CLOB_API = "https://clob.polymarket.com"

os.makedirs(REPORT_DIR, exist_ok=True)

def get_current_price(token_id):
    """Récupère le prix actuel d'un token sur Polymarket."""
    try:
        resp = requests.get(f"{CLOB_API}/price", params={"token_id": token_id, "side": "sell"}, timeout=10)
        if resp.ok:
            return float(resp.json().get("price", 0))
    except Exception:
        pass
    return None

def generate_report():
    if not os.path.exists(STATE_FILE):
        print("Pas de fichier state.json trouvé.")
        return

    with open(STATE_FILE) as f:
        state = json.load(f)

    now = datetime.now()
    capital_initial = 5000.0
    capital_dispo = state.get("capital", 0)
    positions = state.get("positions", {})
    trade_log = state.get("trade_log", [])
    iteration = state.get("iteration", 0)
    total_pnl_realized = state.get("total_pnl", 0)

    # Calcul PnL latent par position
    lines = []
    total_unrealized = 0.0
    total_invested = 0.0

    for cid, pos in positions.items():
        entry = pos["entry_price"]
        shares = pos["shares"]
        size = pos["size_usd"]
        question = pos["market_question"][:50]
        token_id = pos["token_id"]
        entry_time = pos.get("entry_time", "?")

        current = get_current_price(token_id)
        if current is not None:
            # Pour NO: on a acheté à entry, prix actuel = current
            # Valeur actuelle = shares * (1 - current_YES) mais on a le prix NO
            # PnL = shares * (current_NO - entry_NO) ... mais on veut le prix NO
            # current est le prix SELL du token, donc c'est ce qu'on obtiendrait en vendant
            value_now = shares * current
            cost = shares * entry
            pnl = value_now - cost
            pnl_pct = (pnl / cost * 100) if cost > 0 else 0
            total_unrealized += pnl
        else:
            current = entry
            pnl = 0
            pnl_pct = 0
            value_now = size

        total_invested += size

        sign = "+" if pnl >= 0 else ""
        lines.append(
            f"  {pos['side']} | ${size:>7.0f} @ {entry:.3f} → {current:.3f} | "
            f"{sign}${pnl:.2f} ({sign}{pnl_pct:.1f}%) | {question}"
        )

    # Trades clôturés
    wins = sum(1 for t in trade_log if t.get("pnl", 0) > 0)
    losses = sum(1 for t in trade_log if t.get("pnl", 0) <= 0)
    total_closed_pnl = sum(t.get("pnl", 0) for t in trade_log)

    equity = capital_dispo + total_invested + total_unrealized
    total_pnl = total_closed_pnl + total_unrealized
    total_pnl_pct = (total_pnl / capital_initial * 100) if capital_initial > 0 else 0
    exposure = (total_invested / equity * 100) if equity > 0 else 0

    report = f"""
╔══════════════════════════════════════════════════════════╗
║        RAPPORT HORAIRE — INSURANCE SELLER BOT           ║
║        {now.strftime('%Y-%m-%d %H:%M:%S'):^48s}║
╠══════════════════════════════════════════════════════════╣
║  Capital initial:   ${capital_initial:>10,.2f}                       ║
║  Capital dispo:     ${capital_dispo:>10,.2f}                       ║
║  Equity estimée:    ${equity:>10,.2f}                       ║
║                                                          ║
║  PnL réalisé:      {'+' if total_closed_pnl >= 0 else ''}${total_closed_pnl:>10,.2f}                       ║
║  PnL latent:       {'+' if total_unrealized >= 0 else ''}${total_unrealized:>10,.2f}                       ║
║  PnL TOTAL:        {'+' if total_pnl >= 0 else ''}${total_pnl:>10,.2f}  ({'+' if total_pnl_pct >= 0 else ''}{total_pnl_pct:.2f}%)             ║
║                                                          ║
║  Positions:         {len(positions)} / 6                                ║
║  Exposition:        {exposure:.1f}%                                 ║
║  Cycles exécutés:   {iteration}                                    ║
║  Trades clôturés:   {len(trade_log)}  (W:{wins} / L:{losses})                   ║
╠══════════════════════════════════════════════════════════╣
║  POSITIONS OUVERTES                                      ║
╠══════════════════════════════════════════════════════════╣
"""
    for line in lines:
        report += f"║ {line:<57s}║\n"

    if not lines:
        report += "║  Aucune position ouverte.                                ║\n"

    # Derniers trades clôturés
    if trade_log:
        report += "╠══════════════════════════════════════════════════════════╣\n"
        report += "║  DERNIERS TRADES CLÔTURÉS                                ║\n"
        report += "╠══════════════════════════════════════════════════════════╣\n"
        for t in trade_log[-5:]:
            sign = "+" if t.get("pnl", 0) >= 0 else ""
            q = t.get("market_question", "?")[:40]
            report += f"║  {sign}${t.get('pnl',0):.2f} | {q:<42s}║\n"

    report += "╚══════════════════════════════════════════════════════════╝\n"

    # Sauvegarder
    filename = f"{REPORT_DIR}/report_{now.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, "w") as f:
        f.write(report)

    # Aussi afficher
    print(report)
    print(f"Rapport sauvegardé: {filename}")

if __name__ == "__main__":
    generate_report()
