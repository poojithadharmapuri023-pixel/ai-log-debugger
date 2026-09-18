"""Read-only loading and inference for the trained anomaly model."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import joblib
import pandas as pd

from src.ml.constants import FEATURE_COLUMNS, MODEL_FILE


class ModelServiceError(RuntimeError):
    """Raised when the trained model cannot be loaded or used."""


class ModelService:
    """Load the existing model lazily and use it without modifying it."""

    def __init__(self, model_path: Path | str = MODEL_FILE) -> None:
        self.model_path = Path(model_path)
        self._model = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load_model(self):
        """Load and cache the pre-trained model from disk."""
        if self._model is not None:
            return self._model

        if not self.model_path.is_file():
            raise ModelServiceError(
                f"Trained model file was not found: {self.model_path}"
            )

        try:
            self._model = joblib.load(self.model_path)
        except Exception as error:
            raise ModelServiceError(
                f"Unable to load trained model: {self.model_path}"
            ) from error

        return self._model

    def predict(self, features: Mapping[str, int | float]) -> int:
        """Return the Isolation Forest prediction for one feature record."""
        missing_columns = [
            column for column in FEATURE_COLUMNS if column not in features
        ]
        if missing_columns:
            raise ModelServiceError(
                "Prediction features are missing required columns: "
                + ", ".join(missing_columns)
            )

        input_data = pd.DataFrame(
            [[features[column] for column in FEATURE_COLUMNS]],
            columns=FEATURE_COLUMNS,
        )

        try:
            prediction = self.load_model().predict(input_data)[0]
        except ModelServiceError:
            raise
        except Exception as error:
            raise ModelServiceError("Unable to generate model prediction") from error

        return int(prediction)
