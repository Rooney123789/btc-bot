"""
Run backtest - requires trained model and collected data.

Usage: python run_backtest.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backtest.simulator import run_backtest
from backtest.performance import plot_equity_and_drawdown, print_trade_summary
from config import LOGS_DIR


def setup_logging() -> None:
    """Configure logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(LOGS_DIR / "backtest.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    """Run backtest and output results."""
    setup_logging()
    logger = logging.getLogger("backtest")

    try:
        result = run_backtest(limit=3000)
        trades = result["trades"]
        stats = result["stats"]

        for i, t in enumerate(trades):
            logger.info(
                "Trade %d: ts=%s edge=%.3f pos=$%.2f outcome=%d pnl=$%.2f bal=$%.2f",
                i + 1,
                t.open_time_ms,
                t.edge,
                t.position_usd,
                t.outcome,
                t.pnl,
                t.balance_after,
            )

        print_trade_summary(trades, stats)
        plot_equity_and_drawdown(result["equity_curve"], result["drawdown_curve"])
        print("\nPHASE 4 COMPLETE")

    except FileNotFoundError as e:
        logger.error("Model not found. Run train_model.py first.")
        print("ERROR: Run train_model.py first to train the model.")
        sys.exit(1)


if __name__ == "__main__":
    main()
