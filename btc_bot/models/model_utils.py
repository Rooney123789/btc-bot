"""
Model utilities: load/save, scaling, persistence.
"""

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from config import MODEL_DIR

logger = logging.getLogger(__name__)

MODEL_FILENAME = "logistic_model.pkl"
SCALER_FILENAME = "scaler.pkl"
META_FILENAME = "model_meta.json"


def ensure_model_dir() -> Path:
    """Ensure model directory exists."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    return MODEL_DIR


def save_model(
    model: LogisticRegression,
    scaler: StandardScaler,
    feature_names: list[str],
    n_train: int,
    metrics: dict[str, float],
) -> None:
    """Save model, scaler, and metadata to disk."""
    import joblib

    ensure_model_dir()
    joblib.dump(model, MODEL_DIR / MODEL_FILENAME)
    joblib.dump(scaler, MODEL_DIR / SCALER_FILENAME)
    meta = {
        "feature_names": feature_names,
        "n_train": n_train,
        "metrics": metrics,
    }
    with open(MODEL_DIR / META_FILENAME, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info("Saved model to %s", MODEL_DIR)


def load_model() -> tuple[LogisticRegression, StandardScaler, dict[str, Any]]:
    """Load model, scaler, and metadata from disk. Raises FileNotFoundError if not found."""
    import joblib

    model_path = MODEL_DIR / MODEL_FILENAME
    scaler_path = MODEL_DIR / SCALER_FILENAME
    meta_path = MODEL_DIR / META_FILENAME
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    meta: dict[str, Any] = {}
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
    return model, scaler, meta


def create_model(
    C: float = 1.0,
    max_iter: int = 1000,
    random_state: int = 42,
) -> LogisticRegression:
    """Create LogisticRegression with default config."""
    return LogisticRegression(
        C=C,
        max_iter=max_iter,
        random_state=random_state,
        solver="lbfgs",
        class_weight="balanced",
    )
