import json
import tempfile
import unittest
from pathlib import Path

from lottery.models import Draw
from lottery.storage import load_draws, save_draws


class StorageTests(unittest.TestCase):
    def test_load_draws_ignores_corrupt_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "draws.json"
            cache_file.write_text("{bad json", encoding="utf-8")

            self.assertEqual(load_draws(cache_file), [])

    def test_load_draws_skips_invalid_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "draws.json"
            cache_file.write_text(
                json.dumps(
                    {
                        "draws": [
                            {"issue": "2024001", "date": "2024-01-01", "reds": [1, 2, 3, 4, 5, 6], "blue": 7},
                            {"issue": "bad", "date": "2024-01-02", "reds": [1, 1, 3, 4, 5, 6], "blue": 7},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            draws = load_draws(cache_file)

            self.assertEqual(draws, [Draw(issue="2024001", date="2024-01-01", reds=(1, 2, 3, 4, 5, 6), blue=7)])

    def test_save_and_load_draws_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "draws.json"
            expected = [Draw(issue="2024001", date="2024-01-01", reds=(1, 2, 3, 4, 5, 6), blue=7)]

            save_draws(expected, cache_file)

            self.assertEqual(load_draws(cache_file), expected)


if __name__ == "__main__":
    unittest.main()
