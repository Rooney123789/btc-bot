"""
Prediction: load model, scale features, return probabilities.
"""

from typing import Any

import numpy as np

from .model_utils import load_model


def predict_proba(X: np.ndarray) -> np.ndarray:
    """
    Predict class probabilities for samples.

    X must have same features and order as training (use get_feature_names).
    Returns array of shape (n_samples, 2) - [P(class 0), P(class 1)].
    For Up probability use index 1.
    """
    model, scaler, meta = load_model()
    feature_names = meta.get("feature_names", [])
    if X.ndim == 1:
        X = X.reshape(1, -1)
    X_scaled = scaler.transform(X)
    return model.predict_proba(X_scaled)


def predict_up_probability(X: np.ndarray) -> np.ndarray:
    """
    Predict probability of Up (next close > current close).

    Returns 1d array of probabilities.
    """
    proba = predict_proba(X)
    return proba[:, 1]


def get_model_meta() -> dict[str, Any]:
    """Return model metadata (feature names, metrics, etc.)."""
    _, _, meta = load_model()
    return meta
