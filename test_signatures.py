import unittest
from signatures import identify, parse_rs, StableSignal, ORES, TIERS, tier_for, candidates

class SignatureTests(unittest.TestCase):
    def test_screenshot(self):
        for value in ('21,200','21.200','21200','21 200'):
            self.assertEqual(identify(parse_rs(value)), [('Copper',5)])
    def test_targets(self):
        self.assertEqual(identify(6370), [('Stileron',2)])
        self.assertEqual(identify(10155), [('Riccite',3)])
    def test_reject_other_hud_values(self):
        for value in ('15.1km','599m','21.20','RS 21200','21,200 6370','','0','100%'):
            self.assertIsNone(parse_rs(value))
    def test_missing_signal_resets_confirmation(self):
        s=StableSignal()
        self.assertIsNone(s.feed(6370))
        self.assertEqual(s.feed(6370),6370)
        self.assertIsNone(s.feed(None))
        self.assertIsNone(s.feed(6370))
        self.assertIsNone(s.feed(3385))
        self.assertEqual(s.feed(3385),3385)
    def test_all_values(self):
        self.assertEqual(len(ORES),26)
        for ore,base in ORES:
            for n in range(1,TIERS[tier_for(base)][0]+1):
                self.assertIn((ore,n),identify(base*n))

    def test_tier_limits(self):
        self.assertEqual(identify(20310), [])
        self.assertEqual(identify(16000), [])
        self.assertEqual(identify(18000), [])
    def test_categories(self):
        self.assertEqual([m['name'] for m in candidates(12000)], ['ROC','MANUAL (FPS)','DEBRIS'])
        self.assertEqual([m['name'] for m in candidates(8000)], ['ROC','DEBRIS'])
        self.assertEqual([m['name'] for m in candidates(10000)], ['DEBRIS'])
        self.assertEqual(parse_rs('30.000'),30000)
        self.assertEqual(parse_rs('2.000'),2000)
        self.assertIsNone(parse_rs('30.001'))
    def test_color_follows_mineral(self):
        self.assertEqual(candidates(3185)[0]['color'], candidates(6370)[0]['color'])
        self.assertNotEqual(candidates(3185)[0]['color'],candidates(3385)[0]['color'])

if __name__ == '__main__': unittest.main()
