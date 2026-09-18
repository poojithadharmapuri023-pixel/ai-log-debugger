"""Shared model configuration and project-relative paths."""

from pathlib import Path


# ``constants.py`` lives in ``<project root>/src/ml``.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

FEATURES_FILE = PROCESSED_DATA_DIR / "features.csv"
MODEL_FILE = PROCESSED_DATA_DIR / "isolation_forest_model.joblib"
ANOMALY_RESULTS_FILE = PROCESSED_DATA_DIR / "anomaly_results.csv"
INCIDENTS_FILE = PROCESSED_DATA_DIR / "incidents.json"
ROOT_CAUSE_ANALYSIS_FILE = PROCESSED_DATA_DIR / "root_cause_analysis.json"

FEATURE_COLUMNS = [
    "severity",
    "is_error",
    "service_code",
    "message_length",
    "time_since_previous",
    "errors_in_last_minute",
    "warnings_in_last_minute",
    "service_error_rate",
]

ISOLATION_FOREST_CONTAMINATION = 0.3
ISOLATION_FOREST_RANDOM_STATE = 42
ANOMALY_MODEL_OUTPUT = -1
NORMAL_MODEL_OUTPUT = 1
