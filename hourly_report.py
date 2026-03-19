#!/usr/bin/env python3
"""Rapport horaire combiné — Insurance Seller Bot + Intraday Fader Bot."""

import json
import os
import requests
from datetime import datetime, timedelta

INSURANCE_STATE = "logs/insurance_bot/state.json"
INTRADAY_STATE = "logs/intraday_bot/state.json"
REPORT_DIR = "logs/reports"
CLOB_API = "https://clob.polymarket.com"
NTFY_TOPIC = "insurance-bot-easypc-03757"

os.makedirs(REPORT_DIR, exist_ok=True)


def get_current_price(token_id):
    """Récupère le prix actuel d'un token sur Polymarket."""
    try:
        resp = requests.get(
            f"{CLOB_API}/price",
            params={"token_id": token_id, "side": "sell"},
            timeout=10,
        )
        if resp.ok:
            return float(resp.json().get("price", 0))
    except Exception:
        pass
    return None


def load_state(path):
    """Charge un fichier state.json."""
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def generate_insurance_section(state):
    """Génère la section du rapport pour le bot Insurance Seller."""
    if not state:
        return "", 0, 0, 0

    capital_initial = 5000.0
    capital_dispo = state.get("capital", 0)
    positions = state.get("positions", {})
    trade_log = state.get("trade_log", [])
    iteration = state.get("iteration", 0)

    lines = []
    total_unrealized = 0.0
    total_invested = 0.0

    for cid, pos in positions.items():
        entry = pos["entry_price"]
        shares = pos["shares"]
        size = pos["size_usd"]
        question = pos.get("market_question", "?")[:45]
        token_id = pos["token_id"]

        current = get_current_price(token_id)
        if current is not None:
            value_now = shares * current
            cost = shares * entry
            pnl = value_now - cost
            pnl_pct = (pnl / cost * 100) if cost > 0 else 0
            total_unrealized += pnl
        else:
            current = entry
            pnl = 0
            pnl_pct = 0

        total_invested += size
        sign = "+" if pnl >= 0 else ""
        lines.append(
            f"  {pos['side']} | ${size:>6.0f} @ {entry:.3f} → {current:.3f} | "
            f"{sign}${pnl:.2f} ({sign}{pnl_pct:.1f}%) | {question}"
        )

    wins = sum(1 for t in trade_log if t.get("pnl", 0) > 0)
    losses = sum(1 for t in trade_log if t.get("pnl", 0) <= 0)
    total_closed_pnl = sum(t.get("pnl", 0) for t in trade_log)
    equity = capital_dispo + total_invested + total_unrealized
    total_pnl = total_closed_pnl + total_unrealized
    exposure = (total_invested / equity * 100) if equity > 0 else 0

    section = f"""
║  INSURANCE SELLER BOT (Swing)                           ║
╠══════════════════════════════════════════════════════════╣
║  Capital initial:   ${capital_initial:>10,.2f}                       ║
║  Capital dispo:     ${capital_dispo:>10,.2f}                       ║
║  Equity estimée:    ${equity:>10,.2f}                       ║
║  PnL réalisé:      {'+' if total_closed_pnl >= 0 else ''}${total_closed_pnl:>10,.2f}                       ║
║  PnL latent:       {'+' if total_unrealized >= 0 else ''}${total_unrealized:>10,.2f}                       ║
║  PnL TOTAL:        {'+' if total_pnl >= 0 else ''}${total_pnl:>10,.2f}                       ║
║  Positions:         {len(positions)} / 6   Expo: {exposure:.0f}%                   ║
║  Trades clôturés:   {len(trade_log)}  (W:{wins} / L:{losses})                   ║
╠══════════════════════════════════════════════════════════╣
"""
    for line in lines:
        section += f"║ {line:<57s}║\n"
    if not lines:
        section += "║  Aucune position ouverte.                                ║\n"

    return section, total_pnl, equity, len(positions)


