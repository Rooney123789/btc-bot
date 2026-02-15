"""
Performance analysis: equity curve, drawdown plot, trade summary.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from config import LOGS_DIR

logger = logging.getLogger(__name__)


def plot_equity_and_drawdown(
    equity_curve: list[float],
    drawdown_curve: list[float],
    output_path: Path | None = None,
) -> None:
    """Generate equity curve and drawdown curve plots."""
    if output_path is None:
        output_path = LOGS_DIR / "backtest_equity_drawdown.png"

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    x = range(len(equity_curve))

    ax1.plot(x, equity_curve, color="steelblue", linewidth=2)
    ax1.set_ylabel("Balance ($)")
    ax1.set_title("Equity Curve")
    ax1.grid(True, alpha=0.3)
    ax1.fill_between(x, equity_curve[0], equity_curve, alpha=0.2, color="steelblue")

    ax2.fill_between(x, 0, [-d * 100 for d in drawdown_curve], color="coral", alpha=0.7)
    ax2.set_ylabel("Drawdown (%)")
    ax2.set_xlabel("Trade #")
    ax2.set_title("Drawdown Curve")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Saved plot to %s", output_path)


def print_trade_summary(trades: list[Any], stats: dict[str, Any]) -> None:
    """Print formatted trade summary to console."""
    print("\n" + "=" * 60)
    print("BACKTEST TRADE SUMMARY")
    print("=" * 60)
    print(f"Total Trades:   {stats.get('total_trades', 0)}")
    print(f"Wins:           {stats.get('wins', 0)}")
    print(f"Losses:         {stats.get('losses', 0)}")
    print(f"Win Rate:       {stats.get('win_rate', 0):.2%}")
    print(f"Total PnL:      ${stats.get('total_pnl', 0):.2f}")
    print(f"Final Balance:  ${stats.get('final_balance', 0):.2f}")
    print(f"Max Drawdown:   {stats.get('max_drawdown', 0):.1%}")
    print(f"Stop Reason:    {stats.get('stop_reason', 'N/A')}")
    print("=" * 60)

    if trades:
        print("\nLast 5 trades:")
        for t in trades[-5:]:
            outcome = "WIN" if t.outcome == 1 else "LOSS"
            print(f"  {t.open_time_ms} | edge={t.edge:.3f} | ${t.position_usd:.2f} | {outcome} | PnL=${t.pnl:.2f}")
