# TraceRoot AI

TraceRoot AI is an AI-assisted log analysis and incident investigation platform that combines machine learning, deterministic evidence, service correlation, and root-cause analysis to help identify application failures faster.

## Features

* Machine-learning-based anomaly detection
* Hybrid ML + rule-based anomaly prediction
* Automated incident detection
* Service-level event correlation
* Evidence-based root-cause analysis
* Interactive monitoring dashboard
* Event search and filtering
* API health monitoring
* ML model health monitoring
* REST API with Swagger/OpenAPI documentation
* Dockerized FastAPI backend
* Comprehensive automated test suite

---

## Architecture

```text
Application Logs
       |
       v
Log Ingestion
       |
       v
Preprocessing
       |
       v
Feature Engineering
       |
       v
ML Anomaly Detection
       |
       +--------------------+
       |                    |
       v                    v
Rule-Based Detection    Incident Correlation
       |                    |
       +---------+----------+
                 |
                 v
        Root-Cause Analysis
                 |
                 v
          FastAPI Backend
                 |
                 v
         TraceRoot Dashboard
```

---

## Machine Learning

TraceRoot AI uses an Isolation Forest model for anomaly detection.

The feature pipeline includes:

* Severity
* Error indicator
* Service code
* Message length
* Time since previous event
* Errors in the last minute
* Warnings in the last minute
* Service error rate

The current sample model uses:

```text
Algorithm: Isolation Forest
Contamination: 0.3
Random State: 42
```

The system also combines ML predictions with severity-based rules to provide hybrid anomaly detection.

---

## Sample Dataset

The included sample dataset contains:

* 20 analyzed log events
* 11 detected anomalies
* 1 critical event
* 4 affected services
* 2 recorded incidents

The primary root cause identified from the stored incident evidence is:

```text
database-service
```

The analysis identifies the database service's earliest problem event before subsequent payment-service and API-gateway failures.

---

## Tech Stack

### Programming

* Python
* SQL

### Machine Learning

* Scikit-learn
* Isolation Forest
* Feature engineering
* Anomaly detection

### Backend

* FastAPI
* Uvicorn
* Pydantic
* REST API
* Swagger / OpenAPI

### Data Processing

* Pandas
* NumPy
* JSON
* CSV

### Frontend

* HTML
* CSS
* JavaScript

### Development & Deployment

* Git
* GitHub
* VS Code
* Docker
* Docker Desktop

---

## Project Structure

```text
traceroot-ai/
|
├── data/
│   ├── raw/
│   └── processed/
│
├── src/
│   ├── analysis/
│   ├── api/
│   ├── correlation/
│   ├── ml/
│   └── processing/
│
├── tests/
│
├── ui/
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
├── Dockerfile
├── .dockerignore
├── requirements.txt
├── run.py
└── README.md
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/poojithadharmapuri023-pixel/traceroot-ai.git
cd traceroot-ai
```

### 2. Create a virtual environment

Windows:

```powershell
python -m venv venv
```

Activate it:

