import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import create_app


class DatasetHistoryRouteTests(unittest.TestCase):
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
        return response.get_json()

    def analyze_current(self):
        response = self.client.post("/api/analyze", json={"method": "kmeans", "k": 2})
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_upload_history_lists_multiple_files_and_activation_switches_current_dataset(self):
        first_id = self.upload_csv("first.csv", "name,sales\nA,10\nB,20\n")
        second_id = self.upload_csv("second.csv", "name,sales\nC,100\nD,200\n")

        response = self.client.get("/api/datasets")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], "DATASETS_OK")
        self.assertEqual(len(payload["data"]["datasets"]), 2)
        self.assertEqual(payload["data"]["active_dataset"]["id"], second_id)

        activate_response = self.client.post(f"/api/datasets/{first_id}/activate")
        activate_payload = activate_response.get_json()

        self.assertEqual(activate_response.status_code, 200)
        self.assertEqual(activate_payload["code"], "DATASET_ACTIVATED")
        self.assertEqual(activate_payload["data"]["active_dataset"]["id"], first_id)

    def test_cleaning_uses_the_activated_dataset(self):
        first_id = self.upload_csv("first.csv", "name,sales\nA,10\nB,20\n")
        self.upload_csv("second.csv", "name,sales\nC,100\nD,\nE,300\n")

        self.client.post(f"/api/datasets/{first_id}/activate")
        first_clean = self.clean_current()

        self.assertEqual(first_clean["data"]["summary"]["input_rows"], 2)
        self.assertEqual(first_clean["data"]["summary"]["output_rows"], 2)

    def test_status_flags_do_not_treat_cleared_results_as_ready(self):
        self.upload_csv("status.csv", "name,sales,profit\nA,10,1\nB,20,2\nC,30,3\n")

        clean_payload = self.clean_current()
        clean_status = clean_payload["data"]["state"]["active_dataset"]["status"]
        self.assertTrue(clean_status["has_cleaned_dataset"])
        self.assertFalse(clean_status["has_analysis_result"])

        analyze_payload = self.analyze_current()
        analyze_status = analyze_payload["data"]["state"]["active_dataset"]["status"]
        self.assertTrue(analyze_status["has_analysis_result"])
        self.assertFalse(analyze_status["has_prediction_result"])

    def test_prediction_flow_stores_result_on_active_dataset(self):
        self.upload_csv(
            "predict.csv",
            "name,sales,profit\nA,10,1\nB,12,1.2\nC,100,9\nD,105,9.5\n",
        )
        self.clean_current()
        self.analyze_current()

        rows_response = self.client.get("/api/predict/rows")
        rows_payload = rows_response.get_json()
        rows = rows_payload["data"]["predict_rows"]["rows"]

        predict_response = self.client.post("/api/predict", json={"rows": rows[:2]})
        predict_payload = predict_response.get_json()

        self.assertEqual(rows_response.status_code, 200)
        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(predict_response.status_code, 200)
        self.assertEqual(predict_payload["code"], "PREDICT_OK")
        self.assertEqual(predict_payload["data"]["summary"]["rows_used"], 2)
        self.assertTrue(
            predict_payload["data"]["state"]["active_dataset"]["status"]["has_prediction_result"]
        )

    def test_export_uses_current_dataset_by_default_and_dataset_id_when_provided(self):
        first_id = self.upload_csv("first.csv", "name,sales\nA,10\nB,20\n")
        self.clean_current()
        second_id = self.upload_csv("second.csv", "name,sales\nC,100\nD,200\nE,300\n")
        self.clean_current()

        current_response = self.client.get("/api/export?type=cleaned")
        current_payload = current_response.get_json()
        first_response = self.client.get(f"/api/export?type=cleaned&dataset_id={first_id}")
        first_payload = first_response.get_json()

        self.assertEqual(current_response.status_code, 200)
        self.assertEqual(current_payload["data"]["export"]["filename"], "cleaned_dataset.csv")
        self.assertIn("100", current_payload["data"]["export"]["content"])
        self.assertNotIn("10\n", current_payload["data"]["export"]["content"])

        self.assertEqual(first_response.status_code, 200)
        self.assertIn("10", first_payload["data"]["export"]["content"])
        self.assertNotIn("100", first_payload["data"]["export"]["content"])

        second_response = self.client.get(f"/api/export?type=cleaned&dataset_id={second_id}")
        self.assertEqual(second_response.status_code, 200)

    def test_delete_dataset_removes_history_and_switches_active_dataset(self):
        first_id = self.upload_csv("first.csv", "name,sales\nA,10\nB,20\n")
        second_id = self.upload_csv("second.csv", "name,sales\nC,100\nD,200\n")

        delete_response = self.client.delete(f"/api/datasets/{second_id}")
        delete_payload = delete_response.get_json()

        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_payload["code"], "DATASET_DELETED")
        self.assertEqual(delete_payload["data"]["deleted_dataset"]["id"], second_id)
        self.assertEqual(delete_payload["data"]["state"]["active_dataset_id"], first_id)

        datasets_response = self.client.get("/api/datasets")
        datasets = datasets_response.get_json()["data"]["datasets"]
        self.assertEqual([dataset["id"] for dataset in datasets], [first_id])

    def test_delete_last_dataset_clears_active_dataset(self):
        dataset_id = self.upload_csv("only.csv", "name,sales\nA,10\nB,20\n")

        delete_response = self.client.delete(f"/api/datasets/{dataset_id}")
        payload = delete_response.get_json()

        self.assertEqual(delete_response.status_code, 200)
        self.assertIsNone(payload["data"]["state"]["active_dataset_id"])
        self.assertFalse(payload["data"]["state"]["has_raw_dataset"])

    def test_delete_dataset_rejects_unknown_id(self):
        response = self.client.delete("/api/datasets/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["code"], "DATASET_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
