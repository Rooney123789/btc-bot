"""
Test Polymarket connectivity. Run this to verify API access.

Usage:
  python test_polymarket.py                    # Direct connection
  POLYMARKET_PROXY=http://127.0.0.1:7890 python test_polymarket.py   # Via proxy
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import POLYMARKET_PROXY


async def test_gamma() -> bool:
    """Test Gamma API connectivity."""
    from data.polymarket_client import fetch_btc_5m_markets

    try:
        markets = await fetch_btc_5m_markets()
        print(f"  Gamma API: OK — found {len(markets)} BTC 5m market(s)")
        return True
    except Exception as e:
        print(f"  Gamma API: FAILED — {e}")
        return False


async def test_clob() -> bool:
    """Test CLOB API connectivity (use known token if Gamma works)."""
    import aiohttp
    from config import POLYMARKET_CLOB_URL, POLYMARKET_PROXY, POLYMARKET_TIMEOUT

    # Simple ping: CLOB /book endpoint with any token (will 400 but we check connection)
    url = f"{POLYMARKET_CLOB_URL}/markets"
    timeout = aiohttp.ClientTimeout(total=POLYMARKET_TIMEOUT, connect=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, proxy=POLYMARKET_PROXY) as resp:
                print(f"  CLOB API: OK — HTTP {resp.status}")
                return True
    except Exception as e:
        print(f"  CLOB API: FAILED — {e}")
        return False


async def main() -> None:
    """Run connectivity tests."""
    print("=" * 50)
    print("POLYMARKET CONNECTIVITY TEST")
    print("=" * 50)
    if POLYMARKET_PROXY:
        print(f"Using proxy: {POLYMARKET_PROXY}")
    else:
        print("No proxy set (POLYMARKET_PROXY env not set)")
    print()

    gamma_ok = await test_gamma()
    clob_ok = await test_clob()

    print()
    if gamma_ok and clob_ok:
        print("SUCCESS — Polymarket is reachable. Run: python main.py collect")
    else:
        print("FAILED — Polymarket not reachable from this network.")
        print()
        print("Options:")
        print("  1. Set proxy:  set POLYMARKET_PROXY=http://127.0.0.1:7890")
        print("  2. Use VPN:    Connect VPN, then retry (no proxy needed)")
        print("  3. Use VPS:    Run this bot on a VPS where Polymarket works")
        print()
        print("See POLYMARKET_SETUP.md for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
