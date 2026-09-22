import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("data/processed/logs_clean.csv")

print("First 5 logs:")
print(df.head())

print("\nDataset shape:")
print(df.shape)

print("\nLog levels:")
print(df["level"].value_counts())

print("\nErrors by service:")
print(df[df["level"] == "ERROR"]["service"].value_counts())

print("\nAll error logs:")
print(df[df["level"].isin(["ERROR", "CRITICAL"])][
    ["timestamp", "service", "level", "message"]
])
print("\nLog count by service:")
print(df["service"].value_counts())

print("\nError and critical logs by service:")

problem_logs = df[df["level"].isin(["ERROR", "CRITICAL"])]

print(problem_logs["service"].value_counts())


print("\nError percentage by service:")

error_counts = problem_logs["service"].value_counts()

error_percentage = (
    error_counts / len(problem_logs) * 100
).round(2)

print(error_percentage)


# Convert timestamp to datetime
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Create error indicator
df["is_error"] = df["level"].isin(["ERROR", "CRITICAL"]).astype(int)

# Plot errors over time
plt.figure(figsize=(10, 5))
plt.plot(df["timestamp"], df["is_error"], marker="o")

plt.xlabel("Time")
plt.ylabel("Error (1 = Yes, 0 = No)")
plt.title("Error Events Over Time")

plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Count errors per minute
error_logs = df[df["level"].isin(["ERROR", "CRITICAL"])].copy()

error_logs["minute"] = error_logs["timestamp"].dt.floor("min")

errors_per_minute = error_logs.groupby("minute").size()


# Count errors per minute
error_logs = df[df["level"].isin(["ERROR", "CRITICAL"])].copy()

error_logs["minute"] = error_logs["timestamp"].dt.floor("min")

errors_per_minute = error_logs.groupby("minute").size()

print("\nErrors per minute:")
print(errors_per_minute)

# Logs during the incident
incident_logs = df[
    (df["timestamp"] >= "2026-09-02 10:20:00") &
    (df["timestamp"] <= "2026-09-02 10:21:59")
]

print("\nIncident logs by service:")
print(incident_logs["service"].value_counts())

print("\nIncident Timeline:")

timeline = df[
    (df["timestamp"] >= "2026-09-02 10:20:00") &
    (df["timestamp"] <= "2026-09-02 10:21:30")
][["timestamp", "service", "level", "message"]]

print(timeline.to_string(index=False))

print("\nIncident Event Gaps:")

timeline = timeline.copy()

timeline["time_gap_seconds"] = (
    timeline["timestamp"].diff().dt.total_seconds()
)

print(
    timeline[
        ["timestamp", "service", "level", "time_gap_seconds"]
    ].to_string(index=False)
)

print("\nService Incident Summary:")

service_summary = df.groupby("service").agg(
    total_logs=("service", "count"),
    error_logs=("level", lambda x: x.isin(["ERROR", "CRITICAL"]).sum()),
    warning_logs=("level", lambda x: (x == "WARNING").sum())
)

service_summary["problem_rate"] = (
    (service_summary["error_logs"] + service_summary["warning_logs"])
    / service_summary["total_logs"] * 100
).round(2)

print(service_summary)

print("\nIncident Starting Points:")

warnings = df[df["level"] == "WARNING"]

errors = df[df["level"].isin(["ERROR", "CRITICAL"])]

if not warnings.empty:
    first_warning = warnings.iloc[0]
    print(
        "First warning:",
        first_warning["timestamp"],
        "|",
        first_warning["service"],
        "|",
        first_warning["message"]
    )

if not errors.empty:
    first_error = errors.iloc[0]
    print(
        "First error:",
        first_error["timestamp"],
        "|",
        first_error["service"],
        "|",
        first_error["message"]
    )

print("\nEDA Conclusion:")

first_warning_service = first_warning["service"]
first_error_service = first_error["service"]

if first_warning_service == first_error_service:
    print(
        f"Probable root-cause service: {first_error_service}"
    )
    print(
        "Reason: The same service generated the first warning "
        "and the first error before downstream failures."
    )
else:
    print(
        "No clear root-cause service identified from the "
        "initial warning and error sequence."
    )
