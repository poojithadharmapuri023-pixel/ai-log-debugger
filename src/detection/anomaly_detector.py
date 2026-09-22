"""Reusable anomaly-detection helpers.

This module intentionally performs no file I/O or model training when imported.
Use ``src.training.train_model`` for the explicit training command and
``src.ml.model_service`` for inference in the API.
"""

from __future__ import annotations

try:
    from src.analysis.feature_engineering import select_model_features
except ModuleNotFoundError:  # Supports running legacy scripts from ``src``.
    from analysis.feature_engineering import select_model_features

import pandas as pd


def predict_anomalies(model, dataframe: pd.DataFrame) -> pd.DataFrame:
    """Attach Isolation Forest predictions to a copy of ``dataframe``.

    The caller supplies a trained model and decides whether and where to save
    the returned data. This keeps importing and using the module side-effect
    free.
    """
    predictions = model.predict(select_model_features(dataframe))
    results = dataframe.copy()
    results["anomaly"] = predictions
    return results
