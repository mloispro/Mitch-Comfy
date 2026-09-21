"""Run-local raw-face reuse: isolation, invalidation and unchanged caller reports."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

import numpy as np


spec = importlib.util.spec_from_file_location("likeness_under_test", Path(__file__).with_name("evaluate-face-likeness.py"))
likeness = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"insightface.app": types.SimpleNamespace(FaceAnalysis=Mock())}):
    spec.loader.exec_module(likeness)


class Face(dict):
    def __getattr__(self, name):
        return self[name]

    @property
    def normed_embedding(self):
        return self.embedding / np.linalg.norm(self.embedding)


def faces(value=1):
    return [Face(bbox=np.array([0, 0, 2, 2], dtype=np.float32), det_score=np.float32(.9),
                 embedding=np.array([1, value / 10, .2], dtype=np.float32)),
            Face(bbox=np.array([0, 0, 1, 1], dtype=np.float32), det_score=np.float32(.8),
                 embedding=np.array([.2, 1, .3], dtype=np.float32))]


class FaceReuseTests(unittest.TestCase):
    def test_identical_pixels_reuse_all_faces_with_independent_values(self):
        original = faces()
        backend = Mock(get=Mock(return_value=original))
        cache = likeness._RunFaceCache(backend)
        pixels = np.zeros((4, 5, 3), dtype=np.uint8)
        first = cache.get(pixels)
        expected = original[0].normed_embedding.copy()
        first[0].embedding[:] = 99
        first[0].bbox[:] = 0
        second = cache.get(np.asfortranarray(pixels))
        backend.get.assert_called_once()
        self.assertEqual(len(second), 2)
        self.assertEqual(second[0].bbox.dtype, np.float32)
        np.testing.assert_array_equal(second[0].normed_embedding, expected)
        for actual, initial in zip(second, original):
            for key in initial:
                np.testing.assert_array_equal(actual[key], initial[key])
        self.assertIsNot(second[0], original[0])

    def test_changed_pixels_shape_or_dtype_require_new_inference(self):
        backend = Mock(get=Mock(return_value=faces()))
        cache = likeness._RunFaceCache(backend)
        pixels = np.zeros((2, 2, 3), dtype=np.uint8)
        cache.get(pixels)
        pixels[0, 0, 0] = 1
        cache.get(pixels)
        cache.get(pixels.reshape(1, 4, 3))
        cache.get(pixels.view(np.int8))
        self.assertEqual(backend.get.call_count, 4)

    def test_errors_are_not_cached_and_valid_empty_detection_is(self):
        backend = Mock(get=Mock(side_effect=[RuntimeError("inference failed"), []]))
        cache = likeness._RunFaceCache(backend)
        pixels = np.zeros((2, 2, 3), dtype=np.uint8)
        with self.assertRaisesRegex(RuntimeError, "inference failed"):
            cache.get(pixels)
        self.assertEqual(cache.get(pixels), [])
        self.assertEqual(cache.get(pixels), [])
        self.assertEqual(backend.get.call_count, 2)

    def test_analyzers_and_runs_do_not_share_records(self):
        first, second = Mock(get=Mock(return_value=faces(1))), Mock(get=Mock(return_value=faces(9)))
        pixels = np.zeros((2, 2, 3), dtype=np.uint8)
        a = likeness._RunFaceCache(first).get(pixels)
        b = likeness._RunFaceCache(second).get(pixels)
        self.assertFalse(np.array_equal(a[0].embedding, b[0].embedding))
        self.assertEqual(first.get.call_count, 1)
        self.assertEqual(second.get.call_count, 1)

    def test_main_keeps_distinct_scoring_and_calibration_cohorts_and_exact_report(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / f"image-{n}.png" for n in range(4)]
            for path in paths:
                path.write_bytes(b"existence fixture; decoder is mocked")
            pixels = {str(path): np.full((4, 4, 3), n + 1, dtype=np.uint8)
                      for n, path in enumerate(paths)}
            args = types.SimpleNamespace(reference=list(map(str, paths[:2])),
                calibration_reference=list(map(str, paths[1:3])), candidate=[str(paths[3])],
                candidate_label=["candidate"], json_output=None, insightface_root=None)

            def run(cached):
                backend = Mock(get=Mock(side_effect=lambda image: faces(int(image[0, 0, 0]))))
                output = io.StringIO()
                wrapper = likeness._RunFaceCache if cached else lambda app: app
                with patch.object(likeness, "parse_args", return_value=args), \
                     patch.object(likeness, "FaceAnalysis", return_value=backend), \
                     patch.object(likeness, "_RunFaceCache", wrapper), \
                     patch.object(likeness.cv2, "imread", side_effect=lambda path, flags: pixels[path]), \
                     contextlib.redirect_stdout(output):
                    likeness.main()
                return json.loads(output.getvalue()), backend.get.call_count

            baseline, old_calls = run(False)
            candidate, new_calls = run(True)
            self.assertEqual(candidate, baseline)
            self.assertEqual((old_calls, new_calls), (5, 4))
            self.assertEqual(candidate["scoring_references"]["paths"], list(map(str, paths[:2])))
            self.assertEqual(candidate["reference_calibration"]["paths"], list(map(str, paths[1:3])))


if __name__ == "__main__":
    unittest.main()
