import unittest
from unittest.mock import patch

try:
    from lottery import web
except ModuleNotFoundError as exc:
    if exc.name != "flask":
        raise
    web = None


@unittest.skipIf(web is None, "Flask is not installed")
class WebApiTests(unittest.TestCase):
    def setUp(self):
        self.client = web.app.test_client()

    @patch("lottery.web._fetch_draws", return_value=[])
    def test_predict_rejects_unknown_strategy(self, _):
        response = self.client.get("/api/predict?strategy=unknown")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Unknown strategy: unknown")

    @patch("lottery.web._fetch_draws", return_value=[])
    def test_predict_rejects_non_integer_count(self, _):
        response = self.client.get("/api/predict?count=many")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "count must be an integer")

    @patch("lottery.web._fetch_draws", return_value=[])
    def test_predict_rejects_out_of_range_count(self, _):
        response = self.client.get("/api/predict?count=99")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "count must be between 1 and 10")


if __name__ == "__main__":
    unittest.main()
