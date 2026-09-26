from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_FILE = PROJECT_ROOT / "data" / "processed" / "anomaly_results.csv"


def load_results():
    assert RESULTS_FILE.is_file(), "anomaly_results.csv was not found"

    data = pd.read_csv(RESULTS_FILE)

    required_columns = {
        "actual_anomaly",
        "predicted_anomaly",
        "final_anomaly",
    }

    assert required_columns.issubset(data.columns)

    return data


def test_evaluation_dataset_has_expected_size():
    data = load_results()

    assert len(data) == 20
    assert data["actual_anomaly"].isin([0, 1]).all()
    assert data["predicted_anomaly"].isin([0, 1]).all()
    assert data["final_anomaly"].isin([0, 1]).all()


def test_model_performance_meets_minimum_thresholds():
    data = load_results()

    actual = data["actual_anomaly"]
    predicted = data["predicted_anomaly"]

    precision = precision_score(actual, predicted, zero_division=0)
    recall = recall_score(actual, predicted, zero_division=0)
    f1 = f1_score(actual, predicted, zero_division=0)

    # Minimum acceptance thresholds for the current small evaluation dataset.
    assert precision >= 0.50
    assert recall >= 0.40
    assert f1 >= 0.45


def test_model_accuracy_is_valid():
    data = load_results()

    accuracy = accuracy_score(
        data["actual_anomaly"],
        data["predicted_anomaly"],
    )

    assert 0.0 <= accuracy <= 1.0


def test_hybrid_rule_does_not_remove_ml_anomalies():
    data = load_results()

    ml_anomalies = data["predicted_anomaly"] == 1
    final_anomalies = data["final_anomaly"] == 1

    assert (final_anomalies[ml_anomalies]).all()


def test_evaluation_contains_both_normal_and_anomalous_events():
    data = load_results()

    assert data["actual_anomaly"].sum() > 0
    assert (data["actual_anomaly"] == 0).sum() > 0