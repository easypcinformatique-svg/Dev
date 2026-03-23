"""Entry point for the sale alert tool.

Usage:
    python -m sale_alert.src.main                       # dry mode, no dashboard
    python -m sale_alert.src.main --mode live            # live alerts
    python -m sale_alert.src.main --mode live --dashboard  # live + web dashboard
    python -m sale_alert.src.main --mode live --dashboard --port 5051
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import threading
from dataclasses import asdict
from pathlib import Path

from sale_alert.src.config import load_config
from sale_alert.src.monitor import TicketmasterMonitor, DetectedEvent
from sale_alert.src.alerts import AlertEngine
from sale_alert.src.dashboard import AlertState, create_dashboard_app, _start_keep_alive

logger = logging.getLogger("sale_alert")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ticket sale alert tool")
    parser.add_argument(
        "--mode",
        choices=["dry", "live"],
        default="dry",
        help="dry = log only, live = send real alerts (default: dry)",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Lancer le dashboard web",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5051,
        help="Port du dashboard (default: 5051)",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("config"),
        help="Directory containing events.yaml (default: config/)",
    )
    return parser.parse_args(argv)


async def run(args: argparse.Namespace, state: AlertState) -> None:
    config_dir = args.config_dir
    env_path = config_dir.parent / ".env"
    events_path = config_dir / "events.yaml"

    config = load_config(env_path=env_path, events_path=events_path)

    if not config.events:
        logger.error("No events configured in %s", events_path)
        sys.exit(1)

    if not config.tm_api_key:
        logger.error("TM_API_KEY is not set in .env")
        sys.exit(1)

    # Populate dashboard state
    state.artists_watched = [ev.artist for ev in config.events]

    alert_engine = AlertEngine(config)

    async def on_sale_detected(event: DetectedEvent) -> None:
        logger.info(
            "DETECTED: %s — %s — %s",
            event.artist,
            event.event_name,
            event.url,
        )

        # Record in dashboard state
        state.record_detection({
            "artist": event.artist,
            "event_id": event.event_id,
            "event_name": event.event_name,
            "url": event.url,
            "start_date": event.start_date,
            "min_price": event.min_price,
            "max_price": event.max_price,
            "detected_at": event.detected_at.isoformat(),
        })

        if args.mode == "live":
            await alert_engine.send(event)
        else:
            logger.info("[DRY MODE] Would send alert for: %s", event.event_name)

    # Wrap poll to track in dashboard
    original_poll = TicketmasterMonitor._poll_once

    async def tracked_poll(self, session, event_cfg):
        state.record_poll()
        try:
            await original_poll(self, session, event_cfg)
        except Exception as e:
            state.record_error(f"{event_cfg.artist}: {e}")
            raise

    TicketmasterMonitor._poll_once = tracked_poll

    monitor = TicketmasterMonitor(config, on_sale_callback=on_sale_detected)

    logger.info("Sale alert tool started in %s mode", args.mode.upper())
    logger.info("Monitoring %d artist(s)", len(config.events))

    try:
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Shutting down…")
        await monitor.stop()


def main() -> None:
    _setup_logging()
    args = parse_args()

    state = AlertState()

    # Render.com définit PORT automatiquement — priorité à $PORT
    port = int(os.environ.get("PORT", 0)) or args.port or 5051

    # Lancer le dashboard dans un thread séparé
    if args.dashboard:
        app = create_dashboard_app(state)

        dash_thread = threading.Thread(
            target=lambda: app.run(
                host="0.0.0.0",
                port=port,
                debug=False,
                use_reloader=False,
            ),
            daemon=True,
        )
        dash_thread.start()
        logger.info(f"Dashboard démarré sur http://localhost:{port}")

        # Keep-alive pour les hébergeurs gratuits (Render, etc.)
        render_url = os.environ.get("RENDER_EXTERNAL_URL")
        if render_url:
            _start_keep_alive(render_url)
            logger.info(f"  Keep-alive actif pour {render_url}")

    asyncio.run(run(args, state))


if __name__ == "__main__":
    main()
