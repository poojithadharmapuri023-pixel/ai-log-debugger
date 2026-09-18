"""Pydantic request and response schemas for the FastAPI application."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LogFeatures(BaseModel):
    """Engineered features required by the trained Isolation Forest model.

    Historical/context features must be computed by the caller from actual log
    history. The prediction endpoints never invent rolling values.
    """

    severity: int = Field(ge=0, le=3, description="INFO=0, WARNING=1, ERROR=2, CRITICAL=3.")
    is_error: int = Field(ge=0, le=1, description="1 for ERROR/CRITICAL, otherwise 0.")
    service_code: int = Field(ge=0, description="Service code from the training feature mapping.")
    message_length: int = Field(ge=0, description="Character length of the log message.")
    time_since_previous: float = Field(
        ge=0,
        description="Seconds since the prior log event; must be supplied from real history.",
    )
    errors_in_last_minute: int = Field(
        ge=0,
        description="Prior error count in this log minute; must be supplied from real history.",
    )
    warnings_in_last_minute: int = Field(
        ge=0,
        description="Prior warning count in this log minute; must be supplied from real history.",
    )
    service_error_rate: float = Field(
        ge=0,
        le=1,
        description="Observed error rate for the service; must be supplied from real history.",
    )


class LegacyPredictionResponse(BaseModel):
    prediction: Literal["anomaly", "normal"]
    model_output: Literal[-1, 1]


class HybridPredictionResponse(BaseModel):
    prediction: Literal["Anomaly", "Normal"]
    severity: int
    ml_prediction: Literal["Anomaly", "Normal"]
    rule_prediction: Literal["Anomaly", "Normal"]
    message: str
    context_note: str


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    model_available: bool
    model_loaded: bool


class AnomalyResultsResponse(BaseModel):
    total: int
    offset: int
    limit: int
    results: list[dict[str, Any]]


class IncidentsResponse(BaseModel):
    total: int
    incidents: list[dict[str, Any]]


class RootCauseAnalysisResponse(BaseModel):
    analysis: dict[str, Any]


class MetricsResponse(BaseModel):
    total_logs: int
    ml_anomaly_count: int
    hybrid_anomaly_count: int
    incident_count: int
    logs_by_service: dict[str, int]
    logs_by_level: dict[str, int]
    root_cause_service: str | None
