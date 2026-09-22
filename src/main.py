from preprocessing.log_parser import load_and_process_logs
import pandas as pd


print("AI Log Debugger Pipeline")
print("=========================")


# STEP 1 — Log Parsing
print("\nRunning log parser...")

input_file = "data/raw/application.log"

df = load_and_process_logs(input_file)

print("Log parsing completed!")
print("Logs loaded:", len(df))


# STEP 2 — Save parsed logs
parsed_file = "data/processed/logs.csv"

df.to_csv(parsed_file, index=False)

print("Parsed logs saved:", parsed_file)


# STEP 3 — Data Cleaning
print("\nRunning data cleaning...")

df = pd.read_csv(parsed_file)

df = df.drop_duplicates()
df = df.dropna()

df["service"] = df["service"].str.strip()
df["level"] = df["level"].str.strip()
df["message"] = df["message"].str.strip()

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)

df = df.dropna(subset=["timestamp"])

df = df.sort_values("timestamp").reset_index(drop=True)


cleaned_file = "data/processed/logs_clean.csv"

df.to_csv(cleaned_file, index=False)

print("Data cleaning completed!")
print("Cleaned logs:", len(df))
print("Cleaned file:", cleaned_file)

# STEP 4 — Feature Engineering
print("\nRunning feature engineering...")

feature_columns = [
    "severity",
    "is_error",
    "service_code",
    "message_length",
    "time_since_previous",
    "errors_in_last_minute",
    "warnings_in_last_minute",
    "service_error_rate"
]

# STEP 4 — Feature Engineering
print("\nFeature engineering completed!")

features_file = "data/processed/features.csv"

print("Features saved:", features_file)

# STEP 5 — Anomaly Detection

print("\nRunning anomaly detection...")

import detection.anomaly_detector

print("\nAnomaly detection completed!")
print("Results saved: data/processed/anomaly_results.csv")

# STEP 6 — Incident Correlation

print("\nRunning incident correlation...")

import correlation.incident_correlator

print("\nIncident correlation completed!")
print("Results saved: data/processed/incidents.json")

# STEP 7 — Root Cause Analysis
print("\nRunning root cause analysis...")

import ai.root_cause_analyzer

ai.root_cause_analyzer.analyze_root_cause()

print("\nRoot cause analysis completed!")
print("Results saved: data/processed/root_cause_analysis.json")