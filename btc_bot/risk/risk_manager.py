"""
Risk management: position sizing, loss limits, drawdown caps.

Centralizes all risk rules. Used by backtest and paper trading.
"""

from typing import Tuple

from config import (
    CONSECUTIVE_LOSS_STOP,
    DAILY_DRAWDOWN_CAP_PCT,
    EDGE_THRESHOLD,
    MAX_RISK_PCT,
    MAX_TRADE_USD,
)


def position_size(balance: float) -> float:
    """Max position size = min(10% of balance, $10)."""
    return min(MAX_RISK_PCT * balance, MAX_TRADE_USD)


def has_edge(model_prob: float, market_prob: float) -> bool:
    """Edge threshold: model_prob - market_prob >= 0.06."""
    return (model_prob - market_prob) >= EDGE_THRESHOLD


def should_stop_consecutive_losses(consecutive_losses: int) -> bool:
    """Stop after 2 consecutive losses."""
    return consecutive_losses >= CONSECUTIVE_LOSS_STOP


def should_stop_daily_drawdown(
    day_start_balance: float,
    current_balance: float,
) -> bool:
    """Stop if daily drawdown >= 10%."""
    if day_start_balance <= 0:
        return False
    dd = (day_start_balance - current_balance) / day_start_balance
    return dd >= DAILY_DRAWDOWN_CAP_PCT


def can_trade(
    balance: float,
    consecutive_losses: int,
    day_start_balance: float,
) -> Tuple[bool, str]:
    """
    Check if trading is allowed.

    Returns (allowed, reason).
    """
    if balance < 0.01:
        return False, "insufficient balance"
    if should_stop_consecutive_losses(consecutive_losses):
        return False, "stopped: 2 consecutive losses"
    if day_start_balance > 0 and should_stop_daily_drawdown(day_start_balance, balance):
        return False, "stopped: daily drawdown >= 10%"
    if position_size(balance) < 0.01:
        return False, "position size too small"
    return True, "ok"
