"""Focused end-to-end checks for the read-only FastAPI dashboard data layer."""

from __future__ import annotations

import json
import socket
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import uvicorn

from src.api import main as api_main
from src.api.artifact_service import ArtifactPaths, ArtifactService


class ApiDataLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            cls.port = probe.getsockname()[1]
        cls.server = uvicorn.Server(
            uvicorn.Config(api_main.app, host="127.0.0.1", port=cls.port, log_level="critical")
        )
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        for _ in range(150):
            try:
                cls.request("/health")
                break
            except (TimeoutError, URLError):
                time.sleep(0.1)
        else:
            raise RuntimeError("FastAPI test server did not start")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.should_exit = True
        cls.thread.join(timeout=5)

    @classmethod
    def request(cls, path: str, payload: dict | None = None) -> tuple[int, dict]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"http://127.0.0.1:{cls.port}{path}", data=data,
            headers={"Content-Type": "application/json"} if data else {},
        )
        try:
            with urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))

    def test_anomaly_pagination_and_filters(self) -> None:
        status, body = self.request("/api/v1/anomalies?page=1&page_size=3")
        self.assertEqual(status, 200)
        self.assertEqual((body["page"], body["page_size"], body["total"], body["pages"]), (1, 3, 20, 7))
        self.assertEqual(len(body["items"]), 3)
        self.assertEqual(body["items"], body["results"])

        status, body = self.request("/api/v1/anomalies?service=database-service&level=ERROR&anomaly_only=true")
        self.assertEqual(status, 200)
        self.assertGreater(body["total"], 0)
        self.assertTrue(all(item["service"] == "database-service" and item["level"] == "ERROR" for item in body["items"]))

    def test_invalid_pagination_returns_validation_error(self) -> None:
        status, body = self.request("/api/v1/anomalies?page=0")
        self.assertEqual(status, 422)
        self.assertIn("detail", body)

    def test_incidents_and_not_found_detail(self) -> None:
        status, body = self.request("/api/v1/incidents")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["items"], body["incidents"])
        self.assertIn("related_anomaly_count", body["items"][0])

        status, body = self.request("/api/v1/incidents/1")
        self.assertEqual(status, 200)
        self.assertEqual(body["incident_id"], 1)
        self.assertEqual(body["affected_services"], body["services"])

        status, body = self.request("/api/v1/incidents/999")
        self.assertEqual(status, 404)
        self.assertIn("not found", body["detail"])

    def test_root_cause_metrics_and_health(self) -> None:
        status, root_cause = self.request("/api/v1/root-cause-analysis")
        self.assertEqual(status, 200)
        self.assertEqual((root_cause["total"], len(root_cause["items"])), (1, 1))
        self.assertEqual(root_cause["analysis"]["root_cause_service"], "database-service")

        status, metrics = self.request("/api/v1/metrics")
        self.assertEqual(status, 200)
        self.assertEqual(metrics["total_logs"], metrics["normal_record_count"] + metrics["hybrid_anomaly_count"])
        self.assertEqual(metrics["incident_count"], 2)
        self.assertIn("sample artifact", metrics["data_scope"])

        status, health = self.request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["status"], "healthy")
        self.assertTrue(all(item["readable"] for item in health["dashboard_artifacts"].values()))

    def test_missing_artifact_returns_clear_error(self) -> None:
        original_service = api_main.artifact_service
        api_main.artifact_service = ArtifactService(
            ArtifactPaths(
                anomaly_results=Path("data/processed/not-present.csv"),
                incidents=original_service.paths.incidents,
                root_cause_analysis=original_service.paths.root_cause_analysis,
            )
        )
        try:
            status, body = self.request("/api/v1/anomalies")
        finally:
            api_main.artifact_service = original_service
        self.assertEqual(status, 404)
        self.assertIn("Anomaly results artifact", body["detail"])

    def test_prediction_routes_and_invalid_payload(self) -> None:
        payload = {
            "severity": 0, "is_error": 0, "service_code": 1, "message_length": 21,
            "time_since_previous": 0.0, "errors_in_last_minute": 0,
            "warnings_in_last_minute": 0, "service_error_rate": 0.0,
        }
        status, legacy = self.request("/predict", payload)
        self.assertEqual(status, 200)
        self.assertEqual(set(legacy), {"prediction", "model_output"})

        status, hybrid = self.request("/api/v1/predict", payload)
        self.assertEqual(status, 200)
        self.assertEqual(hybrid["prediction"], "Normal")
        self.assertIn("context_note", hybrid)

        status, body = self.request("/predict", {"severity": 0})
        self.assertEqual(status, 422)
        self.assertIn("detail", body)


if __name__ == "__main__":
    unittest.main()
