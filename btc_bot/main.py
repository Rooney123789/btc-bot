"""
BTC 5-Min ML Trading Bot - Entry point.

Phase 1: Data collection (Binance + Polymarket + SQLite + logging).
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import LOGS_DIR
from data.data_collector import collect_all


def setup_logging() -> None:
    """Configure structured logging to file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "btc_bot.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    # Reduce noise from aiohttp
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


async def run_phase1() -> None:
    """Execute Phase 1: data collection and persistence."""
    logger = logging.getLogger("btc_bot")
    logger.info("Starting Phase 1 data collection")
    result = await collect_all()
    logger.info(
        "Phase 1 complete: binance_inserted=%d polymarket_inserted=%d",
        result["binance_inserted"],
        result["polymarket_inserted"],
    )
    print("PHASE 1 COMPLETE")


def main() -> None:
    """Main entry point."""
    setup_logging()
    asyncio.run(run_phase1())


if __name__ == "__main__":
    main()
