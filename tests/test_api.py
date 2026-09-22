from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["model_loaded"] is True


def test_predict_anomaly():
    payload = {
        "severity": 1,
        "is_error": 1,
        "service_code": 2,
        "message_length": 45,
        "time_since_previous": 5.0,
        "errors_in_last_minute": 2,
        "warnings_in_last_minute": 1,
        "service_error_rate": 0.5,
    }

    response = client.post("/predict", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["prediction"] == "Anomaly"
    assert data["model_output"] in [-1, 1]


def test_predict_normal():
    payload = {
        "severity": 0,
        "is_error": 0,
        "service_code": 1,
        "message_length": 20,
        "time_since_previous": 10.0,
        "errors_in_last_minute": 0,
        "warnings_in_last_minute": 0,
        "service_error_rate": 0.0,
    }

    response = client.post("/predict", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["prediction"] in ["Normal", "Anomaly"]


def test_root_cause():
    response = client.post("/root-cause")

    assert response.status_code == 200

    data = response.json()

    assert "deterministic_analysis" in data
    assert "ai_analysis" in data

    assert (
        data["deterministic_analysis"]["root_cause_service"]
        == "database-service"
    )