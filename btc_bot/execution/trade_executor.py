"""
Trade executor - paper trading only.

Generates live signals, logs hypothetical trades. NO REAL EXECUTION.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import (
    CONSECUTIVE_LOSS_STOP,
    DAILY_DRAWDOWN_CAP_PCT,
    EDGE_THRESHOLD,
    INITIAL_BALANCE,
    LOGS_DIR,
    MAX_RISK_PCT,
    MAX_TRADE_USD,
)


logger = logging.getLogger(__name__)

PAPER_LOG_FILE = LOGS_DIR / "paper_trades.log"


@dataclass
class PaperTrade:
    """Hypothetical paper trade."""

    timestamp_utc: str
    open_time_ms: int
    signal: str  # "BUY_YES" or "SKIP"
    model_prob: float
    market_prob: float
    edge: float
    position_usd: float
    reason: str  # Why trade or why skip


class PaperTradingState:
    """Tracks paper trading state: balance, loss streak, daily start."""

    def __init__(self, initial_balance: float = INITIAL_BALANCE):
        self.balance = initial_balance
        self.consecutive_losses = 0
        self.daily_start: dict[str, float] = {}
        self.trades_log: list[dict[str, Any]] = []


def _format_trade_log(trade: PaperTrade) -> str:
    """Format trade for log file."""
    return (
        f"{trade.timestamp_utc} | {trade.open_time_ms} | {trade.signal} | "
        f"model={trade.model_prob:.3f} market={trade.market_prob:.3f} edge={trade.edge:.3f} | "
        f"pos=${trade.position_usd:.2f} | {trade.reason}"
    )


def log_paper_trade(trade: PaperTrade) -> None:
    """Append paper trade to log file."""
    PAPER_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PAPER_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(_format_trade_log(trade) + "\n")
    logger.info("Paper trade: %s", _format_trade_log(trade))


def generate_signal(
    model_prob: float,
    market_prob: float,
    state: PaperTradingState,
) -> tuple[str, float, str]:
    """
    Generate trading signal. Paper only - no execution.

    Returns (signal, position_usd, reason).
    signal: "BUY_YES" or "SKIP"
    """
    edge = model_prob - market_prob
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    if state.consecutive_losses >= CONSECUTIVE_LOSS_STOP:
        return "SKIP", 0.0, "stopped: 2 consecutive losses"

    if date_str in state.daily_start:
        day_start = state.daily_start[date_str]
        daily_dd = (day_start - state.balance) / day_start if day_start > 0 else 0
        if daily_dd >= DAILY_DRAWDOWN_CAP_PCT:
            return "SKIP", 0.0, "stopped: daily drawdown >= 10%"

    if edge < EDGE_THRESHOLD:
        return "SKIP", 0.0, f"no edge (need >= {EDGE_THRESHOLD})"

    position = min(MAX_RISK_PCT * state.balance, MAX_TRADE_USD)
    if position < 0.01:
        return "SKIP", 0.0, "insufficient balance"

    return "BUY_YES", position, "edge ok"


def record_paper_trade(
    open_time_ms: int,
    model_prob: float,
    market_prob: float,
    signal: str,
    position_usd: float,
    reason: str,
    state: PaperTradingState,
) -> PaperTrade:
    """Record and log a paper trade."""
    now = datetime.now(timezone.utc)
    edge = model_prob - market_prob
    trade = PaperTrade(
        timestamp_utc=now.isoformat(),
        open_time_ms=open_time_ms,
        signal=signal,
        model_prob=model_prob,
        market_prob=market_prob,
        edge=edge,
        position_usd=position_usd,
        reason=reason,
    )
    log_paper_trade(trade)
    state.trades_log.append({
        "timestamp": trade.timestamp_utc,
        "open_time_ms": open_time_ms,
        "signal": signal,
        "model_prob": model_prob,
        "market_prob": market_prob,
        "edge": edge,
        "position_usd": position_usd,
        "reason": reason,
    })
    return trade


def get_paper_trading_stats(state: PaperTradingState) -> dict[str, Any]:
    """Return current paper trading stats."""
    return {
        "balance": state.balance,
        "consecutive_losses": state.consecutive_losses,
        "total_signals": len(state.trades_log),
        "buy_signals": sum(1 for t in state.trades_log if t["signal"] == "BUY_YES"),
    }
