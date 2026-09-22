"""Canonical, side-effect-free log feature engineering."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from src.ml.constants import (
    ERROR_LEVELS,
    FEATURE_COLUMNS,
    SERVICE_CODE_MAP,
    SEVERITY_CODE_MAP,
    WARNING_LEVEL,
)
from src.preprocessing.data_cleaning import normalize_log_records


def encode_severity(levels: pd.Series) -> pd.Series:
    """Encode normalized log levels using the model's severity convention."""
    normalized_levels = levels.astype("string").str.strip().str.upper()
    encoded = normalized_levels.map(SEVERITY_CODE_MAP)
    unknown_levels = sorted(
        str(level) for level in normalized_levels[encoded.isna()].dropna().unique()
    )
    if unknown_levels:
        raise ValueError("Unsupported log levels: " + ", ".join(unknown_levels))
    if encoded.isna().any():
        raise ValueError("Log levels cannot be missing")
    return encoded.astype(int)


def encode_service_names(
    services: pd.Series,
    service_code_map: Mapping[str, int] = SERVICE_CODE_MAP,
) -> pd.Series:
    """Encode services with an explicit, model-compatible mapping.

    Unknown services are rejected instead of being assigned a new code, because
    a newly assigned numeric value would not be compatible with the model that
    was trained on the existing service mapping.
    """
    normalized_services = services.astype("string").str.strip()
    encoded = normalized_services.map(service_code_map)
    unknown_services = sorted(
        str(service)
        for service in normalized_services[encoded.isna()].dropna().unique()
    )
    if unknown_services:
        raise ValueError("Unknown service names: " + ", ".join(unknown_services))
    if encoded.isna().any():
        raise ValueError("Service names cannot be missing")
    return encoded.astype(int)


def calculate_message_length(messages: pd.Series) -> pd.Series:
    """Return the character length of each normalized message."""
    if messages.isna().any():
        raise ValueError("Log messages cannot be missing")
    return messages.astype("string").str.len().astype(int)


def calculate_time_since_previous(timestamps: pd.Series) -> pd.Series:
    """Return chronological gaps in seconds, with zero for the first record."""
    parsed_timestamps = pd.to_datetime(timestamps, errors="coerce")
    if parsed_timestamps.isna().any():
        raise ValueError("Log timestamps must be valid")
    return parsed_timestamps.diff().dt.total_seconds().fillna(0.0)


def _rolling_count(levels: pd.Series, timestamps: pd.Series, target_level: str) -> pd.Series:
    if len(levels) != len(timestamps):
        raise ValueError("Levels and timestamps must have the same length")

    parsed_timestamps = pd.to_datetime(timestamps, errors="coerce")
    if parsed_timestamps.isna().any():
        raise ValueError("Log timestamps must be valid")

    indicator = (levels.astype("string").str.upper() == target_level).astype(int)
    minute = parsed_timestamps.dt.floor("min")
    return (indicator.groupby(minute).cumsum() - indicator).astype(int)


def calculate_rolling_error_counts(
    levels: pd.Series, timestamps: pd.Series
) -> pd.Series:
    """Count preceding ERROR/CRITICAL events in each record's minute."""
    if len(levels) != len(timestamps):
        raise ValueError("Levels and timestamps must have the same length")

    parsed_timestamps = pd.to_datetime(timestamps, errors="coerce")
    if parsed_timestamps.isna().any():
        raise ValueError("Log timestamps must be valid")

    indicator = levels.astype("string").str.upper().isin(ERROR_LEVELS).astype(int)
    minute = parsed_timestamps.dt.floor("min")
    return (indicator.groupby(minute).cumsum() - indicator).astype(int)


def calculate_rolling_warning_counts(
    levels: pd.Series, timestamps: pd.Series
) -> pd.Series:
    """Count preceding WARNING events in each record's minute."""
    return _rolling_count(levels, timestamps, WARNING_LEVEL)


def calculate_service_error_rate(
    services: pd.Series, is_error: pd.Series
) -> pd.Series:
    """Return the full-dataset error rate for each service."""
    if len(services) != len(is_error):
        raise ValueError("Services and error flags must have the same length")
    if services.isna().any():
        raise ValueError("Service names cannot be missing")
    return is_error.astype(int).groupby(services).transform("mean").astype(float)


def engineer_log_features(
    records: pd.DataFrame,
    service_code_map: Mapping[str, int] = SERVICE_CODE_MAP,
) -> pd.DataFrame:
    """Normalize logs and append all eight deterministic model features.

    Input records are normalized and sorted before sequential features are
    calculated. No file is read or written, and no model is loaded or trained.
    """
    features = normalize_log_records(records)
    features["severity"] = encode_severity(features["level"])
    features["is_error"] = features["level"].isin(ERROR_LEVELS).astype(int)
    features["service_code"] = encode_service_names(
        features["service"], service_code_map
    )
    features["message_length"] = calculate_message_length(features["message"])
    features["time_since_previous"] = calculate_time_since_previous(
        features["timestamp"]
    )
    features["errors_in_last_minute"] = calculate_rolling_error_counts(
        features["level"], features["timestamp"]
    )
    features["warnings_in_last_minute"] = calculate_rolling_warning_counts(
        features["level"], features["timestamp"]
    )
    features["service_error_rate"] = calculate_service_error_rate(
        features["service"], features["is_error"]
    )
    return features


def select_model_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return exactly the eight model features in the trained-model order."""
    missing_columns = [
        column for column in FEATURE_COLUMNS if column not in dataframe.columns
    ]
    if missing_columns:
        raise ValueError(
            "Feature data is missing required columns: " + ", ".join(missing_columns)
        )
    return dataframe.loc[:, FEATURE_COLUMNS].copy()


def build_model_feature_frame(
    records: pd.DataFrame,
    service_code_map: Mapping[str, int] = SERVICE_CODE_MAP,
) -> pd.DataFrame:
    """Normalize raw records and return only the eight model input columns."""
    return select_model_features(engineer_log_features(records, service_code_map))
