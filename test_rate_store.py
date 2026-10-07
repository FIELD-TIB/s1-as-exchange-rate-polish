import tempfile
import unittest
from pathlib import Path

from rate_store import RateStore


class RateStoreTests(unittest.TestCase):
    def test_saved_samples_are_returned_oldest_first(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RateStore(Path(directory) / "rates.sqlite3")
            store.save_sample("2026-10-07T06:00:00+03:00", 15.2, "first")
            store.save_sample("2026-10-07T06:10:00+03:00", 15.3, "second")

            self.assertEqual(
                [sample["rate"] for sample in store.get_samples(10)],
                [15.2, 15.3],
            )
            self.assertEqual(store.get_latest()["provider_updated_at"], "second")


if __name__ == "__main__":
    unittest.main()
