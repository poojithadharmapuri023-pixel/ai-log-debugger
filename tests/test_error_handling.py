
"""Tests for API error handling and failure scenarios."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, artifact_service, model_service


client = TestClient(app)


VALID_FEATURES = {
    "severity": 2,
    "is_error": 1,
    "service_code": 2,
    "message_length": 45,
    "time_since_previous": 10.0,
    "errors_in_last_minute": 3,
    "warnings_in_last_minute": 1,
    "service_error_rate": 0.5,
}


# ---------------------------------------------------------------------------
# Health and validation errors
# ---------------------------------------------------------------------------


def test_health_endpoint_returns_success():
    """Health endpoint should report the current service state."""
    response = client.get("/health")

    assert response.status_code in (200, 503)
    assert response.json()["status"] in ("healthy", "degraded")


@pytest.mark.parametrize(
    "field,value",
    [
        ("severity", -1),
        ("severity", 4),
        ("is_error", -1),
        ("is_error", 2),
        ("service_error_rate", -0.1),
        ("service_error_rate", 1.1),
        ("time_since_previous", -1),
        ("message_length", -1),
    ],
)
def test_predict_rejects_invalid_feature_ranges(field, value):
    """Prediction endpoint should reject values outside schema constraints."""
    payload = VALID_FEATURES.copy()
    payload[field] = value

    response = client.post("/api/v1/predict", json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()


def test_predict_rejects_missing_feature():
    """Prediction endpoint should reject requests with missing features."""
    payload = VALID_FEATURES.copy()
    payload.pop("severity")

    response = client.post("/api/v1/predict", json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()


def test_predict_rejects_invalid_feature_type():
    """Prediction endpoint should reject values with invalid data types."""
    payload = VALID_FEATURES.copy()
    payload["severity"] = "not-a-number"

    response = client.post("/api/v1/predict", json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# Resource / artifact errors
# ---------------------------------------------------------------------------


def test_unknown_incident_returns_404():
    """Requesting an incident that does not exist should return 404."""
    response = client.get("/api/v1/incidents/999999")

    assert response.status_code == 404
    assert "detail" in response.json()
    assert "was not found" in response.json()["detail"]


def test_invalid_incident_id_returns_422():
    """Incident IDs must be positive integers."""
    response = client.get("/api/v1/incidents/0")

    assert response.status_code == 422
    assert "detail" in response.json()


def test_missing_anomaly_artifact_returns_404(monkeypatch):
    """A missing anomaly artifact should be exposed as a 404."""
    original_paths = artifact_service.paths

    monkeypatch.setattr(
        artifact_service,
        "paths",
        replace(
            original_paths,
            anomaly_results=Path("missing_anomaly_results.csv"),
        ),
    )

    response = client.get("/api/v1/anomalies")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_corrupted_anomaly_artifact_returns_500(
    monkeypatch,
    tmp_path,
):
    """A malformed anomaly CSV should return a controlled 500 error."""
    corrupted_file = tmp_path / "corrupted_anomaly_results.csv"

    corrupted_file.write_text(
        "this,is,not,the,expected,schema\n"
        "1,2,3,4,5,6\n",
        encoding="utf-8",
    )

    original_paths = artifact_service.paths

    monkeypatch.setattr(
        artifact_service,
        "paths",
        replace(
            original_paths,
            anomaly_results=corrupted_file,
        ),
    )

    response = client.get("/api/v1/anomalies")

    assert response.status_code == 500
    assert "detail" in response.json()


def test_corrupted_root_cause_artifact_returns_500(
    monkeypatch,
    tmp_path,
):
    """Malformed root-cause JSON should return a controlled 500 error."""
    corrupted_file = tmp_path / "corrupted_root_cause.json"

    corrupted_file.write_text(
        '{"root_cause_service": 123, "confidence": ["invalid"]}',
        encoding="utf-8",
    )

    original_paths = artifact_service.paths

    monkeypatch.setattr(
        artifact_service,
        "paths",
        replace(
            original_paths,
            root_cause_analysis=corrupted_file,
        ),
    )

    response = client.get("/api/v1/root-cause-analysis")

    assert response.status_code == 500
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# Model failure handling
# ---------------------------------------------------------------------------


def test_model_service_failure_returns_503(monkeypatch):
    """Known model-service failures should become HTTP 503 responses."""

    def failing_prediction(_features):
        from src.ml.model_service import ModelServiceError

        raise ModelServiceError("Test model failure")

    monkeypatch.setattr(
        model_service,
        "predict",
        failing_prediction,
    )

    response = client.post(
        "/api/v1/predict",
        json=VALID_FEATURES,
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Test model failure"


def test_unexpected_model_failure_returns_500(monkeypatch):
    """Unexpected model failures should become HTTP 500 responses."""

    def unexpected_failure(_features):
        raise RuntimeError("Unexpected test failure")

    monkeypatch.setattr(
        model_service,
        "predict",
        unexpected_failure,
    )

    response = client.post(
        "/api/v1/predict",
        json=VALID_FEATURES,
    )

    assert response.status_code == 500
    assert (
        response.json()["detail"]
        == "Unexpected error while generating model prediction"
    )


# ---------------------------------------------------------------------------
# Error-response structure
# ---------------------------------------------------------------------------


def test_error_response_has_consistent_detail_field():
    """HTTP errors should expose a consistent detail field."""
    response = client.get("/api/v1/incidents/999999")

    assert response.status_code == 404

    body = response.json()

    assert isinstance(body, dict)
    assert "detail" in body
    assert isinstance(body["detail"], str)

