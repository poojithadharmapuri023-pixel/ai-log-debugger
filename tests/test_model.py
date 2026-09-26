from pathlib import Path

import pytest

from src.ml.constants import FEATURE_COLUMNS, MODEL_FILE
from src.ml.model_service import ModelService, ModelServiceError


VALID_FEATURES = {
    "severity": 2,
    "is_error": 1,
    "service_code": 2,
    "message_length": 45,
    "time_since_previous": 10,
    "errors_in_last_minute": 3,
    "warnings_in_last_minute": 1,
    "service_error_rate": 0.5,
}


def test_model_file_exists():
    assert Path(MODEL_FILE).is_file()


def test_model_loads_successfully():
    service = ModelService()

    model = service.load_model()

    assert model is not None
    assert service.is_loaded is True


def test_model_is_cached_after_first_load():
    service = ModelService()

    first_model = service.load_model()
    second_model = service.load_model()

    assert first_model is second_model


def test_model_predict_returns_valid_output():
    service = ModelService()

    prediction = service.predict(VALID_FEATURES)

    assert prediction in (-1, 1)


def test_model_predict_requires_all_features():
    service = ModelService()

    incomplete_features = {
        "severity": 2,
        "is_error": 1,
    }

    with pytest.raises(ModelServiceError, match="missing required columns"):
        service.predict(incomplete_features)


def test_model_predict_with_zero_values():
    service = ModelService()

    features = {
        column: 0
        for column in FEATURE_COLUMNS
    }

    prediction = service.predict(features)

    assert prediction in (-1, 1)


def test_model_predict_with_high_severity_features():
    service = ModelService()

    features = {
        "severity": 3,
        "is_error": 1,
        "service_code": 2,
        "message_length": 100,
        "time_since_previous": 1,
        "errors_in_last_minute": 10,
        "warnings_in_last_minute": 5,
        "service_error_rate": 1.0,
    }

    prediction = service.predict(features)

    assert prediction in (-1, 1)


def test_missing_model_file_returns_clear_error(tmp_path):
    missing_model = tmp_path / "missing_model.joblib"

    service = ModelService(model_path=missing_model)

    with pytest.raises(
        ModelServiceError,
        match="Trained model file was not found",
    ):
        service.load_model()