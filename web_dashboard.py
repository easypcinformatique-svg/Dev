"""
Dashboard web temps reel pour le Hedge Fund Bot Polymarket.

Interface HTML/CSS/JS embarquee (pas de fichiers statiques externes).
Rafraichissement automatique toutes les 10 secondes.

Fonctionnalites :
    - Vue d'ensemble : equity, PnL, drawdown
    - Equity curve interactive (Chart.js via CDN)
    - Positions ouvertes avec PnL temps reel
    - Historique des trades
    - Statistiques detaillees
    - Log des erreurs

Usage :
    # Standalone (lecture du fichier d'etat)
    python web_dashboard.py --port 5050

    # Integre au bot (lance automatiquement)
    python hedge_fund_bot.py --dashboard --port 5050
"""

import csv
import json
import logging
import argparse
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta

from flask import Flask, jsonify, Response, request

from config_manager import ConfigManager


def _start_keep_alive(app_url: str, interval: int = 600):
    """Ping le serveur toutes les 10 min pour eviter le sleep du free tier."""
    import urllib.request

    def _ping():
        while True:
            try:
                urllib.request.urlopen(f"{app_url}/api/health", timeout=10)
            except Exception:
                pass
            import time
            time.sleep(interval)

    t = threading.Thread(target=_ping, daemon=True)
    t.start()


def create_dashboard_app(bot=None, state_file="bot_state.json", config_manager=None):
    """Cree l'application Flask du dashboard."""
    app = Flask(__name__)

    # Gestionnaire de configuration
    if config_manager is None:
        config_manager = ConfigManager()
    cm = config_manager

    def _get_data():
        """Recupere les donnees du bot ou du fichier d'etat."""
        if bot is not None:
            return bot.get_dashboard_data()

        # Mode standalone : lire le fichier d'etat
        path = Path(state_file)
        if not path.exists():
            return {"status": "no_data", "overview": {}, "positions": [],
                    "recent_trades": [], "trade_stats": {}, "equity_history": [],
                    "errors": []}

        try:
            with open(path) as f:
                state = json.load(f)

            positions = state.get("positions", {})
            trades = state.get("trades", [])

            # Fallback: charger l'historique depuis TradeLogger ou backtest
            if not trades:
                base = Path(state_file).parent
                # 1) TradeLogger JSON (logs/trades_real.json) — trades du bot live
                trade_logger_json = base / "logs" / "trades_real.json"
                if trade_logger_json.exists():
                    try:
                        with open(trade_logger_json) as f:
                            tl_data = json.load(f)
                        for ct in tl_data.get("closed_trades", []):
                            trades.append({
                                "market_id": ct.get("market_id", ""),
                                "question": ct.get("question", ct.get("market_id", "")),
                                "side": ct.get("side", ""),
                                "entry_price": float(ct.get("entry_price", 0)),
                                "exit_price": float(ct.get("exit_price", 0)),
                                "size_usd": float(ct.get("size_usd", 0)),
                                "pnl": float(ct.get("pnl_net", ct.get("pnl_gross", 0))),
                                "pnl_pct": float(ct.get("pnl_pct", 0)),
                                "entry_time": ct.get("entry_time", ""),
                                "exit_time": ct.get("exit_time", ""),
                                "reason": ct.get("exit_reason", ""),
                                "fees_total": float(ct.get("fees_total", 0)),
                            })
                    except Exception:
                        pass

                # 2) Backtest CSV (trades_report.csv) — historique backtest
                if not trades:
                    csv_path = base / "trades_report.csv"
                    if csv_path.exists():
                        try:
                            with open(csv_path) as csvf:
                                reader = csv.DictReader(csvf)
                                for row in reader:
                                    trades.append({
                                        "market_id": row.get("market_id", ""),
                                        "question": row.get("market_id", ""),
                                        "side": row.get("side", ""),
                                        "entry_price": float(row.get("entry_price", 0)),
                                        "exit_price": float(row.get("exit_price", 0)),
                                        "size_usd": float(row.get("montant_engage", 0)),
                                        "pnl": float(row.get("gain_perte", 0)),
                                        "pnl_pct": float(row.get("rendement_%", 0)),
                                        "entry_time": row.get("entry_time", ""),
                                        "exit_time": row.get("exit_time", ""),
                                        "reason": row.get("exit_reason", ""),
                                    })
                        except Exception:
                            pass

            # Calculer les frais si absents (2% du montant engagé)
            for t in trades:
                if "fees_total" not in t:
                    t["fees_total"] = round(t.get("size_usd", 0) * 0.02, 2)
                if "pnl_gross" not in t:
                    t["pnl_gross"] = t.get("pnl", 0) + t["fees_total"]
                if "pnl_net" not in t:
                    t["pnl_net"] = t.get("pnl", 0)

            pnls = [t.get("pnl", 0) for t in trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            total_fees = round(sum(t.get("fees_total", 0) for t in trades), 2)

            total_exposure = sum(
                p.get("size_usd", 0) for p in
                (positions.values() if isinstance(positions, dict) else positions)
            )
            total_unrealized = sum(
                p.get("unrealized_pnl", 0) for p in
                (positions.values() if isinstance(positions, dict) else positions)
            )
            capital = state.get("capital", 0)
            equity = capital + total_exposure + total_unrealized
            peak = state.get("peak_equity", equity)
            initial = 1000.0
            dd = (peak - equity) / peak if peak > 0 else 0

            return {
                "status": "running",
                "mode": "DRY RUN",
                "strategy": "AlphaComposite",
                "started_at": state.get("started_at", ""),
                "last_scan": state.get("last_scan", ""),
                "iteration": state.get("iteration", 0),
                "overview": {
                    "capital": round(capital, 2),
                    "equity": round(equity, 2),
                    "total_pnl": round(state.get("total_pnl", 0), 2),
                    "total_fees": total_fees,
                    "total_pnl_gross": round(state.get("total_pnl_gross", state.get("total_pnl", 0) + total_fees), 2),
                    "daily_pnl": round(state.get("daily_pnl", 0), 2),
                    "unrealized_pnl": round(total_unrealized, 2),
                    "exposure": round(total_exposure, 2),
                    "exposure_pct": round(total_exposure / max(equity, 1) * 100, 1),
                    "drawdown_pct": round(dd * 100, 2),
                    "peak_equity": round(peak, 2),
                    "initial_capital": initial,
                    "total_return_pct": round((equity / initial - 1) * 100, 2),
                },
                "positions": list(positions.values()) if isinstance(positions, dict) else positions,
                "recent_trades": trades[-20:],
                "all_trades": trades,
                "trade_stats": {
                    "total_trades": len(trades),
                    "winning_trades": len(wins),
                    "losing_trades": len(losses),
                    "win_rate": round(len(wins) / max(len(trades), 1) * 100, 1),
                    "avg_win": round(sum(wins) / max(len(wins), 1), 2),
                    "avg_loss": round(sum(losses) / max(len(losses), 1), 2),
                    "profit_factor": round(abs(sum(wins) / sum(losses)), 2) if losses else 0,
                    "largest_win": round(max(pnls), 2) if pnls else 0,
                    "largest_loss": round(min(pnls), 2) if pnls else 0,
                },
                "equity_history": state.get("equity_history", [])[-200:],
                "markets_scanned": state.get("markets_scanned", 0),
                "signals_generated": state.get("signals_generated", 0),
                "errors": state.get("errors", [])[-10:],
            }
        except Exception:
            return {"status": "error", "overview": {}, "positions": [],
                    "recent_trades": [], "all_trades": [], "trade_stats": {},
                    "equity_history": [], "errors": []}

    @app.route("/api/data")
    def api_data():
        return jsonify(_get_data())

    # ---- Settings API ----

    @app.route("/api/settings")
    def api_settings():
        """Retourne la config active avec metadonnees."""
        return jsonify(cm.get_active_with_meta())

    @app.route("/api/settings/update", methods=["POST"])
    def api_settings_update():
        """Met a jour des parametres."""
        updates = request.get_json(force=True)
        result = cm.update_params(updates)
        return jsonify(result)

    @app.route("/api/settings/reset", methods=["POST"])
    def api_settings_reset():
        """Restaure les parametres d'origine."""
        result = cm.reset_to_defaults()
        return jsonify(result)

    @app.route("/api/settings/diff")
    def api_settings_diff():
        """Compare la config active vs les defaults."""
        return jsonify(cm.get_diff())

    @app.route("/api/settings/profiles", methods=["GET"])
    def api_profiles_list():
        """Liste les profils sauvegardes."""
        profiles = list(cm.data.get("profiles", {}).keys())
        return jsonify({"profiles": profiles})

    @app.route("/api/settings/profiles/save", methods=["POST"])
    def api_profiles_save():
        """Sauvegarde la config active comme profil."""
        data = request.get_json(force=True)
        name = data.get("name", "")
        if not name:
            return jsonify({"error": "Nom requis"}), 400
        return jsonify(cm.save_profile(name))

    @app.route("/api/settings/profiles/load", methods=["POST"])
    def api_profiles_load():
        """Charge un profil."""
        data = request.get_json(force=True)
        name = data.get("name", "")
        if not name:
            return jsonify({"error": "Nom requis"}), 400
        return jsonify(cm.load_profile(name))

    @app.route("/api/settings/profiles/delete", methods=["POST"])
    def api_profiles_delete():
        """Supprime un profil."""
        data = request.get_json(force=True)
        name = data.get("name", "")
        if not name:
            return jsonify({"error": "Nom requis"}), 400
        return jsonify(cm.delete_profile(name))

    @app.route("/api/health")
    def api_health():
        """Endpoint de sante pour le keep-alive."""
        return jsonify({"status": "ok", "time": datetime.now().isoformat()})

    def _inject_version(html: str) -> str:
        """Injecte la version basee sur le dernier commit git (MAJ de code uniquement)."""
        import subprocess
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%cd", "--date=format:%Y-%m-%d %H:%M"],
                capture_output=True, text=True, timeout=5,
            )
            version = result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            version = "unknown"
        return html.replace("__BUILD_VERSION__", version)

    @app.route("/")
    def index():
        return Response(_inject_version(DASHBOARD_HTML), mimetype="text/html")

    @app.route("/settings")
    def settings_page():
        return Response(_inject_version(SETTINGS_HTML), mimetype="text/html")

    @app.route("/report")
    def report_page():
        return Response(_inject_version(REPORT_HTML), mimetype="text/html")

    return app


