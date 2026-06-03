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


if __name__ == "__main__":
    unittest.main()
