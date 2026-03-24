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

/* Tooltips */
.tip {
    position: relative;
    cursor: help;
}
.tip::after {
    content: attr(data-tip);
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
    background: #1c2333;
    color: #e6edf3;
    border: 1px solid #58a6ff;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 11px;
    font-weight: 400;
    line-height: 1.5;
    white-space: normal;
    width: max-content;
    max-width: 320px;
    z-index: 1000;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    text-transform: none;
    letter-spacing: 0;
    text-align: left;
}
.tip:hover::after { opacity: 1; }
/* Tooltip pointing down (for header items) */
.tip-down::after {
    bottom: auto;
    top: calc(100% + 8px);
}

/* Bot info banner */
.bot-info {
    background: linear-gradient(135deg, #0d2744 0%, #1a0d3d 100%);
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 16px;
}
.bot-info-toggle {
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
}
.bot-info-toggle h2 { font-size: 14px; color: var(--cyan); }
.bot-info-toggle span { font-size: 11px; color: var(--muted); }
.bot-info-content {
    margin-top: 12px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    font-size: 12px;
    color: var(--muted);
    line-height: 1.7;
}
.bot-info-content h3 { color: var(--blue); font-size: 12px; margin-bottom: 4px; }
@media (max-width: 900px) { .bot-info-content { grid-template-columns: 1fr; } }
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
    document.getElementById('mode-badge').innerHTML = `<span class="badge-mode badge-${mode} tip tip-down" data-tip="PAPER = trades simules sans argent reel. DRY_RUN = meme chose. LIVE = trades reels sur la blockchain Solana.">${mode.toUpperCase()}</span>`;

    const pulseClass = status === 'running' ? 'pulse-green' : status === 'halted' ? 'pulse-red' : 'pulse-yellow';
    document.getElementById('status-pulse').innerHTML = `<span class="pulse ${pulseClass}"></span><span class="tip tip-down" data-tip="RUNNING = le bot tourne et scanne les exchanges. HALTED = trading suspendu (limite de pertes atteinte). STOPPED = arrete.">${status.toUpperCase()}</span>`;

    let html = '';

    // ── Bot info banner ──
    html += `<div class="bot-info">
        <div class="bot-info-toggle" onclick="let c=this.nextElementSibling;c.style.display=c.style.display==='none'?'grid':'none';this.querySelector('.arrow').textContent=c.style.display==='none'?'&#9654; Voir':'&#9660; Masquer'">
            <h2>&#9670; Qu'est-ce que le Listing Sniper ?</h2>
            <span class="arrow">&#9660; Masquer</span>
        </div>
        <div class="bot-info-content">
            <div>
                <h3>Le concept</h3>
                <p>Le Listing Sniper est un bot de trading automatise qui detecte les <strong style="color:#58a6ff">nouvelles annonces de listing</strong> sur les exchanges crypto (Binance, Bybit, OKX, KuCoin) et achete le token immediatement apres l'annonce, avant que le prix ne monte.</p>
                <p style="margin-top:6px">L'idee : quand un exchange annonce qu'il va lister un nouveau token, le prix monte souvent de +20% a +500% en quelques minutes. Le bot detecte cette annonce en &lt;2 secondes et execute un achat automatique.</p>
            </div>
            <div>
                <h3>Le pipeline (en 8 etapes)</h3>
                <p><strong style="color:#f0b90b">1.</strong> Les <em>Scanners</em> surveillent les annonces (API, Twitter, WebSocket, on-chain)<br>
                <strong style="color:#f0b90b">2.</strong> Le <em>Validateur</em> filtre les faux positifs et les delistings<br>
                <strong style="color:#f0b90b">3.</strong> Le <em>Token Discovery</em> trouve l'adresse du contrat sur Solana<br>
                <strong style="color:#f0b90b">4.</strong> Le <em>Risk Assessor</em> evalue le risque (honeypot, liquidite, holders)<br>
                <strong style="color:#f0b90b">5.</strong> Le <em>Position Sizer</em> calcule la taille optimale (Kelly Criterion)<br>
                <strong style="color:#f0b90b">6.</strong> Le <em>Risk Manager</em> verifie les limites (pertes, exposition)<br>
                <strong style="color:#f0b90b">7.</strong> L'<em>Executeur Jupiter</em> achete via le DEX Jupiter sur Solana<br>
                <strong style="color:#f0b90b">8.</strong> Le <em>Position Manager</em> gere les take-profit et stop-loss</p>
            </div>
        </div>
    </div>`;

    // ── Stats overview ──
    html += `<div class="full-width card" style="margin-bottom:16px">
        <div class="card-body">
            <div class="stats-row">
                <div class="stat-box tip" data-tip="Valeur totale du portefeuille en USD. C'est le capital initial + les gains/pertes cumules. En mode PAPER, c'est un portefeuille virtuel.">
                    <div class="stat-label">Portfolio</div>
                    <div class="stat-value">$${fmt(d.portfolio_value_usd)}</div>
                </div>
                <div class="stat-box tip" data-tip="Profit ou perte realise(e) aujourd'hui. Vert = en gain, Rouge = en perte. Se remet a zero a minuit UTC.">
                    <div class="stat-label">PnL Jour</div>
                    <div class="stat-value ${pc(d.daily_pnl_usd)}">$${fmt(d.daily_pnl_usd)}</div>
                </div>
                <div class="stat-box tip" data-tip="PnL = Profit and Loss. Gains ou pertes non-realises sur toutes les positions ouvertes. Change en temps reel avec le prix des tokens.">
                    <div class="stat-label">PnL Total</div>
                    <div class="stat-value ${pc(d.total_pnl_usd)}">$${fmt(d.total_pnl_usd)}</div>
                </div>
                <div class="stat-box tip" data-tip="Solde en SOL (la crypto native de Solana) dans le wallet du bot. Sert a payer les frais de transaction et a acheter les tokens. En mode PAPER = 0.">
                    <div class="stat-label">SOL Balance</div>
                    <div class="stat-value neutral">${fmt(d.sol_balance, 4)}</div>
                </div>
                <div class="stat-box tip" data-tip="Nombre de positions actuellement ouvertes. Une position = un token achete que le bot n'a pas encore vendu.">
                    <div class="stat-label">Positions</div>
                    <div class="stat-value">${(d.open_positions||[]).length}</div>
                </div>
                <div class="stat-box tip" data-tip="Nombre de trades que le bot peut encore faire aujourd'hui. Limite fixe a 10/jour pour eviter le sur-trading. Se reinitialise a minuit UTC.">
                    <div class="stat-label">Trades Restants</div>
                    <div class="stat-value">${(d.risk_status||{}).trades_remaining ?? 10}</div>
                </div>
                <div class="stat-box tip" data-tip="Systeme de securite automatique. Se declenche (TRIPPED) si : le taux d'erreur RPC depasse 10%, le solde SOL est trop bas, ou le reseau Solana est congestione. Bloque tous les trades jusqu'a resolution.">
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
        <div class="card-header"><span class="tip tip-down" data-tip="Les scanners surveillent en permanence les sources d'information (pages d'annonces, Twitter, WebSocket, blockchain) pour detecter de nouveaux listings. Point vert = actif, gris = desactive.">Scanners Actifs</span><span>${Object.values(sc).filter(s=>s.active).length}/${Object.keys(sc).length} en ligne</span></div>
        <div class="card-body"><div class="scanner-grid">`;

    const scannerDefs = [
        { key: 'binance', name: 'Binance', icon: 'B', color: '#f0b90b', tip: 'Scrape la page d\'annonces Binance toutes les 2s pour detecter les nouveaux listings (via API REST). Source la plus fiable.' },
        { key: 'bybit', name: 'Bybit', icon: 'By', color: '#f7a600', tip: 'Surveille les annonces de listing Bybit toutes les 3s. 2eme plus gros exchange mondial.' },
        { key: 'okx', name: 'OKX', icon: 'OK', color: '#fff', tip: 'Scrape les annonces OKX toutes les 3s, notamment la Innovation Zone ou les nouveaux tokens sont listes en premier.' },
        { key: 'kucoin', name: 'KuCoin', icon: 'KC', color: '#23af91', tip: 'Surveille KuCoin toutes les 5s. Souvent le premier exchange a lister des tokens a faible capitalisation.' },
        { key: 'twitter', name: 'Twitter/X', icon: '𝕏', color: '#1da1f2', tip: 'Monitore les comptes Twitter officiels des exchanges pour les annonces de listing. Souvent publie avant la page officielle.' },
        { key: 'websocket', name: 'WebSocket', icon: 'WS', color: '#bc8cff', tip: 'Connexion WebSocket permanente aux exchanges pour detecter l\'apparition de nouvelles paires de trading en temps reel.' },
        { key: 'onchain', name: 'On-Chain', icon: '⛓', color: '#39d2c0', tip: 'Surveille les wallets "hot" des exchanges sur la blockchain pour detecter les depots de nouveaux tokens avant l\'annonce officielle.' },
    ];

    scannerDefs.forEach(sd => {
        const s = sc[sd.key] || { active: false, scans: 0, last_scan: null, errors: 0 };
        const statusCls = s.active ? (s.errors > 5 ? 'sc-error' : 'sc-active') : 'sc-inactive';
        const lastScan = s.last_scan ? ago(s.last_scan) + ' ago' : 'never';
        html += `<div class="scanner-item tip" data-tip="${sd.tip}">
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
        <div class="card-header"><span class="tip tip-down" data-tip="Journal en temps reel de tout ce que le bot fait : detection de signal, validation, evaluation de risque, execution de trade, ouverture/fermeture de position. Vert = succes, Jaune = avertissement, Rouge = erreur.">Activite en Direct</span><span>${acts.length} events</span></div>
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
        <div class="card-header"><span class="tip tip-down" data-tip="Liste de toutes les annonces de listing detectees par les scanners. Chaque signal passe ensuite par le pipeline de validation, risk assessment, et execution.">Signaux Detectes</span><span>${sigs.length} signaux</span></div>
        <div class="card-body" style="padding:0;max-height:350px;overflow-y:auto">`;
    if (sigs.length) {
        html += `<table><tr>
            <th class="tip tip-down" data-tip="Symbole du token detecte (ex: NEWTOKEN). C'est le ticker qui sera trade sur le DEX Solana.">Token</th>
            <th class="tip tip-down" data-tip="L'exchange qui a annonce le listing. Plus l'exchange est gros (Binance), plus l'impact sur le prix est fort.">Exchange</th>
            <th class="tip tip-down" data-tip="Comment le signal a ete detecte : API = page d'annonces, TWITTER = tweet officiel, WEBSOCKET = nouvelle paire detectee, ONCHAIN = activite blockchain.">Source</th>
            <th class="tip tip-down" data-tip="Niveau de confiance du signal (0-100%). Calcule en fonction de la source, la corroboration multi-source, et la presence d'infos verifiables. Au-dessus de 70% = signal fiable.">Confiance</th>
            <th class="tip tip-down" data-tip="Extrait du texte brut de l'annonce detectee (tweet, page web, etc.)">Texte</th>
        </tr>`;
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
        <div class="card-header"><span class="tip tip-down" data-tip="Tokens actuellement detenus par le bot. Le bot achete automatiquement et vend par paliers (take-profit) ou si le stop-loss est atteint.">Positions Ouvertes</span><span>${pos.length} positions</span></div>
        <div class="card-body" style="padding:0">`;
    if (pos.length) {
        html += `<table><tr>
            <th class="tip tip-down" data-tip="Symbole du token detenu">Token</th>
            <th class="tip tip-down" data-tip="Prix d'achat du token en USD au moment de l'entree">Entree</th>
            <th class="tip tip-down" data-tip="Prix actuel du token en USD (mis a jour en temps reel)">Actuel</th>
            <th class="tip tip-down" data-tip="Profit ou Perte en pourcentage = (Prix actuel - Prix d'entree) / Prix d'entree x 100. Vert = en gain, Rouge = en perte.">PnL</th>
            <th class="tip tip-down" data-tip="Depuis combien de temps le bot detient ce token. Influence la strategie de sortie (time-based stop).">Duree</th>
            <th class="tip tip-down" data-tip="Score de risque du token (0-100). 0-30 = SAFE (vert), 31-60 = MEDIUM (jaune), 61-80 = RISKY (rouge). Calcule a partir de la liquidite, holders, honeypot, etc.">Risk</th>
        </tr>`;
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
        <div class="card-header"><span class="tip tip-down" data-tip="Metriques de performance globales du bot depuis le demarrage. Ces indicateurs sont utilises par les traders professionnels pour evaluer une strategie.">Performance</span></div>
        <div class="card-body">
            <div class="stats-row">
                <div class="stat-box tip" data-tip="Nombre total de trades (achats + ventes) executes depuis le demarrage du bot.">
                    <div class="stat-label">Total Trades</div><div class="stat-value">${perf.total_trades||0}</div>
                </div>
                <div class="stat-box tip" data-tip="Pourcentage de trades gagnants. Win Rate = Nombre de gains / Total trades x 100. Au-dessus de 50% = la strategie gagne plus souvent qu'elle ne perd.">
                    <div class="stat-label">Win Rate</div><div class="stat-value ${(perf.win_rate||0)>=0.5?'positive':'negative'}">${fmt((perf.win_rate||0)*100,1)}%</div>
                </div>
                <div class="stat-box tip" data-tip="Sharpe Ratio = rendement moyen / volatilite. Mesure le rapport risque/rendement. &gt;1 = bon, &gt;2 = tres bon, &lt;0 = la strategie perd de l'argent.">
                    <div class="stat-label">Sharpe Ratio</div><div class="stat-value ${(perf.sharpe_ratio||0)>=1?'positive':''}">${fmt(perf.sharpe_ratio||0)}</div>
                </div>
                <div class="stat-box tip" data-tip="Sortino Ratio = comme le Sharpe mais ne penalise que la volatilite negative (les pertes). Plus pertinent car on ne veut pas penaliser les gros gains. &gt;1 = bon.">
                    <div class="stat-label">Sortino Ratio</div><div class="stat-value">${fmt(perf.sortino_ratio||0)}</div>
                </div>
                <div class="stat-box tip" data-tip="Pire chute du portefeuille depuis son plus haut. Exemple : Max DD = -15% signifie qu'a un moment le portfolio a perdu 15% depuis son pic. Plus c'est bas (proche de 0%), mieux c'est.">
                    <div class="stat-label">Max Drawdown</div><div class="stat-value negative">${fmt((perf.max_drawdown_pct||0)*100,1)}%</div>
                </div>
                <div class="stat-box tip" data-tip="Profit Factor = Somme des gains / Somme des pertes. &gt;1 = profitable, &gt;2 = tres bon. Un PF de 1.5 signifie que pour chaque $1 perdu, le bot gagne $1.50.">
                    <div class="stat-label">Profit Factor</div><div class="stat-value">${fmt(perf.profit_factor||0)}</div>
                </div>
            </div>
        </div>
    </div>`;

    // ── Risk Management ──
    const risk = d.risk_status || {};
    html += `<div class="card full-width">
        <div class="card-header"><span class="tip tip-down" data-tip="Systeme de gestion des risques. Ces limites sont codees en dur et ne peuvent pas etre contournees. Elles protegent le capital contre les pertes excessives.">Risk Management</span><span class="${risk.is_halted?'negative':'positive'}">${risk.is_halted?'TRADING HALTED':'TRADING ACTIVE'}</span></div>
        <div class="card-body">
            <div class="stats-row">
                <div class="stat-box tip" data-tip="Limite de 10 trades par jour pour eviter le sur-trading emotionnel. Quand le compteur atteint 0, plus aucun trade ne sera execute jusqu'a minuit UTC.">
                    <div class="stat-label">Trades Restants</div><div class="stat-value">${risk.trades_remaining ?? 10}/10</div>
                </div>
                <div class="stat-box tip" data-tip="Perte maximale autorisee par jour = 5% du portfolio. Si atteinte, le bot arrete de trader pour la journee. Protege contre les sequences de pertes.">
                    <div class="stat-label">Perte Jour</div><div class="stat-value ${pc(-(risk.daily_loss_pct||0))}">${fmt((risk.daily_loss_pct||0)*100,2)}% / 5%</div>
                </div>
                <div class="stat-box tip" data-tip="Exposition = pourcentage du portfolio investi dans des positions ouvertes. Limite a 30% max. Les 70% restants sont en reserve (SOL non-investi).">
                    <div class="stat-label">Exposition</div><div class="stat-value">${fmt((risk.exposure_pct||0)*100,1)}% / 30%</div>
                </div>
                <div class="stat-box tip" data-tip="Taux d'erreur des appels RPC (Remote Procedure Call) vers la blockchain Solana. Si &gt;10%, le circuit breaker se declenche car la blockchain est probablement congestionnee.">
                    <div class="stat-label">RPC Error Rate</div><div class="stat-value ${((d.circuit_breaker||{}).rpc_error_rate||0)>0.1?'negative':'positive'}">${fmt(((d.circuit_breaker||{}).rpc_error_rate||0)*100,1)}%</div>
                </div>
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
