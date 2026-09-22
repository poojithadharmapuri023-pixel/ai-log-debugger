"""Pure helpers for parsing the project's pipe-delimited application logs."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from src.ml.constants import SEVERITY_CODE_MAP


LOG_RECORD_COLUMNS = ["timestamp", "service", "level", "message"]


def parse_log_line(line: str) -> dict[str, object] | None:
    """Parse one ``timestamp | service | level | message`` log line.

    Malformed lines return ``None`` so callers can skip them without stopping
    an ingestion batch. Valid records keep a parsed pandas timestamp.
    """
    if not isinstance(line, str):
        return None

    parts = line.strip().split(" | ", 3)
    if len(parts) != 4:
        return None

    timestamp_value, service, level, message = parts
    service = service.strip()
    level = level.strip().upper()
    message = message.strip()

    if not service or not message or level not in SEVERITY_CODE_MAP:
        return None

    try:
        timestamp = pd.to_datetime(timestamp_value, errors="raise")
    except (TypeError, ValueError):
        return None

    return {
        "timestamp": timestamp,
        "service": service,
        "level": level,
        "message": message,
    }


def parse_log_lines(lines: Iterable[str]) -> pd.DataFrame:
    """Parse an iterable of log lines into a schema-stable DataFrame."""
    records = [record for line in lines if (record := parse_log_line(line))]
    return pd.DataFrame(records, columns=LOG_RECORD_COLUMNS)


def load_and_process_logs(file_path: Path | str) -> pd.DataFrame:
    """Read and parse a raw application log file without writing artifacts."""
    with Path(file_path).open(encoding="utf-8") as file:
        return parse_log_lines(file)
