"""
Dashboard web temps reel pour le Listing Sniper.

Interface HTML/CSS/JS embarquee. Rafraichissement automatique toutes les 10 secondes.
Keep-alive integre pour eviter le sleep du free tier (Render/Railway/Fly.io).

Fonctionnalites :
    - Vue d'ensemble : portfolio, PnL, positions ouvertes
    - Signaux detectes en temps reel
    - Historique des trades avec PnL
    - Metriques de performance (Sharpe, win rate, drawdown)
    - Circuit breaker status
    - Logs d'erreurs

Usage :
    # Standalone
    python listing-sniper/src/web_dashboard.py --port 5050

    # Integre au bot
    python -m src.main --dashboard --port 5050
"""

import json
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from flask import Flask, jsonify, Response


# ── Keep-Alive ───────────────────────────────────────────────

def _start_keep_alive(app_url: str, interval: int = 600):
    """Ping le serveur toutes les 10 min pour eviter le sleep du free tier."""
    def _ping():
        while True:
            try:
                urllib.request.urlopen(f"{app_url}/api/health", timeout=10)
            except Exception:
                pass
            time.sleep(interval)

    t = threading.Thread(target=_ping, daemon=True)
    t.start()


# ── State File ───────────────────────────────────────────────

_STATE_FILE = Path(__file__).parent.parent / "sniper_state.json"


def save_state(data: dict[str, Any]) -> None:
    """Sauvegarde l'etat du sniper pour le dashboard."""
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass


def _load_state() -> dict[str, Any]:
    """Charge l'etat du sniper."""
    if not _STATE_FILE.exists():
        return {
            "status": "starting",
            "mode": "dry_run",
            "portfolio_value_usd": 0,
            "sol_balance": 0,
            "daily_pnl_usd": 0,
            "total_pnl_usd": 0,
            "open_positions": [],
            "recent_signals": [],
            "recent_trades": [],
            "performance": {},
            "risk_status": {},
            "circuit_breaker": {},
            "errors": [],
            "uptime": "",
            "last_update": "",
        }
    try:
        with open(_STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"status": "error", "errors": ["Could not read state file"]}


