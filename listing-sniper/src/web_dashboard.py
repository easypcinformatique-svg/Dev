"""
Dashboard web temps reel pour le Listing Sniper.

Interface complete avec :
    - Statut de chaque scanner (Binance, Bybit, OKX, KuCoin, Twitter, WebSocket, On-chain)
    - Feed d'activite live (ce que le bot fait en temps reel)
    - Signaux detectes, positions, trades
    - Metriques de performance
    - Logs scrollables
    - Keep-alive integre
"""

import json
import threading
import time
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


# ── Activity Log (in-memory ring buffer) ─────────────────────

_activity_log: deque[dict] = deque(maxlen=200)


def log_activity(source: str, action: str, detail: str = "", level: str = "info"):
    """Ajoute une entree au feed d'activite."""
    _activity_log.append({
        "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "action": action,
        "detail": detail[:300],
        "level": level,  # info, success, warning, error
    })


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
        return _default_state()
    try:
        with open(_STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return _default_state()


def _default_state() -> dict[str, Any]:
    return {
        "status": "starting",
        "mode": "dry_run",
        "portfolio_value_usd": 0,
        "sol_balance": 0,
        "sol_price_usd": 0,
        "daily_pnl_usd": 0,
        "total_pnl_usd": 0,
        "open_positions": [],
        "recent_signals": [],
        "recent_trades": [],
        "performance": {},
        "risk_status": {},
        "circuit_breaker": {},
        "scanners": {},
        "errors": [],
        "activity": [],
        "uptime": "",
        "last_update": "",
    }


# ── Dashboard HTML ───────────────────────────────────────────

_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Listing Sniper Dashboard</title>
<style>
:root {
    --bg: #0a0e14;
    --bg2: #0d1117;
    --card: #161b22;
    --card2: #1c2333;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --green: #3fb950;
    --green-dim: #1a4731;
    --red: #f85149;
    --red-dim: #4a1d1d;
    --blue: #58a6ff;
    --blue-dim: #0d2744;
    --yellow: #d29922;
    --yellow-dim: #3d2e00;
    --purple: #bc8cff;
    --orange: #f0883e;
    --cyan: #39d2c0;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', Consolas, monospace;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    font-size: 13px;
}
.container { max-width: 1600px; margin: 0 auto; padding: 16px; }

/* Header */
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 20px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 100;
}
.header h1 { font-size: 16px; letter-spacing: 1px; }
.header h1 span.logo { color: var(--cyan); }
.header-right { display: flex; gap: 12px; align-items: center; }
.badge-mode {
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}
.badge-dry_run { background: var(--yellow); color: #000; }
.badge-live { background: var(--green); color: #000; }
.badge-paper { background: var(--blue); color: #000; }
.uptime-badge { color: var(--muted); font-size: 11px; }
.pulse {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    animation: pulse-anim 2s infinite;
}
.pulse-green { background: var(--green); box-shadow: 0 0 6px var(--green); }
.pulse-red { background: var(--red); box-shadow: 0 0 6px var(--red); }
.pulse-yellow { background: var(--yellow); box-shadow: 0 0 6px var(--yellow); }
@keyframes pulse-anim {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* Layout */
.main-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-top: 16px;
}
@media (max-width: 1200px) { .main-grid { grid-template-columns: 1fr; } }
.full-width { grid-column: 1 / -1; }

/* Cards */
.card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
}
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    background: var(--card2);
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--muted);
}
.card-body { padding: 16px; }

/* Stats row */
.stats-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
}
.stat-box {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px;
    text-align: center;
}
.stat-label { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }
.stat-value { font-size: 22px; font-weight: 700; margin-top: 2px; }

/* Scanner status */
.scanner-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 10px;
}
.scanner-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 6px;
}
.scanner-icon {
    width: 36px; height: 36px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    font-weight: 700;
}
.scanner-info { flex: 1; }
.scanner-name { font-size: 12px; font-weight: 600; }
.scanner-detail { font-size: 10px; color: var(--muted); }
.scanner-status {
    width: 8px; height: 8px;
    border-radius: 50%;
}
.sc-active { background: var(--green); box-shadow: 0 0 4px var(--green); }
.sc-inactive { background: var(--muted); }
.sc-error { background: var(--red); box-shadow: 0 0 4px var(--red); }

