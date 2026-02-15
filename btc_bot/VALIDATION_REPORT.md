# Validation Report — 360° Assessment

**Date:** 2026-02-15  
**Status:** PRE-LIVE VALIDATION — DO NOT GO LIVE

---

## 1️⃣ Data Collection

| Check | Status | Notes |
|-------|--------|-------|
| Binance candles | ✅ | 20,160 rows (after backfill) |
| Polymarket prices | ❌ | 0 rows — connection timeout from current network |
| Timestamp alignment | ✅ | No mismatch; features built from klines |
| Missing values | ✅ | None in feature matrix |
| NaNs in features | ✅ | 0 |
| Dataset size | ✅ | >10,000 rows (4,964 usable after feature warmup) |

**Action:** Run `python main.py backfill --days 70` to get historical data. Polymarket needs a network that can reach `gamma-api.polymarket.com`.

---

## 2️⃣ Training Metrics (Validation Set)

| Metric | Value | Advisor Threshold |
|--------|-------|-------------------|
| **Accuracy** | 52.57% | ❌ < 54% (no real edge) |
| **Precision** | 54.49% | ⚠️ Near 50% = random; slightly above |
| **Recall** | 56.07% | — |
| **Expected Value** | 0.0514 | Small positive |
| **Confusion Matrix** | 231/243 (0), 228/291 (1) | Roughly balanced |

**Assessment:** Accuracy below 54% suggests no clear edge. Precision around 54% is only marginally better than random.

---

## 3️⃣ Backtest Results

| Metric | Value | Advisor Target |
|--------|-------|----------------|
| **Final Balance** | $90.00 | — |
| **Max Drawdown** | 18.2% | Target <20% ✅ |
| **Win Rate** | 33.33% | — |
| **Profit Factor** | 0.50 | <1 = losing |
| **Total Trades** | 3 | ❌ Need 200+ |
| **Equity Curve** | C) Downtrend | Down after 3 trades |

**Assessment:** Too few trades (3) for meaningful evaluation. Win rate and profit factor indicate a losing system. Max drawdown is within the 20% cap.

---

## 4️⃣ 360° Risk Checks

| Question | Answer |
|----------|--------|
| Time-series split? (no shuffle) | ✅ Yes — `train_frac` split; no random shuffle |
| Train on past, test on future? | ✅ Yes — first 80% train, last 20% validation |
| Polymarket prob aligned with candle timestamps? | ⚠️ N/A — 0 Polymarket rows; using 0.5 as market prob |
| Simulating slippage? | ❌ No — not simulated |
| Edge threshold enforced? | ✅ Yes — trades only when model_prob - market_prob ≥ 0.06 |
| Risk manager stops after 2 losses? | ✅ Yes — verified in backtest |

---

## 5️⃣ Edge Threshold Stress Test

| Edge | Trades | Win Rate | Final | Max DD |
|------|--------|----------|-------|--------|
| 0.05 | 1 | 0% | $90 | 10% |
| 0.06 | 3 | 33% | $90 | 18.2% |
| 0.07 | 1 | 0% | $90 | 10% |
| 0.08 | 1 | 0% | $90 | 10% |

**Assessment:** Very few trades at all thresholds. Higher thresholds reduce trades further. Results are not stable across thresholds.

---

## 6️⃣ What’s Missing

1. **Polymarket data** — Backtest uses market_prob = 0.5. Real Polymarket prices would change edge and trade frequency.
2. **200+ trades** — Need more data and/or a lower edge threshold so the model produces more signals.
3. **Slippage** — No slippage in simulation; live may differ.
4. **Realistic accuracy** — <54% suggests weak or no edge.

---

## 7️⃣ Recommendation

**DO NOT GO LIVE.**

- No clear statistical edge (accuracy <54%).
- Very few backtest trades (3).
- Profit factor < 1.
- Polymarket data not available to validate alignment.

**Next steps before any live discussion:**
1. Get Polymarket data (different network/VPN or API access).
2. Run paper trading for 3–5 days and record all signals.
3. Re-evaluate after more data and paper results; do not change parameters or add features until then.

---

## Summary Metrics (For Your Records)

- **Accuracy:** 52.57%
- **Precision:** 54.49%
- **Recall:** 56.07%
- **Expected Value:** 0.0514
- **Final Balance (backtest):** $90.00
- **Max Drawdown:** 18.2%
- **Win Rate:** 33.33%
- **Total Trades:** 3
- **Profit Factor:** 0.50
