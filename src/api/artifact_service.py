"""Read-only, validated access to generated analysis artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.ml.constants import ANOMALY_RESULTS_FILE, INCIDENTS_FILE, ROOT_CAUSE_ANALYSIS_FILE


class ArtifactNotFoundError(FileNotFoundError):
    """Raised when an expected processed artifact is unavailable."""


class ArtifactReadError(RuntimeError):
    """Raised when an existing artifact cannot be parsed safely."""


@dataclass(frozen=True)
class ArtifactPaths:
    anomaly_results: Path = ANOMALY_RESULTS_FILE
    incidents: Path = INCIDENTS_FILE
    root_cause_analysis: Path = ROOT_CAUSE_ANALYSIS_FILE


class ArtifactService:
    """Small data-access layer that never writes or regenerates artifacts."""

    def __init__(self, paths: ArtifactPaths | None = None) -> None:
        self.paths = paths or ArtifactPaths()

    @staticmethod
    def _require_file(path: Path, artifact_name: str) -> Path:
        if not path.is_file():
            raise ArtifactNotFoundError(f"{artifact_name} artifact is not available: {path.name}")
        return path

    def read_anomaly_results(self) -> list[dict[str, Any]]:
        path = self._require_file(self.paths.anomaly_results, "Anomaly results")
        try:
            dataframe = pd.read_csv(path)
            required_columns = {
                "timestamp", "service", "level", "message", "severity", "is_error",
                "service_code", "message_length", "time_since_previous",
                "errors_in_last_minute", "warnings_in_last_minute", "service_error_rate",
                "anomaly",
            }
            missing_columns = required_columns.difference(dataframe.columns)
            if missing_columns:
                raise ArtifactReadError(
                    "Anomaly results artifact is missing columns: " + ", ".join(sorted(missing_columns))
                )
            return json.loads(dataframe.to_json(orient="records", date_format="iso"))
        except ArtifactReadError:
            raise
        except (ValueError, TypeError, OSError) as error:
            raise ArtifactReadError("Unable to read anomaly results artifact") from error

    def read_incidents(self) -> list[dict[str, Any]]:
        path = self._require_file(self.paths.incidents, "Incidents")
        try:
            with path.open(encoding="utf-8") as file:
                incidents = json.load(file)
        except (json.JSONDecodeError, OSError) as error:
            raise ArtifactReadError("Unable to read incidents artifact") from error
        if not isinstance(incidents, list) or not all(isinstance(item, dict) for item in incidents):
            raise ArtifactReadError("Incidents artifact must contain a JSON list of objects")
        return incidents

    def read_root_cause_analysis(self) -> dict[str, Any]:
        path = self._require_file(self.paths.root_cause_analysis, "Root-cause analysis")
        try:
            with path.open(encoding="utf-8") as file:
                analysis = json.load(file)
        except (json.JSONDecodeError, OSError) as error:
            raise ArtifactReadError("Unable to read root-cause analysis artifact") from error
        if not isinstance(analysis, dict):
            raise ArtifactReadError("Root-cause analysis artifact must contain a JSON object")
        return analysis

    def readiness(self) -> dict[str, tuple[bool, bool]]:
        """Return (available, readable) for every required dashboard artifact."""
        readers = {
            "anomaly_results": self.read_anomaly_results,
            "incidents": self.read_incidents,
            "root_cause_analysis": self.read_root_cause_analysis,
        }
        status: dict[str, tuple[bool, bool]] = {}
        for name, reader in readers.items():
            try:
                reader()
                status[name] = (True, True)
            except ArtifactNotFoundError:
                status[name] = (False, False)
            except ArtifactReadError:
                status[name] = (True, False)
        return status


# Compatibility helpers for the Phase 2 module-level data-access functions.
_default_service = ArtifactService()


def read_anomaly_results() -> list[dict[str, Any]]:
    return _default_service.read_anomaly_results()


def read_incidents() -> list[dict[str, Any]]:
    return _default_service.read_incidents()


def read_root_cause_analysis() -> dict[str, Any]:
    return _default_service.read_root_cause_analysis()
