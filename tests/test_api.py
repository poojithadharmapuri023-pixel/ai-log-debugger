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

def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body, dict)
    assert "message" in body
    assert isinstance(body["message"], str)
    assert body["message"]

def test_openapi_documentation():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    body = response.json()

    assert body["info"]["title"] == "AI Log Debugger API"
    assert body["info"]["version"] == "1.0.0"
    assert "/health" in body["paths"]    

def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body, dict)
    assert body["status"] == "healthy"
    assert isinstance(body["status"], str)

def test_health_status_is_healthy():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()

    assert body.get("status") == "healthy" 

def test_health_returns_json():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert isinstance(response.json(), dict)

def test_docs_endpoint():
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_redoc_endpoint():
    response = client.get("/redoc")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_openapi_contains_api_tags():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    body = response.json()
    tags = {
        item["name"]: item["description"]
        for item in body.get("tags", [])
    }

    assert "Service" in tags
    assert "Predictions" in tags
    assert "Analysis results" in tags  

def test_openapi_contains_expected_endpoints():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/" in paths
    assert "/health" in paths
    assert "/predict" in paths
    assert "/root-cause" in paths

def test_health_response_fields():
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert "status" in body
    assert "model_loaded" in body
    assert "gemini_available" in body

    assert body["status"] == "healthy"
    assert body["model_loaded"] is True


def test_predict_response_fields():
    payload = {
        "severity": 2,
        "is_error": 1,
        "service_code": 2,
        "message_length": 45,
        "time_since_previous": 10.0,
        "errors_in_last_minute": 3,
        "warnings_in_last_minute": 1,
        "service_error_rate": 0.5,
    }

    response = client.post("/predict", json=payload)

    assert response.status_code == 200

    body = response.json()

    assert "prediction" in body
    assert "severity" in body
    assert "ml_prediction" in body
    assert "rule_prediction" in body
    assert "model_output" in body
    assert "message" in body

    assert body["prediction"] in {"Anomaly", "Normal"}
    assert body["ml_prediction"] in {"Anomaly", "Normal"}
    assert body["rule_prediction"] in {"Anomaly", "Normal"}


def test_predict_rejects_invalid_payload():
    payload = {
        "severity": 2,
        "is_error": 1,
        "service_code": 2,
        "message_length": 45,
        "time_since_previous": 10.0,
        "errors_in_last_minute": 3,
        # warnings_in_last_minute is intentionally missing
        "service_error_rate": 0.5,
    }

    response = client.post("/predict", json=payload)

    assert response.status_code == 422


def test_root_cause_response_fields():
    response = client.post("/root-cause")

    assert response.status_code == 200

    body = response.json()

    assert "deterministic_analysis" in body
    assert "ai_analysis" in body