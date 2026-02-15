"""
Logistic Regression training pipeline.

Time-series split, walk-forward validation, save model, print metrics.
"""

import logging
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import StandardScaler

from config import MODEL_DIR
from data.database import get_binance_klines
from features.feature_engineering import build_features, get_feature_names
from .model_utils import create_model, ensure_model_dir, save_model

logger = logging.getLogger(__name__)


def _expected_value_estimate(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    """
    Estimate expected value: E[reward] per trade.
    Assume binary outcome: win 1 unit if correct, lose 1 if wrong.
    EV = P(correct) * 1 + P(wrong) * (-1) = 2*accuracy - 1 (simplified).
    For probability-weighted: EV ≈ mean( (2*y_proba - 1) * (2*y_true - 1) ) per decision.
    """
    if len(y_true) == 0:
        return 0.0
    # Decision: predict 1 if proba >= 0.5 else 0
    y_pred = (y_proba >= 0.5).astype(int)
    # Reward: +1 if correct, -1 if wrong
    rewards = np.where(y_pred == y_true, 1.0, -1.0)
    return float(np.mean(rewards))


def train(
    limit: int = 10_000,
    train_frac: float = 0.8,
    C: float = 1.0,
    max_iter: int = 1000,
) -> dict[str, Any]:
    """
    Train Logistic Regression with time-series split.

    No random shuffle. Uses first train_frac for training, rest for validation.
    Saves model to disk. Returns metrics dict.
    """
    ensure_model_dir()
    klines = get_binance_klines(limit=limit)
    X, y, timestamps = build_features(klines)
    feature_names = get_feature_names()

    if X.shape[0] < 100:
        raise ValueError(f"Insufficient data: {X.shape[0]} samples. Need at least 100.")

    # Time-series split: no shuffle
    n = len(X)
    n_train = int(n * train_frac)
    if n_train < 50:
        n_train = min(50, n - 10)
    n_val = n - n_train
    if n_val < 10:
        raise ValueError("Insufficient validation samples after split.")

    X_train, X_val = X[:n_train], X[n_train:]
    y_train, y_val = y[:n_train], y[n_train:]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    model = create_model(C=C, max_iter=max_iter)
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_val_scaled)
    y_proba = model.predict_proba(X_val_scaled)[:, 1]

    accuracy = float(accuracy_score(y_val, y_pred))
    precision = float(precision_score(y_val, y_pred, zero_division=0))
    recall = float(recall_score(y_val, y_pred, zero_division=0))
    cm = confusion_matrix(y_val, y_pred)
    ev = _expected_value_estimate(y_val, y_proba)

    metrics = {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "expected_value": ev,
        "n_train": n_train,
        "n_val": n_val,
    }

    # Print metrics
    print("\n" + "=" * 50)
    print("TRAINING METRICS (Validation Set)")
    print("=" * 50)
    print(f"Accuracy:       {accuracy:.4f}")
    print(f"Precision:      {precision:.4f}")
    print(f"Recall:         {recall:.4f}")
    print(f"Expected Value: {ev:.4f}")
    print(f"\nConfusion Matrix:")
    print(f"  Pred 0  Pred 1")
    print(f"0  {cm[0,0]:5d}  {cm[0,1]:5d}")
    print(f"1  {cm[1,0]:5d}  {cm[1,1]:5d}")
    print("=" * 50)

    save_model(model, scaler, feature_names, n_train, metrics)
    return metrics


def run_walk_forward(
    limit: int = 5_000,
    train_size: int = 500,
    step_size: int = 100,
) -> list[dict[str, float]]:
    """
    Walk-forward validation: train on window, validate on next step, slide forward.

    Returns list of validation metrics per fold.
    """
    klines = get_binance_klines(limit=limit)
    X, y, _ = build_features(klines)
    feature_names = get_feature_names()

    if X.shape[0] < train_size + step_size:
        logger.warning("Insufficient data for walk-forward")
        return []

    results: list[dict[str, float]] = []
    scaler = StandardScaler()

    for start in range(0, X.shape[0] - train_size - step_size, step_size):
        X_train = X[start : start + train_size]
        y_train = y[start : start + train_size]
        X_val = X[start + train_size : start + train_size + step_size]
        y_val = y[start + train_size : start + train_size + step_size]

        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)

        model = create_model()
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_val_scaled)
        y_proba = model.predict_proba(X_val_scaled)[:, 1]

        results.append({
            "accuracy": float(np.mean(y_pred == y_val)),
            "expected_value": _expected_value_estimate(y_val, y_proba),
        })
    return results
