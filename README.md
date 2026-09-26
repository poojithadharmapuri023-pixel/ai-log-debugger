# TraceRoot AI

### AI-Powered Incident Intelligence & Root-Cause Analysis

TraceRoot AI is an AI/ML-powered incident intelligence platform that analyzes application logs, detects anomalous events, correlates failures across services, and identifies the most likely root cause of an incident.

It combines **machine-learning anomaly detection**, **rule-based analysis**, **incident correlation**, and a **FastAPI backend** with a dark enterprise-style observability dashboard.

---

## 🚀 What TraceRoot AI Does

TraceRoot AI helps answer three key questions:

> **What went wrong?**
> **Which events are anomalous?**
> **What service most likely caused the incident?**

The platform processes application log events and provides:

* Real-time anomaly prediction
* ML-based anomaly detection
* Rule-based anomaly detection
* Incident analysis
* Cross-service event correlation
* Deterministic root-cause analysis
* Historical event exploration
* Backend health monitoring
* API documentation through Swagger
* Interactive observability dashboard

---

## ✨ Key Features

### 🔍 Anomaly Detection

Analyze an individual event using the trained anomaly detection model.

The detection engine uses features such as:

* Severity
* Error status
* Service code
* Message length
* Time since previous event
* Errors in the last minute
* Warnings in the last minute
* Service error rate

The system provides:

* Final prediction
* ML prediction
* Rule prediction
* Model output
* Detection context

---

### 🧠 Root-Cause Analysis

TraceRoot AI analyzes stored incident evidence and identifies the service most likely responsible for the incident.

The analysis considers:

* Event chronology
* Service-level failures
* Error and warning counts
* Critical events
* First observed problem
* Downstream service failures

For the included sample incident, the analysis identifies:

**database-service**

as the earliest source of the failure chain.

---

### 📋 Event Analyzer

The Event Analyzer provides an interactive view of stored log events.

Users can filter events by:

* Search term
* Service
* Log level
* Anomaly status

The dashboard also supports anomaly-only analysis.

---

### 📊 Incident Intelligence Dashboard

The Overview dashboard provides a high-level operational view containing:

* API status
* ML model status
* Gemini availability
* Active incidents
* Detected anomalies
* Critical events
* Affected services
* Root-cause status

All displayed dashboard metrics are retrieved from the backend rather than hard-coded into the UI.

---

### 🔌 FastAPI Backend

TraceRoot AI exposes a REST API for prediction, analysis, health monitoring, and dashboard data.

Interactive API documentation is available through FastAPI Swagger.

---

## 🏗️ Architecture

```text
                    ┌─────────────────────────┐
                    │     Application Logs    │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Log Preprocessing     │
                    │  Cleaning & Features    │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   ML Anomaly Detection  │
                    │     Isolation Forest    │
                    └────────────┬────────────┘
                                 │
                         ┌───────┴────────┐
                         ▼                ▼
                ┌────────────────┐  ┌───────────────┐
                │ Rule Detection  │  │ ML Prediction │
                └────────┬───────┘  └───────┬───────┘
                         │                  │
                         └────────┬─────────┘
                                  ▼
                    ┌─────────────────────────┐
                    │   Incident Correlation  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Deterministic Root-Cause│
                    │       Analysis          │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │       FastAPI API        │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   TraceRoot AI Dashboard │
                    │      HTML/CSS/JS         │
                    └─────────────────────────┘
```

---

## 🤖 Machine Learning

The anomaly detection component uses an **Isolation Forest** model.

The current model is trained using engineered log-event features and is designed to identify unusual combinations of event characteristics.

### Model

```text
Algorithm: Isolation Forest
Contamination: 0.3
Random State: 42
```

The system also combines ML predictions with deterministic severity-based rules to provide a hybrid anomaly signal.

---

## 🛠️ Tech Stack

### Backend

* Python
* FastAPI
* Pydantic
* Uvicorn

### Machine Learning

* Scikit-learn
* Isolation Forest
* Joblib
* Pandas
* NumPy

### Frontend

* HTML5
* CSS3
* JavaScript
* REST API integration

### Development

* Git
* GitHub
* VS Code
* Swagger / OpenAPI

---

## 📁 Project Structure

```text
traceroot-ai/
│
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
├── ui/
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
├── tests/
│
├── run.py
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## ⚡ Getting Started

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

## 🔗 API Endpoints

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

## 🧪 Example Detection Request

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

## 📈 Sample Incident

The included sample dataset contains:

* **20** analyzed events
* **11** detected anomalies
* **1** critical event
* **4** affected services
* **2** recorded incidents

The primary root cause identified from the stored incident evidence is:

```text
database-service
```

The analysis identifies the database service's earliest problem event before subsequent payment-service and API-gateway failures.

---

## 🖥️ Dashboard Pages

TraceRoot AI includes:

### Overview

High-level incident and system intelligence.

### Detection

Manual event anomaly prediction.

### Root Cause

Evidence-based incident root-cause analysis.

### Event Analyzer

Searchable and filterable event analysis.

### API

Live backend endpoint information and Swagger access.

### System

Backend, ML model, CORS, and artifact health monitoring.

---

## ⚠️ Current Limitations

* The current project uses a sample log dataset.
* The current root-cause explanation is deterministic and evidence-based.
* Gemini-generated narrative output is not currently exposed by the backend dashboard API.
* Production-scale distributed tracing and streaming ingestion are not yet implemented.

---

## 🔮 Future Improvements

Potential future improvements include:

* Real-time log streaming
* Kafka-based ingestion
* Distributed tracing integration
* Larger production datasets
* Advanced incident clustering
* Transformer-based log representations
* LLM-powered investigation summaries
* Automated remediation suggestions
* Dockerized deployment
* Cloud deployment
* Authentication and role-based access
* Monitoring and evaluation dashboards

---

## 🎯 Project Goal

TraceRoot AI was built to explore how machine learning and intelligent incident analysis can reduce the time required to detect, investigate, and understand application failures.

The project focuses on combining **ML detection + deterministic evidence + service correlation** into one operational workflow.

---

## 👩‍💻 Author

**Poojitha Dharmapuri**

B.Tech Computer Science Engineering
Methodist College of Engineering & Technology, Osmania University

GitHub:
https://github.com/poojithadharmapuri023-pixel

LinkedIn:
https://www.linkedin.com/in/poojitha-dharmapuri-648a2b3b7/
