import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from src.analysis.feature_engineering import (
    build_model_feature_frame,
    calculate_message_length,
    calculate_rolling_error_counts,
    calculate_rolling_warning_counts,
    calculate_service_error_rate,
    calculate_time_since_previous,
    encode_service_names,
    encode_severity,
    engineer_log_features,
)
from src.ml.constants import FEATURE_COLUMNS
from src.preprocessing.log_parser import parse_log_line, parse_log_lines


class PreprocessingAndFeatureEngineeringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = pd.DataFrame(
            [
                {
                    "timestamp": "2026-09-02 10:00:00",
                    "service": "auth-service",
                    "level": "INFO",
                    "message": "Login ok",
                },
                {
                    "timestamp": "2026-09-02 10:00:05",
                    "service": "auth-service",
                    "level": "ERROR",
                    "message": "Login failed",
                },
                {
                    "timestamp": "2026-09-02 10:00:10",
                    "service": "payment-service",
                    "level": "WARNING",
                    "message": "Payment delayed",
                },
                {
                    "timestamp": "2026-09-02 10:00:15",
                    "service": "payment-service",
                    "level": "CRITICAL",
                    "message": "Payment unavailable",
                },
                {
                    "timestamp": "2026-09-02 10:01:00",
                    "service": "api-gateway",
                    "level": "WARNING",
                    "message": "Gateway delayed",
                },
            ]
        )

    def test_valid_log_parsing(self) -> None:
        record = parse_log_line(
            "2026-09-02 10:00:00 | auth-service | info | Login ok"
        )
        self.assertIsNotNone(record)
        self.assertEqual(record["service"], "auth-service")
        self.assertEqual(record["level"], "INFO")

        parsed = parse_log_lines(
            [
                "2026-09-02 10:00:00 | auth-service | INFO | Login ok\n",
                "invalid line\n",
            ]
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed.columns.tolist(), ["timestamp", "service", "level", "message"])

    def test_malformed_log_handling(self) -> None:
        self.assertIsNone(parse_log_line("not a structured log"))
        self.assertIsNone(
            parse_log_line("not-a-date | auth-service | INFO | Login ok")
        )
        self.assertIsNone(
            parse_log_line("2026-09-02 10:00:00 | auth-service | TRACE | Login ok")
        )
        self.assertIsNone(
            parse_log_line("2026-09-02 10:00:00 |  | INFO | Login ok")
        )

    def test_severity_and_service_encoding(self) -> None:
        self.assertEqual(
            encode_severity(pd.Series(["INFO", "warning", "ERROR", "CRITICAL"])).tolist(),
            [0, 1, 2, 3],
        )
        self.assertEqual(
            encode_service_names(
                pd.Series(["api-gateway", "auth-service", "database-service", "payment-service"])
            ).tolist(),
            [0, 1, 2, 3],
        )
        with self.assertRaisesRegex(ValueError, "Unknown service names"):
            encode_service_names(pd.Series(["new-service"]))

    def test_message_length_and_time_since_previous(self) -> None:
        self.assertEqual(calculate_message_length(pd.Series(["one", "four"])).tolist(), [3, 4])
        timestamps = pd.Series(
            pd.to_datetime(
                ["2026-09-02 10:00:00", "2026-09-02 10:00:02", "2026-09-02 10:00:05"]
            )
        )
        self.assertEqual(calculate_time_since_previous(timestamps).tolist(), [0.0, 2.0, 3.0])

    def test_rolling_counts_and_service_error_rate(self) -> None:
        timestamps = pd.Series(
            pd.to_datetime(
                [
                    "2026-09-02 10:00:00",
                    "2026-09-02 10:00:01",
                    "2026-09-02 10:00:02",
                    "2026-09-02 10:00:03",
                    "2026-09-02 10:01:00",
                ]
            )
        )
        levels = pd.Series(["INFO", "ERROR", "WARNING", "CRITICAL", "ERROR"])
        self.assertEqual(calculate_rolling_error_counts(levels, timestamps).tolist(), [0, 0, 1, 1, 0])
        self.assertEqual(calculate_rolling_warning_counts(levels, timestamps).tolist(), [0, 0, 0, 1, 0])
        self.assertEqual(
            calculate_service_error_rate(
                pd.Series(["auth-service", "auth-service", "payment-service"]),
                pd.Series([0, 1, 1]),
            ).tolist(),
            [0.5, 0.5, 1.0],
        )

    def test_final_feature_order_and_values(self) -> None:
        model_features = build_model_feature_frame(self.records)
        self.assertEqual(model_features.columns.tolist(), FEATURE_COLUMNS)
        self.assertEqual(model_features["severity"].tolist(), [0, 2, 1, 3, 1])
        self.assertEqual(model_features["service_code"].tolist(), [1, 1, 3, 3, 0])
        self.assertEqual(model_features["time_since_previous"].tolist(), [0.0, 5.0, 5.0, 5.0, 45.0])
        self.assertEqual(model_features["errors_in_last_minute"].tolist(), [0, 0, 1, 1, 0])
        self.assertEqual(model_features["warnings_in_last_minute"].tolist(), [0, 0, 0, 1, 0])

        expected = engineer_log_features(self.records).loc[:, FEATURE_COLUMNS]
        assert_frame_equal(model_features, expected)


if __name__ == "__main__":
    unittest.main()
