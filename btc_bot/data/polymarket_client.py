"""
Polymarket client for fetching BTC 5-minute market prices.

Uses Gamma API for discovery and CLOB for live prices.
Supports HTTP/HTTPS proxy via POLYMARKET_PROXY env var for blocked regions.
"""

import asyncio
import json
import logging
import re
from typing import Any

import aiohttp

from config import (
    POLYMARKET_CLOB_URL,
    POLYMARKET_GAMMA_URL,
    POLYMARKET_MAX_RETRIES,
    POLYMARKET_PROXY,
    POLYMARKET_TIMEOUT,
)

logger = logging.getLogger(__name__)


async def _request_with_retry(
    url: str,
    params: dict[str, str | int] | None = None,
) -> dict[str, Any] | list[Any]:
    """GET with retries and optional proxy."""
    timeout = aiohttp.ClientTimeout(total=POLYMARKET_TIMEOUT, connect=10)
    last_err: Exception | None = None

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for attempt in range(POLYMARKET_MAX_RETRIES):
            try:
                async with session.get(
                    url,
                    params=params or {},
                    proxy=POLYMARKET_PROXY,
                ) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_err = e
                if attempt < POLYMARKET_MAX_RETRIES - 1:
                    await asyncio.sleep(2)
    if last_err:
        raise last_err
    raise RuntimeError("Request failed after retries")


async def fetch_btc_5m_markets() -> list[dict[str, Any]]:
    """
    Discover active BTC 5-minute Up/Down markets from Gamma API.

    Returns list of market dicts with: id, slug, question, clobTokenIds,
    outcomePrices, endDate, startDate, etc.
    """
    url = f"{POLYMARKET_GAMMA_URL}/events"
    params: dict[str, str | int] = {
        "active": "true",
        "closed": "false",
        "limit": 200,
    }
    pattern = re.compile(r"btc[-_]?updown[-_]?5m|btc[-_]?5m", re.I)

    try:
        events = await _request_with_retry(url, params)
    except aiohttp.ClientError as e:
        logger.error("Polymarket Gamma request failed: %s", e)
        raise
    except Exception as e:
        logger.error("Polymarket Gamma error: %s", e)
        raise

    if not isinstance(events, list):
        events = []

    markets: list[dict[str, Any]] = []
    for event in events:
        slug = event.get("slug", "")
        title = (event.get("title") or "").lower()
        if not (pattern.search(slug) or ("bitcoin" in title and "5" in title and "min" in title)):
            continue
        for m in event.get("markets", []):
            if m.get("active") and not m.get("closed"):
                markets.append({
                    "market_id": str(m["id"]),
                    "slug": m.get("slug", slug),
                    "question": m.get("question", ""),
                    "clobTokenIds": m.get("clobTokenIds", "[]"),
                    "outcomePrices": m.get("outcomePrices", "[]"),
                    "outcomes": m.get("outcomes", "[]"),
                    "endDate": m.get("endDate"),
                    "startDate": m.get("startDate"),
                })
    logger.info("Found %d Polymarket BTC 5m markets", len(markets))
    return markets


def _parse_token_ids(clob_ids: str) -> tuple[str | None, str | None]:
    """Parse clobTokenIds JSON to (yes_id, no_id)."""
    try:
        ids = json.loads(clob_ids) if isinstance(clob_ids, str) else clob_ids
        if isinstance(ids, list) and len(ids) >= 2:
            return ids[0], ids[1]
    except (json.JSONDecodeError, TypeError):
        pass
    return None, None


def _parse_prices(outcome_prices: str) -> tuple[float | None, float | None]:
    """Parse outcomePrices JSON to (yes_price, no_price)."""
    try:
        prices = json.loads(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
        if isinstance(prices, list) and len(prices) >= 2:
            return float(prices[0]), float(prices[1])
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return None, None


async def fetch_clob_price(token_id: str, side: str = "buy") -> float | None:
    """Fetch current price for a token from CLOB."""
    url = f"{POLYMARKET_CLOB_URL}/price"
    params = {"token_id": token_id, "side": side}

    try:
        data = await _request_with_retry(url, params)
        return float(data.get("price", 0))
    except (aiohttp.ClientError, KeyError, ValueError, TypeError) as e:
        logger.warning("CLOB price fetch failed for %s: %s", token_id[:20], e)
        return None


async def fetch_market_prices(market: dict[str, Any]) -> dict[str, Any] | None:
    """
    Fetch live prices for a market from CLOB.

    Falls back to outcomePrices from Gamma if CLOB fails.
    Returns dict with: market_id, slug, yes_token_id, no_token_id, yes_price, no_price.
    """
    yes_id, no_id = _parse_token_ids(market.get("clobTokenIds", "[]"))
    yes_price, no_price = _parse_prices(market.get("outcomePrices", "[]"))

    if yes_id:
        live_yes = await fetch_clob_price(yes_id, "buy")
        if live_yes is not None:
            yes_price = live_yes
    if no_id:
        live_no = await fetch_clob_price(no_id, "buy")
        if live_no is not None:
            no_price = live_no

    if yes_price is None and no_price is None:
        return None

    if yes_price is None:
        yes_price = 1.0 - (no_price or 0)
    if no_price is None:
        no_price = 1.0 - (yes_price or 0)

    return {
        "market_id": market["market_id"],
        "slug": market.get("slug", ""),
        "yes_token_id": yes_id,
        "no_token_id": no_id,
        "yes_price": round(yes_price, 4),
        "no_price": round(no_price, 4),
    }