# ── Dashboard HTML ───────────────────────────────────────────

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Listing Sniper Dashboard</title>
<meta http-equiv="refresh" content="10">
<style>
:root {
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --green: #3fb950;
    --red: #f85149;
    --blue: #58a6ff;
    --yellow: #d29922;
    --purple: #bc8cff;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    padding: 20px;
}
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
}
.header h1 { font-size: 24px; }
.header .mode {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
}
.mode-dry_run { background: var(--yellow); color: #000; }
.mode-live { background: var(--green); color: #000; }
.mode-paper { background: var(--blue); color: #000; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
.card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
}
.card .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
.card .value { font-size: 28px; font-weight: 700; margin-top: 4px; }
.positive { color: var(--green); }
.negative { color: var(--red); }
.neutral { color: var(--blue); }
h2 { font-size: 18px; margin: 24px 0 12px; color: var(--muted); }
table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); font-size: 14px; }
th { color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; }
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
}
.badge-safe { background: #1a4731; color: var(--green); }
.badge-medium { background: #3d2e00; color: var(--yellow); }
.badge-risky { background: #4a1d1d; color: var(--red); }
.badge-open { background: #0d2744; color: var(--blue); }
.badge-closed { background: #1a1a2e; color: var(--purple); }
.badge-buy { background: #1a4731; color: var(--green); }
.badge-sell { background: #4a1d1d; color: var(--red); }
.breaker-ok { color: var(--green); }
.breaker-tripped { color: var(--red); font-weight: 700; }
.footer { margin-top: 32px; text-align: center; color: var(--muted); font-size: 12px; }
.status-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}
.dot-running { background: var(--green); }
.dot-halted { background: var(--red); }
.dot-starting { background: var(--yellow); }
</style>
</head>
<body>
<div id="app"></div>
<script>
async function load() {
    try {
        const r = await fetch('/api/state');
        const d = await r.json();
        render(d);
    } catch(e) {
        document.getElementById('app').innerHTML = '<p style="color:red">Erreur de chargement</p>';
    }
}

function pnlClass(v) { return v > 0 ? 'positive' : v < 0 ? 'negative' : 'neutral'; }
function fmt(v, dec=2) { return v != null ? Number(v).toFixed(dec) : '—'; }

function render(d) {
    const status = d.status || 'unknown';
    const dotClass = status === 'running' ? 'dot-running' : status === 'halted' ? 'dot-halted' : 'dot-starting';
    const mode = d.mode || 'dry_run';

    let html = `
    <div class="header">
        <h1><span class="status-dot ${dotClass}"></span> Listing Sniper</h1>
        <span class="mode mode-${mode}">${mode.toUpperCase()}</span>
    </div>
    <div class="grid">
        <div class="card">
            <div class="label">Portfolio</div>
            <div class="value">$${fmt(d.portfolio_value_usd)}</div>
        </div>
        <div class="card">
            <div class="label">PnL Jour</div>
            <div class="value ${pnlClass(d.daily_pnl_usd)}">$${fmt(d.daily_pnl_usd)}</div>
        </div>
        <div class="card">
            <div class="label">PnL Total</div>
            <div class="value ${pnlClass(d.total_pnl_usd)}">$${fmt(d.total_pnl_usd)}</div>
        </div>
        <div class="card">
            <div class="label">SOL Balance</div>
            <div class="value neutral">${fmt(d.sol_balance, 4)}</div>
        </div>
        <div class="card">
            <div class="label">Positions Ouvertes</div>
            <div class="value">${(d.open_positions || []).length}</div>
        </div>
        <div class="card">
            <div class="label">Circuit Breaker</div>
            <div class="value ${(d.circuit_breaker||{}).is_tripped ? 'breaker-tripped' : 'breaker-ok'}">
                ${(d.circuit_breaker||{}).is_tripped ? 'TRIPPED' : 'OK'}
            </div>
        </div>
    </div>`;

    // Performance
    const perf = d.performance || {};
    if (perf.total_trades != null) {
        html += `<h2>Performance</h2>
        <div class="grid">
            <div class="card"><div class="label">Trades</div><div class="value">${perf.total_trades}</div></div>
            <div class="card"><div class="label">Win Rate</div><div class="value">${fmt((perf.win_rate||0)*100,1)}%</div></div>
            <div class="card"><div class="label">Sharpe</div><div class="value">${fmt(perf.sharpe_ratio)}</div></div>
            <div class="card"><div class="label">Max Drawdown</div><div class="value negative">${fmt((perf.max_drawdown_pct||0)*100,1)}%</div></div>
            <div class="card"><div class="label">Profit Factor</div><div class="value">${fmt(perf.profit_factor)}</div></div>
        </div>`;
    }

    // Positions ouvertes
    const pos = d.open_positions || [];
    if (pos.length) {
        html += '<h2>Positions Ouvertes</h2><div class="card"><table><tr><th>Token</th><th>Entree</th><th>Actuel</th><th>PnL</th><th>Duree</th><th>Risk</th></tr>';
        pos.forEach(p => {
            const pnl = ((p.current_price_usd - p.entry_price_usd) / p.entry_price_usd * 100) || 0;
            html += `<tr>
                <td><strong>${p.token_symbol}</strong></td>
                <td>$${fmt(p.entry_price_usd, 6)}</td>
                <td>$${fmt(p.current_price_usd, 6)}</td>
                <td class="${pnlClass(pnl)}">${fmt(pnl,1)}%</td>
                <td>${fmt(p.hold_hours,1)}h</td>
                <td><span class="badge badge-${p.risk_score <= 30 ? 'safe' : p.risk_score <= 60 ? 'medium' : 'risky'}">${p.risk_score}</span></td>
            </tr>`;
        });
        html += '</table></div>';
    }

    // Signaux recents
    const sigs = d.recent_signals || [];
    if (sigs.length) {
        html += '<h2>Signaux Recents</h2><div class="card"><table><tr><th>Token</th><th>Exchange</th><th>Source</th><th>Confiance</th><th>Heure</th></tr>';
        sigs.slice(0, 20).forEach(s => {
            html += `<tr>
                <td><strong>${s.token_symbol}</strong></td>
                <td>${s.exchange}</td>
                <td>${s.source}</td>
                <td>${fmt((s.confidence||0)*100,0)}%</td>
                <td>${s.detection_time || '—'}</td>
            </tr>`;
        });
        html += '</table></div>';
    }

    // Trades recents
    const trades = d.recent_trades || [];
    if (trades.length) {
        html += '<h2>Trades Recents</h2><div class="card"><table><tr><th>Token</th><th>Side</th><th>Montant</th><th>Prix</th><th>Status</th><th>TX</th></tr>';
        trades.slice(0, 20).forEach(t => {
            const txShort = t.tx_signature ? t.tx_signature.substring(0, 12) + '...' : '—';
            html += `<tr>
                <td><strong>${t.token_symbol}</strong></td>
                <td><span class="badge badge-${(t.side||'').toLowerCase()}">${t.side}</span></td>
                <td>$${fmt(t.amount_usd)}</td>
                <td>$${fmt(t.price_usd, 8)}</td>
                <td><span class="badge badge-${(t.status||'').toLowerCase()}">${t.status}</span></td>
                <td>${txShort}</td>
            </tr>`;
        });
        html += '</table></div>';
    }

    // Risk status
    const risk = d.risk_status || {};
    html += `<h2>Risk Management</h2>
    <div class="grid">
        <div class="card"><div class="label">Trades Restants</div><div class="value">${risk.trades_remaining ?? '—'}</div></div>
        <div class="card"><div class="label">Perte Jour</div><div class="value ${pnlClass(-(risk.daily_loss_pct||0)*100)}">${fmt((risk.daily_loss_pct||0)*100,1)}%</div></div>
        <div class="card"><div class="label">Exposition</div><div class="value">${fmt((risk.exposure_pct||0)*100,1)}%</div></div>
        <div class="card"><div class="label">Halted</div><div class="value ${risk.is_halted ? 'negative' : 'positive'}">${risk.is_halted ? 'OUI' : 'NON'}</div></div>
    </div>`;

    // Errors
    const errors = d.errors || [];
    if (errors.length) {
        html += '<h2>Erreurs Recentes</h2><div class="card"><table><tr><th>Module</th><th>Message</th><th>Heure</th></tr>';
        errors.slice(0, 10).forEach(e => {
            html += `<tr><td>${e.module||'—'}</td><td>${e.message||e}</td><td>${e.time||'—'}</td></tr>`;
        });
        html += '</table></div>';
    }

    html += `<div class="footer">
        Uptime: ${d.uptime || '—'} | Derniere MAJ: ${d.last_update || '—'} | Auto-refresh 10s
    </div>`;

    document.getElementById('app').innerHTML = html;
}

load();
setInterval(load, 10000);
</script>
</body>
</html>"""


# ── Flask App ────────────────────────────────────────────────

def create_dashboard_app(sniper=None) -> Flask:
    """Cree l'application Flask du dashboard."""
    app = Flask(__name__)

    @app.route("/")
    def index():
        return Response(_DASHBOARD_HTML, content_type="text/html")

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})

    @app.route("/api/state")
    def state():
        if sniper:
            return jsonify(sniper.get_dashboard_data())
        return jsonify(_load_state())

    @app.route("/api/signals")
    def signals():
        data = _load_state() if not sniper else sniper.get_dashboard_data()
        return jsonify(data.get("recent_signals", []))

    @app.route("/api/positions")
    def positions():
        data = _load_state() if not sniper else sniper.get_dashboard_data()
        return jsonify(data.get("open_positions", []))

    @app.route("/api/trades")
    def trades():
        data = _load_state() if not sniper else sniper.get_dashboard_data()
        return jsonify(data.get("recent_trades", []))

    @app.route("/api/performance")
    def performance():
        data = _load_state() if not sniper else sniper.get_dashboard_data()
        return jsonify(data.get("performance", {}))

    return app


def run_standalone(port: int = 5050):
    """Lance le dashboard en mode standalone."""
    app = create_dashboard_app()

    # Keep-alive
    _start_keep_alive(f"http://localhost:{port}")

    print(f"Dashboard Listing Sniper: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(__import__("os").environ.get("PORT", 5050)))
    args = parser.parse_args()
    run_standalone(args.port)
