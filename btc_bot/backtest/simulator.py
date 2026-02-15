"""
Backtesting simulator.

$10 per trade max, edge threshold 0.06, stop after 2 consecutive losses,
stop if daily drawdown >= 10%. Log each trade. One position at a time.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

from config import (
    CONSECUTIVE_LOSS_STOP,
    DAILY_DRAWDOWN_CAP_PCT,
    EDGE_THRESHOLD,
    INITIAL_BALANCE,
    MAX_RISK_PCT,
    MAX_TRADE_USD,
)
from data.database import get_aligned_data
from features.feature_engineering import build_features
from models.model_utils import load_model

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Single simulated trade."""

    open_time_ms: int
    model_prob: float
    market_prob: float
    edge: float
    position_usd: float
    outcome: int  # 1 = win (Up), 0 = loss (Down)
    pnl: float
    balance_after: float
    consecutive_losses_before: int


def _ms_to_date(ms: int) -> str:
    """Convert open_time_ms to date string for daily grouping."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def run_backtest(
    limit: int = 5_000,
    initial_balance: float = INITIAL_BALANCE,
    max_trade_usd: float = MAX_TRADE_USD,
    max_risk_pct: float = MAX_RISK_PCT,
    edge_threshold: float = EDGE_THRESHOLD,
    consecutive_loss_stop: int = CONSECUTIVE_LOSS_STOP,
    daily_drawdown_cap: float = DAILY_DRAWDOWN_CAP_PCT,
) -> dict[str, Any]:
    """
    Run backtest and return trades, equity curve, drawdown, stats.

    Returns dict with: trades, equity_curve, drawdown_curve, stats.
    """
    model, scaler, meta = load_model()
    aligned = get_aligned_data(limit=limit)
    klines = [{"open": r["open"], "high": r["high"], "low": r["low"], "close": r["close"], "volume": r["volume"], "open_time_ms": r["open_time_ms"]} for r in aligned]
    market_probs = [r.get("yes_price") for r in aligned]

    X, y, timestamps = build_features(klines)
    if X.shape[0] == 0:
        return {"trades": [], "equity_curve": [], "drawdown_curve": [], "stats": {}}

    X_scaled = scaler.transform(X)
    model_probs = model.predict_proba(X_scaled)[:, 1]

    # Align market_probs with X (build_features drops rows)
    # build_features returns rows from min_len to n-1. aligned has same order.
    # We need market_prob for each row in X. aligned indices: 0..n-1.
    # X rows correspond to klines indices start_idx..end_idx-1.
    # For aligned, same indices. So market_probs for row i in X = aligned[start_idx + i]["yes_price"]
    # Actually build_features uses klines - and aligned has one row per kline. So for each row in X,
    # we need the market prob from the same timestamp. The timestamps in build_features come from klines.
    # Let me map: X row j corresponds to timestamp timestamps[j], which is klines[start_idx + j].
    # aligned has same order as klines. So aligned[start_idx + j] has yes_price. But we don't have start_idx.
    # Easier: pass aligned to build_features and have it return market_probs. Or we can iterate.
    # build_features returns indices from the klines. The aligned data - each row has open_time_ms.
    # We can build a lookup: open_time_ms -> yes_price. Then for each timestamp in timestamps, get market_prob.
    market_lookup = {r["open_time_ms"]: (r.get("yes_price") or 0.5) for r in aligned}

    balance = initial_balance
    peak_balance = balance
    daily_start: dict[str, float] = {}
    trades: list[Trade] = []
    consecutive_losses = 0
    stopped = False
    stop_reason = ""

    for i in range(len(X)):
        if stopped:
            break
        market_prob = market_lookup.get(timestamps[i], 0.5)
        model_prob = float(model_probs[i])
        edge = model_prob - market_prob

        if edge < edge_threshold:
            continue

        position = min(max_risk_pct * balance, max_trade_usd)
        if position < 0.01:
            continue

        outcome = int(y[i])
        pnl = position if outcome == 1 else -position
        balance += pnl
        peak_balance = max(peak_balance, balance)

        trade = Trade(
            open_time_ms=int(timestamps[i]),
            model_prob=model_prob,
            market_prob=market_prob,
            edge=edge,
            position_usd=position,
            outcome=outcome,
            pnl=pnl,
            balance_after=balance,
            consecutive_losses_before=consecutive_losses,
        )
        trades.append(trade)
        logger.debug("Trade: %s", trade)

        if outcome == 0:
            consecutive_losses += 1
            if consecutive_losses >= consecutive_loss_stop:
                stopped = True
                stop_reason = "2 consecutive losses"
        else:
            consecutive_losses = 0

        date_str = _ms_to_date(int(timestamps[i]))
        if date_str not in daily_start:
            daily_start[date_str] = balance - pnl
        day_start = daily_start[date_str]
        daily_dd = (day_start - balance) / day_start if day_start > 0 else 0
        if daily_dd >= daily_drawdown_cap:
            stopped = True
            stop_reason = "daily drawdown >= 10%"

    equity_curve = [initial_balance]
    for t in trades:
        equity_curve.append(t.balance_after)
    if not trades:
        equity_curve = [initial_balance]

    peak = initial_balance
    drawdown_curve = [0.0]
    for b in equity_curve[1:]:
        peak = max(peak, b)
        dd = (peak - b) / peak if peak > 0 else 0
        drawdown_curve.append(dd)

    stats = _compute_stats(trades, initial_balance, equity_curve, drawdown_curve)
    stats["stop_reason"] = stop_reason
    return {"trades": trades, "equity_curve": equity_curve, "drawdown_curve": drawdown_curve, "stats": stats}


def _compute_stats(
    trades: list[Trade],
    initial_balance: float,
    equity_curve: list[float],
    drawdown_curve: list[float],
) -> dict[str, Any]:
    """Compute summary statistics."""
    if not trades:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "final_balance": initial_balance,
            "max_drawdown": 0.0,
        }
    wins = sum(1 for t in trades if t.outcome == 1)
    total_pnl = sum(t.pnl for t in trades)
    final_balance = equity_curve[-1]
    max_dd = max(drawdown_curve) if drawdown_curve else 0
    return {
        "total_trades": len(trades),
        "wins": wins,
        "losses": len(trades) - wins,
        "win_rate": wins / len(trades),
        "total_pnl": total_pnl,
        "final_balance": final_balance,
        "max_drawdown": max_dd,
    }
