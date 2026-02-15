"""
Binance API client for historical 5-minute BTC candles.

Uses public REST API. No API key required for klines.
"""

import logging
from typing import Any

import aiohttp

from config import (
    BINANCE_BASE_URL,
    BINANCE_INTERVAL,
    BINANCE_KLINES_LIMIT,
    BINANCE_SYMBOL,
)

logger = logging.getLogger(__name__)

KLINES_ENDPOINT = f"{BINANCE_BASE_URL}/api/v3/klines"


async def fetch_klines(
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    limit: int = BINANCE_KLINES_LIMIT,
) -> list[dict[str, Any]]:
    """
    Fetch 5-minute klines from Binance.

    Binance kline array indices:
    0: open_time, 1: open, 2: high, 3: low, 4: close, 5: volume,
    6: close_time, 7: quote_volume, 8: trades, 9: taker_buy_volume, 10: taker_buy_quote_volume

    Returns list of dicts: open_time_ms, open, high, low, close, volume, close_time_ms.
    """
    params: dict[str, str | int] = {
        "symbol": BINANCE_SYMBOL,
        "interval": BINANCE_INTERVAL,
        "limit": limit,
    }
    if start_time_ms is not None:
        params["startTime"] = start_time_ms
    if end_time_ms is not None:
        params["endTime"] = end_time_ms

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(KLINES_ENDPOINT, params=params) as resp:
                resp.raise_for_status()
                raw = await resp.json()
        except aiohttp.ClientError as e:
            logger.error("Binance request failed: %s", e)
            raise
        except Exception as e:
            logger.error("Binance parse error: %s", e)
            raise

    result: list[dict[str, Any]] = []
    for k in raw:
        if len(k) < 7:
            continue
        result.append({
            "open_time_ms": int(k[0]),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "close_time_ms": int(k[6]),
        })
    logger.info("Fetched %d Binance klines", len(result))
    return result


async def fetch_klines_range(
    start_time_ms: int,
    end_time_ms: int,
) -> list[dict[str, Any]]:
    """
    Fetch all klines in a time range by paging.

    Binance returns up to 1000 per request. We page until we have all.
    """
    all_klines: list[dict[str, Any]] = []
    current_start = start_time_ms

    while current_start < end_time_ms:
        batch = await fetch_klines(
            start_time_ms=current_start,
            end_time_ms=end_time_ms,
            limit=BINANCE_KLINES_LIMIT,
        )
        if not batch:
            break
        all_klines.extend(batch)
        last_time = batch[-1]["open_time_ms"]
        if last_time >= end_time_ms:
            break
        current_start = last_time + 1

    return all_klines
