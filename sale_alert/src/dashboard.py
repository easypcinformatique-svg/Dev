"""
Dashboard web pour Sale Alert — Ticketmaster monitor.

Affiche le statut du monitoring, les événements détectés,
et fournit un endpoint /api/health pour le keep-alive.

Usage :
    python -m sale_alert.src.dashboard --port 5051
"""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, Response


# ── Keep-alive ───────────────────────────────────────────────────────

def _start_keep_alive(app_url: str, interval: int = 600):
    """Ping le serveur toutes les 10 min pour éviter le sleep du free tier."""

    def _ping():
        while True:
            try:
                urllib.request.urlopen(f"{app_url}/api/health", timeout=10)
            except Exception:
                pass
            time.sleep(interval)

    t = threading.Thread(target=_ping, daemon=True)
    t.start()


# ── State tracking ──────────────────────────────────────────────────

class AlertState:
    """Thread-safe state shared between monitor and dashboard."""

    def __init__(self):
        self.started_at: str = datetime.now(timezone.utc).isoformat()
        self.artists_watched: list[str] = []
        self.detected_events: list[dict] = []
        self.last_poll: str | None = None
        self.total_polls: int = 0
        self.errors: list[dict] = []
        self._lock = threading.Lock()

    def record_poll(self):
        with self._lock:
            self.total_polls += 1
            self.last_poll = datetime.now(timezone.utc).isoformat()

    def record_detection(self, event_dict: dict):
        with self._lock:
            self.detected_events.append(event_dict)

    def record_error(self, msg: str):
        with self._lock:
            self.errors.append({
                "time": datetime.now(timezone.utc).isoformat(),
                "message": msg,
            })
            # Keep last 50 errors
            if len(self.errors) > 50:
                self.errors = self.errors[-50:]

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "started_at": self.started_at,
                "uptime_since": self.started_at,
                "artists_watched": list(self.artists_watched),
                "detected_events": list(self.detected_events),
                "last_poll": self.last_poll,
                "total_polls": self.total_polls,
                "recent_errors": list(self.errors[-10:]),
            }


# ── Flask app ────────────────────────────────────────────────────────

def create_dashboard_app(state: AlertState | None = None) -> Flask:
    app = Flask(__name__)
    if state is None:
        state = AlertState()
    app._alert_state = state

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})

    @app.route("/api/status")
    def status():
        return jsonify(app._alert_state.to_dict())

    @app.route("/")
    def index():
        return Response(_render_html(app._alert_state), content_type="text/html")

    return app


def _render_html(state: AlertState) -> str:
    data = state.to_dict()
    events_html = ""
    for ev in reversed(data["detected_events"]):
        events_html += f"""
        <tr>
            <td>{ev.get('detected_at','')[:19]}</td>
            <td><strong>{ev.get('artist','')}</strong></td>
            <td>{ev.get('event_name','')}</td>
            <td>{ev.get('start_date','')}</td>
            <td>{ev.get('min_price','—')}€ – {ev.get('max_price','—')}€</td>
            <td><a href="{ev.get('url','#')}" target="_blank">Acheter</a></td>
        </tr>"""

    if not events_html:
        events_html = '<tr><td colspan="6" style="text-align:center;color:#888;">Aucun événement détecté pour le moment</td></tr>'

    artists = ", ".join(data["artists_watched"]) or "—"
    errors_html = ""
    for err in reversed(data["recent_errors"]):
        errors_html += f"<li><code>{err['time'][:19]}</code> — {err['message']}</li>"

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sale Alert — Ticketmaster Monitor</title>
<meta http-equiv="refresh" content="15">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,sans-serif; background:#0d1117; color:#c9d1d9; padding:20px; }}
  h1 {{ color:#58a6ff; margin-bottom:8px; }}
  .subtitle {{ color:#8b949e; margin-bottom:24px; }}
  .cards {{ display:flex; gap:16px; flex-wrap:wrap; margin-bottom:24px; }}
  .card {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px 20px; min-width:180px; }}
  .card .label {{ color:#8b949e; font-size:13px; }}
  .card .value {{ font-size:24px; font-weight:bold; color:#58a6ff; margin-top:4px; }}
  .card .value.green {{ color:#3fb950; }}
  table {{ width:100%; border-collapse:collapse; background:#161b22; border-radius:8px; overflow:hidden; margin-bottom:24px; }}
  th {{ background:#21262d; color:#8b949e; text-align:left; padding:10px 12px; font-size:13px; }}
  td {{ padding:10px 12px; border-top:1px solid #21262d; }}
  a {{ color:#58a6ff; text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .errors {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px; }}
  .errors li {{ margin:4px 0; font-size:13px; color:#f85149; }}
</style>
</head>
<body>
<h1>🎫 Sale Alert — Ticketmaster Monitor</h1>
<p class="subtitle">Surveillance active · Rafraîchissement auto toutes les 15s</p>

<div class="cards">
  <div class="card">
    <div class="label">Artistes surveillés</div>
    <div class="value">{len(data['artists_watched'])}</div>
  </div>
  <div class="card">
    <div class="label">Événements détectés</div>
    <div class="value green">{len(data['detected_events'])}</div>
  </div>
  <div class="card">
    <div class="label">Polls effectués</div>
    <div class="value">{data['total_polls']}</div>
  </div>
  <div class="card">
    <div class="label">Dernier poll</div>
    <div class="value" style="font-size:14px;">{(data['last_poll'] or '—')[:19]}</div>
  </div>
</div>

<p style="margin-bottom:8px;color:#8b949e;">Artistes : <strong style="color:#c9d1d9;">{artists}</strong></p>

<table>
  <tr><th>Détecté à</th><th>Artiste</th><th>Événement</th><th>Date</th><th>Prix</th><th>Lien</th></tr>
  {events_html}
</table>

{"<div class='errors'><h3 style='margin-bottom:8px;color:#f85149;'>Erreurs récentes</h3><ul>" + errors_html + "</ul></div>" if errors_html else ""}

<p style="margin-top:24px;color:#484f58;font-size:12px;">Démarré le {data['started_at'][:19]} UTC</p>
</body>
</html>"""
