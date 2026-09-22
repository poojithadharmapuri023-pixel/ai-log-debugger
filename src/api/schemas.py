"""Explicit request and response schemas for the FastAPI application."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LogFeatures(BaseModel):
    """The eight engineered features required by the stored model."""

    severity: int = Field(ge=0, le=3, description="INFO=0, WARNING=1, ERROR=2, CRITICAL=3.")
    is_error: int = Field(ge=0, le=1, description="1 for ERROR/CRITICAL, otherwise 0.")
    service_code: int = Field(ge=0, description="Service code from the training feature mapping.")
    message_length: int = Field(ge=0, description="Character length of the log message.")
    time_since_previous: float = Field(ge=0, description="Seconds since the prior log event.")
    errors_in_last_minute: int = Field(ge=0, description="Prior error count in this log minute.")
    warnings_in_last_minute: int = Field(ge=0, description="Prior warning count in this log minute.")
    service_error_rate: float = Field(ge=0, le=1, description="Observed service error rate.")


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


class ErrorResponse(BaseModel):
    detail: str


class ArtifactReadiness(BaseModel):
    available: bool
    readable: bool


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    api_running: bool = True
    model_available: bool
    model_loadable: bool
    model_loaded: bool
    dashboard_artifacts: dict[str, ArtifactReadiness]


class AnomalyRecord(BaseModel):
    """One row from ``anomaly_results.csv``; extra compatible columns remain available."""

    model_config = ConfigDict(extra="allow")

    timestamp: str
    service: str
    level: str
    message: str
    severity: int
    is_error: int
    service_code: int
    message_length: int
    time_since_previous: float
    errors_in_last_minute: int
    warnings_in_last_minute: int
    service_error_rate: float
    anomaly: int
    actual_anomaly: int | None = None
    predicted_anomaly: int | None = None
    rule_anomaly: int | None = None
    final_anomaly: int | None = None


class AnomalyResultsResponse(BaseModel):
    """Paginated anomaly results with Phase 2 fields retained for compatibility."""

    items: list[AnomalyRecord]
    page: int
    page_size: int
    total: int
    pages: int
    offset: int
    limit: int
    results: list[AnomalyRecord]


class IncidentEvent(BaseModel):
    timestamp: str
    service: str
    level: str
    message: str


class RootCauseSummary(BaseModel):
    root_cause_service: str
    confidence: str | None = None
    first_problem_time: str | None = None
    first_problem_level: str | None = None
    first_problem_message: str | None = None
    reason: str | None = None


class IncidentRecord(BaseModel):
    incident_id: int
    severity: str
    services: list[str]
    event_count: int
    events: list[IncidentEvent]
    summary: str | None = None
    affected_services: list[str] = Field(default_factory=list)
    status: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    related_anomaly_count: int = 0
    root_cause: RootCauseSummary | None = None


class IncidentsResponse(BaseModel):
    total: int
    items: list[IncidentRecord]
    incidents: list[IncidentRecord]


class RootCauseAnalysis(BaseModel):
    model_config = ConfigDict(extra="allow")

    root_cause_service: str
    confidence: str | None = None
    first_problem_time: str | None = None
    first_problem_level: str | None = None
    first_problem_message: str | None = None
    reason: str | None = None
    service_scores: dict[str, dict[str, int | str]] = Field(default_factory=dict)


class RootCauseAnalysisResponse(BaseModel):
    total: int
    items: list[RootCauseAnalysis]
    analysis: RootCauseAnalysis


class MetricsResponse(BaseModel):
    """Counts derived from stored sample artifacts, not model evaluation metrics."""

    total_logs: int
    ml_anomaly_count: int
    hybrid_anomaly_count: int
    normal_record_count: int
    anomaly_percentage: float
    incident_count: int
    logs_by_service: dict[str, int]
    logs_by_level: dict[str, int]
    anomalies_by_service: dict[str, int]
    anomalies_by_level: dict[str, int]
    root_cause_service: str | None
    data_scope: str
