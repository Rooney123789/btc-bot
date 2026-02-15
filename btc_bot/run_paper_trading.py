"""
Paper trading mode: live signal generation, no real execution.

Fetches latest data, generates signal, logs hypothetical trade.
Run periodically (e.g. every 5 min) or once.

Usage: python run_paper_trading.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import LOGS_DIR
from data.data_collector import collect_all
from data.database import get_aligned_data
from execution.trade_executor import (
    PaperTradingState,
    generate_signal,
    get_paper_trading_stats,
    record_paper_trade,
)
from features.feature_engineering import build_features
from models.model_utils import load_model


def setup_logging() -> None:
    """Configure logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(LOGS_DIR / "paper_trading.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run_paper_signal(state: PaperTradingState) -> dict[str, object]:
    """
    Generate one paper trading signal from latest data.

    Returns dict with signal, model_prob, market_prob, etc.
    """
    aligned = get_aligned_data(limit=500)
    if not aligned:
        return {"status": "no_data", "message": "No aligned data. Run data collection first."}

    klines = [
        {
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
            "volume": r["volume"],
            "open_time_ms": r["open_time_ms"],
        }
        for r in aligned
    ]
    X, _, timestamps = build_features(klines)
    if X.shape[0] == 0:
        return {"status": "no_features", "message": "Insufficient data for features."}

    model, scaler, _ = load_model()
    X_scaled = scaler.transform(X[-1:])
    model_prob = float(model.predict_proba(X_scaled)[0, 1])
    last_row = aligned[-1]
    market_prob = last_row.get("yes_price") or 0.5
    open_time_ms = last_row["open_time_ms"]

    signal, position_usd, reason = generate_signal(model_prob, market_prob, state)
    record_paper_trade(
        open_time_ms=open_time_ms,
        model_prob=model_prob,
        market_prob=market_prob,
        signal=signal,
        position_usd=position_usd,
        reason=reason,
        state=state,
    )

    return {
        "status": "ok",
        "signal": signal,
        "model_prob": model_prob,
        "market_prob": market_prob,
        "position_usd": position_usd,
        "reason": reason,
        "open_time_ms": open_time_ms,
    }


def main() -> None:
    """Run paper trading signal generation."""
    setup_logging()
    logger = logging.getLogger("paper_trading")

    print("\n" + "=" * 50)
    print("PAPER TRADING MODE (No real execution)")
    print("=" * 50)

    state = PaperTradingState()
    result = run_paper_signal(state)

    if result.get("status") == "ok":
        print(f"Signal:      {result['signal']}")
        print(f"Model Prob:  {result['model_prob']:.3f}")
        print(f"Market Prob: {result['market_prob']:.3f}")
        print(f"Position:    ${result['position_usd']:.2f}")
        print(f"Reason:      {result['reason']}")
        stats = get_paper_trading_stats(state)
        print(f"\nBalance: ${stats['balance']:.2f} | Loss streak: {stats['consecutive_losses']}")
    else:
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Message: {result.get('message', 'N/A')}")

    print("=" * 50)
    print("\nPHASE 5 COMPLETE")


if __name__ == "__main__":
    main()
