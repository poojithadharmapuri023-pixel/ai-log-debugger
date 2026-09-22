"""Pure normalization helpers for parsed log records."""

from __future__ import annotations

import pandas as pd

from src.ml.constants import SEVERITY_CODE_MAP
from src.preprocessing.log_parser import LOG_RECORD_COLUMNS


def normalize_log_records(records: pd.DataFrame) -> pd.DataFrame:
    """Validate, clean, de-duplicate, and chronologically sort log records.

    A DataFrame missing any required log column raises ``ValueError``. Rows
    with invalid timestamps, blank text values, or unsupported levels are
    removed. The input is never modified.
    """
    if not isinstance(records, pd.DataFrame):
        raise TypeError("records must be a pandas DataFrame")

    missing_columns = [
        column for column in LOG_RECORD_COLUMNS if column not in records.columns
    ]
    if missing_columns:
        raise ValueError(
            "Log records are missing required columns: " + ", ".join(missing_columns)
        )

    normalized = records.loc[:, LOG_RECORD_COLUMNS].copy()
    normalized["timestamp"] = pd.to_datetime(
        normalized["timestamp"], errors="coerce"
    )
    for column in ("service", "level", "message"):
        normalized[column] = normalized[column].astype("string").str.strip()

    normalized["level"] = normalized["level"].str.upper()
    normalized = normalized.replace("", pd.NA)
    normalized = normalized.dropna(subset=LOG_RECORD_COLUMNS)
    normalized = normalized[
        normalized["level"].isin(SEVERITY_CODE_MAP)
    ].drop_duplicates()

    return normalized.sort_values("timestamp", kind="mergesort").reset_index(
        drop=True
    )
