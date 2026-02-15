"""
SQLite database for raw Binance candles and Polymarket prices.

Handles schema init, inserts, and queries. Thread-safe connection handling.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from config import DB_INIT_SQL, DB_PATH


def _ensure_db_dir() -> None:
    """Create parent directory for DB if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a database connection with proper resource cleanup."""
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables and indexes if they do not exist."""
    with get_connection() as conn:
        conn.executescript(DB_INIT_SQL)


def insert_binance_klines(rows: list[tuple[int, float, float, float, float, float, int]]) -> int:
    """
    Insert Binance kline rows. Ignores duplicates.

    Each row: (open_time_ms, open, high, low, close, volume, close_time_ms)
    Returns count of inserted rows.
    """
    sql = """
    INSERT OR IGNORE INTO binance_klines
    (open_time_ms, open, high, low, close, volume, close_time_ms)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    with get_connection() as conn:
        cur = conn.executemany(sql, rows)
        return cur.rowcount


def insert_polymarket_prices(rows: list[dict[str, Any]]) -> int:
    """
    Insert Polymarket price rows. Ignores duplicates.

    Each row dict: market_id, slug, yes_token_id, no_token_id, yes_price, no_price,
    resolution_time_utc, open_time_ms
    Returns count of inserted rows.
    """
    sql = """
    INSERT OR IGNORE INTO polymarket_prices
    (market_id, slug, yes_token_id, no_token_id, yes_price, no_price, resolution_time_utc, open_time_ms)
    VALUES (:market_id, :slug, :yes_token_id, :no_token_id, :yes_price, :no_price, :resolution_time_utc, :open_time_ms)
    """
    with get_connection() as conn:
        cur = conn.executemany(sql, rows)
        return cur.rowcount


def get_latest_binance_open_time() -> int | None:
    """Return the most recent open_time_ms from binance_klines, or None if empty."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT MAX(open_time_ms) AS latest FROM binance_klines"
        ).fetchone()
        val = row["latest"] if row else None
        return int(val) if val is not None else None


def get_binance_klines(
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    limit: int = 10_000,
) -> list[dict[str, Any]]:
    """
    Fetch Binance klines, optionally filtered by time range.

    Returns list of dicts with keys: open_time_ms, open, high, low, close, volume, close_time_ms.
    """
    conditions: list[str] = []
    params: list[Any] = []
    if start_time_ms is not None:
        conditions.append("open_time_ms >= ?")
        params.append(start_time_ms)
    if end_time_ms is not None:
        conditions.append("open_time_ms <= ?")
        params.append(end_time_ms)
    where = (" AND ".join(conditions)) if conditions else "1=1"
    params.append(limit)
    sql = f"""
    SELECT open_time_ms, open, high, low, close, volume, close_time_ms
    FROM binance_klines
    WHERE {where}
    ORDER BY open_time_ms ASC
    LIMIT ?
    """
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def get_polymarket_prices(
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    limit: int = 10_000,
) -> list[dict[str, Any]]:
    """
    Fetch Polymarket prices, optionally filtered by time range.

    Returns list of dicts with full row fields.
    """
    conditions: list[str] = []
    params: list[Any] = []
    if start_time_ms is not None:
        conditions.append("open_time_ms >= ?")
        params.append(start_time_ms)
    if end_time_ms is not None:
        conditions.append("open_time_ms <= ?")
        params.append(end_time_ms)
    where = (" AND ".join(conditions)) if conditions else "1=1"
    params.append(limit)
    sql = f"""
    SELECT market_id, slug, yes_token_id, no_token_id, yes_price, no_price,
           resolution_time_utc, open_time_ms, created_at
    FROM polymarket_prices
    WHERE open_time_ms IS NOT NULL AND {where}
    ORDER BY open_time_ms ASC
    LIMIT ?
    """
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def get_aligned_data(
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    limit: int = 10_000,
) -> list[dict[str, Any]]:
    """
    Return aligned data: binance klines joined with polymarket prices by open_time_ms.

    Each row: binance fields + yes_price (market prob for Up), no_price.
    Uses LEFT JOIN so we get all binance candles even when Polymarket has no price.
    """
    conditions: list[str] = ["b.open_time_ms IS NOT NULL"]
    params: list[Any] = []
    if start_time_ms is not None:
        conditions.append("b.open_time_ms >= ?")
        params.append(start_time_ms)
    if end_time_ms is not None:
        conditions.append("b.open_time_ms <= ?")
        params.append(end_time_ms)
    where = " AND ".join(conditions)
    params.append(limit)
    sql = f"""
    SELECT b.open_time_ms, b.open, b.high, b.low, b.close, b.volume, b.close_time_ms,
           p.yes_price, p.no_price, p.market_id, p.slug
    FROM binance_klines b
    LEFT JOIN polymarket_prices p ON b.open_time_ms = p.open_time_ms
    WHERE {where}
    ORDER BY b.open_time_ms ASC
    LIMIT ?
    """
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
