import unittest
from signatures import DisplaySignal

class DisplayTests(unittest.TestCase):
    def test_short_gap_and_expiry(self):
        s=DisplaySignal()
        self.assertIsNone(s.feed(16960,0))
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
    def test_new_number_requires_confirmation(self):
        s=DisplaySignal()
        s.feed(16960,0);s.feed(16960,.1)
        self.assertEqual(s.feed(6370,.2),16960)
        self.assertEqual(s.feed(6370,.3),6370)
    def test_wrong_read_does_not_extend_old_value(self):
        s=DisplaySignal()
        s.feed(16960,0);s.feed(16960,.1)
        self.assertEqual(s.feed(6370,1),16960)
        self.assertEqual(s.feed(None,1.1),16960)
        self.assertIsNone(s.feed(6370,2.7))
