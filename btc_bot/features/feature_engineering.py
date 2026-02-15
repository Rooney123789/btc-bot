"""
Feature engineering for BTC 5-min ML trading bot.

Computes: 5-min returns, EMA 9/21, EMA slope, RSI, MACD, ATR, volume change.
Clean labeling: target = 1 if next candle close > current close else 0.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Feature constants
EMA_FAST: int = 9
EMA_SLOW: int = 21
RSI_PERIOD: int = 14
MACD_FAST: int = 12
MACD_SLOW: int = 26
MACD_SIGNAL: int = 9
ATR_PERIOD: int = 14


def _ema(series: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average."""
    result = np.full_like(series, np.nan, dtype=float)
    if len(series) < period:
        return result
    mult = 2.0 / (period + 1)
    result[period - 1] = np.mean(series[:period])
    for i in range(period, len(series)):
        result[i] = (series[i] - result[i - 1]) * mult + result[i - 1]
    return result


def _rsi(closes: np.ndarray, period: int = RSI_PERIOD) -> np.ndarray:
    """Relative Strength Index."""
    result = np.full_like(closes, np.nan, dtype=float)
    if len(closes) < period + 1:
        return result
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.zeros(len(closes))
    avg_loss = np.zeros(len(closes))
    avg_gain[period] = np.mean(gains[:period])
    avg_loss[period] = np.mean(losses[:period])
    for i in range(period + 1, len(closes)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(avg_loss == 0, 100.0, avg_gain / np.where(avg_loss == 0, 1.0, avg_loss))
    result[period:] = 100.0 - (100.0 / (1.0 + rs[period:]))
    return result


def _macd(
    closes: np.ndarray,
    fast: int = MACD_FAST,
    slow: int = MACD_SLOW,
    signal: int = MACD_SIGNAL,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MACD line, signal line, histogram."""
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = ema_fast - ema_slow
    macd_signal = _ema(np.nan_to_num(macd_line, nan=0), signal)
    macd_hist = macd_line - macd_signal
    return macd_line, macd_signal, macd_hist


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = ATR_PERIOD) -> np.ndarray:
    """Average True Range."""
    result = np.full_like(close, np.nan, dtype=float)
    if len(close) < 2:
        return result
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    if len(tr) < period:
        return result
    result[period - 1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        result[i] = (result[i - 1] * (period - 1) + tr[i]) / period
    return result


def build_features(klines: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build feature matrix and labels from kline data.

    Args:
        klines: List of dicts with open, high, low, close, volume, open_time_ms.

    Returns:
        X: Feature matrix (n_samples, n_features), rows with NaN dropped.
        y: Labels (n_samples,) - 1 if next close > current close else 0.
        timestamps: open_time_ms for each sample (aligned with X, y).
    """
    if not klines or len(klines) < 2:
        return np.array([]).reshape(0, 0), np.array([]), np.array([])

    n = len(klines)
    open_arr = np.array([k["open"] for k in klines], dtype=float)
    high_arr = np.array([k["high"] for k in klines], dtype=float)
    low_arr = np.array([k["low"] for k in klines], dtype=float)
    close_arr = np.array([k["close"] for k in klines], dtype=float)
    volume_arr = np.array([k["volume"] for k in klines], dtype=float)

    # 5-min returns: (close - prev_close) / prev_close
    returns = np.zeros(n)
    returns[1:] = (close_arr[1:] - close_arr[:-1]) / np.where(close_arr[:-1] == 0, 1e-10, close_arr[:-1])

    # EMA 9, EMA 21, EMA slope
    ema9 = _ema(close_arr, EMA_FAST)
    ema21 = _ema(close_arr, EMA_SLOW)
    ema_slope = np.zeros(n)
    ema_slope[1:] = ema9[1:] - ema9[:-1]

    # RSI
    rsi = _rsi(close_arr, RSI_PERIOD)

    # MACD
    macd_line, macd_signal, macd_hist = _macd(close_arr)

    # ATR
    atr = _atr(high_arr, low_arr, close_arr, ATR_PERIOD)

    # Volume change: (vol - prev_vol) / prev_vol
    vol_change = np.zeros(n)
    vol_change[1:] = (volume_arr[1:] - volume_arr[:-1]) / np.where(volume_arr[:-1] == 0, 1e-10, volume_arr[:-1])

    # Label: target = 1 if next candle close > current close else 0
    # Last row has no "next" candle, so we exclude it
    labels = np.zeros(n - 1, dtype=int)
    labels = (close_arr[1:] > close_arr[:-1]).astype(int)

    # Stack features (exclude last row for labels alignment)
    min_len = max(EMA_SLOW, RSI_PERIOD, MACD_SLOW + MACD_SIGNAL, ATR_PERIOD)
    start_idx = min_len
    end_idx = n - 1  # exclude last: we need next close for label

    if start_idx >= end_idx:
        return np.array([]).reshape(0, 0), np.array([]), np.array([])

    features_list = [
        returns[start_idx:end_idx],
        ema9[start_idx:end_idx],
        ema21[start_idx:end_idx],
        ema_slope[start_idx:end_idx],
        rsi[start_idx:end_idx],
        macd_line[start_idx:end_idx],
        macd_signal[start_idx:end_idx],
        macd_hist[start_idx:end_idx],
        atr[start_idx:end_idx],
        vol_change[start_idx:end_idx],
    ]
    X = np.column_stack(features_list)
    y = labels[start_idx:end_idx]
    timestamps = np.array([klines[i]["open_time_ms"] for i in range(start_idx, end_idx)])

    # Drop rows with any NaN/Inf
    valid = np.isfinite(X).all(axis=1)
    X = X[valid]
    y = y[valid]
    timestamps = timestamps[valid]

    logger.info("Built features: %d samples, %d features", X.shape[0], X.shape[1])
    return X, y, timestamps


def get_feature_names() -> list[str]:
    """Return ordered feature names for the feature matrix."""
    return [
        "return_5m",
        "ema_9",
        "ema_21",
        "ema_slope",
        "rsi",
        "macd_line",
        "macd_signal",
        "macd_hist",
        "atr",
        "vol_change",
    ]
