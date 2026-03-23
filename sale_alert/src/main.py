"""Entry point for the sale alert tool.

Usage:
    python -m sale_alert.src.main                # default: dry mode
    python -m sale_alert.src.main --mode dry     # explicit dry mode (logs only)
    python -m sale_alert.src.main --mode live    # sends real alerts
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from sale_alert.src.config import load_config
from sale_alert.src.monitor import TicketmasterMonitor, DetectedEvent
from sale_alert.src.alerts import AlertEngine

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
        "--config-dir",
        type=Path,
        default=Path("config"),
        help="Directory containing events.yaml (default: config/)",
    )
    return parser.parse_args(argv)


async def run(args: argparse.Namespace) -> None:
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

    alert_engine = AlertEngine(config)

    async def on_sale_detected(event: DetectedEvent) -> None:
        logger.info(
            "DETECTED: %s — %s — %s",
            event.artist,
            event.event_name,
            event.url,
        )
        if args.mode == "live":
            await alert_engine.send(event)
        else:
            logger.info("[DRY MODE] Would send alert for: %s", event.event_name)

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
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
