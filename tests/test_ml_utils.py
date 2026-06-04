import builtins
import importlib.util
import math
import unittest
from unittest import mock

from app.utils import ml_utils


HAS_PANDAS = importlib.util.find_spec("pandas") is not None
HAS_SKLEARN = importlib.util.find_spec("sklearn") is not None

if HAS_PANDAS:
    import pandas as pd


@unittest.skipUnless(HAS_PANDAS and HAS_SKLEARN, "pandas and scikit-learn are required")
class RunKMeansTests(unittest.TestCase):
    def make_clustered_dataframe(self):
        return pd.DataFrame(
            {
                "sales": [10, 12, 11, math.nan, 80, 82, 78],
                "profit": [1.0, 2.0, 1.5, 5.0, 10.0, 11.0, 9.0],
                "region": ["north", "north", "north", "skip", "south", "south", "south"],
            },
            index=["a", "b", "c", "missing", "d", "e", "f"],
        )

    def test_run_kmeans_returns_expected_contract(self):
        result = ml_utils.run_kmeans(self.make_clustered_dataframe(), 2)

        self.assertEqual(set(result), {"result", "summary"})
        analysis = result["result"]
        summary = result["summary"]

        self.assertEqual(analysis["method"], "kmeans")
        self.assertEqual(analysis["k"], 2)
        self.assertEqual(analysis["columns"], ["sales", "profit"])
        self.assertEqual(analysis["rows_used"], 6)
        self.assertEqual(analysis["rows_skipped"], 1)
        self.assertIsInstance(analysis["inertia"], float)
        self.assertEqual(summary["k"], analysis["k"])
        self.assertEqual(summary["columns"], analysis["columns"])
        self.assertEqual(summary["clusters"], analysis["clusters"])
        self.assertIn("model", analysis)
        self.assertEqual(analysis["model"]["type"], "kmeans")

    def test_run_kmeans_predict_returns_cluster_for_new_rows(self):
        trained = ml_utils.run_kmeans(self.make_clustered_dataframe(), 2)
        predict_rows = [
            {"sales": 10.5, "profit": 1.2},
            {"sales": 81.0, "profit": 10.5},
        ]

        prediction = ml_utils.run_kmeans_predict(predict_rows, trained["result"])

        self.assertEqual(set(prediction), {"result", "summary"})
        self.assertEqual(prediction["summary"]["rows_used"], 2)
        self.assertEqual(len(prediction["result"]["predictions"]), 2)
        self.assertTrue(all(item["cluster"] in {0, 1} for item in prediction["result"]["predictions"]))

    def test_run_kmeans_predict_rejects_missing_columns(self):
        trained = ml_utils.run_kmeans(self.make_clustered_dataframe(), 2)

        with self.assertRaisesRegex(ValueError, "缺少字段"):
            ml_utils.run_kmeans_predict([{"sales": 10.0}], trained["result"])

    def test_run_kmeans_predict_rejects_invalid_model(self):
        with self.assertRaisesRegex(ValueError, "不包含可用于预测的模型参数"):
            ml_utils.run_kmeans_predict([{"sales": 10, "profit": 1}], {"method": "kmeans"})

    def test_run_kmeans_finds_expected_cluster_centers(self):
        result = ml_utils.run_kmeans(self.make_clustered_dataframe(), 2)

        centers = {
            (cluster["center"]["sales"], cluster["center"]["profit"])
            for cluster in result["summary"]["clusters"]
        }
        self.assertEqual(centers, {(11.0, 1.5), (80.0, 10.0)})

        counts = sorted(cluster["count"] for cluster in result["summary"]["clusters"])
        self.assertEqual(counts, [3, 3])

    def test_run_kmeans_preserves_row_labels_and_skips_missing_rows(self):
        result = ml_utils.run_kmeans(self.make_clustered_dataframe(), 2)

        labels = result["result"]["labels"]
        self.assertEqual(len(labels), 6)
        self.assertEqual({label["row_index"] for label in labels}, {"a", "b", "c", "d", "e", "f"})
        self.assertNotIn("missing", {label["row_index"] for label in labels})
        self.assertTrue(all(label["cluster"] in {0, 1} for label in labels))

    def test_run_kmeans_accepts_numeric_string_k(self):
        result = ml_utils.run_kmeans(self.make_clustered_dataframe(), "2")

        self.assertEqual(result["summary"]["k"], 2)

    def test_run_kmeans_rejects_non_dataframe_input(self):
        with self.assertRaisesRegex(ValueError, "Pandas DataFrame"):
            ml_utils.run_kmeans([{"sales": 10}], 2)

    def test_run_kmeans_rejects_non_numeric_k(self):
        with self.assertRaisesRegex(ValueError, "k 值必须是数字"):
            ml_utils.run_kmeans(self.make_clustered_dataframe(), "abc")

    def test_run_kmeans_rejects_k_less_than_two(self):
        with self.assertRaisesRegex(ValueError, "k 值不能小于 2"):
            ml_utils.run_kmeans(self.make_clustered_dataframe(), 1)

    def test_run_kmeans_rejects_k_larger_than_available_rows(self):
        dataframe = pd.DataFrame({"sales": [10, 20], "profit": [1, 2]})

        with self.assertRaisesRegex(ValueError, "k 值不能大于可用样本数 2"):
            ml_utils.run_kmeans(dataframe, 3)

    def test_run_kmeans_rejects_dataframe_without_numeric_columns(self):
        dataframe = pd.DataFrame({"region": ["north", "south"], "name": ["A", "B"]})

        with self.assertRaisesRegex(ValueError, "没有可用于聚类的数值列"):
            ml_utils.run_kmeans(dataframe, 2)

    def test_run_kmeans_rejects_dataframe_without_valid_numeric_rows(self):
        dataframe = pd.DataFrame({"sales": [math.nan, math.nan], "profit": [1.0, math.nan]})

        with self.assertRaisesRegex(ValueError, "没有可用于聚类的有效样本"):
            ml_utils.run_kmeans(dataframe, 2)


class LoadSklearnTests(unittest.TestCase):
    def test_load_sklearn_reports_missing_dependency(self):
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("sklearn"):
                raise ImportError("blocked for test")
            return original_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=fake_import):
            with self.assertRaisesRegex(ValueError, "缺少 scikit-learn 依赖"):
                ml_utils._load_sklearn()


if __name__ == "__main__":
    unittest.main()
