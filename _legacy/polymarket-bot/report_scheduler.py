#!/usr/bin/env python3
"""
Scheduler de rapports — lance hourly_report.py toutes les N minutes.
Remplace cron quand il n'est pas disponible.

Usage:
    python report_scheduler.py                # Toutes les 30 min (défaut)
    python report_scheduler.py --interval 15  # Toutes les 15 min
    nohup python report_scheduler.py &        # En arrière-plan
"""

import argparse
import subprocess
import sys
import time
import signal
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_SCRIPT = os.path.join(SCRIPT_DIR, "hourly_report.py")
PID_FILE = os.path.join(SCRIPT_DIR, "logs", "report_scheduler.pid")

running = True


def handle_signal(signum, frame):
    global running
    running = False
    print(f"\n[{datetime.now():%H:%M:%S}] Arrêt du scheduler...")


def run_report():
    """Exécute le rapport."""
    try:
        result = subprocess.run(
            [sys.executable, REPORT_SCRIPT],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            # Afficher les dernières lignes (résumé)
            lines = result.stdout.strip().split("\n")
            for line in lines[-3:]:
                print(f"  {line}")
        else:
            print(f"  ERREUR: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print("  TIMEOUT (>120s)")
    except Exception as e:
        print(f"  ERREUR: {e}")


def save_pid():
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))


def main():
    parser = argparse.ArgumentParser(description="Scheduler de rapports Polymarket")
    parser.add_argument("--interval", type=int, default=30,
                        help="Intervalle en minutes (défaut: 30)")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    save_pid()

    interval_sec = args.interval * 60
    print(f"[{datetime.now():%H:%M:%S}] Scheduler démarré — rapport toutes les {args.interval} min")
    print(f"  PID: {os.getpid()}")
    print(f"  Script: {REPORT_SCRIPT}")
    print()

    # Premier rapport immédiat
    print(f"[{datetime.now():%H:%M:%S}] Rapport...")
    run_report()

    while running:
        # Dormir par tranches de 1s pour rester interruptible
        for _ in range(interval_sec):
            if not running:
                break
            time.sleep(1)

        if running:
            print(f"\n[{datetime.now():%H:%M:%S}] Rapport...")
            run_report()

    # Nettoyage
    try:
        os.remove(PID_FILE)
    except OSError:
        pass
    print("Scheduler arrêté.")


if __name__ == "__main__":
    main()