```powershell
venv\Scripts\activate
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Start the backend

```powershell
python -m uvicorn src.api.main:app --reload --port 8000
```

The API will be available at:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

### 5. Start the dashboard

Open another terminal:

```powershell
cd ui
python -m http.server 5500
```

Open:

```text
http://localhost:5500
```

---

## Docker Deployment

### 6. Build the Docker image

```powershell
docker build -t traceroot-ai:latest .
```

### 7. Run the backend container

```powershell
docker run -d --name traceroot-ai-container -p 8000:8000 traceroot-ai:latest
```

Verify the running container:

```powershell
docker ps
```

Check the API health:

```powershell
curl.exe http://localhost:8000/health
```

A healthy response should include:

```json
{
  "status": "healthy",
  "api_running": true,
  "model_available": true,
  "model_loaded": true
}
```

Swagger documentation:

```text
http://localhost:8000/docs
```

The Docker container runs the FastAPI backend on port `8000`.

### 8. Run the dashboard with the Docker backend

The frontend is a static HTML/CSS/JavaScript dashboard and can be served separately:

```powershell
cd ui
python -m http.server 5500
```

Open:

```text
http://localhost:5500
```

The dashboard communicates with the Dockerized FastAPI backend at:

```text
http://localhost:8000
```

To stop the container:

```powershell
docker stop traceroot-ai-container
```

To remove the container:

```powershell
docker rm traceroot-ai-container
```

---

## API Endpoints

| Method | Endpoint                          | Purpose                      |
| ------ | --------------------------------- | ---------------------------- |
| GET    | `/`                               | API information              |
| GET    | `/health`                         | Backend and artifact health  |
| POST   | `/predict`                        | Legacy anomaly prediction    |
| POST   | `/api/v1/predict`                 | Hybrid anomaly prediction    |
| GET    | `/api/v1/anomalies`               | Retrieve analyzed events     |
| GET    | `/api/v1/incidents`               | Retrieve incidents           |
| GET    | `/api/v1/incidents/{incident_id}` | Retrieve an incident         |
| GET    | `/api/v1/root-cause-analysis`     | Retrieve root-cause analysis |
| GET    | `/api/v1/metrics`                 | Retrieve dashboard metrics   |

---

## Example Detection Request

```json
{
  "severity": 2,
  "is_error": 1,
  "service_code": 2,
  "message_length": 45,
  "time_since_previous": 10,
  "errors_in_last_minute": 3,
  "warnings_in_last_minute": 1,
  "service_error_rate": 0.5
}
```

Example response:

```json
{
  "prediction": "Anomaly",
  "ml_prediction": "Anomaly",
  "rule_prediction": "Anomaly"
}
```

---

## Dashboard

TraceRoot AI includes an interactive dashboard with the following modules.

### Overview

Provides a high-level view of:

* System health
* Active incidents
* Detected anomalies
* Critical events
* Affected services
* Root-cause information

### Detection

Allows users to submit event features and perform anomaly prediction using the hybrid detection API.

### Root Cause

Displays evidence-based incident analysis, including:

* Root-cause service
* Confidence
* Timeline
* Affected services
* First problem event
* Supporting evidence

### Event Analyzer

Provides searchable and filterable log event analysis.

### API

Provides access to backend API information and Swagger documentation.

### System

Displays:

* Backend status
* ML model status
* Gemini availability
* CORS status
* Artifact readiness

---

## Current Limitations

* The current project uses a sample log dataset.
* The current root-cause explanation is deterministic and evidence-based.
* Gemini-generated narrative output is not currently exposed by the backend dashboard API.
* Production-scale distributed tracing and streaming ingestion are not yet implemented.
* The current Docker deployment is intended for local/containerized demonstration rather than production hosting.

---

## Future Improvements

Potential future improvements include:

* Real-time log streaming
* Kafka-based ingestion
* Distributed tracing integration
* Larger production datasets
* Advanced incident clustering
* Transformer-based log representations
* LLM-powered investigation summaries
* Automated remediation suggestions
* Cloud deployment
* Authentication and role-based access
* Monitoring and evaluation dashboards

---

## Testing

TraceRoot AI includes automated tests covering:

* API endpoint contracts
* Model behavior
* Integration behavior
* Error handling
* Input validation
* Artifact availability
* Artifact corruption
* Pagination behavior
* Response consistency
* Deterministic predictions
* Health checks

Run the complete test suite with:

```powershell
python -m pytest -q
```

---

## Project Goal

TraceRoot AI was built to explore how machine learning and intelligent incident analysis can reduce the time required to detect, investigate, and understand application failures.

The project combines:

**ML detection + deterministic evidence + service correlation + API-driven investigation**

into a single operational workflow.

---

## Author

**Poojitha Dharmapuri**

B.Tech Computer Science Engineering
Methodist College of Engineering & Technology, Osmania University

GitHub:
https://github.com/poojithadharmapuri023-pixel

LinkedIn:
https://www.linkedin.com/in/poojitha-dharmapuri-648a2b3b7/
