import pandas as pd
import json

# Load processed logs
df = pd.read_csv("data/processed/logs.csv")

# Convert timestamp to datetime
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Select ERROR and CRITICAL logs
problem_logs = df[
    df["level"].isin(["ERROR", "CRITICAL"])
].copy()

# Sort logs by time
problem_logs = problem_logs.sort_values("timestamp").reset_index(drop=True)

# Calculate time gap between consecutive problem logs
problem_logs["time_gap"] = (
    problem_logs["timestamp"].diff().dt.total_seconds()
)

# Maximum allowed gap between related events
TIME_WINDOW = 10

# Start a new incident when the gap is greater than 10 seconds
problem_logs["new_incident"] = (
    problem_logs["time_gap"].fillna(0) > TIME_WINDOW
).astype(int)

# Assign incident IDs
problem_logs["incident_id"] = (
    problem_logs["new_incident"].cumsum() + 1
)

# Create structured incident objects
incidents = []

for incident_id, incident in problem_logs.groupby("incident_id"):

    # Determine severity
    if "CRITICAL" in incident["level"].values:
        severity = "CRITICAL"
    elif "ERROR" in incident["level"].values:
        severity = "HIGH"
    else:
        severity = "MEDIUM"

    # Create event list
    events = []

    for _, row in incident.iterrows():
        events.append({
            "timestamp": str(row["timestamp"]),
            "service": row["service"],
            "level": row["level"],
            "message": row["message"]
        })

    # Create incident object
    incident_data = {
        "incident_id": int(incident_id),
        "severity": severity,
        "services": incident["service"].unique().tolist(),
        "event_count": len(events),
        "events": events
    }

    incidents.append(incident_data)


# Display structured incidents
print("\nStructured Incidents:")

for incident in incidents:

    print("\n==============================")
    print(f"INCIDENT #{incident['incident_id']}")
    print("==============================")

    print("Severity:", incident["severity"])
    print("Services:", incident["services"])
    print("Event count:", incident["event_count"])

    print("\nEvents:")

    for event in incident["events"]:
        print(
            f"- {event['timestamp']} | "
            f"{event['service']} | "
            f"{event['level']} | "
            f"{event['message']}"
        )

# Save structured incidents to JSON
with open("data/processed/incidents.json", "w") as file:
    json.dump(incidents, file, indent=4)

print("\nStructured incidents saved successfully!")
