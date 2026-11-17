import unittest
from signatures import DisplaySignal

class DisplayTests(unittest.TestCase):
    def test_short_gap_and_expiry(self):
        s=DisplaySignal()
        self.assertEqual(s.feed(16960,0),16960)
        self.assertEqual(s.feed(16960,.1),16960)
        self.assertEqual(s.feed(None,.2),16960)
        self.assertEqual(s.feed(None,2),16960)
        self.assertIsNone(s.feed(None,2.6))
    def test_recurring_valid_frames_keep_display(self):
        s=DisplaySignal()
        s.feed(16960,0);s.feed(16960,.1)
        for t in range(1,20):
            self.assertEqual(s.feed(None,t),16960)
            self.assertEqual(s.feed(16960,t+.1),16960)
    def test_new_number_is_shown_on_first_read(self):
        s=DisplaySignal()
        self.assertEqual(s.feed(16960,0),16960)
        self.assertEqual(s.feed(6370,.2),6370)
        self.assertEqual(s.feed(None,.3),6370)

    def test_first_read_after_long_gap(self):
        s=DisplaySignal()
        s.feed(16960,0)
        self.assertIsNone(s.feed(None,3))
        self.assertEqual(s.feed(3385,4),3385)
