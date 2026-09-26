
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.ai.gemini_service import GeminiService
from src.ai.root_cause_analyzer import analyze_root_cause


BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = BASE_DIR / "data" / "processed" / "isolation_forest_model.joblib"


app = FastAPI(
    title="AI Log Debugger API",
    description="API for anomaly detection and AI-powered root-cause analysis.",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "Service",
            "description": "Health and service readiness endpoints.",
        },
        {
            "name": "Predictions",
            "description": "Machine-learning anomaly prediction endpoints.",
        },
        {
            "name": "Analysis results",
            "description": (
                "Stored anomaly, incident, root-cause, and metrics data."
            ),
        },
    ],
)

model = joblib.load(MODEL_PATH)
gemini_service = GeminiService()


class LogFeatures(BaseModel):
    severity: int
    is_error: int
    service_code: int
    message_length: int
    time_since_previous: float
    errors_in_last_minute: int
    warnings_in_last_minute: int
    service_error_rate: float


@app.get("/")
def home():
    return {
        "message": "AI Log Debugger API is running",
        "status": "success",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model_loaded": True,
        "gemini_available": gemini_service.available,
    }


@app.post("/predict")
def predict(log: LogFeatures):
    input_data = pd.DataFrame([log.model_dump()])

    feature_columns = [
        "severity",
        "is_error",
        "service_code",
        "message_length",
        "time_since_previous",
        "errors_in_last_minute",
        "warnings_in_last_minute",
        "service_error_rate",
    ]

    try:
        prediction_value = model.predict(
            input_data[feature_columns]
        )[0]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ML prediction failed: {str(e)}",
        )

    ml_anomaly = int(prediction_value == -1)
    rule_anomaly = int(log.severity >= 1)
    final_anomaly = int(
        ml_anomaly == 1 or rule_anomaly == 1
    )

    prediction = "Anomaly" if final_anomaly else "Normal"

    return {
        "prediction": prediction,
        "severity": log.severity,
        "ml_prediction": "Anomaly" if ml_anomaly else "Normal",
        "rule_prediction": "Anomaly" if rule_anomaly else "Normal",
        "model_output": int(prediction_value),
        "message": "Prediction generated successfully",
    }


@app.post("/root-cause")
def root_cause():
    try:
        deterministic_analysis = analyze_root_cause()

        gemini_analysis = gemini_service.explain_root_cause(
            deterministic_analysis
        )

        return {
            "deterministic_analysis": deterministic_analysis,
            "ai_analysis": gemini_analysis,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Root-cause analysis failed: {str(e)}",
        )
