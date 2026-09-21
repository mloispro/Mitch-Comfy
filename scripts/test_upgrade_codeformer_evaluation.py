"""Regression tests for reference orientation and immutable preview audits."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageOps

SCRIPTS = Path(__file__).resolve().parent


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), SCRIPTS/name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExifEvaluationTests(unittest.TestCase):
    def test_every_evaluator_transposes_portrait_and_rotated_references(self):
        modules = [load_script(name) for name in (
            'test-upgrade-codeformer-feasibility.py',
            'evaluate-upgrade-codeformer-preview.py',
            'evaluate-upgrade-codeformer-pasteback.py',
            'preview-upgrade-shape-restoration.py',
            'evaluate-upgrade-v5-live-output.py',
            'verify-upgrade-v5-live-output.py')]
        with tempfile.TemporaryDirectory(prefix='upgrade-exif-test-') as folder:
            path = Path(folder)/'reference.jpg'
            pixels = np.zeros((32,48,3),dtype=np.uint8)
            pixels[:16,:24] = [240,30,10]
            pixels[16:,24:] = [10,50,230]
            for orientation in (1,3,6,8):
                exif = Image.Exif()
                exif[274] = orientation
                Image.fromarray(pixels).save(path,quality=95,exif=exif)
                before = path.read_bytes()
                with Image.open(path) as image:
                    expected = np.array(ImageOps.exif_transpose(image).convert('RGB'))
                for module in modules:
                    with self.subTest(module=module.__name__,orientation=orientation):
                        np.testing.assert_array_equal(module.read(path),expected)
                        self.assertEqual(path.read_bytes(),before)


if __name__ == '__main__':
    unittest.main()
