# AI Log Debugger & Root Cause Analyzer

An AI-assisted incident debugging system that analyzes application logs, detects anomalous events, identifies probable root causes, and generates structured explanations using Google Gemini.

## Overview

Modern applications generate large volumes of logs during failures. Manually investigating these logs can be time-consuming because developers need to determine:

- What went wrong?
- When did the problem begin?
- Which services were affected?
- Which event was likely the initial failure?
- What should be investigated next?

**AI Log Debugger & Root Cause Analyzer** automates several of these steps through a Python-based processing and analysis pipeline.

The system combines:

- Log preprocessing and feature engineering
- Machine-learning-based anomaly detection
- Rule-based anomaly detection
- Incident and event correlation
- Deterministic root-cause analysis
- Google Gemini-based root-cause explanation
- FastAPI REST endpoints
- Docker-based deployment
- Automated API and data-processing tests

## System Workflow

```text
Application Logs
       |
       v
Log Preprocessing
       |
       v
Feature Engineering
       |
       v
Anomaly Detection
   |           |
   |           +--> Rule-based detection
   |
   +--------------> Isolation Forest
       |
       v
Incident / Event Analysis
       |
       v
Deterministic Root-Cause Analysis
       |
       v
Google Gemini Explanation
       |
       v
FastAPI API
       |
       v
Structured Incident Analysis
```

## Key Features

### 1. Log Processing

The system processes application log entries and extracts useful information such as:

- Timestamp
- Log level
- Service
- Message
- Error information
- Warning information

The processed logs are converted into structured data for downstream analysis.

### 2. Feature Engineering

The anomaly detection pipeline generates features including:

```text
severity
is_error
service_code
message_length
time_since_previous
errors_in_last_minute
warnings_in_last_minute
service_error_rate
```

These features are used by the machine-learning model to identify unusual events.

### 3. Anomaly Detection

The project uses **Isolation Forest** for unsupervised anomaly detection.

A hybrid detection approach is also implemented:

```text
Isolation Forest prediction
            +
Severity-based rule
            |
            v
      Final prediction
```

This allows high-severity events to be flagged even when the machine-learning model does not classify them as anomalies.

### 4. Root-Cause Analysis

The system analyzes warning, error, and critical events to determine the service associated with the earliest significant problem.

For the included sample dataset, the deterministic analysis identifies:

```text
Root Cause Service:
database-service
```

The analysis also provides:

- First problem timestamp
- First problem log level
- First problem message
- Service-level event statistics
- Severity scores
- Confidence information
- Reasoning behind the identified root cause

### 5. AI-Assisted Explanation

Google Gemini is used to transform the structured root-cause analysis into an understandable incident explanation.

The generated analysis includes:

- Probable root cause
- Affected services
- Evidence
- Impact
- Recommended investigation steps

The application also includes a deterministic fallback when Gemini is unavailable.

### 6. FastAPI Backend

The application exposes the analysis through REST API endpoints.

Current endpoints include:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | API status |
| GET | `/health` | Health and model status |
| POST | `/predict` | Detect anomaly from log features |
| POST | `/root-cause` | Run root-cause analysis and AI explanation |

FastAPI also provides interactive API documentation through:

```text
/docs
```

and the OpenAPI specification through:

```text
/openapi.json
```

## Example Prediction

A request containing an error event can produce:

```json
{
  "prediction": "Anomaly",
  "severity": 1,
  "ml_prediction": "Anomaly",
  "rule_prediction": "Anomaly",
  "model_output": -1,
  "message": "Prediction generated successfully"
}
```

Where:

```text
-1 = Isolation Forest anomaly
 1 = Isolation Forest normal
```

## Root-Cause Analysis Example

For the included sample logs, the analysis identifies `database-service` as the probable initial source of the incident.

The sequence is approximately:

```text
database-service
    |
    | Database response time increased
    v
payment-service
    |
    | Multiple errors
    v
api-gateway
```

Gemini then produces a structured explanation describing the evidence, affected services, impact, and recommended investigation steps.

## Machine Learning Model

The project uses:

**Algorithm:** Isolation Forest

**Configuration:**

```text
contamination = 0.3
random_state = 42
```

The trained model is stored locally as:

```text
data/processed/isolation_forest_model.joblib
```

The project also stores processed logs, engineered features, anomaly results, incident information, and root-cause analysis artifacts under:

```text
data/processed/
```

## Testing

