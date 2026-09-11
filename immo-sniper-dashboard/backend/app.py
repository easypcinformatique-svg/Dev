"""
ImmoSniper Backend — API Flask servant les annonces immobilières réelles.
Scan périodique des sources, scoring automatique, API REST pour le frontend.
"""
import os
import json
import time
import threading
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from scraper import scan_all_sources
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__, static_folder="../dist", static_url_path="")
CORS(app)

# ── État global ──
_data_lock = threading.Lock()
_annonces = []
_last_scan = 0
_scan_count = 0
_scan_running = False

SCAN_INTERVAL_MIN = int(os.environ.get("SCAN_INTERVAL", 45))
DATA_FILE = os.path.join(os.path.dirname(__file__), "data_cache.json")


def _save_cache():
    """Sauvegarde les annonces en cache sur disque."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "annonces": _annonces,
                "last_scan": _last_scan,
                "scan_count": _scan_count,
            }, f, ensure_ascii=False)
    except Exception as e:
        print(f"[CACHE] Erreur sauvegarde: {e}")


def _load_cache():
    """Charge les annonces depuis le cache disque."""
    global _annonces, _last_scan, _scan_count
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _annonces = data.get("annonces", [])
                _last_scan = data.get("last_scan", 0)
                _scan_count = data.get("scan_count", 0)
                print(f"[CACHE] {len(_annonces)} annonces chargées depuis le cache")
    except Exception as e:
        print(f"[CACHE] Erreur chargement: {e}")


def run_scan():
    """Exécute un scan complet de toutes les sources."""
    global _annonces, _last_scan, _scan_count, _scan_running

    if _scan_running:
        print("[SCAN] Scan déjà en cours, ignoré")
        return

    _scan_running = True
    try:
        print(f"[SCAN] Lancement du scan #{_scan_count + 1}...")
        results = scan_all_sources()

        with _data_lock:
            if results:
                # Fusionner avec les annonces existantes (garder le statut)
                old_statuts = {a["id"]: a.get("statut", "nouveau") for a in _annonces}
                for r in results:
                    if r["id"] in old_statuts:
                        r["statut"] = old_statuts[r["id"]]
                _annonces = results
            _last_scan = time.time()
            _scan_count += 1

        _save_cache()
        print(f"[SCAN] Terminé: {len(results)} annonces")
    except Exception as e:
        print(f"[SCAN] Erreur: {e}")
    finally:
        _scan_running = False


# ── API Endpoints ──

@app.route("/api/annonces")
def api_annonces():
    """Retourne toutes les annonces scorées."""
    with _data_lock:
        return jsonify({
            "annonces": _annonces,
            "last_scan": _last_scan,
            "scan_count": _scan_count,
            "next_scan_in": max(0, int(SCAN_INTERVAL_MIN * 60 - (time.time() - _last_scan))),
            "total": len(_annonces),
        })


@app.route("/api/annonces/<annonce_id>/statut", methods=["POST"])
def api_update_statut(annonce_id):
    """Met à jour le statut d'une annonce (nouveau, en_cours, traite)."""
    data = request.get_json()
    new_statut = data.get("statut", "nouveau")
    with _data_lock:
        for a in _annonces:
            if a["id"] == annonce_id:
                a["statut"] = new_statut
                _save_cache()
                return jsonify({"ok": True})
    return jsonify({"error": "annonce not found"}), 404


@app.route("/api/scan", methods=["POST"])
def api_force_scan():
    """Force un scan immédiat."""
    if _scan_running:
        return jsonify({"error": "scan already running"}), 429
    threading.Thread(target=run_scan, daemon=True).start()
    return jsonify({"ok": True, "message": "Scan lancé"})


@app.route("/api/stats")
def api_stats():
    """Retourne les statistiques."""
    with _data_lock:
        total = len(_annonces)
        opportunites = len([a for a in _annonces if a.get("score", 0) >= 65])
        exceptionnelles = len([a for a in _annonces if a.get("score", 0) >= 80])
        par_source = {}
        par_type = {}
        for a in _annonces:
            src = a.get("source", "?")
            par_source[src] = par_source.get(src, 0) + 1
            t = a.get("type", "?")
            par_type[t] = par_type.get(t, 0) + 1

        decote_moy = 0
        decotes = [a.get("decote", 0) for a in _annonces if a.get("decote", 0) > 0]
        if decotes:
            decote_moy = round(sum(decotes) / len(decotes), 1)

        return jsonify({
            "total": total,
            "opportunites": opportunites,
            "exceptionnelles": exceptionnelles,
            "decote_moyenne": decote_moy,
            "par_source": par_source,
            "par_type": par_type,
            "last_scan": _last_scan,
            "scan_count": _scan_count,
        })


# ── Serve React SPA ──

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    try:
        return send_from_directory(app.static_folder, path)
    except:
        return send_from_directory(app.static_folder, "index.html")


# ── Démarrage ──

if __name__ == "__main__":
    _load_cache()

    # Lancer un scan initial en arrière-plan
    threading.Thread(target=run_scan, daemon=True).start()

    # Programmer les scans périodiques
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_scan, "interval", minutes=SCAN_INTERVAL_MIN)
    scheduler.start()

    port = int(os.environ.get("PORT", 5051))
    print(f"[SERVER] Démarrage sur le port {port}")
    print(f"[SERVER] Scan toutes les {SCAN_INTERVAL_MIN} minutes")
    app.run(host="0.0.0.0", port=port, debug=False)
