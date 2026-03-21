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

import json
import argparse
import threading
from pathlib import Path
from datetime import datetime

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
            pnls = [t.get("pnl", 0) for t in trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]

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
                    "recent_trades": [], "trade_stats": {}, "equity_history": [],
                    "errors": []}

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

    @app.route("/")
    def index():
        return Response(DASHBOARD_HTML, mimetype="text/html")

    @app.route("/settings")
    def settings_page():
        return Response(SETTINGS_HTML, mimetype="text/html")

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
}
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
    <h1><span>POLYMARKET</span> Hedge Fund Bot</h1>
    <div class="header-right">
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
                        <th>Marche</th>
                        <th>Side</th>
                        <th>Taille</th>
                        <th>Entree</th>
                        <th>Actuel</th>
                        <th>PnL</th>
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
                    <th>Date</th>
                    <th>Marche</th>
                    <th>Side</th>
                    <th>Entree</th>
                    <th>Sortie</th>
                    <th>Taille</th>
                    <th>PnL</th>
                    <th>Raison</th>
                </tr>
            </thead>
            <tbody id="trades-body"></tbody>
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
        { label: 'Equity', value: fmtUsd(o.equity), cls: '' },
        { label: 'Capital Cash', value: fmtUsd(o.capital), cls: '' },
        { label: 'PnL Total', value: fmtUsd(o.total_pnl), cls: valueClass(o.total_pnl), sub: fmt(o.total_return_pct) + '%' },
        { label: 'PnL Journalier', value: fmtUsd(o.daily_pnl), cls: valueClass(o.daily_pnl) },
        { label: 'PnL Non Realise', value: fmtUsd(o.unrealized_pnl), cls: valueClass(o.unrealized_pnl) },
        { label: 'Exposition', value: fmtUsd(o.exposure), sub: fmt(o.exposure_pct, 1) + '%' },
        { label: 'Drawdown', value: fmt(o.drawdown_pct, 1) + '%', cls: o.drawdown_pct > 5 ? 'negative' : '' },
        { label: 'Peak Equity', value: fmtUsd(o.peak_equity) },
    ];

    const grid = document.getElementById('metrics-grid');
    grid.innerHTML = cards.map(c => `
        <div class="metric-card">
            <div class="metric-label">${c.label}</div>
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
        body.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#4b5563;padding:20px;">Aucune position ouverte</td></tr>';
        return;
    }

    body.innerHTML = positions.map(p => `
        <tr>
            <td title="${p.question || ''}">${truncate(p.question || p.market_id, 35)}</td>
            <td><span style="color:${p.side === 'YES' ? '#4ade80' : '#f87171'};font-weight:600;">${p.side}</span></td>
            <td>${fmtUsd(p.size_usd)}</td>
            <td>${fmt(p.entry_price, 3)}</td>
            <td>${fmt(p.current_price, 3)}</td>
            <td class="${pnlClass(p.unrealized_pnl)}">${fmtUsd(p.unrealized_pnl)} (${fmt((p.unrealized_pnl_pct || 0) * 100, 1)}%)</td>
        </tr>
    `).join('');
}

function renderStats(data) {
    const s = data.trade_stats || {};
    const rows = [
        ['Total Trades', s.total_trades || 0],
        ['Win Rate', fmt(s.win_rate, 1) + '%'],
        ['Trades Gagnants', s.winning_trades || 0],
        ['Trades Perdants', s.losing_trades || 0],
        ['Gain Moyen', fmtUsd(s.avg_win)],
        ['Perte Moyenne', fmtUsd(s.avg_loss)],
        ['Profit Factor', fmt(s.profit_factor)],
        ['Plus Gros Gain', fmtUsd(s.largest_win)],
        ['Plus Grosse Perte', fmtUsd(s.largest_loss)],
        ['Marches Scannes', data.markets_scanned || 0],
        ['Signaux Generes', data.signals_generated || 0],
        ['Iteration', data.iteration || 0],
    ];

    document.getElementById('stats-grid').innerHTML = rows.map(([label, value]) => `
        <div class="stat-row">
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
.param-info { }
.param-label {
    font-size: 13px;
    font-weight: 500;
    color: #e0e6ed;
}
.param-label.modified { color: #fbbf24; }
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
    <h1><span>POLYMARKET</span> Hedge Fund Bot</h1>
    <div class="header-right">
        <a href="/" class="nav-link">Dashboard</a>
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

function createParamRow(p) {
    const row = document.createElement('div');
    row.className = 'param-row';
    row.id = 'row-' + p.key;

    const displayValue = p.type === 'percent' ? (p.value * 100).toFixed(1) + '%' : p.value;
    const displayDefault = p.type === 'percent' ? (p.default * 100).toFixed(1) + '%' : p.default;

    // Info
    const info = document.createElement('div');
    info.className = 'param-info';
    info.innerHTML = `
        <div class="param-label ${p.modified ? 'modified' : ''}">${p.label || p.key}</div>
        <div class="param-desc">${p.desc || ''}</div>
        <div class="param-default">Default: ${displayDefault}</div>
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
    print(f"Dashboard demarre sur http://localhost:{port}")
    app.run(host=args.host, port=port, debug=True)


if __name__ == "__main__":
    main()
