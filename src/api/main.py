from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.ml.constants import ANOMALY_MODEL_OUTPUT
from src.ml.model_service import ModelService, ModelServiceError

app = FastAPI(
    title="AI Log Debugger",
    description="Automated log analysis and root cause detection system",
    version="0.1.0"
)

# The service loads the existing model only when inference is requested.
# Importing or starting the API never trains or writes model artifacts.
model_service = ModelService()


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
        "message": "AI Log Debugger is running!",
        "status": "success"
    }


@app.post("/predict")
def predict(features: LogFeatures):
    try:
        prediction = model_service.predict(features.model_dump())
    except ModelServiceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    if prediction == ANOMALY_MODEL_OUTPUT:
        result = "anomaly"
    else:
        result = "normal"

    return {
        "prediction": result,
        "model_output": int(prediction)
    }
