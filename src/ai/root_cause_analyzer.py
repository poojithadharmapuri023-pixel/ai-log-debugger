
import json
from pathlib import Path

import pandas as pd


INPUT_FILE = Path("data/processed/logs_clean.csv")
OUTPUT_FILE = Path("data/processed/root_cause_analysis.json")


def analyze_root_cause_from_dataframe(df: pd.DataFrame) -> dict:
    """Run deterministic root-cause analysis without writing files."""

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    problem_logs = df[
        df["level"].isin(["WARNING", "ERROR", "CRITICAL"])
    ].copy()

    problem_logs = problem_logs.sort_values("timestamp")

    if problem_logs.empty:
        return {
            "root_cause_service": None,
            "confidence": "Low",
            "first_problem_time": None,
            "first_problem_level": None,
            "first_problem_message": None,
            "reason": "No problematic events were found.",
            "service_scores": {},
        }

    service_scores = {}

    for service in problem_logs["service"].unique():
        service_logs = problem_logs[
            problem_logs["service"] == service
        ]

        warnings = int((service_logs["level"] == "WARNING").sum())
        errors = int((service_logs["level"] == "ERROR").sum())
        criticals = int((service_logs["level"] == "CRITICAL").sum())

        severity_score = (
            warnings * 1
            + errors * 2
            + criticals * 3
        )

        first_problem_time = service_logs["timestamp"].min()

        service_scores[service] = {
            "severity_score": int(severity_score),
            "problem_events": int(len(service_logs)),
            "warnings": warnings,
            "errors": errors,
            "criticals": criticals,
            "first_problem": str(first_problem_time),
        }

    root_cause = min(
        service_scores,
        key=lambda service: service_scores[service]["first_problem"],
    )

    root_cause_logs = problem_logs[
        problem_logs["service"] == root_cause
    ].sort_values("timestamp")

    first_event = root_cause_logs.iloc[0]

    first_event_time = str(first_event["timestamp"])
    first_event_level = first_event["level"]
    first_event_message = first_event["message"]

    explanation = (
        f"{root_cause} is the most likely root cause because "
        f"it generated the earliest problem event at "
        f"{first_event_time}. The first problem was a "
        f"{first_event_level} event: '{first_event_message}'. "
        f"This was followed by failures in other services, "
        f"indicating that those services were likely affected "
        f"downstream."
    )

    return {
        "root_cause_service": root_cause,
        "confidence": "High",
        "first_problem_time": first_event_time,
        "first_problem_level": first_event_level,
        "first_problem_message": first_event_message,
        "reason": explanation,
        "service_scores": service_scores,
    }


def analyze_root_cause() -> dict:
    """Analyze the stored logs and write the existing JSON artifact."""

    df = pd.read_csv(INPUT_FILE)

    result = analyze_root_cause_from_dataframe(df)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=4)

    return result


if __name__ == "__main__":
    result = analyze_root_cause()

    print("\nRoot Cause Analysis")
    print("===================")
    print("Root Cause:", result["root_cause_service"])
    print("Confidence:", result["confidence"])
    print("First Problem:", result["first_problem_message"])
    print("First Problem Time:", result["first_problem_time"])

    print("\nReason:")
    print(result["reason"])

    print("\nService Analysis:")

    for service, details in result["service_scores"].items():
        print(
            f"- {service}: "
            f"score={details['severity_score']}, "
            f"events={details['problem_events']}, "
            f"first_problem={details['first_problem']}"
        )

    print("\nAnalysis saved:", OUTPUT_FILE)
