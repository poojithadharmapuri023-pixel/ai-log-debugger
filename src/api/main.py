"""FastAPI application for read-only log-analysis inference and results."""

from __future__ import annotations

import os
from collections import Counter

from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.artifact_service import (
    ArtifactNotFoundError,
    ArtifactReadError,
    read_anomaly_results,
    read_incidents,
    read_root_cause_analysis,
)
from src.api.schemas import (
    AnomalyResultsResponse,
    HealthResponse,
    HybridPredictionResponse,
    IncidentsResponse,
    LegacyPredictionResponse,
    LogFeatures,
    MetricsResponse,
    RootCauseAnalysisResponse,
)
from src.ml.constants import ANOMALY_MODEL_OUTPUT, MODEL_FILE
from src.ml.model_service import ModelService, ModelServiceError


def _cors_origins() -> list[str]:
    """Return configured dashboard origins, with safe local-development defaults."""
    configured_origins = os.getenv("CORS_ORIGINS")
    if configured_origins:
        return [
            origin.strip() for origin in configured_origins.split(",") if origin.strip()
        ]

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


app = FastAPI(
    title="AI Log Debugger",
    description=(
        "Read-only log anomaly prediction and processed incident-analysis API. "
        "The API never retrains the model or regenerates processed artifacts."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# The service loads the existing model only when inference is requested.
# Importing or starting the API never trains or writes model artifacts.
model_service = ModelService()


@app.exception_handler(ArtifactNotFoundError)
async def artifact_not_found_handler(
    _request: Request, error: ArtifactNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(ArtifactReadError)
async def artifact_read_error_handler(
    _request: Request, error: ArtifactReadError
) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(error)})


def _model_prediction(features: LogFeatures) -> int:
    try:
        return model_service.predict(features.model_dump())
    except ModelServiceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


def _is_ml_anomaly(record: dict) -> bool:
    if "predicted_anomaly" in record:
        return record["predicted_anomaly"] in (1, 1.0, "1", True)
    return record.get("anomaly") in (ANOMALY_MODEL_OUTPUT, "-1")


def _is_hybrid_anomaly(record: dict) -> bool:
    if "final_anomaly" in record:
        return record["final_anomaly"] in (1, 1.0, "1", True)
    return _is_ml_anomaly(record)


@app.get("/", tags=["Service"], summary="API home")
def home() -> dict[str, str]:
    return {
        "message": "AI Log Debugger is running!",
        "status": "success",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Service"],
    summary="Check API and trained-model availability",
)
def health() -> HealthResponse:
    """Report readiness without loading, training, or modifying the model."""
    if not MODEL_FILE.is_file():
        raise HTTPException(status_code=503, detail="Trained model artifact is unavailable")

    return HealthResponse(
        status="healthy",
        model_available=True,
        model_loaded=model_service.is_loaded,
    )


@app.post(
    "/predict",
    response_model=LegacyPredictionResponse,
    tags=["Predictions"],
    summary="Predict a single anomaly (legacy-compatible)",
    description=(
        "Preserves the original eight-feature request and two-field response "
        "contract. Historical context must be supplied by the caller."
    ),
)
def predict(features: LogFeatures) -> LegacyPredictionResponse:
    """Return the raw Isolation Forest classification for a feature record."""
    prediction = _model_prediction(features)
    result = "anomaly" if prediction == ANOMALY_MODEL_OUTPUT else "normal"
    return LegacyPredictionResponse(prediction=result, model_output=prediction)


@app.post(
    "/api/v1/predict",
    response_model=HybridPredictionResponse,
    tags=["Predictions"],
    summary="Predict an anomaly using ML and the project severity rule",
    description=(
        "Uses the stored Isolation Forest result together with the existing "
        "rule that treats WARNING, ERROR, and CRITICAL (severity >= 1) as "
        "anomalies. The caller must explicitly provide all historical-context "
        "features; this endpoint does not derive or invent them."
    ),
)
def predict_hybrid(features: LogFeatures) -> HybridPredictionResponse:
    """Return the FastAPI replacement for the Flask hybrid prediction behavior."""
    model_output = _model_prediction(features)
    ml_anomaly = model_output == ANOMALY_MODEL_OUTPUT
    rule_anomaly = features.severity >= 1
    final_anomaly = ml_anomaly or rule_anomaly

    return HybridPredictionResponse(
        prediction="Anomaly" if final_anomaly else "Normal",
        severity=features.severity,
        ml_prediction="Anomaly" if ml_anomaly else "Normal",
        rule_prediction="Anomaly" if rule_anomaly else "Normal",
        message="Prediction generated successfully",
        context_note=(
            "Historical-context features were supplied by the caller; "
            "the API did not calculate or infer them."
        ),
    )


@app.get(
    "/api/v1/anomalies",
    response_model=AnomalyResultsResponse,
    tags=["Analysis results"],
    summary="List stored anomaly results",
    description="Reads the existing anomaly_results.csv artifact without changing it.",
)
def list_anomalies(
    offset: int = Query(0, ge=0, description="Number of matching records to skip."),
    limit: int = Query(50, ge=1, le=500, description="Maximum matching records to return."),
    service: str | None = Query(None, min_length=1, description="Exact service filter."),
    level: str | None = Query(None, min_length=1, description="Exact log-level filter."),
    anomaly_only: bool = Query(False, description="Return only final hybrid anomalies."),
) -> AnomalyResultsResponse:
    records = read_anomaly_results()
    if service is not None:
        records = [record for record in records if record.get("service") == service]
    if level is not None:
        records = [record for record in records if record.get("level") == level]
    if anomaly_only:
        records = [record for record in records if _is_hybrid_anomaly(record)]

    return AnomalyResultsResponse(
        total=len(records),
        offset=offset,
        limit=limit,
        results=records[offset : offset + limit],
    )


@app.get(
    "/api/v1/incidents",
    response_model=IncidentsResponse,
    tags=["Analysis results"],
    summary="List stored correlated incidents",
    description="Reads the existing incidents.json artifact without changing it.",
)
def list_incidents() -> IncidentsResponse:
    incidents = read_incidents()
    return IncidentsResponse(total=len(incidents), incidents=incidents)


@app.get(
    "/api/v1/incidents/{incident_id}",
    tags=["Analysis results"],
    summary="Get one stored correlated incident",
    description="Reads a single incident from the existing incidents.json artifact.",
)
def get_incident(incident_id: int = Path(..., gt=0)) -> dict:
    incidents = read_incidents()
    incident = next(
        (
            item
            for item in incidents
            if item.get("incident_id") == incident_id
        ),
        None,
    )
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} was not found")
    return incident


