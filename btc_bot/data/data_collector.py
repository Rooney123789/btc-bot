"""
Data collector: orchestrates Binance, Polymarket, DB, and alignment.

Fetches raw data, aligns by 5-min timestamp, saves to SQLite.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

from config import BINANCE_KLINES_LIMIT

from .binance_client import fetch_klines, fetch_klines_range
from .database import (
    get_latest_binance_open_time,
    init_db,
    insert_binance_klines,
    insert_polymarket_prices,
)
from .polymarket_client import fetch_btc_5m_markets, fetch_market_prices

logger = logging.getLogger(__name__)

# 5 minutes in ms
FIVE_MIN_MS = 5 * 60 * 1000


def _slug_to_open_time_ms(slug: str) -> int | None:
    """
    Extract Unix timestamp from slug (e.g. btc-updown-5m-1771113000) and
    convert to 5-min-aligned open_time_ms for Binance.
    """
    match = re.search(r"(\d{9,11})$", slug)
    if match:
        ts = int(match.group(1))
        # Align to 5-min boundary (Binance candle open)
        bucket = (ts // 300) * 300
        return bucket * 1000
    return None


def _end_date_to_open_time_ms(end_date: str | None) -> int | None:
    """Parse ISO endDate and return 5-min-aligned open_time_ms."""
    if not end_date:
        return None
    try:
        dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        ts = int(dt.timestamp())
        bucket = (ts // 300) * 300
        return bucket * 1000
    except (ValueError, TypeError):
        return None


async def collect_binance_klines(
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    use_latest: bool = True,
) -> int:
    """
    Fetch Binance klines and save to DB.

    If use_latest and start_time_ms is None, continues from last saved candle.
    Returns count of newly inserted rows.
    """
    if use_latest and start_time_ms is None:
        latest = get_latest_binance_open_time()
        if latest is not None:
            start_time_ms = latest + FIVE_MIN_MS

    if end_time_ms is None:
        end_time_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    if start_time_ms is not None and start_time_ms >= end_time_ms:
        logger.info("Binance: no new candles to fetch")
        return 0

    if start_time_ms is None:
        # First run: fetch last N candles
        klines = await fetch_klines(end_time_ms=end_time_ms, limit=BINANCE_KLINES_LIMIT)
    else:
        klines = await fetch_klines_range(start_time_ms, end_time_ms)

    if not klines:
        return 0

    rows = [
        (
            k["open_time_ms"],
            k["open"],
            k["high"],
            k["low"],
            k["close"],
            k["volume"],
            k["close_time_ms"],
        )
        for k in klines
    ]
    count = insert_binance_klines(rows)
    logger.info("Inserted %d Binance klines", count)
    return count


async def collect_polymarket_prices() -> int:
    """
    Fetch BTC 5m market prices and save to DB.

    Aligns each market to open_time_ms using slug timestamp or endDate.
    Returns count of newly inserted rows.
    """
    markets = await fetch_btc_5m_markets()
    if not markets:
        logger.info("No Polymarket BTC 5m markets found")
        return 0

    rows: list[dict[str, Any]] = []
    for market in markets:
        prices = await fetch_market_prices(market)
        if not prices:
            continue

        open_time_ms = _slug_to_open_time_ms(market.get("slug", ""))
        if open_time_ms is None:
            open_time_ms = _end_date_to_open_time_ms(market.get("endDate"))
        if open_time_ms is None:
            continue

        rows.append({
            "market_id": prices["market_id"],
            "slug": prices["slug"],
            "yes_token_id": prices.get("yes_token_id"),
            "no_token_id": prices.get("no_token_id"),
            "yes_price": prices["yes_price"],
            "no_price": prices["no_price"],
            "resolution_time_utc": market.get("endDate"),
            "open_time_ms": open_time_ms,
        })

    if not rows:
        return 0

    count = insert_polymarket_prices(rows)
    logger.info("Inserted %d Polymarket price rows", count)
    return count


async def collect_all() -> dict[str, int]:
    """
    Run full data collection: Binance + Polymarket, save all raw data.

    Returns dict with binance_inserted and polymarket_inserted counts.
    Polymarket failure is non-fatal; Phase 1 completes with Binance data.
    """
    init_db()
    binance_count = await collect_binance_klines()
    try:
        poly_count = await collect_polymarket_prices()
    except Exception as e:
        logger.warning("Polymarket collection failed (continuing): %s", e)
        poly_count = 0
    return {"binance_inserted": binance_count, "polymarket_inserted": poly_count}
