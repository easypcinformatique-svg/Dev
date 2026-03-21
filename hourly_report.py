#!/usr/bin/env python3
"""
Rapport combiné — Insurance Seller Bot + Intraday Fader Bot.
Envoi via ntfy.sh avec couleurs (emojis), échéances, PnL détaillé.
"""

import json
import os
import requests
from datetime import datetime, timedelta, timezone

INSURANCE_STATE = "logs/insurance_bot/state.json"
INTRADAY_STATE = "logs/intraday_bot/state.json"
REPORT_DIR = "logs/reports"
CLOB_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "insurance-bot-easypc-03757")

os.makedirs(REPORT_DIR, exist_ok=True)


def get_current_price(token_id):
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


def get_market_end_date(condition_id):
    """Récupère la date d'échéance d'un marché via Gamma API."""
    try:
        resp = requests.get(
            f"{GAMMA_API}/markets",
            params={"condition_id": condition_id},
            timeout=10,
        )
        if resp.ok:
            markets = resp.json()
            if markets:
                end_str = markets[0].get("endDate") or markets[0].get("end_date_iso", "")
                if end_str:
                    return datetime.fromisoformat(end_str.replace("Z", "+00:00"))
    except Exception:
        pass
    return None


def load_state(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def format_time_left(end_date):
    """Formate le temps restant avant échéance."""
    if not end_date:
        return "?"
    now = datetime.now(timezone.utc)
    if isinstance(end_date, str):
        try:
            end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except Exception:
            return "?"
    delta = end_date - now
    if delta.total_seconds() < 0:
        return "EXPIRÉ"
    days = delta.days
    hours = delta.seconds // 3600
    if days > 0:
        return f"{days}j {hours}h"
    elif hours > 0:
        mins = (delta.seconds % 3600) // 60
        return f"{hours}h{mins:02d}"
    else:
        mins = delta.seconds // 60
        return f"{mins}min"


def pnl_emoji(pnl):
    """Retourne l'emoji couleur selon le PnL."""
    if pnl > 0:
        return "🟢"
    elif pnl < 0:
        return "🔴"
    return "⚪"


def pnl_str(pnl):
    """Formate le PnL avec signe."""
    if pnl >= 0:
        return f"+${pnl:.2f}"
    return f"-${abs(pnl):.2f}"


def generate_insurance_section(state):
    """Section Insurance Seller Bot avec couleurs et échéances."""
    if not state:
        return "", 0, 0, 0

    capital_initial = 5000.0
    capital_dispo = state.get("capital", 0)
    positions = state.get("positions", {})
    trade_log = state.get("trade_log", [])

    lines = []
    total_unrealized = 0.0
    total_invested = 0.0

    for cid, pos in positions.items():
        entry = pos["entry_price"]
        shares = pos["shares"]
        size = pos["size_usd"]
        question = pos.get("market_question", "?")[:40]
        token_id = pos["token_id"]

        # Prix actuel
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

        # Échéance
        end_date = get_market_end_date(cid)
        time_left = format_time_left(end_date)
        expiry_str = ""
        if end_date:
            if isinstance(end_date, datetime):
                expiry_str = end_date.strftime("%d/%m %Hh")
            else:
                expiry_str = str(end_date)[:10]

        emoji = pnl_emoji(pnl)
        lines.append(
            f"{emoji} {pos['side']} ${size:.0f} @ {entry:.3f}→{current:.3f} "
            f"| {pnl_str(pnl)} ({pnl_pct:+.1f}%)\n"
            f"   📅 Éch: {expiry_str} (reste {time_left})\n"
            f"   📊 {question}"
        )

    wins = sum(1 for t in trade_log if t.get("pnl", 0) > 0)
    losses = sum(1 for t in trade_log if t.get("pnl", 0) <= 0)
    total_closed_pnl = sum(t.get("pnl", 0) for t in trade_log)
    equity = capital_dispo + total_invested + total_unrealized
    total_pnl = total_closed_pnl + total_unrealized
    exposure = (total_invested / equity * 100) if equity > 0 else 0

    e_total = pnl_emoji(total_pnl)
    e_real = pnl_emoji(total_closed_pnl)
    e_latent = pnl_emoji(total_unrealized)

    section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 INSURANCE SELLER BOT (Swing)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Capital: ${capital_dispo:,.2f} / ${capital_initial:,.0f}
💼 Equity:  ${equity:,.2f}
{e_real} PnL réalisé:  {pnl_str(total_closed_pnl)}
{e_latent} PnL latent:   {pnl_str(total_unrealized)}
{e_total} PnL TOTAL:    {pnl_str(total_pnl)}
📋 Positions: {len(positions)}/6 | Expo: {exposure:.0f}%
🏆 Trades: {len(trade_log)} (✅{wins} ❌{losses})
"""

    if lines:
        section += "\n📌 POSITIONS OUVERTES:\n"
        for line in lines:
            section += f"\n{line}\n"
    else:
        section += "\n📌 Aucune position ouverte\n"

    # Derniers trades clôturés
    if trade_log:
        section += "\n🔄 Derniers trades:\n"
        for t in trade_log[-5:]:
            tp = t.get("pnl", 0)
            eq = pnl_emoji(tp)
            q = t.get("question", t.get("market_question", "?"))[:35]
            reason = t.get("reason", "?")
            section += f"  {eq} {pnl_str(tp)} [{reason}] {q}\n"

    return section, total_pnl, equity, len(positions)


def generate_intraday_section(state):
    """Section Intraday Fader Bot avec couleurs et échéances."""
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
    wins = stats.get("wins", 0)
    losses = stats.get("losses", 0)

    e_daily = pnl_emoji(daily_pnl)
    e_total = pnl_emoji(total_pnl)

    section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ INTRADAY FADER BOT (Court terme)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Bankroll:  ${bankroll:,.2f}
{e_daily} PnL jour:    {pnl_str(daily_pnl)}
{e_total} PnL TOTAL:   {pnl_str(total_pnl)}
🏆 Win rate:  {win_rate:.0%} ({total_trades} trades: ✅{wins} ❌{losses})
📊 Avg: 🟢{pnl_str(avg_win)} / 🔴{pnl_str(avg_loss)}
📋 Positions: {len(positions)}/5
"""

    if positions:
        section += "\n📌 POSITIONS OUVERTES:\n"
        now = datetime.now(timezone.utc)
        for pos in positions:
            q = pos.get("question", "?")[:40]
            side = pos.get("side", "?")
            size = pos.get("size_usd", 0)
            sig = pos.get("signal_type", "?")
            entry_price = pos.get("entry_price", 0)
            entry_time = pos.get("entry_time", "")
            max_hold = pos.get("max_hold_hours", 4)
            conf = pos.get("confidence", 0)
            target = pos.get("target_price", 0)
            stop = pos.get("stop_price", 0)

            # Temps restant avant time-stop
            time_left_str = "?"
            if entry_time:
                try:
                    et = datetime.fromisoformat(entry_time)
                    expires_at = et + timedelta(hours=max_hold)
                    time_left_str = format_time_left(expires_at)
                    expiry_date = expires_at.strftime("%d/%m %Hh%M")
                except Exception:
                    expiry_date = "?"
            else:
                expiry_date = "?"

            section += (
                f"\n{'🟢' if 'YES' in side else '🔴'} {side} ${size:.2f} @ {entry_price:.4f}\n"
                f"   🎯 TP={target:.4f} | SL={stop:.4f} | Conf={conf:.0%}\n"
                f"   📅 Éch: {expiry_date} (reste {time_left_str})\n"
                f"   ⚡ [{sig}] {q}\n"
            )
    else:
        section += "\n📌 Aucune position ouverte\n"

    # Derniers trades
    if trade_history:
        section += "\n🔄 Derniers trades:\n"
        for t in trade_history[-5:]:
            tp = t.get("pnl", 0)
            eq = pnl_emoji(tp)
            q = t.get("question", "?")[:30]
            reason = t.get("exit_reason", "?")
            sig = t.get("signal_type", "?")
            held = ""
            if t.get("entry_time") and t.get("exit_time"):
                try:
                    e = datetime.fromisoformat(t["entry_time"])
                    x = datetime.fromisoformat(t["exit_time"])
                    dur = x - e
                    held = f" ({dur.seconds // 3600}h{(dur.seconds % 3600) // 60:02d})"
                except Exception:
                    pass
            section += f"  {eq} {pnl_str(tp)} [{reason}]{held} {q}\n"

    return section, total_pnl, bankroll, len(positions)


def generate_report():
    """Génère le rapport combiné avec couleurs et échéances."""
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

    e_combined = pnl_emoji(combined_pnl)

    report = f"""
🏦 POLYMARKET TRADING SUITE
📅 {now.strftime('%d/%m/%Y %H:%M:%S')}
══════════════════════════════════════
{e_combined} PnL COMBINÉ:  {pnl_str(combined_pnl)}
💼 Equity:      ${combined_equity:,.2f}
📋 Positions:   {total_positions}
"""

    if ins_section:
        report += ins_section

    if int_section:
        report += int_section

    report += "\n══════════════════════════════════════\n"

    # Sauvegarder en local
    filename = f"{REPORT_DIR}/report_{now.strftime('%Y%m%d_%H%M%S')}.txt"
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(filename, "w") as f:
        f.write(report)

    print(report)
    print(f"Rapport sauvegardé: {filename}")

    # Envoyer via ntfy
    send_notification(report, combined_pnl, combined_equity, total_positions)


def send_notification(report, total_pnl, equity, nb_positions):
    """Envoie via ntfy.sh avec emojis couleur."""
    e = "📈" if total_pnl >= 0 else "📉"
    title = f"{e} Polymarket | {pnl_str(total_pnl)} | {nb_positions} pos | ${equity:,.0f}"

    try:
        resp = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=report.encode("utf-8"),
            headers={
                "Title": title.encode("utf-8"),
                "Tags": "chart_with_upwards_trend" if total_pnl >= 0 else "chart_with_downwards_trend",
                "Priority": "4" if abs(total_pnl) > 50 else "3",
                "Content-Type": "text/plain; charset=utf-8",
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