# ================================================================
#  DASHBOARD HTML/CSS/JS COMPLET (EMBARQUE)
# ================================================================

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Polymarket Hedge Fund Bot</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #0a0e17;
    color: #e0e6ed;
    min-height: 100vh;
}
.header {
    background: linear-gradient(135deg, #0d1321 0%, #1a1f35 100%);
    border-bottom: 1px solid #2a3a5c;
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.header h1 { font-size: 20px; color: #fff; font-weight: 600; }
.header h1 span { color: #6c63ff; }
.header-right { display: flex; gap: 16px; align-items: center; font-size: 13px; }
.status-badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
}
.status-running { background: #0d3320; color: #4ade80; border: 1px solid #22c55e; }
.status-stopped { background: #3b1818; color: #f87171; border: 1px solid #ef4444; }
.mode-badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    background: #1e1b4b;
    color: #a5b4fc;
    border: 1px solid #6366f1;
}

.container { max-width: 1400px; margin: 0 auto; padding: 20px; }

/* Cards grid */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}
.metric-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 16px 20px;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: #374151; }
.metric-label {
    font-size: 12px;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}
.metric-value {
    font-size: 24px;
    font-weight: 700;
    color: #fff;
}
.metric-value.positive { color: #4ade80; }
.metric-value.negative { color: #f87171; }
.metric-sub {
    font-size: 12px;
    color: #6b7280;
    margin-top: 4px;
}
/* Dashboard tooltips */
.metric-card { position: relative; cursor: help; }
.metric-tooltip {
    display: none;
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    bottom: 100%;
    z-index: 100;
    width: 300px;
    background: #1a1f35;
    border: 1px solid #6366f1;
    border-radius: 8px;
    padding: 10px 14px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.6);
    margin-bottom: 8px;
    font-size: 12px;
    color: #d1d5db;
    line-height: 1.5;
    pointer-events: none;
}
.metric-card:hover .metric-tooltip { display: block; }
.metric-tooltip strong { color: #a5b4fc; }
.metric-tooltip .tip-example { color: #4ade80; margin-top: 6px; font-size: 11px; }
.stat-row { position: relative; cursor: help; }
.stat-tooltip {
    display: none;
    position: absolute;
    left: 0;
    bottom: 100%;
    z-index: 100;
    width: 280px;
    background: #1a1f35;
    border: 1px solid #6366f1;
    border-radius: 8px;
    padding: 8px 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.6);
    margin-bottom: 6px;
    font-size: 11px;
    color: #d1d5db;
    line-height: 1.4;
    pointer-events: none;
}
.stat-row:hover .stat-tooltip { display: block; }

/* Chart */
.chart-container {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 24px;
}
.chart-container h2 {
    font-size: 16px;
    margin-bottom: 16px;
    color: #d1d5db;
}
.chart-wrapper { position: relative; height: 300px; }

/* Tables */
.table-container {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 24px;
    overflow-x: auto;
}
.table-container h2 {
    font-size: 16px;
    margin-bottom: 16px;
    color: #d1d5db;
}
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th {
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid #1f2937;
    color: #6b7280;
    font-weight: 500;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
    position: relative;
    cursor: help;
}
.th-tooltip {
    display: none;
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    bottom: 100%;
    z-index: 100;
    width: 250px;
    background: #1a1f35;
    border: 1px solid #6366f1;
    border-radius: 8px;
    padding: 8px 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.6);
    margin-bottom: 6px;
    font-size: 11px;
    color: #d1d5db;
    line-height: 1.4;
    pointer-events: none;
    text-transform: none;
    letter-spacing: normal;
    font-weight: 400;
}
th:hover .th-tooltip { display: block; }
td {
    padding: 10px 12px;
    border-bottom: 1px solid #111827;
    color: #d1d5db;
}
tr:hover td { background: #1a2332; }
.pnl-positive { color: #4ade80; font-weight: 600; }
.pnl-negative { color: #f87171; font-weight: 600; }

/* Two column layout */
.two-col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
}
@media (max-width: 900px) {
    .two-col { grid-template-columns: 1fr; }
}

/* Stats grid */
.stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}
.stat-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid #1a2332;
    font-size: 13px;
}
.stat-label { color: #6b7280; }
.stat-value { color: #e0e6ed; font-weight: 500; }

/* Errors */
.error-item {
    background: #1c1111;
    border: 1px solid #7f1d1d;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 12px;
}
.error-time { color: #9ca3af; font-size: 11px; }
.error-msg { color: #fca5a5; margin-top: 4px; }

.refresh-info {
    text-align: center;
    color: #374151;
    font-size: 12px;
    padding: 16px;
}
</style>
</head>
<body>

<div class="header">
    <h1><span>POLYMARKET</span> Hedge Fund Bot <span style="font-size:11px;color:#6b7280;font-weight:400;margin-left:8px;">v__BUILD_VERSION__</span></h1>
    <div class="header-right">
        <a href="/report" style="color:#a5b4fc;text-decoration:none;font-size:13px;padding:4px 12px;border:1px solid #6366f1;border-radius:20px;margin-right:8px;">Rapport</a>
        <a href="/settings" style="color:#a5b4fc;text-decoration:none;font-size:13px;padding:4px 12px;border:1px solid #6366f1;border-radius:20px;margin-right:8px;">Parametres</a>
        <span id="strategy-name"></span>
        <span id="mode-badge" class="mode-badge"></span>
        <span id="status-badge" class="status-badge"></span>
        <span id="last-update" style="color:#6b7280;font-size:12px;"></span>
    </div>
</div>

<div class="container">
    <!-- Metriques principales -->
    <div class="metrics-grid" id="metrics-grid"></div>

    <!-- Equity Curve -->
    <div class="chart-container">
        <h2>Equity Curve</h2>
        <div class="chart-wrapper">
            <canvas id="equityChart"></canvas>
        </div>
    </div>

    <!-- Positions & Stats -->
    <div class="two-col">
        <div class="table-container">
            <h2>Positions Ouvertes (<span id="pos-count">0</span>)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date<span class="th-tooltip">Date et heure d'ouverture de la position</span></th>
                        <th>Marche<span class="th-tooltip">Nom du marche Polymarket sur lequel la position est ouverte</span></th>
                        <th>Side<span class="th-tooltip">Direction du pari : YES (hausse) ou NO (baisse)</span></th>
                        <th>Taille<span class="th-tooltip">Montant investi en dollars dans cette position</span></th>
                        <th>Entree<span class="th-tooltip">Prix d'achat de la position (entre 0 et 1)</span></th>
                        <th>Actuel<span class="th-tooltip">Prix actuel du marche en temps reel</span></th>
                        <th>PnL<span class="th-tooltip">Profit ou perte non realise(e) sur cette position</span></th>
                    </tr>
                </thead>
                <tbody id="positions-body"></tbody>
            </table>
        </div>

        <div class="table-container">
            <h2>Statistiques de Trading</h2>
            <div class="stats-grid" id="stats-grid"></div>
        </div>
    </div>

    <!-- Trades recents -->
    <div class="table-container">
        <h2>Trades Recents</h2>
        <table>
            <thead>
                <tr>
                    <th>Date<span class="th-tooltip">Date et heure de cloture du trade</span></th>
                    <th>Marche<span class="th-tooltip">Nom du marche Polymarket sur lequel le trade a ete effectue</span></th>
                    <th>Side<span class="th-tooltip">Direction du pari : YES (hausse) ou NO (baisse)</span></th>
                    <th>Entree<span class="th-tooltip">Prix d'achat au moment de l'ouverture du trade</span></th>
                    <th>Sortie<span class="th-tooltip">Prix de vente au moment de la fermeture du trade</span></th>
                    <th>Taille<span class="th-tooltip">Montant investi en dollars dans ce trade</span></th>
                    <th>PnL<span class="th-tooltip">Profit ou perte realise(e) sur ce trade</span></th>
                    <th>Raison<span class="th-tooltip">Motif de fermeture : stop-loss, take-profit, trailing-stop, expiration...</span></th>
                </tr>
            </thead>
            <tbody id="trades-body"></tbody>
        </table>
    </div>

    <!-- Historique complet des trades -->
    <div class="table-container" id="history-container" style="display:none;">
        <h2>Historique des Trades (<span id="history-count">0</span>)</h2>
        <table>
            <thead>
                <tr>
                    <th>Date<span class="th-tooltip">Date et heure de cloture du trade</span></th>
                    <th>Marche<span class="th-tooltip">Nom du marche Polymarket sur lequel le trade a ete effectue</span></th>
                    <th>Side<span class="th-tooltip">Direction du pari : YES (hausse) ou NO (baisse)</span></th>
                    <th>Entree<span class="th-tooltip">Prix d'achat au moment de l'ouverture du trade</span></th>
                    <th>Sortie<span class="th-tooltip">Prix de vente au moment de la fermeture du trade</span></th>
                    <th>Taille<span class="th-tooltip">Montant investi en dollars dans ce trade</span></th>
                    <th>PnL<span class="th-tooltip">Profit ou perte realise(e) sur ce trade</span></th>
                    <th>Raison<span class="th-tooltip">Motif de fermeture : stop-loss, take-profit, trailing-stop, expiration...</span></th>
                </tr>
            </thead>
            <tbody id="history-body"></tbody>
        </table>
    </div>

    <!-- Erreurs -->
    <div class="table-container" id="errors-container" style="display:none;">
        <h2>Erreurs Recentes</h2>
        <div id="errors-list"></div>
    </div>

    <div class="refresh-info">Rafraichissement automatique toutes les 10 secondes</div>
</div>

<script>
let equityChart = null;

function fmt(n, decimals=2) {
    if (n === undefined || n === null) return '-';
    return Number(n).toFixed(decimals);
}

function fmtUsd(n) {
    if (n === undefined || n === null) return '-';
    const sign = n >= 0 ? '' : '-';
    return sign + '$' + Math.abs(n).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function pnlClass(n) {
    return n >= 0 ? 'pnl-positive' : 'pnl-negative';
}

function valueClass(n) {
    return n >= 0 ? 'positive' : 'negative';
}

function truncate(s, len) {
    if (!s) return '';
    return s.length > len ? s.substring(0, len) + '...' : s;
}

function renderMetrics(data) {
    const o = data.overview || {};
    const cards = [
        { label: 'Equity', value: fmtUsd(o.equity), cls: '', icon: '\u{1F4B0}',
          tip: '<strong>Equity = Capital cash + Positions ouvertes + Gains non realises</strong><br>C\'est la valeur totale de ton portefeuille a cet instant.',
          ex: 'Capital 700$ + 2 positions de 150$ + 30$ de gains = Equity 1030$' },
        { label: 'Capital Cash', value: fmtUsd(o.capital), cls: '', icon: '\u{1F4B5}',
          tip: '<strong>L\'argent disponible</strong> qui n\'est pas investi dans des positions. C\'est ta reserve pour ouvrir de nouvelles positions.',
          ex: 'Sur 1000$ total, si 300$ sont investis, il reste 700$ de cash' },
        { label: 'PnL Net (apr\u00e8s frais)', value: fmtUsd(o.total_pnl), cls: valueClass(o.total_pnl), sub: fmt(o.total_return_pct) + '% | Frais: ' + fmtUsd(o.total_fees || 0), icon: '\u{1F4CA}',
          tip: '<strong>Profit and Loss net</strong> depuis le lancement du bot. Somme de tous les trades fermes (gains - pertes - frais).',
          ex: '+45$ = le bot a gagne 45$ net apres frais. Frais = 2% du montant engage par trade' },
        { label: 'PnL Journalier', value: fmtUsd(o.daily_pnl), cls: valueClass(o.daily_pnl), icon: '\u{1F4C5}',
          tip: '<strong>Profit et perte du jour</strong>. Se reinitialise a minuit. Si ca depasse la limite journaliere, le bot arrete de trader.',
          ex: '+12$ = le bot a gagne 12$ aujourd\'hui. -30$ = il a perdu 30$ depuis minuit' },
        { label: 'PnL Non Realise', value: fmtUsd(o.unrealized_pnl), cls: valueClass(o.unrealized_pnl), icon: '\u{23F3}',
          tip: '<strong>Gains/pertes des positions encore ouvertes</strong>. Ce n\'est pas du vrai profit tant que la position n\'est pas fermee. Ca peut changer a tout moment.',
          ex: '+15$ = tes positions ouvertes sont en gain de 15$. Mais si le marche bouge, ca peut devenir -15$' },
        { label: 'Exposition', value: fmtUsd(o.exposure), sub: fmt(o.exposure_pct, 1) + '%', icon: '\u{1F3AF}',
          tip: '<strong>Montant total investi</strong> dans les positions ouvertes. L\'exposition en % = combien de ton capital est "a risque".',
          ex: '300$ (30%) = 300$ sont investis sur les marches, soit 30% de ton equity' },
        { label: 'Drawdown', value: fmt(o.drawdown_pct, 1) + '%', cls: o.drawdown_pct > 5 ? 'negative' : '', icon: '\u{1F4C9}',
          tip: '<strong>Baisse depuis le plus haut</strong> (peak equity). Mesure combien tu as "perdu" depuis ton meilleur moment. Si ca depasse le max (15%), le bot s\'arrete.',
          ex: 'Peak a 1100$, equity actuelle 1050$ = drawdown de 4.5%. A 15% le bot coupe tout' },
        { label: 'Peak Equity', value: fmtUsd(o.peak_equity), icon: '\u{1F3D4}',
          tip: '<strong>La plus haute valeur atteinte</strong> par ton portefeuille. Sert de reference pour calculer le drawdown.',
          ex: 'Peak 1100$ = a un moment, ton portefeuille valait 1100$. C\'est le record a battre' },
    ];

    const grid = document.getElementById('metrics-grid');
    grid.innerHTML = cards.map(c => `
        <div class="metric-card">
            <div class="metric-tooltip">${c.tip}${c.ex ? '<div class="tip-example">' + c.icon + ' ' + c.ex + '</div>' : ''}</div>
            <div class="metric-label">${c.icon} ${c.label}</div>
            <div class="metric-value ${c.cls}">${c.value}</div>
            ${c.sub ? '<div class="metric-sub">' + c.sub + '</div>' : ''}
        </div>
    `).join('');
}

function renderEquityChart(data) {
    const history = data.equity_history || [];
    if (history.length === 0) return;

    const labels = history.map(h => {
        const d = new Date(h.timestamp);
        return d.toLocaleString('fr-FR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    });
    const values = history.map(h => h.equity);
    const initial = (data.overview || {}).initial_capital || values[0];

    const ctx = document.getElementById('equityChart').getContext('2d');

    if (equityChart) {
        equityChart.data.labels = labels;
        equityChart.data.datasets[0].data = values;
        equityChart.data.datasets[1].data = Array(values.length).fill(initial);
        equityChart.update('none');
        return;
    }

    equityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Equity',
                    data: values,
                    borderColor: '#6c63ff',
                    backgroundColor: 'rgba(108,99,255,0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    borderWidth: 2,
                },
                {
                    label: 'Capital Initial',
                    data: Array(values.length).fill(initial),
                    borderColor: '#374151',
                    borderDash: [5, 5],
                    pointRadius: 0,
                    borderWidth: 1,
                    fill: false,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#9ca3af', font: { size: 11 } } },
                tooltip: {
                    callbacks: {
                        label: (ctx) => ctx.dataset.label + ': $' + ctx.parsed.y.toFixed(2)
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#4b5563', maxTicksLimit: 12, font: { size: 10 } },
                    grid: { color: '#1f2937' },
                },
                y: {
                    ticks: { color: '#4b5563', callback: v => '$' + v.toFixed(0) },
                    grid: { color: '#1f2937' },
                }
            }
        }
    });
}

function renderPositions(data) {
    const positions = data.positions || [];
    document.getElementById('pos-count').textContent = positions.length;

    const body = document.getElementById('positions-body');
    if (positions.length === 0) {
        body.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#4b5563;padding:20px;">Aucune position ouverte</td></tr>';
        return;
    }

    body.innerHTML = positions.map(p => {
        const entryTime = p.entry_time ? new Date(p.entry_time).toLocaleString('fr-FR', {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        }) : '-';
        return `
        <tr>
            <td>${entryTime}</td>
            <td title="${p.question || ''}">${truncate(p.question || p.market_id, 35)}</td>
            <td><span style="color:${p.side === 'YES' ? '#4ade80' : '#f87171'};font-weight:600;">${p.side}</span></td>
            <td>${fmtUsd(p.size_usd)}</td>
            <td>${fmt(p.entry_price, 3)}</td>
            <td>${fmt(p.current_price, 3)}</td>
            <td class="${pnlClass(p.unrealized_pnl)}">${fmtUsd(p.unrealized_pnl)} (${fmt((p.unrealized_pnl_pct || 0) * 100, 1)}%)</td>
        </tr>`;
    }).join('');
}

function renderStats(data) {
    const s = data.trade_stats || {};
    const rows = [
        ['Total Trades', s.total_trades || 0, 'Nombre total de trades fermes (gagnes + perdus) depuis le lancement'],
        ['Win Rate', fmt(s.win_rate, 1) + '%', 'Pourcentage de trades gagnants. Ex: 60% = 6 trades sur 10 sont positifs. Au-dessus de 50% c\'est bon signe'],
        ['Trades Gagnants', s.winning_trades || 0, 'Nombre de trades qui ont rapporte de l\'argent (PnL > 0)'],
        ['Trades Perdants', s.losing_trades || 0, 'Nombre de trades qui ont perdu de l\'argent (PnL < 0)'],
        ['Gain Moyen', fmtUsd(s.avg_win), 'Combien un trade gagnant rapporte en moyenne. Ex: +8.50$ = chaque trade positif gagne 8.50$ en moyenne'],
        ['Perte Moyenne', fmtUsd(s.avg_loss), 'Combien un trade perdant coute en moyenne. Ex: -5.20$ = chaque trade negatif perd 5.20$ en moyenne'],
        ['Profit Factor', fmt(s.profit_factor), 'Gains totaux / Pertes totales. > 1 = rentable. Ex: 1.5 = pour chaque 1$ perdu, le bot gagne 1.50$. < 1 = non rentable'],
        ['Plus Gros Gain', fmtUsd(s.largest_win), 'Le meilleur trade jamais realise. Montre le potentiel max du bot'],
        ['Plus Grosse Perte', fmtUsd(s.largest_loss), 'Le pire trade jamais realise. Montre le risque max par trade'],
        ['Marches Scannes', data.markets_scanned || 0, 'Nombre de marches Polymarket analyses a la derniere iteration (apres filtrage volume/liquidite)'],
        ['Signaux Generes', data.signals_generated || 0, 'Nombre total de signaux de trading generes depuis le debut. Pas tous ne menent a un trade'],
        ['Iteration', data.iteration || 0, 'Nombre de cycles complets du bot. Chaque iteration = scan + analyse + decisions + mise a jour'],
    ];

    document.getElementById('stats-grid').innerHTML = rows.map(([label, value, tip]) => `
        <div class="stat-row">
            <div class="stat-tooltip">${tip}</div>
            <span class="stat-label">${label}</span>
            <span class="stat-value">${value}</span>
        </div>
    `).join('');
}

function renderTrades(data) {
    const trades = (data.recent_trades || []).slice().reverse();
    const body = document.getElementById('trades-body');

    if (trades.length === 0) {
        body.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#4b5563;padding:20px;">Aucun trade</td></tr>';
        return;
    }

    body.innerHTML = trades.map(t => {
        const exitTime = t.exit_time ? new Date(t.exit_time).toLocaleString('fr-FR', {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        }) : '-';
        return `
        <tr>
            <td>${exitTime}</td>
            <td title="${t.question || ''}">${truncate(t.question || t.market_id, 30)}</td>
            <td><span style="color:${t.side === 'YES' ? '#4ade80' : '#f87171'}">${t.side}</span></td>
            <td>${fmt(t.entry_price, 3)}</td>
            <td>${fmt(t.exit_price, 3)}</td>
            <td>${fmtUsd(t.size_usd)}</td>
            <td class="${pnlClass(t.pnl)}">${fmtUsd(t.pnl)}</td>
            <td style="color:#9ca3af;font-size:11px;">${t.reason || ''}</td>
        </tr>`;
    }).join('');
}

function renderTradesHistory(data) {
    const trades = (data.all_trades || []).slice().reverse();
    const container = document.getElementById('history-container');
    const body = document.getElementById('history-body');
    document.getElementById('history-count').textContent = trades.length;

    if (trades.length === 0) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';
    body.innerHTML = trades.map(t => {
        const exitTime = t.exit_time ? new Date(t.exit_time).toLocaleString('fr-FR', {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        }) : '-';
        return `
        <tr>
            <td>${exitTime}</td>
            <td title="${t.question || ''}">${truncate(t.question || t.market_id, 30)}</td>
            <td><span style="color:${t.side === 'YES' ? '#4ade80' : '#f87171'}">${t.side}</span></td>
            <td>${fmt(t.entry_price, 3)}</td>
            <td>${fmt(t.exit_price, 3)}</td>
            <td>${fmtUsd(t.size_usd)}</td>
            <td class="${pnlClass(t.pnl)}">${fmtUsd(t.pnl)}</td>
            <td style="color:#9ca3af;font-size:11px;">${t.reason || ''}</td>
        </tr>`;
    }).join('');
}

function renderErrors(data) {
    const errors = data.errors || [];
    const container = document.getElementById('errors-container');
    const list = document.getElementById('errors-list');

    if (errors.length === 0) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';
    list.innerHTML = errors.slice().reverse().map(e => `
        <div class="error-item">
            <div class="error-time">${e.time || ''} [${e.type || 'unknown'}]</div>
            <div class="error-msg">${e.error || ''}</div>
        </div>
    `).join('');
}

function updateHeader(data) {
    document.getElementById('strategy-name').textContent = data.strategy || '';
    document.getElementById('mode-badge').textContent = data.mode || 'DRY RUN';

    const badge = document.getElementById('status-badge');
    const isRunning = data.status === 'running';
    badge.textContent = isRunning ? 'EN LIGNE' : 'ARRETE';
    badge.className = 'status-badge ' + (isRunning ? 'status-running' : 'status-stopped');

    document.getElementById('last-update').textContent =
        'MAJ: ' + new Date().toLocaleTimeString('fr-FR');
}

async function fetchAndRender() {
    try {
        const resp = await fetch('/api/data');
        const data = await resp.json();

        updateHeader(data);
        renderMetrics(data);
        renderEquityChart(data);
        renderPositions(data);
        renderStats(data);
        renderTrades(data);
        renderTradesHistory(data);
        renderErrors(data);
    } catch (err) {
        console.error('Erreur de chargement:', err);
    }
}

// Premier chargement + refresh automatique
fetchAndRender();
setInterval(fetchAndRender, 10000);
</script>
</body>
</html>
"""


# ================================================================
#  SETTINGS HTML/CSS/JS COMPLET (EMBARQUE)
# ================================================================

SETTINGS_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Parametres - Polymarket Bot</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #0a0e17;
    color: #e0e6ed;
    min-height: 100vh;
}
.header {
    background: linear-gradient(135deg, #0d1321 0%, #1a1f35 100%);
    border-bottom: 1px solid #2a3a5c;
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.header h1 { font-size: 20px; color: #fff; font-weight: 600; }
.header h1 span { color: #6c63ff; }
.header-right { display: flex; gap: 12px; align-items: center; }
.nav-link {
    color: #a5b4fc;
    text-decoration: none;
    font-size: 13px;
    padding: 4px 12px;
    border: 1px solid #6366f1;
    border-radius: 20px;
    transition: all 0.2s;
}
.nav-link:hover { background: #6366f1; color: #fff; }
.nav-link.active { background: #6366f1; color: #fff; }

.container { max-width: 1200px; margin: 0 auto; padding: 20px; }

/* Top bar */
.top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 12px;
}
.top-bar h2 { font-size: 18px; color: #fff; }
.btn-group { display: flex; gap: 8px; flex-wrap: wrap; }
.btn {
    padding: 8px 16px;
    border-radius: 8px;
    border: 1px solid #374151;
    background: #111827;
    color: #e0e6ed;
    cursor: pointer;
    font-size: 13px;
    font-family: inherit;
    transition: all 0.2s;
}
.btn:hover { border-color: #6366f1; color: #a5b4fc; }
.btn-primary { background: #6366f1; border-color: #6366f1; color: #fff; }
.btn-primary:hover { background: #4f46e5; }
.btn-danger { border-color: #ef4444; color: #f87171; }
.btn-danger:hover { background: #7f1d1d; }
.btn-success { border-color: #22c55e; color: #4ade80; }
.btn-success:hover { background: #0d3320; }

/* Diff badge */
.diff-count {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 12px;
    background: #1e1b4b;
    border: 1px solid #6366f1;
    color: #a5b4fc;
    font-size: 12px;
}

/* Sections */
.settings-section {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    margin-bottom: 20px;
    overflow: hidden;
}
.section-header {
    padding: 14px 20px;
    background: #0d1321;
    border-bottom: 1px solid #1f2937;
    font-size: 14px;
    font-weight: 600;
    color: #a5b4fc;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.section-header:hover { background: #111827; }
.section-header .chevron { transition: transform 0.2s; }
.section-header.collapsed .chevron { transform: rotate(-90deg); }
.section-body { padding: 16px 20px; }
.section-body.hidden { display: none; }

/* Param rows */
.param-row {
    display: grid;
    grid-template-columns: 1fr 1fr auto;
    gap: 16px;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #1a2332;
}
.param-row:last-child { border-bottom: none; }
.param-info { position: relative; }
.param-label {
    font-size: 13px;
    font-weight: 500;
    color: #e0e6ed;
    display: flex;
    align-items: center;
    gap: 6px;
}
.param-label.modified { color: #fbbf24; }
.param-icon {
    width: 18px;
    height: 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    opacity: 0.7;
}
.param-desc {
    font-size: 11px;
    color: #6b7280;
    margin-top: 2px;
}
.param-default {
    font-size: 11px;
    color: #4b5563;
    margin-top: 2px;
}
/* Info bulle */
.info-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #374151;
    color: #9ca3af;
    font-size: 10px;
    font-weight: 700;
    cursor: pointer;
    border: none;
    transition: all 0.2s;
    flex-shrink: 0;
}
.info-btn:hover { background: #6366f1; color: #fff; }
.tooltip-popup {
    display: none;
    position: absolute;
    left: 0;
    top: 100%;
    z-index: 100;
    width: 380px;
    background: #1a1f35;
    border: 1px solid #6366f1;
    border-radius: 10px;
    padding: 14px 16px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.6);
    margin-top: 6px;
}
.tooltip-popup.visible { display: block; }
.tooltip-title {
    font-size: 13px;
    font-weight: 600;
    color: #a5b4fc;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.tooltip-text {
    font-size: 12px;
    color: #d1d5db;
    line-height: 1.5;
    margin-bottom: 10px;
}
.tooltip-example {
    background: #0d1321;
    border: 1px solid #2a3a5c;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 11px;
    color: #4ade80;
    line-height: 1.5;
}
.tooltip-example-label {
    font-size: 10px;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.param-input { text-align: right; }
.param-input input, .param-input select {
    background: #0d1321;
    border: 1px solid #374151;
    color: #e0e6ed;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 13px;
    font-family: inherit;
    width: 180px;
    text-align: right;
}
.param-input input:focus, .param-input select:focus {
    outline: none;
    border-color: #6366f1;
}
.param-input input.modified {
    border-color: #fbbf24;
    background: #1a1500;
}
.param-reset-btn {
    background: none;
    border: 1px solid #374151;
    color: #6b7280;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    transition: all 0.2s;
    white-space: nowrap;
}
.param-reset-btn:hover { border-color: #ef4444; color: #f87171; }
.param-reset-btn.hidden { visibility: hidden; }

/* Toggle switch */
.toggle-switch {
    position: relative;
    width: 48px;
    height: 24px;
    display: inline-block;
}
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.toggle-slider {
    position: absolute;
    cursor: pointer;
    top: 0; left: 0; right: 0; bottom: 0;
    background: #374151;
    border-radius: 24px;
    transition: 0.3s;
}
.toggle-slider:before {
    content: "";
    position: absolute;
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background: white;
    border-radius: 50%;
    transition: 0.3s;
}
input:checked + .toggle-slider { background: #6366f1; }
input:checked + .toggle-slider:before { transform: translateX(24px); }

/* Profiles section */
.profiles-section {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
}
.profiles-section h3 {
    font-size: 14px;
    color: #d1d5db;
    margin-bottom: 12px;
}
.profile-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    border: 1px solid #1f2937;
    border-radius: 8px;
    margin-bottom: 8px;
    font-size: 13px;
}
.profile-row:hover { border-color: #374151; }
.profile-name { color: #e0e6ed; font-weight: 500; }
.profile-actions { display: flex; gap: 6px; }
.save-profile-row {
    display: flex;
    gap: 8px;
    margin-top: 12px;
}
.save-profile-row input {
    flex: 1;
    background: #0d1321;
    border: 1px solid #374151;
    color: #e0e6ed;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 13px;
    font-family: inherit;
}
.save-profile-row input:focus { outline: none; border-color: #6366f1; }

/* History */
.history-section {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
}
.history-section h3 {
    font-size: 14px;
    color: #d1d5db;
    margin-bottom: 12px;
}
.history-item {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid #1a2332;
    font-size: 12px;
}
.history-item:last-child { border-bottom: none; }
.history-key { color: #a5b4fc; }
.history-change { color: #6b7280; }
.history-time { color: #4b5563; }

/* Toast */
.toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    z-index: 9999;
    animation: slideIn 0.3s ease-out;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}
.toast-success { background: #0d3320; color: #4ade80; border: 1px solid #22c55e; }
.toast-error { background: #3b1818; color: #f87171; border: 1px solid #ef4444; }
.toast-info { background: #1e1b4b; color: #a5b4fc; border: 1px solid #6366f1; }
@keyframes slideIn {
    from { transform: translateX(100px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}
</style>
</head>
<body>

<div class="header">
    <h1><span>POLYMARKET</span> Hedge Fund Bot <span style="font-size:11px;color:#6b7280;font-weight:400;margin-left:8px;">v__BUILD_VERSION__</span></h1>
    <div class="header-right">
        <a href="/" class="nav-link">Dashboard</a>
        <a href="/report" class="nav-link">Rapport</a>
        <a href="/settings" class="nav-link active">Parametres</a>
    </div>
</div>

<div class="container">
    <!-- Top bar -->
    <div class="top-bar">
        <div style="display:flex;align-items:center;gap:16px;">
            <h2>Configuration du Bot</h2>
            <span id="diff-count" class="diff-count" style="display:none;"></span>
        </div>
        <div class="btn-group">
            <button class="btn btn-danger" onclick="resetToDefaults()">Restaurer les Defaults</button>
            <button class="btn btn-success" onclick="applyChanges()">Appliquer les Modifications</button>
        </div>
    </div>

    <!-- Profiles -->
    <div class="profiles-section">
        <h3>Profils de Configuration</h3>
        <div id="profiles-list"></div>
        <div class="save-profile-row">
            <input type="text" id="profile-name-input" placeholder="Nom du nouveau profil...">
            <button class="btn btn-primary" onclick="saveProfile()">Sauvegarder le Profil</button>
        </div>
    </div>

    <!-- Settings groups -->
    <div id="settings-groups"></div>

    <!-- History -->
    <div class="history-section">
        <h3>Historique des Modifications</h3>
        <div id="history-list"></div>
    </div>
</div>

<script>
let settingsData = null;
let pendingChanges = {};

function toggleTooltip(id, event) {
    event.stopPropagation();
    const el = document.getElementById(id);
    if (!el) return;
    // Fermer tous les autres tooltips
    document.querySelectorAll('.tooltip-popup.visible').forEach(t => {
        if (t.id !== id) t.classList.remove('visible');
    });
    el.classList.toggle('visible');
}
// Fermer les tooltips en cliquant ailleurs
document.addEventListener('click', () => {
    document.querySelectorAll('.tooltip-popup.visible').forEach(t => t.classList.remove('visible'));
});

function showToast(msg, type='success') {
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

async function loadSettings() {
    try {
        const resp = await fetch('/api/settings');
        settingsData = await resp.json();
        pendingChanges = {};
        renderSettings();
        renderProfiles();
        renderHistory();
        updateDiffCount();
    } catch(e) {
        showToast('Erreur de chargement des parametres', 'error');
    }
}

function renderSettings() {
    const groups = {};
    for (const p of settingsData.params) {
        const g = p.group || 'Autre';
        if (!groups[g]) groups[g] = [];
        groups[g].push(p);
    }

    const container = document.getElementById('settings-groups');
    container.innerHTML = '';

    for (const [groupName, params] of Object.entries(groups)) {
        const section = document.createElement('div');
        section.className = 'settings-section';

        const header = document.createElement('div');
        header.className = 'section-header';
        header.innerHTML = `<span>${groupName}</span><span class="chevron">&#9660;</span>`;
        header.onclick = function() {
            const body = this.nextElementSibling;
            body.classList.toggle('hidden');
            this.classList.toggle('collapsed');
        };

        const body = document.createElement('div');
        body.className = 'section-body';

        for (const p of params) {
            body.appendChild(createParamRow(p));
        }

        section.appendChild(header);
        section.appendChild(body);
        container.appendChild(section);
    }
}

const ICONS = {
    dollar: '\u{1F4B0}', target: '\u{1F3AF}', shield: '\u{1F6E1}', layers: '\u{1F4DA}',
    chart: '\u{1F4CA}', droplet: '\u{1F4A7}', arrows: '\u{2194}\uFE0F', clock: '\u{23F0}',
    alert: '\u{26A0}\uFE0F', toggle: '\u{1F504}', brain: '\u{1F9E0}', users: '\u{1F465}',
    filter: '\u{1F50D}', trendUp: '\u{1F4C8}', trendDown: '\u{1F4C9}', scissors: '\u{2702}\uFE0F',
    trophy: '\u{1F3C6}',
};

function createParamRow(p) {
    const row = document.createElement('div');
    row.className = 'param-row';
    row.id = 'row-' + p.key;

    const displayValue = p.type === 'percent' ? (p.value * 100).toFixed(1) + '%' : p.value;
    const displayDefault = p.type === 'percent' ? (p.default * 100).toFixed(1) + '%' : p.default;
    const icon = ICONS[p.icon] || '\u{2699}\uFE0F';
    const tooltipId = 'tip-' + p.key;

    // Info
    const info = document.createElement('div');
    info.className = 'param-info';
    info.innerHTML = `
        <div class="param-label ${p.modified ? 'modified' : ''}">
            <span class="param-icon">${icon}</span>
            ${p.label || p.key}
            ${p.tooltip ? '<button class="info-btn" onclick="toggleTooltip(\'' + tooltipId + '\', event)">?</button>' : ''}
        </div>
        <div class="param-desc">${p.desc || ''}</div>
        <div class="param-default">Default: ${displayDefault}</div>
        ${p.tooltip ? '<div class="tooltip-popup" id="' + tooltipId + '">' +
            '<div class="tooltip-title">' + icon + ' ' + (p.label || p.key) + '</div>' +
            '<div class="tooltip-text">' + (p.tooltip || '') + '</div>' +
            (p.example ? '<div class="tooltip-example"><div class="tooltip-example-label">Exemple concret</div>' + p.example + '</div>' : '') +
        '</div>' : ''}
    `;

    // Input
    const inputDiv = document.createElement('div');
    inputDiv.className = 'param-input';

    if (p.type === 'boolean') {
        inputDiv.innerHTML = `
            <label class="toggle-switch">
                <input type="checkbox" id="input-${p.key}" ${p.value ? 'checked' : ''}
                    onchange="onParamChange('${p.key}', this.checked, 'boolean')">
                <span class="toggle-slider"></span>
            </label>
        `;
    } else if (p.type === 'select') {
        const options = (p.options || []).map(o =>
            `<option value="${o}" ${o === p.value ? 'selected' : ''}>${o}</option>`
        ).join('');
        inputDiv.innerHTML = `
            <select id="input-${p.key}" onchange="onParamChange('${p.key}', this.value, 'select')">
                ${options}
            </select>
        `;
    } else if (p.type === 'percent') {
        inputDiv.innerHTML = `
            <input type="number" id="input-${p.key}" value="${(p.value * 100).toFixed(1)}"
                min="${(p.min || 0) * 100}" max="${(p.max || 100) * 100}" step="${(p.step || 0.01) * 100}"
                onchange="onParamChange('${p.key}', this.value / 100, 'percent')"
                class="${p.modified ? 'modified' : ''}">
        `;
    } else if (p.type === 'integer') {
        inputDiv.innerHTML = `
            <input type="number" id="input-${p.key}" value="${p.value}"
                min="${p.min || 0}" max="${p.max || 999999}" step="${p.step || 1}"
                onchange="onParamChange('${p.key}', parseInt(this.value), 'integer')"
                class="${p.modified ? 'modified' : ''}">
        `;
    } else {
        inputDiv.innerHTML = `
            <input type="number" id="input-${p.key}" value="${p.value}"
                min="${p.min || 0}" max="${p.max || 999999}" step="${p.step || 0.01}"
                onchange="onParamChange('${p.key}', parseFloat(this.value), 'number')"
                class="${p.modified ? 'modified' : ''}">
        `;
    }

    // Reset button
    const resetDiv = document.createElement('div');
    resetDiv.innerHTML = `
        <button class="param-reset-btn ${p.modified ? '' : 'hidden'}" id="reset-${p.key}"
            onclick="resetParam('${p.key}', ${JSON.stringify(p.default)}, '${p.type}')">
            Reset
        </button>
    `;

    row.appendChild(info);
    row.appendChild(inputDiv);
    row.appendChild(resetDiv);
    return row;
}

function onParamChange(key, value, type) {
    pendingChanges[key] = value;
    const input = document.getElementById('input-' + key);
    if (input && input.type !== 'checkbox') input.classList.add('modified');
    const resetBtn = document.getElementById('reset-' + key);
    if (resetBtn) resetBtn.classList.remove('hidden');
    updateDiffCount();
}

function resetParam(key, defaultValue, type) {
    const input = document.getElementById('input-' + key);
    if (!input) return;

    if (type === 'boolean') {
        input.checked = defaultValue;
    } else if (type === 'percent') {
        input.value = (defaultValue * 100).toFixed(1);
    } else {
        input.value = defaultValue;
    }

    pendingChanges[key] = defaultValue;
    input.classList.remove('modified');
    const resetBtn = document.getElementById('reset-' + key);
    if (resetBtn) resetBtn.classList.add('hidden');
}

async function applyChanges() {
    if (Object.keys(pendingChanges).length === 0) {
        showToast('Aucune modification a appliquer', 'info');
        return;
    }

    try {
        const resp = await fetch('/api/settings/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(pendingChanges),
        });
        const result = await resp.json();
        showToast(`${result.changes.length} parametre(s) modifie(s)`, 'success');
        pendingChanges = {};
        loadSettings();
    } catch(e) {
        showToast('Erreur lors de la sauvegarde', 'error');
    }
}

async function resetToDefaults() {
    if (!confirm('Restaurer TOUS les parametres aux valeurs d\'origine ?')) return;

    try {
        await fetch('/api/settings/reset', { method: 'POST' });
        showToast('Parametres restaures aux valeurs d\'origine', 'success');
        pendingChanges = {};
        loadSettings();
    } catch(e) {
        showToast('Erreur lors de la restauration', 'error');
    }
}

async function updateDiffCount() {
    try {
        const resp = await fetch('/api/settings/diff');
        const diffs = await resp.json();
        const el = document.getElementById('diff-count');
        const total = diffs.length + Object.keys(pendingChanges).length;
        if (total > 0) {
            el.textContent = total + ' modification(s) vs defaults';
            el.style.display = '';
        } else {
            el.style.display = 'none';
        }
    } catch(e) {}
}

function renderProfiles() {
    const profiles = settingsData.profiles || [];
    const list = document.getElementById('profiles-list');

    if (profiles.length === 0) {
        list.innerHTML = '<div style="color:#4b5563;font-size:13px;padding:8px 0;">Aucun profil sauvegarde</div>';
        return;
    }

    list.innerHTML = profiles.map(name => `
        <div class="profile-row">
            <span class="profile-name">${name}</span>
            <div class="profile-actions">
                <button class="btn" onclick="loadProfile('${name}')">Charger</button>
                <button class="btn btn-danger" onclick="deleteProfile('${name}')">Supprimer</button>
            </div>
        </div>
    `).join('');
}

async function saveProfile() {
    const input = document.getElementById('profile-name-input');
    const name = input.value.trim();
    if (!name) {
        showToast('Entre un nom pour le profil', 'error');
        return;
    }

    // Apply pending changes first
    if (Object.keys(pendingChanges).length > 0) {
        await fetch('/api/settings/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(pendingChanges),
        });
        pendingChanges = {};
    }

    try {
        await fetch('/api/settings/profiles/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name}),
        });
        input.value = '';
        showToast(`Profil "${name}" sauvegarde`, 'success');
        loadSettings();
    } catch(e) {
        showToast('Erreur lors de la sauvegarde du profil', 'error');
    }
}

async function loadProfile(name) {
    if (!confirm(`Charger le profil "${name}" ? Les modifications non sauvegardees seront perdues.`)) return;

    try {
        await fetch('/api/settings/profiles/load', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name}),
        });
        showToast(`Profil "${name}" charge`, 'success');
        pendingChanges = {};
        loadSettings();
    } catch(e) {
        showToast('Erreur lors du chargement du profil', 'error');
    }
}

async function deleteProfile(name) {
    if (!confirm(`Supprimer le profil "${name}" ?`)) return;

    try {
        await fetch('/api/settings/profiles/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name}),
        });
        showToast(`Profil "${name}" supprime`, 'success');
        loadSettings();
    } catch(e) {
        showToast('Erreur lors de la suppression', 'error');
    }
}

function renderHistory() {
    const history = (settingsData.history || []).slice().reverse().slice(0, 20);
    const list = document.getElementById('history-list');

    if (history.length === 0) {
        list.innerHTML = '<div style="color:#4b5563;font-size:13px;">Aucune modification</div>';
        return;
    }

    list.innerHTML = history.map(h => {
        const time = h.time ? new Date(h.time).toLocaleString('fr-FR', {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        }) : '';

        if (h.key === '__reset__') {
            return `<div class="history-item">
                <span class="history-key" style="color:#f87171;">RESET aux defaults</span>
                <span class="history-time">${time}</span>
            </div>`;
        }
        if (h.key === '__load_profile__') {
            return `<div class="history-item">
                <span class="history-key" style="color:#4ade80;">Profil charge: ${h.new}</span>
                <span class="history-time">${time}</span>
            </div>`;
        }

        return `<div class="history-item">
            <span class="history-key">${h.key}</span>
            <span class="history-change">${h.old} → ${h.new}</span>
            <span class="history-time">${time}</span>
        </div>`;
    }).join('');
}

// Initial load
loadSettings();
</script>
</body>
</html>
"""


# ================================================================
#  REPORT HTML/CSS/JS COMPLET (EMBARQUE)
# ================================================================

REPORT_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rapport - Polymarket Bot</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0f1117; color: #e5e7eb; font-family: 'Inter', system-ui, sans-serif; }
.header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 24px; background: #161822; border-bottom: 1px solid #1e2030;
}
.header h1 { font-size: 16px; font-weight: 600; color: #e5e7eb; }
.header h1 span:first-child { color: #818cf8; }
.header-right { display: flex; align-items: center; gap: 8px; }
.nav-link {
    color: #a5b4fc; text-decoration: none; font-size: 13px;
    padding: 4px 12px; border: 1px solid #6366f1; border-radius: 20px;
}
.nav-link:hover { background: #6366f1; color: #fff; }
.nav-link.active { background: #6366f1; color: #fff; }
.container { max-width: 1400px; margin: 0 auto; padding: 20px; }

/* KPI Cards */
.kpi-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px; margin-bottom: 24px;
}
.kpi-card {
    background: #161822; border: 1px solid #1e2030; border-radius: 10px;
    padding: 16px; text-align: center;
}
.kpi-label { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.kpi-value { font-size: 22px; font-weight: 700; }
.kpi-sub { font-size: 11px; color: #6b7280; margin-top: 2px; }
.positive { color: #4ade80; }
.negative { color: #f87171; }
.neutral { color: #a5b4fc; }

/* Charts */
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
@media (max-width: 900px) { .charts-grid { grid-template-columns: 1fr; } }
.chart-box {
    background: #161822; border: 1px solid #1e2030; border-radius: 10px;
    padding: 16px;
}
.chart-box h2 { font-size: 14px; color: #818cf8; margin-bottom: 12px; }
.chart-box canvas { width: 100% !important; height: 250px !important; }

/* Table */
.table-box {
    background: #161822; border: 1px solid #1e2030; border-radius: 10px;
    padding: 16px; margin-bottom: 24px;
}
.table-box h2 { font-size: 14px; color: #818cf8; margin-bottom: 12px; }
.table-box .controls { display: flex; gap: 8px; margin-bottom: 12px; align-items: center; }
.table-box input, .table-box select {
    background: #1e2030; border: 1px solid #2d3048; color: #e5e7eb;
    padding: 6px 10px; border-radius: 6px; font-size: 12px;
}
.table-box input { flex: 1; max-width: 300px; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { background: #1e2030; color: #9ca3af; padding: 8px; text-align: left; font-weight: 600; cursor: pointer; user-select: none; }
th:hover { color: #a5b4fc; }
td { padding: 8px; border-bottom: 1px solid #1e2030; }
tr:hover { background: #1a1c2e; }
.badge {
    padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600;
}
.badge-win { background: #4ade8022; color: #4ade80; }
.badge-loss { background: #f8717122; color: #f87171; }
.badge-reason { background: #818cf822; color: #818cf8; }

/* Footer */
.footer { text-align: center; padding: 20px; color: #374151; font-size: 11px; }
</style>
</head>
<body>

<div class="header">
    <h1><span>POLYMARKET</span> Hedge Fund Bot <span style="font-size:11px;color:#6b7280;font-weight:400;margin-left:8px;">v__BUILD_VERSION__</span></h1>
    <div class="header-right">
        <a href="/" class="nav-link">Dashboard</a>
        <a href="/report" class="nav-link active">Rapport</a>
        <a href="/settings" class="nav-link">Parametres</a>
    </div>
</div>

<div class="container">
    <div class="kpi-grid" id="kpi-grid"></div>

    <div class="charts-grid">
        <div class="chart-box">
            <h2>PnL Cumule</h2>
            <canvas id="pnlChart"></canvas>
        </div>
        <div class="chart-box">
            <h2>Distribution des Trades</h2>
            <canvas id="distChart"></canvas>
        </div>
    </div>

    <div class="table-box">
        <h2>Historique Complet des Trades (<span id="trade-count">0</span>)</h2>
        <div class="controls">
            <input type="text" id="search" placeholder="Rechercher un marche...">
            <select id="filter-side">
                <option value="">Tous</option>
                <option value="YES">YES</option>
                <option value="NO">NO</option>
            </select>
            <select id="filter-result">
                <option value="">Tous</option>
                <option value="win">Gagnants</option>
                <option value="loss">Perdants</option>
            </select>
        </div>
        <div style="max-height:500px;overflow-y:auto;">
            <table>
                <thead>
                    <tr>
                        <th data-sort="idx">#</th>
                        <th data-sort="date">Date</th>
                        <th data-sort="market">Marche</th>
                        <th data-sort="side">Side</th>
                        <th data-sort="entry">Entree</th>
                        <th data-sort="exit">Sortie</th>
                        <th data-sort="size">Taille</th>
                        <th data-sort="fees">Frais</th>
                        <th data-sort="pnl">PnL Net</th>
                        <th data-sort="pct">%</th>
                        <th data-sort="reason">Raison</th>
                    </tr>
                </thead>
                <tbody id="trades-body"></tbody>
            </table>
        </div>
    </div>

    <div class="footer">Polymarket Hedge Fund Bot — Rapport genere automatiquement</div>
</div>

<script>
let allTrades = [];
let sortKey = 'idx';
let sortAsc = false;

function fmt(n, d=2) { return n == null ? '-' : Number(n).toFixed(d); }
function fmtUsd(n) {
    if (n == null) return '-';
    const s = n >= 0 ? '' : '-';
    return s + '$' + Math.abs(n).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function renderKPIs(data) {
    const s = data.trade_stats || {};
    const o = data.overview || {};
    const trades = data.all_trades || [];

    // Calculs supplementaires
    let pnlCumul = 0;
    let peak = 0;
    let maxDD = 0;
    const pnls = trades.map(t => t.pnl || 0);
    pnls.forEach(p => {
        pnlCumul += p;
        if (pnlCumul > peak) peak = pnlCumul;
        const dd = peak > 0 ? (peak - pnlCumul) / peak * 100 : 0;
        if (dd > maxDD) maxDD = dd;
    });

    const avgTrade = pnls.length > 0 ? pnls.reduce((a,b) => a+b, 0) / pnls.length : 0;
    const expectancy = (s.win_rate/100 || 0) * (s.avg_win || 0) + (1 - (s.win_rate/100 || 0)) * (s.avg_loss || 0);
    const totalFees = trades.reduce((acc, t) => acc + (t.fees_total || 0), 0);
    const totalPnlGross = trades.reduce((acc, t) => acc + (t.pnl_gross || t.pnl || 0), 0);

    const cards = [
        { label: 'PnL Brut', value: fmtUsd(totalPnlGross), cls: totalPnlGross >= 0 ? 'positive' : 'negative' },
        { label: 'Frais Totaux', value: fmtUsd(totalFees), cls: 'negative' },
        { label: 'PnL Net', value: fmtUsd(o.total_pnl || pnlCumul), cls: (o.total_pnl || pnlCumul) >= 0 ? 'positive' : 'negative' },
        { label: 'Total Trades', value: s.total_trades || trades.length, cls: 'neutral' },
        { label: 'Win Rate', value: fmt(s.win_rate, 1) + '%', cls: (s.win_rate || 0) >= 50 ? 'positive' : 'negative' },
        { label: 'Profit Factor', value: fmt(s.profit_factor), cls: (s.profit_factor || 0) >= 1 ? 'positive' : 'negative' },
        { label: 'Gain Moyen', value: fmtUsd(s.avg_win), cls: 'positive' },
        { label: 'Perte Moyenne', value: fmtUsd(s.avg_loss), cls: 'negative' },
        { label: 'Esperance/Trade', value: fmtUsd(expectancy), cls: expectancy >= 0 ? 'positive' : 'negative' },
        { label: 'Max Drawdown', value: fmt(maxDD, 1) + '%', cls: 'negative' },
    ];

    document.getElementById('kpi-grid').innerHTML = cards.map(c => `
        <div class="kpi-card">
            <div class="kpi-label">${c.label}</div>
            <div class="kpi-value ${c.cls}">${c.value}</div>
        </div>
    `).join('');
}

function renderPnlChart(trades) {
    const ctx = document.getElementById('pnlChart').getContext('2d');
    let cumul = 0;
    const data = trades.map((t, i) => { cumul += (t.pnl || 0); return cumul; });
    const labels = trades.map((t, i) => '#' + (i + 1));

    new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'PnL Cumule ($)',
                data,
                borderColor: '#818cf8',
                backgroundColor: 'rgba(129,140,248,0.1)',
                fill: true, tension: 0.3, pointRadius: 2, borderWidth: 2,
            }, {
                label: 'Zero',
                data: Array(data.length).fill(0),
                borderColor: '#374151', borderDash: [4,4], pointRadius: 0, borderWidth: 1,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#9ca3af', font: { size: 11 } } } },
            scales: {
                x: { ticks: { color: '#4b5563', maxTicksLimit: 15, font: { size: 10 } }, grid: { color: '#1f2937' } },
                y: { ticks: { color: '#4b5563', callback: v => '$' + v }, grid: { color: '#1f2937' } }
            }
        }
    });
}

function renderDistChart(trades) {
    const ctx = document.getElementById('distChart').getContext('2d');
    const pnls = trades.map(t => t.pnl || 0);

    // Creer des buckets
    const min = Math.min(...pnls, -50);
    const max = Math.max(...pnls, 50);
    const step = Math.max(10, Math.round((max - min) / 15));
    const buckets = {};
    for (let b = Math.floor(min / step) * step; b <= max; b += step) {
        buckets[b] = 0;
    }
    pnls.forEach(p => {
        const b = Math.floor(p / step) * step;
        buckets[b] = (buckets[b] || 0) + 1;
    });

    const labels = Object.keys(buckets).map(Number).sort((a,b) => a-b);
    const values = labels.map(l => buckets[l]);
    const colors = labels.map(l => l >= 0 ? '#4ade80' : '#f87171');

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels.map(l => '$' + l),
            datasets: [{ label: 'Trades', data: values, backgroundColor: colors }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#4b5563', font: { size: 10 } }, grid: { display: false } },
                y: { ticks: { color: '#4b5563', stepSize: 1 }, grid: { color: '#1f2937' } }
            }
        }
    });
}

function getFilteredTrades() {
    const search = document.getElementById('search').value.toLowerCase();
    const side = document.getElementById('filter-side').value;
    const result = document.getElementById('filter-result').value;

    return allTrades.filter(t => {
        if (search && !(t.question || t.market_id || '').toLowerCase().includes(search)) return false;
        if (side && t.side !== side) return false;
        if (result === 'win' && (t.pnl || 0) <= 0) return false;
        if (result === 'loss' && (t.pnl || 0) >= 0) return false;
        return true;
    });
}

function renderTable() {
    let trades = getFilteredTrades();
    document.getElementById('trade-count').textContent = trades.length;

    // Tri
    trades.sort((a, b) => {
        let va, vb;
        switch(sortKey) {
            case 'idx': va = a._idx; vb = b._idx; break;
            case 'date': va = a.entry_time || a.exit_time || ''; vb = b.entry_time || b.exit_time || ''; break;
            case 'market': va = (a.question || a.market_id || '').toLowerCase(); vb = (b.question || b.market_id || '').toLowerCase(); break;
            case 'side': va = a.side; vb = b.side; break;
            case 'entry': va = a.entry_price || 0; vb = b.entry_price || 0; break;
            case 'exit': va = a.exit_price || 0; vb = b.exit_price || 0; break;
            case 'size': va = a.size_usd || 0; vb = b.size_usd || 0; break;
            case 'fees': va = a.fees_total || 0; vb = b.fees_total || 0; break;
            case 'pnl': va = a.pnl || 0; vb = b.pnl || 0; break;
            case 'pct': va = a.pnl_pct || 0; vb = b.pnl_pct || 0; break;
            case 'reason': va = a.reason || ''; vb = b.reason || ''; break;
            default: va = a._idx; vb = b._idx;
        }
        if (va < vb) return sortAsc ? -1 : 1;
        if (va > vb) return sortAsc ? 1 : -1;
        return 0;
    });

    const body = document.getElementById('trades-body');
    if (trades.length === 0) {
        body.innerHTML = '<tr><td colspan="11" style="text-align:center;color:#4b5563;padding:30px;">Aucun trade</td></tr>';
        return;
    }

    body.innerHTML = trades.map(t => {
        const rawDate = t.entry_time || t.exit_time || '';
        const dt = rawDate ? new Date(rawDate).toLocaleString('fr-FR', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-';
        const pnlCls = (t.pnl || 0) >= 0 ? 'positive' : 'negative';
        return `<tr>
            <td>${t._idx}</td>
            <td>${dt}</td>
            <td title="${t.question || t.market_id || ''}">${(t.question || t.market_id || '').substring(0, 45)}</td>
            <td><span style="color:${t.side==='YES'?'#4ade80':'#f87171'};font-weight:600">${t.side}</span></td>
            <td>${fmt(t.entry_price, 4)}</td>
            <td>${fmt(t.exit_price, 4)}</td>
            <td>${fmtUsd(t.size_usd)}</td>
            <td style="color:#f59e0b">${fmtUsd(t.fees_total || 0)}</td>
            <td class="${pnlCls}" style="font-weight:600">${fmtUsd(t.pnl)}</td>
            <td class="${pnlCls}">${fmt((t.pnl_pct || 0), 1)}%</td>
            <td><span class="badge badge-reason">${t.reason || '-'}</span></td>
        </tr>`;
    }).join('');
}

// Tri par colonnes
document.querySelectorAll('th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
        const key = th.dataset.sort;
        if (sortKey === key) { sortAsc = !sortAsc; }
        else { sortKey = key; sortAsc = true; }
        renderTable();
    });
});

// Filtres
document.getElementById('search').addEventListener('input', renderTable);
document.getElementById('filter-side').addEventListener('change', renderTable);
document.getElementById('filter-result').addEventListener('change', renderTable);

async function loadReport() {
    try {
        const resp = await fetch('/api/data');
        const data = await resp.json();

        allTrades = (data.all_trades || []).map((t, i) => ({ ...t, _idx: i + 1 }));

        renderKPIs(data);
        renderPnlChart(allTrades);
        renderDistChart(allTrades);
        renderTable();
    } catch (err) {
        console.error('Erreur:', err);
    }
}

loadReport();
</script>
</body>
</html>
"""


# ================================================================
#  MAIN (mode standalone)
# ================================================================

def main():
    import os
    parser = argparse.ArgumentParser(description="Dashboard Web Polymarket Bot")
    parser.add_argument("--port", type=int, default=None, help="Port du serveur")
    parser.add_argument("--host", default="0.0.0.0", help="Adresse d'ecoute")
    parser.add_argument("--state-file", default="bot_state.json", help="Fichier d'etat du bot")
    args = parser.parse_args()

    # Render.com definit PORT automatiquement
    port = args.port or int(os.environ.get("PORT", 5050))

    app = create_dashboard_app(state_file=args.state_file)
    logging.getLogger("web_dashboard").info(f"Dashboard demarre sur http://localhost:{port}")
    app.run(host=args.host, port=port, debug=True)


if __name__ == "__main__":
    main()
