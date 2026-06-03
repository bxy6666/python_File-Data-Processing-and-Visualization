import math
import unittest

import pandas as pd

from app.utils.clean_utils import clean_dataframe


class CleanDataFrameTests(unittest.TestCase):
    def make_dirty_dataframe(self):
        return pd.DataFrame(
            {
                "sales": [10, 10, 11, math.nan, 12, 1000],
                "profit": [1.0, 1.0, 1.1, 2.0, 1.2, 100.0],
                "region": ["east", "east", "east", "west", "east", "north"],
            }
        )

    def test_clean_dataframe_applies_missing_duplicate_and_outlier_rules(self):
        result = clean_dataframe(
            self.make_dirty_dataframe(),
            {
                "drop_missing": True,
                "drop_duplicates": True,
                "handle_outliers": True,
            },
        )

        cleaned = result["dataset"]
        summary = result["summary"]

        self.assertEqual(len(cleaned), 3)
        self.assertEqual(cleaned["sales"].tolist(), [10.0, 11.0, 12.0])
        self.assertEqual(summary["input_rows"], 6)
        self.assertEqual(summary["output_rows"], 3)
        self.assertEqual(summary["missing_values_before"], 1)
        self.assertEqual(summary["missing_values_after"], 0)
        self.assertEqual(summary["duplicate_rows_before"], 1)
        self.assertEqual(summary["removed_missing_rows"], 1)
        self.assertEqual(summary["removed_duplicate_rows"], 1)
        self.assertEqual(summary["outlier_rows_removed"], 1)
        self.assertEqual(summary["removed_rows"], 3)
        self.assertEqual(summary["filled_values"], 0)
        self.assertEqual(summary["rules"]["drop_missing"], True)

    def test_clean_dataframe_can_keep_missing_rows_when_rule_is_false(self):
        result = clean_dataframe(
            self.make_dirty_dataframe(),
            {
                "drop_missing": False,
                "drop_duplicates": True,
                "handle_outliers": False,
            },
        )

        cleaned = result["dataset"]
        summary = result["summary"]

        self.assertEqual(len(cleaned), 5)
        self.assertEqual(summary["removed_missing_rows"], 0)
        self.assertEqual(summary["removed_duplicate_rows"], 1)
        self.assertEqual(summary["missing_values_after"], 1)

    def test_clean_dataframe_accepts_bool_like_string_rules(self):
        result = clean_dataframe(
            self.make_dirty_dataframe(),
            {
                "drop_missing": "true",
                "drop_duplicates": "false",
                "handle_outliers": "false",
            },
        )

        self.assertEqual(result["summary"]["rules"]["drop_missing"], True)
        self.assertEqual(result["summary"]["rules"]["drop_duplicates"], False)
        self.assertEqual(result["summary"]["removed_missing_rows"], 1)
        self.assertEqual(result["summary"]["removed_duplicate_rows"], 0)

    def test_clean_dataframe_defaults_missing_rules_to_false(self):
        result = clean_dataframe(self.make_dirty_dataframe(), {})

        self.assertEqual(len(result["dataset"]), 6)
        self.assertEqual(result["summary"]["removed_rows"], 0)
        self.assertEqual(result["summary"]["rules"]["drop_missing"], False)
        self.assertEqual(result["summary"]["rules"]["drop_duplicates"], False)
        self.assertEqual(result["summary"]["rules"]["handle_outliers"], False)

    def test_clean_dataframe_rejects_non_dataframe_input(self):
        with self.assertRaisesRegex(ValueError, "Pandas DataFrame"):
            clean_dataframe([{"sales": 10}], {})

    def test_clean_dataframe_rejects_non_object_rules(self):
        with self.assertRaisesRegex(ValueError, "清洗规则必须是 JSON 对象"):
            clean_dataframe(self.make_dirty_dataframe(), ["drop_missing"])

    def test_clean_dataframe_rejects_unknown_rule(self):
        with self.assertRaisesRegex(ValueError, "不支持的清洗规则"):
            clean_dataframe(self.make_dirty_dataframe(), {"unknown": True})

    def test_clean_dataframe_rejects_invalid_bool_value(self):
        with self.assertRaisesRegex(ValueError, "drop_missing 必须是布尔值"):
            clean_dataframe(self.make_dirty_dataframe(), {"drop_missing": "maybe"})


if __name__ == "__main__":
    unittest.main()
