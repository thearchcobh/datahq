import unittest
from datetime import datetime
from datahq.sync_window import in_window

class WindowTests(unittest.TestCase):
    def row(self, day='2026-10-14', close='18:00:00', opened=True):
        return dict(trading_date=day, is_scheduled_open=opened,
                    open_time='08:30:00', close_time=close, close_next_day=False)
    def test_boundaries(self):
        for stamp, expected in [('07:29', False), ('07:30', True), ('18:30', True), ('18:31', False)]:
            self.assertEqual(in_window([self.row()], datetime.fromisoformat('2026-10-14T'+stamp+':00+00:00')), expected)
    def test_winter(self):
        self.assertTrue(in_window([self.row('2026-10-26')], datetime.fromisoformat('2026-10-26T08:30:00+00:00')))
        self.assertFalse(in_window([self.row('2026-10-26')], datetime.fromisoformat('2026-10-26T07:30:00+00:00')))
    def test_cutoff_minute(self):
        self.assertTrue(in_window([self.row()], datetime.fromisoformat('2026-10-14T18:30:45+00:00')))
    def test_early_close(self):
        self.assertFalse(in_window([self.row(close='14:00:00')], datetime.fromisoformat('2026-10-14T15:00:00+00:00')))
    def test_closed(self):
        self.assertFalse(in_window([self.row(opened=False)], datetime.fromisoformat('2026-10-14T10:00:00+00:00')))
    def test_missing(self):
        with self.assertRaises(ValueError):
            in_window([], datetime.fromisoformat('2026-10-14T10:00:00+00:00'))
