from __future__ import annotations

import unittest

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

if TestClient is not None:
    from backend.main import app


@unittest.skipIf(TestClient is None, "fastapi is not installed")
class UploadApiTest(unittest.TestCase):
    def test_upload_accepts_csv(self):
        client = TestClient(app)
        response = client.post(
            "/upload",
            files={"file": ("sales.csv", "订单日期,区域\n2026-04-03,华东\n", "text/csv")},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["filename"], "sales.csv")
        self.assertGreater(data["size"], 0)
        self.assertTrue(data["server_path"].endswith(".csv"))

    def test_upload_rejects_other_suffixes(self):
        client = TestClient(app)
        response = client.post(
            "/upload",
            files={"file": ("notes.txt", "hello", "text/plain")},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
