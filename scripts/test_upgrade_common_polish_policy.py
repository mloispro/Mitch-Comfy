from types import SimpleNamespace
import unittest

from upgrade_common_polish_policy import common_polish_policy


class CommonPolishPolicyTests(unittest.TestCase):
    def setUp(self):
        self.original=dict(MOUTH_CORNER_LIFT_FACE_HEIGHT=.009,CHEEK_HIGHLIGHT_GAIN=.018,
            SKIN_TEXTURE_BLEND=.12,FOREHEAD_WRINKLE_BLEND=.25,UNDER_EYE_TEXTURE_BLEND=.20)
        self.module=SimpleNamespace(**self.original)

    def test_default_keeps_low_texture_policy(self):
        with common_polish_policy(self.module) as overrides:
            self.assertEqual(set(overrides),{'MOUTH_CORNER_LIFT_FACE_HEIGHT','CHEEK_HIGHLIGHT_GAIN'})
            self.assertEqual(self.module.SKIN_TEXTURE_BLEND,.12)
            self.assertEqual(self.module.FOREHEAD_WRINKLE_BLEND,.25)
        self.assertEqual(vars(self.module),self.original)

    def test_high_skips_only_three_smoothing_controls(self):
        with common_polish_policy(self.module,native_high_skip_smoothing=True) as overrides:
            self.assertEqual(len(overrides),5)
            self.assertTrue(all(value==0 for value in vars(self.module).values()))
        self.assertEqual(vars(self.module),self.original)

    def test_restored_after_error(self):
        with self.assertRaises(RuntimeError):
            with common_polish_policy(self.module,native_high_skip_smoothing=True):
                raise RuntimeError('test')
        self.assertEqual(vars(self.module),self.original)


if __name__=='__main__': unittest.main()
