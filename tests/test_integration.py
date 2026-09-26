from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


ANOMALY_PAYLOAD = {
    "severity": 2,
    "is_error": 1,
    "service_code": 2,
    "message_length": 45,
    "time_since_previous": 10,
    "errors_in_last_minute": 3,
    "warnings_in_last_minute": 1,
    "service_error_rate": 0.5,
}


NORMAL_PAYLOAD = {
    "severity": 0,
    "is_error": 0,
    "service_code": 1,
    "message_length": 20,
    "time_since_previous": 60,
    "errors_in_last_minute": 0,
    "warnings_in_last_minute": 0,
    "service_error_rate": 0.0,
}


def test_end_to_end_anomaly_prediction_pipeline():
    """Verify the complete API-to-ML anomaly detection pipeline."""
    response = client.post("/predict", json=ANOMALY_PAYLOAD)

    assert response.status_code == 200

    result = response.json()

    assert result["prediction"] == "Anomaly"
    assert result["ml_prediction"] in {"Anomaly", "Normal"}
    assert result["rule_prediction"] == "Anomaly"
    assert result["model_output"] in (-1, 1)
    assert result["message"] == "Prediction generated successfully"


def test_end_to_end_normal_prediction_pipeline():
    """Verify the complete API-to-ML pipeline for a normal event."""
    response = client.post("/predict", json=NORMAL_PAYLOAD)

    assert response.status_code == 200

    result = response.json()

    assert result["prediction"] in {"Anomaly", "Normal"}
    assert result["ml_prediction"] in {"Anomaly", "Normal"}
    assert result["rule_prediction"] == "Normal"
    assert result["model_output"] in (-1, 1)
    assert result["message"] == "Prediction generated successfully"


def test_pipeline_rejects_invalid_input():
    """Verify validation prevents malformed data from reaching the model."""
    invalid_payload = {
        "severity": 2,
        "is_error": 1,
        "service_code": 2,
    }

    response = client.post("/predict", json=invalid_payload)

    assert response.status_code == 422


def test_pipeline_returns_consistent_prediction():
    """Verify repeated inference on the same input is deterministic."""
    first_response = client.post("/predict", json=ANOMALY_PAYLOAD)
    second_response = client.post("/predict", json=ANOMALY_PAYLOAD)

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert first_response.json() == second_response.json()