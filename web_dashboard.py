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
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, Response


def create_dashboard_app(bot=None, state_file="bot_state.json"):
    """Cree l'application Flask du dashboard."""
    app = Flask(__name__)

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

    @app.route("/")
    def index():
        return Response(DASHBOARD_HTML, mimetype="text/html")

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
#  MAIN (mode standalone)
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="Dashboard Web Polymarket Bot")
    parser.add_argument("--port", type=int, default=5050, help="Port du serveur")
    parser.add_argument("--host", default="0.0.0.0", help="Adresse d'ecoute")
    parser.add_argument("--state-file", default="bot_state.json", help="Fichier d'etat du bot")
    args = parser.parse_args()

    app = create_dashboard_app(state_file=args.state_file)
    print(f"Dashboard demarre sur http://localhost:{args.port}")
    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
