import io
import json
import unittest

import pandas as pd

from app.utils.file_utils import export_dataset, read_uploaded_file


class UploadedFile:
    def __init__(self, filename, content):
        self.filename = filename
        self._stream = io.BytesIO(content)

    def read(self):
        return self._stream.read()


class ReadUploadedFileTests(unittest.TestCase):
    def test_read_uploaded_csv_returns_dataframe_and_metadata(self):
        file = UploadedFile("sample.csv", "name,sales\nA,10\nB,20\n".encode("utf-8"))

        result = read_uploaded_file(file)

        self.assertEqual(result["metadata"]["filename"], "sample.csv")
        self.assertEqual(result["metadata"]["format"], "CSV")
        self.assertEqual(result["metadata"]["rows"], 2)
        self.assertEqual(result["metadata"]["columns"], ["name", "sales"])
        self.assertEqual(result["dataset"]["sales"].tolist(), [10, 20])

    def test_read_uploaded_csv_supports_gbk_encoding(self):
        file = UploadedFile("中文.csv", "名称,销售额\n甲,10\n乙,20\n".encode("gbk"))

        result = read_uploaded_file(file)

        self.assertEqual(result["metadata"]["columns"], ["名称", "销售额"])
        self.assertEqual(result["dataset"]["名称"].tolist(), ["甲", "乙"])

    def test_read_uploaded_xlsx_returns_dataframe_and_metadata(self):
        buffer = io.BytesIO()
        pd.DataFrame({"sales": [10, 20], "profit": [1, 2]}).to_excel(buffer, index=False)
        file = UploadedFile("sample.xlsx", buffer.getvalue())

        result = read_uploaded_file(file)

        self.assertEqual(result["metadata"]["format"], "XLSX")
        self.assertEqual(result["metadata"]["rows"], 2)
        self.assertEqual(result["metadata"]["columns"], ["sales", "profit"])

    def test_read_uploaded_file_rejects_unsupported_extension(self):
        file = UploadedFile("sample.txt", b"name,sales\nA,10\n")

        with self.assertRaisesRegex(ValueError, "仅支持 CSV、XLS 或 XLSX 文件"):
            read_uploaded_file(file)

    def test_read_uploaded_file_rejects_empty_file(self):
        file = UploadedFile("sample.csv", b"")

        with self.assertRaisesRegex(ValueError, "文件内容为空"):
            read_uploaded_file(file)

    def test_read_uploaded_file_rejects_header_only_file(self):
        file = UploadedFile("sample.csv", b"name,sales\n")

        with self.assertRaisesRegex(ValueError, "文件没有可用数据"):
            read_uploaded_file(file)


class ExportDatasetTests(unittest.TestCase):
    def test_export_cleaned_dataset_as_csv_content(self):
        dataframe = pd.DataFrame({"sales": [10, 20], "profit": [1, 2]})

        result = export_dataset("cleaned", {"cleaned_dataset": dataframe})

        self.assertEqual(result["filename"], "cleaned_dataset.csv")
        self.assertEqual(result["format"], "csv")
        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["columns"], ["sales", "profit"])
        self.assertIn("sales,profit", result["content"])
        self.assertIn("10,1", result["content"])

    def test_export_analysis_result_as_json_content(self):
        analysis_result = {
            "method": "kmeans",
            "clusters": [{"cluster": 0, "count": 2}],
        }

        result = export_dataset("result", {"analysis_result": analysis_result})

        self.assertEqual(result["filename"], "analysis_result.json")
        self.assertEqual(result["format"], "json")
        self.assertEqual(json.loads(result["content"]), analysis_result)

    def test_export_cleaned_dataset_requires_data(self):
        with self.assertRaisesRegex(ValueError, "没有可导出的清洗数据"):
            export_dataset("cleaned", {"cleaned_dataset": None})

    def test_export_result_requires_analysis_result(self):
        with self.assertRaisesRegex(ValueError, "没有可导出的分析结果"):
            export_dataset("result", {"analysis_result": None})

    def test_export_rejects_unknown_type(self):
        with self.assertRaisesRegex(ValueError, "type 仅支持 cleaned 或 result"):
            export_dataset("unknown", {})


if __name__ == "__main__":
    unittest.main()
