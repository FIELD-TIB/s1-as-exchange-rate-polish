import unittest
from datetime import datetime

from rate_service import EAT, is_polling_time, next_poll_time


class PollingScheduleTests(unittest.TestCase):
    def test_window_includes_both_endpoints(self):
        self.assertTrue(is_polling_time(datetime(2026, 10, 7, 6, 0, tzinfo=EAT)))
        self.assertTrue(is_polling_time(datetime(2026, 10, 7, 18, 0, tzinfo=EAT)))
        self.assertFalse(is_polling_time(datetime(2026, 10, 7, 5, 59, tzinfo=EAT)))
        self.assertFalse(is_polling_time(datetime(2026, 10, 7, 18, 1, tzinfo=EAT)))

    def test_next_boundary_during_window(self):
        now = datetime(2026, 10, 7, 9, 34, 20, tzinfo=EAT)
        self.assertEqual(
            next_poll_time(now),
            datetime(2026, 10, 7, 9, 40, tzinfo=EAT),
        )

    def test_next_boundary_after_window_is_next_morning(self):
        now = datetime(2026, 10, 7, 18, 0, tzinfo=EAT)
        self.assertEqual(
            next_poll_time(now),
            datetime(2026, 10, 8, 6, 0, tzinfo=EAT),
        )

    def test_next_boundary_before_window_is_six_am(self):
        now = datetime(2026, 10, 7, 5, 45, tzinfo=EAT)
        self.assertEqual(
            next_poll_time(now),
            datetime(2026, 10, 7, 6, 0, tzinfo=EAT),
        )


if __name__ == "__main__":
    unittest.main()
