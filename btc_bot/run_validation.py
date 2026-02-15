"""Validation script: edge threshold stress test."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.simulator import run_backtest

print("Edge Threshold Stress Test")
print("=" * 50)
for thresh in [0.05, 0.06, 0.07, 0.08]:
    r = run_backtest(limit=15000, edge_threshold=thresh)
    s = r["stats"]
    print(f"Edge {thresh}: trades={s['total_trades']} win_rate={s['win_rate']:.1%} final=${s['final_balance']:.0f} max_dd={s['max_drawdown']:.1%}")
print("=" * 50)
