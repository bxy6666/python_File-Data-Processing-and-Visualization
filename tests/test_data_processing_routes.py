import io
import unittest
from unittest import mock

import pandas as pd

from app import create_app


class DataProcessingRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_upload_endpoint_reads_csv_and_returns_metadata(self):
        captured = {}

        def fake_set_raw_dataset(dataset, metadata):
            captured["dataset"] = dataset
            captured["metadata"] = metadata

        with (
            mock.patch("app.routes.set_raw_dataset", side_effect=fake_set_raw_dataset),
            mock.patch("app.routes.state_summary", return_value={"storage": "test"}),
        ):
            response = self.client.post(
                "/api/upload",
                data={"file": (io.BytesIO(b"name,sales\nA,10\nB,20\n"), "sample.csv")},
                content_type="multipart/form-data",
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], "UPLOAD_OK")
        self.assertEqual(payload["data"]["file"]["rows"], 2)
        self.assertEqual(payload["data"]["file"]["columns"], ["name", "sales"])
        self.assertEqual(captured["dataset"]["sales"].tolist(), [10, 20])

    def test_workflow_page_keeps_predict_and_export_sections_separate(self):
        response = self.client.get("/workflow")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(html.count('data-step="predict"'), 1)
        self.assertEqual(html.count('id="export-panel"'), 1)
        self.assertLess(html.index('data-step="predict"'), html.index('id="export-panel"'))
        self.assertIn('id="predict-fill-example" type="button" disabled', html)
        self.assertIn('id="predict-button" type="button" disabled', html)

    def test_clean_endpoint_cleans_raw_dataset_and_returns_summary(self):
        raw_dataset = pd.DataFrame({"sales": [10, 10, None, 20], "profit": [1, 1, 2, 3]})
        captured = {}

        def fake_set_cleaned_dataset(dataset, summary):
            captured["dataset"] = dataset
            captured["summary"] = summary

        with (
            mock.patch("app.routes.get_raw_dataset", return_value=raw_dataset),
            mock.patch("app.routes.set_cleaned_dataset", side_effect=fake_set_cleaned_dataset),
            mock.patch("app.routes.state_summary", return_value={"storage": "test"}),
        ):
            response = self.client.post(
                "/api/clean",
                json={"drop_missing": True, "drop_duplicates": True, "handle_outliers": False},
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], "CLEAN_OK")
        self.assertEqual(payload["data"]["summary"]["removed_rows"], 2)
        self.assertEqual(captured["dataset"]["sales"].tolist(), [10.0, 20.0])

    def test_export_endpoint_returns_cleaned_csv_content(self):
        cleaned_dataset = pd.DataFrame({"sales": [10, 20], "profit": [1, 2]})

        with (
            mock.patch("app.routes.get_cleaned_dataset", return_value=cleaned_dataset),
            mock.patch("app.routes.get_export_state", return_value={"cleaned_dataset": cleaned_dataset}),
        ):
            response = self.client.get("/api/export?type=cleaned")

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], "EXPORT_OK")
        self.assertEqual(payload["data"]["export"]["filename"], "cleaned_dataset.csv")
        self.assertIn("sales,profit", payload["data"]["export"]["content"])

    def test_predict_endpoint_returns_prediction_summary(self):
        fake_result = {
            "result": {"predictions": [{"row_index": "0", "cluster": 1, "distance": 0.123}]},
            "summary": {"rows_used": 1, "rows_skipped": 0, "columns": ["sales", "profit"], "k": 2},
        }
        captured = {}

        with (
            mock.patch("app.routes.get_analysis_result", return_value={"method": "kmeans", "model": {}}),
            mock.patch("app.routes.run_kmeans_predict", return_value=fake_result),
            mock.patch("app.routes.set_prediction_result", side_effect=lambda result: captured.setdefault("result", result)),
            mock.patch("app.routes.state_summary", return_value={"storage": "test"}),
        ):
            response = self.client.post(
                "/api/predict",
                json={"rows": [{"sales": 10, "profit": 1}]},
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], "PREDICT_OK")
        self.assertEqual(payload["data"]["summary"]["rows_used"], 1)
        self.assertEqual(captured["result"]["result"], fake_result["result"])

    def test_predict_rows_endpoint_returns_current_file_rows(self):
        predict_rows = {
            "columns": ["sales", "profit"],
            "rows": [{"sales": 10.0, "profit": 1.0}, {"sales": 20.0, "profit": 2.0}],
            "rows_used": 2,
            "rows_skipped": 0,
        }

        with (
            mock.patch("app.routes.get_predict_input_rows", return_value=predict_rows),
            mock.patch("app.routes.state_summary", return_value={"storage": "test"}),
        ):
            response = self.client.get("/api/predict/rows")

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], "PREDICT_ROWS_OK")
        self.assertEqual(payload["data"]["predict_rows"]["rows"], predict_rows["rows"])

    def test_predict_endpoint_requires_analysis_result(self):
        with mock.patch("app.routes.get_analysis_result", return_value=None):
            response = self.client.post(
                "/api/predict",
                json={"rows": [{"sales": 10, "profit": 1}]},
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["code"], "DATA_NOT_READY")


if __name__ == "__main__":
    unittest.main()
