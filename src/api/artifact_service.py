"""Read-only access to generated analysis artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.ml.constants import (
    ANOMALY_RESULTS_FILE,
    INCIDENTS_FILE,
    ROOT_CAUSE_ANALYSIS_FILE,
)


class ArtifactNotFoundError(FileNotFoundError):
    """Raised when an expected processed artifact is unavailable."""


class ArtifactReadError(RuntimeError):
    """Raised when an existing artifact cannot be parsed safely."""


def _require_file(path: Path, artifact_name: str) -> Path:
    if not path.is_file():
        raise ArtifactNotFoundError(
            f"{artifact_name} artifact is not available: {path.name}"
        )
    return path


def read_anomaly_results() -> list[dict[str, Any]]:
    """Return CSV results as JSON-compatible records without changing the file."""
    path = _require_file(ANOMALY_RESULTS_FILE, "Anomaly results")
    try:
        dataframe = pd.read_csv(path)
        return json.loads(dataframe.to_json(orient="records", date_format="iso"))
    except (ValueError, TypeError, OSError) as error:
        raise ArtifactReadError("Unable to read anomaly results artifact") from error


def read_incidents() -> list[dict[str, Any]]:
    """Return the correlated incidents artifact."""
    path = _require_file(INCIDENTS_FILE, "Incidents")
    try:
        with path.open(encoding="utf-8") as file:
            incidents = json.load(file)
    except (json.JSONDecodeError, OSError) as error:
        raise ArtifactReadError("Unable to read incidents artifact") from error

    if not isinstance(incidents, list):
        raise ArtifactReadError("Incidents artifact must contain a JSON list")
    return incidents


def read_root_cause_analysis() -> dict[str, Any]:
    """Return the latest root-cause analysis artifact."""
    path = _require_file(ROOT_CAUSE_ANALYSIS_FILE, "Root-cause analysis")
    try:
        with path.open(encoding="utf-8") as file:
            analysis = json.load(file)
    except (json.JSONDecodeError, OSError) as error:
        raise ArtifactReadError("Unable to read root-cause analysis artifact") from error

    if not isinstance(analysis, dict):
        raise ArtifactReadError(
            "Root-cause analysis artifact must contain a JSON object"
        )
    return analysis
