import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import create_app


class DatasetPreviewRouteTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.database_path = Path(self.tempdir.name) / "dataflow.sqlite3"
        self.database_patch = mock.patch("app.utils.data_store.DATABASE_PATH", self.database_path)
        self.database_patch.start()
        self.addCleanup(self.database_patch.stop)
        self.app = create_app()
        self.client = self.app.test_client()

    def upload_csv(self, filename, content):
        response = self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(content.encode("utf-8")), filename)},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        return response.get_json()["data"]["dataset_id"]

    def clean_current(self):
        response = self.client.post(
            "/api/clean",
            json={"drop_missing": True, "drop_duplicates": True, "handle_outliers": False},
        )
        self.assertEqual(response.status_code, 200)

    def test_raw_preview_returns_columns_rows_and_json_safe_missing_values(self):
        dataset_id = self.upload_csv("preview.csv", "name,sales\nA,10\nB,\nC,30\n")

        response = self.client.get(f"/api/datasets/{dataset_id}/preview?type=raw&limit=2")
        payload = response.get_json()
        preview = payload["data"]["preview"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], "DATASET_PREVIEW_OK")
        self.assertEqual(preview["columns"], ["name", "sales"])
        self.assertEqual(preview["total_rows"], 3)
        self.assertEqual(preview["rows"][0]["name"], "A")
        self.assertEqual(preview["rows"][0]["sales"], 10.0)
        self.assertIsNone(preview["rows"][1]["sales"])

    def test_cleaned_preview_requires_cleaning_then_returns_cleaned_rows(self):
        dataset_id = self.upload_csv("dirty.csv", "name,sales\nA,10\nB,\nA,10\n")

        not_ready = self.client.get(f"/api/datasets/{dataset_id}/preview?type=cleaned")
        self.assertEqual(not_ready.status_code, 409)
        self.assertEqual(not_ready.get_json()["code"], "DATA_NOT_READY")

        self.clean_current()
        response = self.client.get(f"/api/datasets/{dataset_id}/preview?type=cleaned")
        preview = response.get_json()["data"]["preview"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(preview["type"], "cleaned")
        self.assertEqual(preview["total_rows"], 1)
        self.assertEqual(preview["rows"][0]["name"], "A")

    def test_clean_profile_reports_missing_duplicates_and_outliers(self):
        dataset_id = self.upload_csv(
            "profile.csv",
            "name,sales,profit\nA,10,1\nA,10,1\nB,,2\nC,1000,100\n",
        )

        response = self.client.get(f"/api/datasets/{dataset_id}/clean-profile")
        profile = response.get_json()["data"]["profile"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(profile["missing_values"], 1)
        self.assertEqual(profile["duplicate_rows"], 1)
        self.assertTrue(profile["recommended_rules"]["drop_missing"])
        self.assertTrue(profile["recommended_rules"]["drop_duplicates"])
        self.assertIn("sales", profile["numeric_columns"])

    def test_preview_rejects_invalid_type_limit_and_unknown_dataset(self):
        dataset_id = self.upload_csv("sample.csv", "name,sales\nA,10\n")

        invalid_type = self.client.get(f"/api/datasets/{dataset_id}/preview?type=analysis")
        invalid_limit = self.client.get(f"/api/datasets/{dataset_id}/preview?limit=0")
        missing_dataset = self.client.get("/api/datasets/999/preview")

        self.assertEqual(invalid_type.status_code, 400)
        self.assertEqual(invalid_type.get_json()["code"], "INVALID_PREVIEW_TYPE")
        self.assertEqual(invalid_limit.status_code, 400)
        self.assertEqual(invalid_limit.get_json()["code"], "INVALID_PREVIEW_LIMIT")
        self.assertEqual(missing_dataset.status_code, 404)
        self.assertEqual(missing_dataset.get_json()["code"], "DATASET_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
