"""Quality assurance tests for TraceRoot AI."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_contract():
    """Health endpoint exposes the required system status fields."""
    response = client.get("/health")

    assert response.status_code in (200, 503)

    body = response.json()

    assert body["status"] in ("healthy", "degraded")
    assert body["api_running"] is True
    assert "model_available" in body
    assert "model_loadable" in body
    assert "model_loaded" in body
    assert "dashboard_artifacts" in body


def test_anomaly_results_contract():
    """Anomaly endpoint returns a valid paginated response."""
    response = client.get("/api/v1/anomalies")

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body["items"], list)
    assert isinstance(body["results"], list)
    assert isinstance(body["total"], int)
    assert body["total"] >= 0
    assert body["page"] >= 1
    assert body["page_size"] > 0
    assert body["pages"] >= 0


def test_incidents_contract():
    """Incidents endpoint returns structured incident records."""
    response = client.get("/api/v1/incidents")

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body["items"], list)
    assert isinstance(body["incidents"], list)
    assert body["total"] == len(body["items"])

    if body["items"]:
        incident = body["items"][0]

        assert isinstance(incident["incident_id"], int)
        assert isinstance(incident["severity"], str)
        assert isinstance(incident["services"], list)
        assert isinstance(incident["events"], list)


def test_root_cause_analysis_contract():
    """Root-cause endpoint returns a usable analysis."""
    response = client.get("/api/v1/root-cause-analysis")

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body["analysis"], dict)
    assert "root_cause_service" in body["analysis"]

    root_cause = body["analysis"]["root_cause_service"]

    assert isinstance(root_cause, str)
    assert root_cause.strip()


def test_metrics_contract():
    """Metrics endpoint exposes consistent dashboard metrics."""
    response = client.get("/api/v1/metrics")

    assert response.status_code == 200

    body = response.json()

    required_fields = {
        "total_logs",
        "ml_anomaly_count",
        "hybrid_anomaly_count",
        "normal_record_count",
        "anomaly_percentage",
        "incident_count",
        "logs_by_service",
        "logs_by_level",
        "anomalies_by_service",
        "anomalies_by_level",
        "data_scope",
    }

    assert required_fields.issubset(body.keys())

    assert body["total_logs"] >= 0
    assert body["ml_anomaly_count"] >= 0
    assert body["hybrid_anomaly_count"] >= 0
    assert body["normal_record_count"] >= 0
    assert body["incident_count"] >= 0
    assert 0 <= body["anomaly_percentage"] <= 100


def test_prediction_is_deterministic():
    """The same valid input should produce the same prediction."""
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

    first = client.post("/api/v1/predict", json=payload)
    second = client.post("/api/v1/predict", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_anomaly_pagination():
    """Pagination parameters should return a valid page."""
    response = client.get(
        "/api/v1/anomalies",
        params={"page": 1, "page_size": 5},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["page"] == 1
    assert body["page_size"] == 5
    assert len(body["items"]) <= 5


def test_incident_pagination():
    """Incident endpoint should respect the requested page size."""
    response = client.get(
        "/api/v1/incidents",
        params={"page": 1, "page_size": 2},
    )

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body["items"], list)
    assert isinstance(body["incidents"], list)
    assert len(body["items"]) <= 2
    
def test_api_returns_json_for_known_endpoints():
    """Known API endpoints should return JSON responses."""
    endpoints = [
        "/health",
        "/api/v1/anomalies",
        "/api/v1/incidents",
        "/api/v1/root-cause-analysis",
        "/api/v1/metrics",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)

        assert "application/json" in response.headers["content-type"]