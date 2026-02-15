"""
BTC 5-Min ML Trading Bot - Main entry point.

Modes: collect | train | backtest | paper | status
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import LOGS_DIR


def setup_logging() -> None:
    """Configure structured logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOGS_DIR / "btc_bot.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


async def cmd_collect() -> None:
    """Phase 1: Data collection."""
    from data.data_collector import collect_all

    result = await collect_all()
    print(f"Binance: {result['binance_inserted']} | Polymarket: {result['polymarket_inserted']}")
    print("PHASE 1 COMPLETE")


def cmd_train() -> None:
    """Phase 3: Train model."""
    from models.train import train

    train(limit=5000, train_frac=0.8)
    print("PHASE 3 COMPLETE")


def cmd_backtest() -> None:
    """Phase 4: Run backtest."""
    from backtest.performance import plot_equity_and_drawdown, print_trade_summary
    from backtest.simulator import run_backtest

    result = run_backtest(limit=3000)
    print_trade_summary(result["trades"], result["stats"])
    plot_equity_and_drawdown(result["equity_curve"], result["drawdown_curve"])
    print("PHASE 4 COMPLETE")


def cmd_paper() -> None:
    """Phase 5: Paper trading signal."""
    from execution.trade_executor import PaperTradingState, get_paper_trading_stats
    from run_paper_trading import run_paper_signal

    state = PaperTradingState()
    result = run_paper_signal(state)
    if result.get("status") == "ok":
        print(f"Signal: {result['signal']} | Model: {result['model_prob']:.3f} | Market: {result['market_prob']:.3f}")
        stats = get_paper_trading_stats(state)
        print(f"Balance: ${stats['balance']:.2f} | Loss streak: {stats['consecutive_losses']}")
    else:
        print(f"Status: {result.get('message', result.get('status'))}")
    print("PHASE 5 COMPLETE")


def cmd_status() -> None:
    """Performance tracking: balance, PnL, win rate, etc."""
    from data.database import get_binance_klines

    try:
        from backtest.simulator import run_backtest

        result = run_backtest(limit=5000)
        stats = result["stats"]
        trades = result["trades"]
        print("\n" + "=" * 50)
        print("PERFORMANCE TRACKING")
        print("=" * 50)
        print(f"Current Balance:  ${stats.get('final_balance', 100):.2f}")
        print(f"Win Rate:         {stats.get('win_rate', 0):.1%}")
        print(f"Total Trades:     {stats.get('total_trades', 0)}")
        print(f"Max Drawdown:     {stats.get('max_drawdown', 0):.1%}")
        if trades:
            loss_streak = 0
            for t in reversed(trades):
                if t.outcome == 0:
                    loss_streak += 1
                else:
                    break
            print(f"Loss Streak:      {loss_streak}")
        print("=" * 50)
        klines = get_binance_klines(limit=1)
        if klines:
            print(f"Latest candle: {klines[-1]['open_time_ms']}")
    except FileNotFoundError:
        print("Model not found. Run: python main.py train")
    except Exception as e:
        print(f"Error: {e}")


def main() -> None:
    """Main entry point."""
    setup_logging()
    parser = argparse.ArgumentParser(description="BTC 5-Min ML Trading Bot")
    parser.add_argument(
        "mode",
        nargs="?",
        default="collect",
        choices=["collect", "train", "backtest", "paper", "status"],
        help="Mode: collect|train|backtest|paper|status",
    )
    args = parser.parse_args()

    if args.mode == "collect":
        asyncio.run(cmd_collect())
    elif args.mode == "train":
        cmd_train()
    elif args.mode == "backtest":
        cmd_backtest()
    elif args.mode == "paper":
        cmd_paper()
    elif args.mode == "status":
        cmd_status()


if __name__ == "__main__":
    main()
