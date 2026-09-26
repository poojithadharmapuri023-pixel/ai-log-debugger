
from __future__ import annotations
from src.ai.gemini_service import GeminiService
import math
import os
from collections import Counter
from typing import Any

from fastapi import FastAPI, HTTPException, Path, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.api.artifact_service import ArtifactNotFoundError, ArtifactReadError, ArtifactService
from src.api.schemas import (
    AnomalyRecord,
    AnomalyResultsResponse,
    ArtifactReadiness,
    ErrorResponse,
    HealthResponse,
    HybridPredictionResponse,
    IncidentRecord,
    IncidentsResponse,
    LegacyPredictionResponse,
    LogFeatures,
    MetricsResponse,
    RootCauseAnalysis,
    RootCauseAnalysisResponse,
    RootCauseSummary,
)
from src.ml.constants import ANOMALY_MODEL_OUTPUT, MODEL_FILE
from src.ml.model_service import ModelService, ModelServiceError


def _cors_origins() -> list[str]:
    configured_origins = os.getenv("CORS_ORIGINS")

    if configured_origins:
        return [
            item.strip()
            for item in configured_origins.split(",")
            if item.strip()
        ]

    return [
        # Frontend running with Python HTTP server
        "http://localhost:5500",
        "http://127.0.0.1:5500",

        # Existing development origins
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


app = FastAPI(
    title="TraceRoot AI API",
    description=(
        "AI-powered log anomaly detection and root-cause analysis API "
        "for investigating service incidents and operational failures."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Allow the TraceRoot AI frontend to communicate with the FastAPI backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# These services only read existing artifacts.
# Starting the API never trains a model or regenerates analysis outputs.
model_service = ModelService()
artifact_service = ArtifactService()
gemini_service = GeminiService()

@app.exception_handler(ArtifactNotFoundError)
async def artifact_not_found_handler(
    _request: Request,
    error: ArtifactNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": str(error)},
    )


@app.exception_handler(ArtifactReadError)
async def artifact_read_error_handler(
    _request: Request,
    error: ArtifactReadError,
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": str(error)},
    )


def _model_prediction(features: LogFeatures) -> int:
    try:
        return model_service.predict(features.model_dump())

    except ModelServiceError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unexpected error while generating model prediction",
        ) from error


def _is_ml_anomaly(record: dict[str, Any]) -> bool:
    if "predicted_anomaly" in record:
        return record["predicted_anomaly"] in (
            1,
            1.0,
            "1",
            True,
        )

    return record.get("anomaly") in (
        ANOMALY_MODEL_OUTPUT,
        "-1",
    )


def _is_hybrid_anomaly(record: dict[str, Any]) -> bool:
    if "final_anomaly" in record:
        return record["final_anomaly"] in (
            1,
            1.0,
            "1",
            True,
        )

    return _is_ml_anomaly(record)


def _validated_anomalies() -> list[dict[str, Any]]:
    records = [
        record
        for _, record in sorted(
            enumerate(artifact_service.read_anomaly_results()),
            key=lambda item: (
                str(item[1].get("timestamp", "")),
                str(item[1].get("service", "")),
                str(item[1].get("level", "")),
                str(item[1].get("message", "")),
                item[0],
            ),
        )
    ]

    try:
        for record in records:
            AnomalyRecord.model_validate(record)

    except ValidationError as error:
        raise ArtifactReadError(
            "Anomaly results artifact has an invalid record"
        ) from error

    return records


def _root_summary(raw_analysis: dict[str, Any]) -> RootCauseSummary:
    try:
        return RootCauseSummary.model_validate(raw_analysis)

    except ValidationError as error:
        raise ArtifactReadError(
            "Root-cause analysis artifact has an invalid structure"
        ) from error


def _event_matches_anomaly(
    event: dict[str, Any],
    record: dict[str, Any],
) -> bool:
    return all(
        str(event.get(key)) == str(record.get(key))
        for key in (
            "timestamp",
            "service",
            "level",
            "message",
        )
    )


def _incident_records(
    incidents: list[dict[str, Any]],
    anomalies: list[dict[str, Any]],
    root_cause: dict[str, Any],
) -> list[IncidentRecord]:

    root_summary = _root_summary(root_cause)

    prepared: list[IncidentRecord] = []

    try:
        for incident in sorted(
            incidents,
            key=lambda item: int(item.get("incident_id", 0)),
        ):
            events = incident.get("events", [])
            services = incident.get("services", [])

            timestamps = sorted(
                str(event["timestamp"])
                for event in events
                if "timestamp" in event
            )

            related_anomalies = sum(
                _is_hybrid_anomaly(record)
                and any(
                    _event_matches_anomaly(event, record)
                    for event in events
                )
                for record in anomalies
            )

            prepared.append(
                IncidentRecord.model_validate(
                    {
                        **incident,
                        "summary": None,
                        "affected_services": services,
                        "status": None,
                        "started_at": timestamps[0] if timestamps else None,
                        "ended_at": timestamps[-1] if timestamps else None,
                        "related_anomaly_count": related_anomalies,
                        "root_cause": (
                            root_summary
                            if root_summary.root_cause_service in services
                            else None
                        ),
                    }
                )
            )

    except (
        TypeError,
        ValueError,
        ValidationError,
    ) as error:
        raise ArtifactReadError(
            "Incidents artifact has an invalid incident record"
        ) from error

    return prepared


@app.get(
    "/",
    tags=["Service"],
    summary="API home",
)
def home() -> dict[str, str]:
    return {
        "message": "AI Log Debugger is running!",
        "status": "success",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Service"],
    summary="Check API, model, and dashboard-artifact readiness",
    responses={
        503: {
            "model": ErrorResponse,
            "description": "A dependency is unavailable.",
        }
    },
)
def health(response: Response) -> HealthResponse:
    """Load-check the stored model and parse-check required read-only artifacts."""

    model_available = MODEL_FILE.is_file()
    model_loadable = False

    if model_available:
        try:
            model_service.load_model()
            model_loadable = True
        except ModelServiceError:
            pass

    artifacts = {
        name: ArtifactReadiness(
            available=available,
            readable=readable,
        )
        for name, (available, readable)
        in artifact_service.readiness().items()
    }

    healthy = (
        model_available
        and model_loadable
        and all(
            item.available and item.readable
            for item in artifacts.values()
        )
    )

    if not healthy:
        response.status_code = 503

    return HealthResponse(
    status="healthy" if healthy else "degraded",
    model_available=model_available,
    model_loadable=model_loadable,
    model_loaded=model_service.is_loaded,
    gemini_available=gemini_service.available,
    dashboard_artifacts=artifacts,
)

@app.post(
    "/predict",
    response_model=LegacyPredictionResponse,
    tags=["Predictions"],
    summary="Predict a single anomaly (legacy-compatible)",
    description=(
        "Preserves the original eight-feature request "
        "and two-field response contract."
    ),
)
def predict(features: LogFeatures) -> LegacyPredictionResponse:
    output = _model_prediction(features)

    return LegacyPredictionResponse(
        prediction=(
            "anomaly"
            if output == ANOMALY_MODEL_OUTPUT
            else "normal"
        ),
        model_output=output,
    )


@app.post(
    "/api/v1/predict",
    response_model=HybridPredictionResponse,
    tags=["Predictions"],
    summary="Predict using the stored model and existing severity rule",
)
def predict_hybrid(
    features: LogFeatures,
) -> HybridPredictionResponse:

    output = _model_prediction(features)

    ml_anomaly = output == ANOMALY_MODEL_OUTPUT
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
    summary="List stored anomaly results with deterministic pagination and filters",
    description=(
        "Reads anomaly_results.csv only; "
        "it never runs model inference or changes the artifact."
    ),
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def list_anomalies(
    page: int = Query(
        1,
        ge=1,
        description="One-based page number.",
    ),
    page_size: int = Query(
        20,
        ge=1,
        le=500,
        description="Records per page.",
    ),
    service: str | None = Query(
        None,
        min_length=1,
        description="Exact service name.",
    ),
    level: str | None = Query(
        None,
        min_length=1,
        description="Exact log level.",
    ),
    anomaly_only: bool = Query(
        False,
        description="Return only final hybrid anomalies.",
    ),
    search: str | None = Query(
        None,
        min_length=1,
        description=(
            "Case-insensitive text search across message, "
            "service, and level."
        ),
    ),
    offset: int | None = Query(
        None,
        ge=0,
        description="Deprecated Phase 2 offset; overrides page when supplied.",
    ),
    limit: int | None = Query(
        None,
        ge=1,
        le=500,
        description="Deprecated Phase 2 limit; overrides page_size when supplied.",
    ),
) -> AnomalyResultsResponse:

    records = _validated_anomalies()

    if service is not None:
        records = [
            record
            for record in records
            if record.get("service") == service
        ]

    if level is not None:
        records = [
            record
            for record in records
            if record.get("level") == level
        ]

    if anomaly_only:
        records = [
            record
            for record in records
            if _is_hybrid_anomaly(record)
        ]

    if search is not None:
        needle = search.casefold()

        records = [
            record
            for record in records
            if needle
            in " ".join(
                str(record.get(key, ""))
                for key in (
                    "message",
                    "service",
                    "level",
                )
            ).casefold()
        ]

    effective_limit = (
        limit
        if limit is not None
        else page_size
    )

    effective_offset = (
        offset
        if offset is not None
        else (page - 1) * effective_limit
    )

    items = records[
        effective_offset:
        effective_offset + effective_limit
    ]

    return AnomalyResultsResponse(
        items=items,
        page=(effective_offset // effective_limit) + 1,
        page_size=effective_limit,
        total=len(records),
        pages=(
            math.ceil(len(records) / effective_limit)
            if records
            else 0
        ),
        offset=effective_offset,
        limit=effective_limit,
        results=items,
    )


@app.get(
    "/api/v1/incidents",
    response_model=IncidentsResponse,
    tags=["Analysis results"],
    summary="List stored correlated incidents with dashboard detail fields",
)
def list_incidents() -> IncidentsResponse:

    records = _incident_records(
        artifact_service.read_incidents(),
        _validated_anomalies(),
        artifact_service.read_root_cause_analysis(),
    )

    return IncidentsResponse(
        total=len(records),
        items=records,
        incidents=records,
    )


@app.get(
    "/api/v1/incidents/{incident_id}",
    response_model=IncidentRecord,
    tags=["Analysis results"],
    summary="Get one stored correlated incident",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Incident ID was not found.",
        }
    },
)
def get_incident(
    incident_id: int = Path(..., gt=0),
) -> IncidentRecord:

    records = _incident_records(
        artifact_service.read_incidents(),
        _validated_anomalies(),
        artifact_service.read_root_cause_analysis(),
    )

    incident = next(
        (
            record
            for record in records
            if record.incident_id == incident_id
        ),
        None,
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail=f"Incident {incident_id} was not found",
        )

    return incident


@app.get(
    "/api/v1/root-cause-analysis",
    response_model=RootCauseAnalysisResponse,
    tags=["Analysis results"],
    summary="Get structured stored root-cause analysis",
    description=(
        "Returns a one-item collection today, ready for future "
        "per-incident analysis without changing the collection field."
    ),
)
def get_root_cause_analysis() -> RootCauseAnalysisResponse:

    try:
        analysis = RootCauseAnalysis.model_validate(
            artifact_service.read_root_cause_analysis()
        )

    except ValidationError as error:
        raise ArtifactReadError(
            "Root-cause analysis artifact has an invalid structure"
        ) from error

    return RootCauseAnalysisResponse(
        total=1,
        items=[analysis],
        analysis=analysis,
    )


@app.get(
    "/api/v1/metrics",
    response_model=MetricsResponse,
    tags=["Analysis results"],
    summary="Summarize stored dashboard artifacts",
    description=(
        "All counts are derived from stored sample artifacts; "
        "no model evaluation metrics are manufactured."
    ),
)
def get_metrics() -> MetricsResponse:

    records = _validated_anomalies()

    hybrid_records = [
        record
        for record in records
        if _is_hybrid_anomaly(record)
    ]

    def counts(
        rows: list[dict[str, Any]],
        key: str,
    ) -> dict[str, int]:
        return dict(
            sorted(
                Counter(
                    str(row[key])
                    for row in rows
                    if row.get(key) is not None
                ).items()
            )
        )

    total = len(records)
    hybrid_count = len(hybrid_records)

    return MetricsResponse(
        total_logs=total,
        ml_anomaly_count=sum(
            _is_ml_anomaly(record)
            for record in records
        ),
        hybrid_anomaly_count=hybrid_count,
        normal_record_count=total - hybrid_count,
        anomaly_percentage=round(
            (hybrid_count / total * 100)
            if total
            else 0.0,
            2,
        ),
        incident_count=len(
            artifact_service.read_incidents()
        ),
        logs_by_service=counts(
            records,
            "service",
        ),
        logs_by_level=counts(
            records,
            "level",
        ),
        anomalies_by_service=counts(
            hybrid_records,
            "service",
        ),
        anomalies_by_level=counts(
            hybrid_records,
            "level",
        ),
        root_cause_service=_root_summary(
            artifact_service.read_root_cause_analysis()
        ).root_cause_service,
        data_scope=(
            "Counts are derived from the stored "
            "anomaly_results.csv sample artifact, "
            "not model evaluation metrics."
        ),
    )