/* Activity feed */
.activity-feed {
    max-height: 400px;
    overflow-y: auto;
    font-size: 12px;
}
.activity-feed::-webkit-scrollbar { width: 6px; }
.activity-feed::-webkit-scrollbar-track { background: var(--bg2); }
.activity-feed::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
.activity-item {
    display: flex;
    gap: 8px;
    padding: 6px 12px;
    border-bottom: 1px solid rgba(48,54,61,0.3);
    align-items: flex-start;
}
.activity-item:hover { background: rgba(88,166,255,0.04); }
.activity-time { color: var(--muted); white-space: nowrap; min-width: 60px; }
.activity-source {
    font-weight: 600;
    min-width: 80px;
    white-space: nowrap;
}
.activity-source.src-binance { color: #f0b90b; }
.activity-source.src-bybit { color: #f7a600; }
.activity-source.src-okx { color: #fff; }
.activity-source.src-kucoin { color: #23af91; }
.activity-source.src-twitter { color: #1da1f2; }
.activity-source.src-websocket { color: var(--purple); }
.activity-source.src-onchain { color: var(--cyan); }
.activity-source.src-system { color: var(--muted); }
.activity-source.src-risk { color: var(--orange); }
.activity-source.src-execution { color: var(--green); }
.activity-action { color: var(--text); flex: 1; word-break: break-word; }
.activity-level-error .activity-action { color: var(--red); }
.activity-level-warning .activity-action { color: var(--yellow); }
.activity-level-success .activity-action { color: var(--green); }

/* Tables */
table { width: 100%; border-collapse: collapse; }
th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid rgba(48,54,61,0.5); font-size: 12px; }
th { color: var(--muted); font-weight: 600; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; background: var(--bg2); }
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
.badge-buy { background: var(--green-dim); color: var(--green); }
.badge-sell { background: var(--red-dim); color: var(--red); }
.badge-open { background: var(--blue-dim); color: var(--blue); }
.badge-safe { background: var(--green-dim); color: var(--green); }
.badge-medium { background: var(--yellow-dim); color: var(--yellow); }
.badge-risky { background: var(--red-dim); color: var(--red); }
.positive { color: var(--green); }
.negative { color: var(--red); }
.neutral { color: var(--blue); }

/* Footer */
.footer {
    text-align: center;
    padding: 16px;
    color: var(--muted);
    font-size: 11px;
    border-top: 1px solid var(--border);
    margin-top: 16px;
}
.footer .refresh-bar {
    width: 100%;
    height: 2px;
    background: var(--border);
    margin-top: 8px;
    border-radius: 1px;
    overflow: hidden;
}
.footer .refresh-fill {
    height: 100%;
    background: var(--cyan);
    animation: refresh-anim 5s linear infinite;
}
@keyframes refresh-anim {
    0% { width: 0%; }
    100% { width: 100%; }
}
</style>
</head>
<body>

<div class="header">
    <h1><span class="logo">&#9670;</span> LISTING SNIPER</h1>
    <div class="header-right">
        <span class="uptime-badge" id="uptime"></span>
        <span class="uptime-badge" id="sol-price"></span>
        <span id="mode-badge"></span>
        <span id="status-pulse"></span>
    </div>
</div>

<div class="container">
    <div id="app">Chargement...</div>
</div>

<script>
let refreshTimer = 0;

async function load() {
    try {
        const r = await fetch('/api/state');
        const d = await r.json();
        renderAll(d);
    } catch(e) {
        document.getElementById('app').innerHTML = '<p style="color:#f85149">Erreur de connexion au serveur</p>';
    }
}

function pc(v) { return v > 0 ? 'positive' : v < 0 ? 'negative' : 'neutral'; }
function fmt(v, d=2) { return v != null && !isNaN(v) ? Number(v).toFixed(d) : '—'; }
function ago(iso) {
    if (!iso) return '—';
    const s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 60) return Math.floor(s) + 's';
    if (s < 3600) return Math.floor(s/60) + 'min';
    return Math.floor(s/3600) + 'h' + Math.floor((s%3600)/60) + 'm';
}

function renderAll(d) {
    const status = d.status || 'starting';
    const mode = d.mode || 'dry_run';

    // Header
    document.getElementById('uptime').textContent = 'Uptime: ' + (d.uptime || '0m');
    document.getElementById('sol-price').textContent = 'SOL $' + fmt(d.sol_price_usd || 0, 0);
    document.getElementById('mode-badge').innerHTML = `<span class="badge-mode badge-${mode}">${mode.toUpperCase()}</span>`;

    const pulseClass = status === 'running' ? 'pulse-green' : status === 'halted' ? 'pulse-red' : 'pulse-yellow';
    document.getElementById('status-pulse').innerHTML = `<span class="pulse ${pulseClass}"></span>${status.toUpperCase()}`;

    let html = '';

    // ── Stats overview ──
    html += `<div class="full-width card" style="margin-bottom:16px">
        <div class="card-body">
            <div class="stats-row">
                <div class="stat-box">
                    <div class="stat-label">Portfolio</div>
                    <div class="stat-value">$${fmt(d.portfolio_value_usd)}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">PnL Jour</div>
                    <div class="stat-value ${pc(d.daily_pnl_usd)}">$${fmt(d.daily_pnl_usd)}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">PnL Total</div>
                    <div class="stat-value ${pc(d.total_pnl_usd)}">$${fmt(d.total_pnl_usd)}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">SOL Balance</div>
                    <div class="stat-value neutral">${fmt(d.sol_balance, 4)}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Positions</div>
                    <div class="stat-value">${(d.open_positions||[]).length}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Trades Restants</div>
                    <div class="stat-value">${(d.risk_status||{}).trades_remaining ?? 10}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Circuit Breaker</div>
                    <div class="stat-value ${(d.circuit_breaker||{}).is_tripped?'negative':'positive'}">${(d.circuit_breaker||{}).is_tripped?'TRIPPED':'OK'}</div>
                </div>
            </div>
        </div>
    </div>`;

    html += '<div class="main-grid">';

    // ── Scanners status ──
    const sc = d.scanners || {};
    html += `<div class="card">
        <div class="card-header"><span>Scanners Actifs</span><span>${Object.values(sc).filter(s=>s.active).length}/${Object.keys(sc).length} en ligne</span></div>
        <div class="card-body"><div class="scanner-grid">`;

    const scannerDefs = [
        { key: 'binance', name: 'Binance', icon: 'B', color: '#f0b90b' },
        { key: 'bybit', name: 'Bybit', icon: 'By', color: '#f7a600' },
        { key: 'okx', name: 'OKX', icon: 'OK', color: '#fff' },
        { key: 'kucoin', name: 'KuCoin', icon: 'KC', color: '#23af91' },
        { key: 'twitter', name: 'Twitter/X', icon: '𝕏', color: '#1da1f2' },
        { key: 'websocket', name: 'WebSocket', icon: 'WS', color: '#bc8cff' },
        { key: 'onchain', name: 'On-Chain', icon: '⛓', color: '#39d2c0' },
    ];

    scannerDefs.forEach(sd => {
        const s = sc[sd.key] || { active: false, scans: 0, last_scan: null, errors: 0 };
        const statusCls = s.active ? (s.errors > 5 ? 'sc-error' : 'sc-active') : 'sc-inactive';
        const lastScan = s.last_scan ? ago(s.last_scan) + ' ago' : 'never';
        html += `<div class="scanner-item">
            <div class="scanner-icon" style="background:${sd.color}22;color:${sd.color}">${sd.icon}</div>
            <div class="scanner-info">
                <div class="scanner-name">${sd.name}</div>
                <div class="scanner-detail">${s.scans} scans | ${lastScan}</div>
            </div>
            <div class="scanner-status ${statusCls}"></div>
        </div>`;
    });

    html += '</div></div></div>';

    // ── Activity Feed ──
    const acts = d.activity || [];
    html += `<div class="card">
        <div class="card-header"><span>Activite en Direct</span><span>${acts.length} events</span></div>
        <div class="card-body" style="padding:0"><div class="activity-feed">`;

    if (acts.length === 0) {
        html += '<div class="activity-item"><span class="activity-action" style="color:var(--muted);padding:20px;text-align:center;width:100%">En attente d\'activite...</span></div>';
    }

    // Show latest first
    [...acts].reverse().forEach(a => {
        const srcClass = 'src-' + (a.source||'system').toLowerCase().replace(/[^a-z]/g,'');
        html += `<div class="activity-item activity-level-${a.level||'info'}">
            <span class="activity-time">${a.time||''}</span>
            <span class="activity-source ${srcClass}">${a.source||'SYSTEM'}</span>
            <span class="activity-action">${a.action}${a.detail ? ' <span style="color:var(--muted)">'+a.detail+'</span>' : ''}</span>
        </div>`;
    });

    html += '</div></div></div>';

    // ── Signals ──
    const sigs = d.recent_signals || [];
    html += `<div class="card">
        <div class="card-header"><span>Signaux Detectes</span><span>${sigs.length} signaux</span></div>
        <div class="card-body" style="padding:0;max-height:350px;overflow-y:auto">`;
    if (sigs.length) {
        html += '<table><tr><th>Token</th><th>Exchange</th><th>Source</th><th>Confiance</th><th>Texte</th></tr>';
        [...sigs].reverse().slice(0,30).forEach(s => {
            const conf = (s.confidence||0)*100;
            const confColor = conf >= 80 ? 'positive' : conf >= 60 ? 'neutral' : '';
            html += `<tr>
                <td><strong>${s.token_symbol}</strong></td>
                <td>${s.exchange}</td>
                <td>${s.source}</td>
                <td class="${confColor}">${fmt(conf,0)}%</td>
                <td style="color:var(--muted);max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${s.raw_text||'—'}</td>
            </tr>`;
        });
        html += '</table>';
    } else {
        html += '<div style="padding:30px;text-align:center;color:var(--muted)">Aucun signal detecte</div>';
    }
    html += '</div></div>';

    // ── Positions ──
    const pos = d.open_positions || [];
    html += `<div class="card">
        <div class="card-header"><span>Positions Ouvertes</span><span>${pos.length} positions</span></div>
        <div class="card-body" style="padding:0">`;
    if (pos.length) {
        html += '<table><tr><th>Token</th><th>Entree</th><th>Actuel</th><th>PnL</th><th>Duree</th><th>Risk</th></tr>';
        pos.forEach(p => {
            const pnl = p.entry_price_usd > 0 ? ((p.current_price_usd - p.entry_price_usd) / p.entry_price_usd * 100) : 0;
            const riskBadge = p.risk_score <= 30 ? 'safe' : p.risk_score <= 60 ? 'medium' : 'risky';
            html += `<tr>
                <td><strong>${p.token_symbol}</strong></td>
                <td>$${fmt(p.entry_price_usd, 6)}</td>
                <td>$${fmt(p.current_price_usd, 6)}</td>
                <td class="${pc(pnl)}">${fmt(pnl,1)}%</td>
                <td>${fmt(p.hold_hours,1)}h</td>
                <td><span class="badge badge-${riskBadge}">${p.risk_score}</span></td>
            </tr>`;
        });
        html += '</table>';
    } else {
        html += '<div style="padding:30px;text-align:center;color:var(--muted)">Aucune position ouverte</div>';
    }
    html += '</div></div>';

    // ── Performance ──
    const perf = d.performance || {};
    html += `<div class="card full-width">
        <div class="card-header"><span>Performance</span></div>
        <div class="card-body">
            <div class="stats-row">
                <div class="stat-box"><div class="stat-label">Total Trades</div><div class="stat-value">${perf.total_trades||0}</div></div>
                <div class="stat-box"><div class="stat-label">Win Rate</div><div class="stat-value ${(perf.win_rate||0)>=0.5?'positive':'negative'}">${fmt((perf.win_rate||0)*100,1)}%</div></div>
                <div class="stat-box"><div class="stat-label">Sharpe Ratio</div><div class="stat-value ${(perf.sharpe_ratio||0)>=1?'positive':''}">${fmt(perf.sharpe_ratio||0)}</div></div>
                <div class="stat-box"><div class="stat-label">Sortino Ratio</div><div class="stat-value">${fmt(perf.sortino_ratio||0)}</div></div>
                <div class="stat-box"><div class="stat-label">Max Drawdown</div><div class="stat-value negative">${fmt((perf.max_drawdown_pct||0)*100,1)}%</div></div>
                <div class="stat-box"><div class="stat-label">Profit Factor</div><div class="stat-value">${fmt(perf.profit_factor||0)}</div></div>
            </div>
        </div>
    </div>`;

    // ── Risk Management ──
    const risk = d.risk_status || {};
    html += `<div class="card full-width">
        <div class="card-header"><span>Risk Management</span><span class="${risk.is_halted?'negative':'positive'}">${risk.is_halted?'TRADING HALTED':'TRADING ACTIVE'}</span></div>
        <div class="card-body">
            <div class="stats-row">
                <div class="stat-box"><div class="stat-label">Trades Restants</div><div class="stat-value">${risk.trades_remaining ?? 10}/10</div></div>
                <div class="stat-box"><div class="stat-label">Perte Jour</div><div class="stat-value ${pc(-(risk.daily_loss_pct||0))}">${fmt((risk.daily_loss_pct||0)*100,2)}% / 5%</div></div>
                <div class="stat-box"><div class="stat-label">Exposition</div><div class="stat-value">${fmt((risk.exposure_pct||0)*100,1)}% / 30%</div></div>
                <div class="stat-box"><div class="stat-label">RPC Error Rate</div><div class="stat-value ${((d.circuit_breaker||{}).rpc_error_rate||0)>0.1?'negative':'positive'}">${fmt(((d.circuit_breaker||{}).rpc_error_rate||0)*100,1)}%</div></div>
            </div>
        </div>
    </div>`;

    // ── Errors ──
    const errors = d.errors || [];
    if (errors.length) {
        html += `<div class="card full-width">
            <div class="card-header"><span>Erreurs Recentes</span><span class="negative">${errors.length}</span></div>
            <div class="card-body" style="padding:0;max-height:200px;overflow-y:auto"><table>
                <tr><th>Module</th><th>Message</th><th>Heure</th></tr>`;
        errors.slice(-10).reverse().forEach(e => {
            html += `<tr><td>${e.module||'—'}</td><td style="color:var(--red)">${e.message||e}</td><td>${e.time||'—'}</td></tr>`;
        });
        html += '</table></div></div>';
    }

    html += '</div>';  // close main-grid

    // Footer
    const now = new Date().toLocaleTimeString('fr-FR');
    html += `<div class="footer">
        Derniere MAJ: ${d.last_update ? new Date(d.last_update).toLocaleTimeString('fr-FR') : now} | Auto-refresh 5s | listing-sniper v1.0
        <div class="refresh-bar"><div class="refresh-fill"></div></div>
    </div>`;

    document.getElementById('app').innerHTML = html;
}

// Initial load + auto-refresh every 5s
load();
setInterval(load, 5000);
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
        data = sniper.get_dashboard_data() if sniper else _load_state()
        data["activity"] = list(_activity_log)
        return jsonify(data)

    @app.route("/api/signals")
    def signals():
        data = sniper.get_dashboard_data() if sniper else _load_state()
        return jsonify(data.get("recent_signals", []))

    @app.route("/api/positions")
    def positions():
        data = sniper.get_dashboard_data() if sniper else _load_state()
        return jsonify(data.get("open_positions", []))

    @app.route("/api/trades")
    def trades():
        data = sniper.get_dashboard_data() if sniper else _load_state()
        return jsonify(data.get("recent_trades", []))

    @app.route("/api/activity")
    def activity():
        return jsonify(list(_activity_log))

    @app.route("/api/performance")
    def performance():
        data = sniper.get_dashboard_data() if sniper else _load_state()
        return jsonify(data.get("performance", {}))

    return app


def run_standalone(port: int = 5050):
    """Lance le dashboard en mode standalone."""
    app = create_dashboard_app()
    _start_keep_alive(f"http://localhost:{port}")
    print(f"Dashboard Listing Sniper: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(__import__("os").environ.get("PORT", 5050)))
    args = parser.parse_args()
    run_standalone(args.port)