The project includes automated tests covering the API, preprocessing, feature engineering, validation, and data-layer behavior.

Current test result:

```text
16 passed
1 warning
```

Tests include:

- Health endpoint
- Anomaly prediction
- Normal prediction
- Root-cause endpoint
- Prediction validation
- Pagination and filtering
- Missing artifact handling
- Log parsing
- Malformed log handling
- Severity encoding
- Service encoding
- Message length calculation
- Time-based features
- Rolling error/warning counts
- Service error rate
- Final feature ordering

Run the tests with:

```powershell
python -m pytest -v
```

## Technology Stack

| Technology | Purpose |
|------------|---------|
| Python | Core development |
| Pandas | Log processing and data manipulation |
| NumPy | Numerical operations |
| Scikit-learn | Machine learning and anomaly detection |
| FastAPI | REST API |
| Pydantic | API request validation |
| Joblib | Model persistence |
| Google Gemini API | AI-assisted analysis |
| Pytest | Automated testing |
| Docker | Application containerization |
| Git & GitHub | Version control |

## Project Structure

```text
ai-log-debugger/
|
├── data/
│   ├── raw/
│   │   └── application.log
│   └── processed/
│       ├── logs_clean.csv
│       ├── features.csv
│       ├── anomaly_results.csv
│       ├── incidents.json
│       ├── root_cause_analysis.json
│       └── isolation_forest_model.joblib
|
├── src/
│   ├── ai/
│   │   ├── gemini_service.py
│   │   └── root_cause_analyzer.py
│   ├── analysis/
│   ├── api/
│   │   └── app.py
│   ├── correlation/
│   ├── data/
│   ├── ml/
│   └── main.py
|
├── tests/
│   ├── test_api.py
│   ├── test_api_data_layer.py
│   └── test_preprocessing_features.py
|
├── ui/
|
├── Dockerfile
├── .dockerignore
├── .gitignore
├── requirements.txt
├── run.py
└── README.md
```

## Running Locally

### 1. Clone the repository

```powershell
git clone https://github.com/poojithadharmapuri023-pixel/ai-log-debugger.git
cd ai-log-debugger
```

### 2. Create and activate a virtual environment

```powershell
python -m venv venv
```

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Gemini

Create a `.env` file in the project root:

```text
GEMINI_API_KEY=your_api_key_here
```

Do not commit the `.env` file to GitHub.

### 5. Start the API

```powershell
uvicorn src.api.app:app --reload --port 8000
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

## Running with Docker

Build the Docker image:

```powershell
docker build -t ai-log-debugger .
```

Run the container:

```powershell
docker run -d --name ai-log-debugger-docker -p 8001:8000 --env-file .env ai-log-debugger
```

The API will then be available at:

```text
http://127.0.0.1:8001
```

Health check:

```text
http://127.0.0.1:8001/health
```

## Security

API credentials are kept outside the source code using environment variables.

The project includes:

```text
.env
```

in `.gitignore`, and `.env` is also excluded from the Docker build context through `.dockerignore`.

API keys should never be committed to the repository.

## Current Project Status

### Completed

- [x] Project structure
- [x] Log preprocessing
- [x] Feature engineering
- [x] Isolation Forest anomaly detection
- [x] Hybrid anomaly detection
- [x] Incident/event analysis
- [x] Deterministic root-cause analysis
- [x] Google Gemini integration
- [x] FastAPI backend
- [x] API validation
- [x] Automated tests
- [x] Docker configuration
- [x] Local Docker deployment
- [x] Environment-variable based API key configuration

### Remaining / Future Work

- [ ] Interactive dashboard
- [ ] Additional log datasets and failure scenarios
- [ ] More extensive model evaluation
- [ ] CI/CD pipeline
- [ ] Cloud deployment
- [ ] Production-scale log ingestion
- [ ] Additional observability integrations

## Future Vision

The long-term goal is to evolve the project into an AI-assisted incident investigation platform capable of processing application logs and producing a structured incident report containing:

```text
Detected anomalies
       +
Related events
       +
Affected services
       +
Probable root cause
       +
Evidence
       +
Impact
       +
Recommended investigation steps
```

The project is intended as a practical exploration of **Artificial Intelligence, Machine Learning, backend engineering, and automated software debugging**.

## Author

**Poojitha Dharmapuri**

B.Tech Computer Science and Engineering  
Methodist College of Engineering & Technology  
Osmania University