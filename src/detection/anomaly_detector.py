"""Reusable anomaly-detection helpers.

This module intentionally performs no file I/O or model training when imported.
Use ``src.training.train_model`` for the explicit training command and
``src.ml.model_service`` for inference in the API.
"""

from __future__ import annotations

import pandas as pd

try:
    from src.ml.constants import FEATURE_COLUMNS
except ModuleNotFoundError:  # Supports running legacy scripts from ``src``.
    from ml.constants import FEATURE_COLUMNS


def select_model_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return the model features in the exact order used during training."""
    missing_columns = [
        column for column in FEATURE_COLUMNS if column not in dataframe.columns
    ]
    if missing_columns:
        raise ValueError(
            "Feature data is missing required columns: "
            + ", ".join(missing_columns)
        )

    return dataframe.loc[:, FEATURE_COLUMNS].copy()


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
