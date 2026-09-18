"""Explicit offline command for training the Isolation Forest model.

Run from the project root with:
    python -m src.training.train_model

This command is the only code in this phase that writes a model file, and it
does so only when invoked directly.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

from src.detection.anomaly_detector import select_model_features
from src.ml.constants import (
    FEATURES_FILE,
    ISOLATION_FOREST_CONTAMINATION,
    ISOLATION_FOREST_RANDOM_STATE,
    MODEL_FILE,
)


def train_model(
    features_path: Path | str = FEATURES_FILE,
    model_path: Path | str = MODEL_FILE,
) -> IsolationForest:
    """Train and explicitly save an Isolation Forest from feature data."""
    features_path = Path(features_path)
    model_path = Path(model_path)

    if not features_path.is_file():
        raise FileNotFoundError(f"Feature dataset was not found: {features_path}")

    dataframe = pd.read_csv(features_path)
    model = IsolationForest(
        contamination=ISOLATION_FOREST_CONTAMINATION,
        random_state=ISOLATION_FOREST_RANDOM_STATE,
    )
    model.fit(select_model_features(dataframe))

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    return model


def main() -> None:
    train_model()
    print(f"Trained model saved: {MODEL_FILE}")


if __name__ == "__main__":
    main()