@app.get(
    "/api/v1/root-cause-analysis",
    response_model=RootCauseAnalysisResponse,
    tags=["Analysis results"],
    summary="Get the stored root-cause analysis",
    description="Reads the existing root_cause_analysis.json artifact without changing it.",
)
def get_root_cause_analysis() -> RootCauseAnalysisResponse:
    return RootCauseAnalysisResponse(analysis=read_root_cause_analysis())


@app.get(
    "/api/v1/metrics",
    response_model=MetricsResponse,
    tags=["Analysis results"],
    summary="Summarize stored analysis artifacts",
    description=(
        "Calculates summary counts from existing processed artifacts. It does "
        "not retrain the model or regenerate analysis results."
    ),
)
def get_metrics() -> MetricsResponse:
    records = read_anomaly_results()
    incidents = read_incidents()
    root_cause = read_root_cause_analysis()

    service_counts = Counter(
        str(record["service"]) for record in records if record.get("service") is not None
    )
    level_counts = Counter(
        str(record["level"]) for record in records if record.get("level") is not None
    )

    return MetricsResponse(
        total_logs=len(records),
        ml_anomaly_count=sum(_is_ml_anomaly(record) for record in records),
        hybrid_anomaly_count=sum(_is_hybrid_anomaly(record) for record in records),
        incident_count=len(incidents),
        logs_by_service=dict(service_counts),
        logs_by_level=dict(level_counts),
        root_cause_service=root_cause.get("root_cause_service"),
    )