def generate_intraday_section(state):
    """Génère la section du rapport pour le bot Intraday Fader."""
    if not state:
        return "", 0, 0, 0

    stats = state.get("stats", {})
    bankroll = state.get("bankroll", 0)
    positions = state.get("open_positions", [])
    trade_history = state.get("trade_history", [])
    daily_pnl = stats.get("daily_pnl", 0)
    total_pnl = stats.get("total_pnl", 0)
    win_rate = stats.get("win_rate", 0)
    total_trades = stats.get("total_trades", 0)
    avg_win = stats.get("avg_win", 0)
    avg_loss = stats.get("avg_loss", 0)

    section = f"""
║  INTRADAY FADER BOT (Court terme)                       ║
╠══════════════════════════════════════════════════════════╣
║  Bankroll:          ${bankroll:>10,.2f}                       ║
║  PnL journalier:   {'+' if daily_pnl >= 0 else ''}${daily_pnl:>10,.2f}                       ║
║  PnL TOTAL:        {'+' if total_pnl >= 0 else ''}${total_pnl:>10,.2f}                       ║
║  Win rate:          {win_rate:.0%}  ({total_trades} trades)                  ║
║  Avg Win/Loss:      ${avg_win:+.2f} / ${avg_loss:+.2f}                   ║
║  Positions:         {len(positions)} / 5                                ║
╠══════════════════════════════════════════════════════════╣
"""
    for pos in positions:
        q = pos.get("question", "?")[:40]
        side = pos.get("side", "?")[:8]
        size = pos.get("size_usd", 0)
        sig = pos.get("signal_type", "?")[:10]
        section += f"║  {side} ${size:>5.2f} [{sig}] | {q:<27s}║\n"

    if not positions:
        section += "║  Aucune position ouverte.                                ║\n"

    # Derniers trades
    if trade_history:
        section += "╠══════════════════════════════════════════════════════════╣\n"
        section += "║  Derniers trades:                                        ║\n"
        for t in trade_history[-5:]:
            pnl = t.get("pnl", 0)
            sign = "+" if pnl >= 0 else ""
            q = t.get("question", "?")[:35]
            reason = t.get("exit_reason", "?")[:10]
            section += f"║  {sign}${pnl:.2f} [{reason}] | {q:<30s}║\n"

    return section, total_pnl, bankroll, len(positions)


def generate_report():
    """Génère le rapport combiné."""
    now = datetime.now()

    insurance_state = load_state(INSURANCE_STATE)
    intraday_state = load_state(INTRADAY_STATE)

    if not insurance_state and not intraday_state:
        print("Aucun bot actif trouvé.")
        return

    ins_section, ins_pnl, ins_equity, ins_pos = generate_insurance_section(insurance_state)
    int_section, int_pnl, int_bankroll, int_pos = generate_intraday_section(intraday_state)

    combined_pnl = ins_pnl + int_pnl
    combined_equity = ins_equity + int_bankroll
    total_positions = ins_pos + int_pos

    report = f"""
╔══════════════════════════════════════════════════════════╗
║     RAPPORT COMBINÉ — POLYMARKET TRADING SUITE          ║
║     {now.strftime('%Y-%m-%d %H:%M:%S'):^52s}║
╠══════════════════════════════════════════════════════════╣
║  PnL COMBINÉ:     {'+' if combined_pnl >= 0 else ''}${combined_pnl:>10,.2f}                       ║
║  Equity totale:    ${combined_equity:>10,.2f}                       ║
║  Positions:         {total_positions}                                     ║
╠══════════════════════════════════════════════════════════╣
"""

    if ins_section:
        report += ins_section

    if int_section:
        report += int_section

    report += "╚══════════════════════════════════════════════════════════╝\n"

    # Sauvegarder
    filename = f"{REPORT_DIR}/report_{now.strftime('%Y%m%d_%H%M%S')}.txt"
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(filename, "w") as f:
        f.write(report)

    print(report)
    print(f"Rapport sauvegardé: {filename}")

    # Notification ntfy
    send_notification(report, combined_pnl, combined_equity, total_positions)


def send_notification(report, total_pnl, equity, nb_positions):
    """Envoie via ntfy.sh."""
    sign = "+" if total_pnl >= 0 else ""
    title = f"Polymarket Suite | {sign}${total_pnl:.2f} | {nb_positions} pos"

    try:
        resp = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=report.encode("utf-8"),
            headers={
                "Title": title,
                "Tags": "chart_with_upwards_trend" if total_pnl >= 0 else "chart_with_downwards_trend",
                "Priority": "3",
            },
            timeout=10,
        )
        if resp.ok:
            print(f"Notification envoyée via ntfy.sh/{NTFY_TOPIC}")
        else:
            print(f"Erreur ntfy: {resp.status_code}")
    except Exception as e:
        print(f"Erreur notification: {e}")


if __name__ == "__main__":
    generate_report()
