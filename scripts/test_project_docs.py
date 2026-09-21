"""Failure-path checks for the documentation freshness tool (CPU/standard library)."""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("project_docs", Path(__file__).with_name("project-docs.py"))
docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs)


class DocumentationChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_inventory_never_executes_code_and_finds_local_tests(self):
        self.put("scripts/danger.py", "raise RuntimeError('must never execute')\n")
        self.put("work/probe/test_sample.py", "def test_sample():\n    pass\n")
        self.put("work/vendor/test_external.py", "bad syntax here")
        self.put("docs/generated/old.md", "# Recursive index must be excluded")
        records = {r["path"]: r for r in docs.inventory(self.root)}
        self.assertEqual(set(records), {"scripts/danger.py", "work/probe/test_sample.py"})
        self.assertEqual(records["work/probe/test_sample.py"]["test_functions"], ["test_sample"])

    def test_inventory_includes_production_speed_without_widening_json_scope(self):
        included = {"workflows/production/original.json", "workflows/production-speed/group.json"}
        excluded = {"workflows/production-speed/local-private.json",
                    "workflows/production-speed-old/retired.json",
                    "workflows/experiments/probe.json", "work/run/receipt.json"}
        for name in included | excluded:
            self.put(name, '{"nodes": []}\n')
        records = docs.inventory(self.root)
        self.assertEqual({r["path"] for r in records}, included)
        self.assertTrue(all(r["scope"] == "project" and r["kind"] == "configuration/workflow"
                            for r in records))
        current_index = docs.render(records)[docs.GENERATED / "CODE-INDEX.md"]
        for name in included:
            self.assertIn(name, current_index)
        for name in excluded:
            self.assertNotIn(name, current_index)

    def test_review_detects_source_changes_additions_and_deletions(self):
        self.put("docs/guide.md", "# Guide\n")
        source = self.put("scripts/one.py", "value = 1\n")
        guide = {"document": "docs/guide.md", "sources": ["scripts/*.py"]}
        saved = {"docs/guide.md": {"sources": docs.review_inputs(self.root, guide)}}
        self.assertEqual(docs.check_reviews(self.root, [guide], saved), [])
        source.write_text("value = 2\n")
        self.put("scripts/two.py", "value = 3\n")
        error = docs.check_reviews(self.root, [guide], saved)[0]
        self.assertIn("scripts/one.py", error)
        self.assertIn("scripts/two.py", error)
        source.unlink()
        self.assertIn("scripts/one.py", docs.check_reviews(self.root, [guide], saved)[0])

    def test_missing_evidence_link_is_not_silently_accepted(self):
        self.put("docs/guide.md", "[evidence](<../work/missing result.md>)")
        with self.assertRaisesRegex(ValueError, "missing link"):
            docs.review_inputs(self.root, {"document": "docs/guide.md"})

    def test_linked_evidence_is_watched_without_explicit_glob(self):
        self.put("docs/guide.md", "[result](<../work/a result.md>)\n[search policy](../.ignore)\n[web](https://example.com)\n")
        self.put("work/a result.md", "# Completed result\n")
        self.put(".ignore", "/archive/\n")
        inputs = docs.review_inputs(self.root, {"document": "docs/guide.md"})
        self.assertEqual(set(inputs), {"docs/guide.md", "work/a result.md", ".ignore"})

    def test_refresh_cannot_accept_an_unreviewed_guide_edit(self):
        self.put("docs/guide.md", "# Verified claim\n")
        guide = {"document": "docs/guide.md"}
        saved = {guide["document"]: {"sources": docs.review_inputs(self.root, guide)}}
        self.put("docs/guide.md", "# Changed claim needing review\n")
        # Refreshing generated outputs does not change the saved source-review state.
        for path, content in docs.render(docs.inventory(self.root)).items():
            docs.write(self.root / path, content)
        self.assertIn("docs/guide.md", docs.check_reviews(self.root, [guide], saved)[0])

    def test_hash_normalizes_bom_and_windows_line_endings(self):
        first = self.put("first.md", "a\nb\n")
        second = self.root / "second.md"
        second.write_bytes(b"\xef\xbb\xbfa\r\nb\r\n")
        self.assertEqual(docs.digest(first), docs.digest(second))

    def test_new_result_invalidates_guide_even_when_it_did_not_exist_at_review(self):
        self.put("docs/status.md", "# Experiment is unresolved\n")
        guide = {"document": "docs/status.md", "watch": ["work/active/*.md", "work/active/RELEASE.json"]}
        saved = {guide["document"]: {"sources": docs.review_inputs(self.root, guide)}}
        self.assertEqual(docs.check_reviews(self.root, [guide], saved), [])
        self.put("work/active/RESULT.md", "# Completed\n")
        self.put("work/active/RELEASE.json", '{"released": false}\n')
        errors = docs.check_reviews(self.root, [guide], saved)
        self.assertIn("work/active/RESULT.md", errors[0])
        self.assertIn("work/active/RELEASE.json", errors[0])
        for path, content in docs.render(docs.inventory(self.root)).items():
            docs.write(self.root / path, content)
        self.assertEqual(docs.check_reviews(self.root, [guide], saved), errors)

    def test_inventory_changes_and_parse_failure_are_visible(self):
        self.put("scripts/broken.py", "def broken(\n")
        records = docs.inventory(self.root)
        self.assertIn("parse_error", records[0])
        before = docs.render(records)
        self.put("scripts/new.py", "def new():\n    pass\n")
        after = docs.render(docs.inventory(self.root))
        self.assertNotEqual(before, after)
        data = json.loads(after[docs.GENERATED / "repository-index.json"])
        self.assertEqual(data["counts"]["code"], 2)

    def test_current_indexes_exclude_history_without_losing_inventory(self):
        expected = {
            "scripts/current.py": "value = 1\n",
            "scripts/test_current.py": "def test_current(): pass\n",
            "archive/old.py": "value = 0\n",
            "checkpoints/legacy-scripts/test_old.py": "def test_old(): pass\n",
            "workflows/experiments/probe/test_probe.py": "def test_probe(): pass\n",
            "work/proof/probe.py": "value = 2\n",
            ".ignore": "/archive/\n",
        }
        for name, value in expected.items():
            self.put(name, value)
        records = docs.inventory(self.root)
        outputs = docs.render(records)
        current_code = outputs[docs.GENERATED / "CODE-INDEX.md"]
        current_tests = outputs[docs.GENERATED / "TEST-INDEX.md"]
        history = outputs[docs.GENERATED / "LOCAL-CODE-INDEX.md"]
        self.assertIn("scripts/current.py", current_code)
        self.assertIn("scripts/test_current.py", current_tests)
        for name in expected:
            if name.startswith(("archive/", "checkpoints/", "workflows/experiments/", "work/")):
                self.assertNotIn(name, current_code)
                self.assertNotIn(name, current_tests)
                self.assertIn(name, history)
        inventory = json.loads(outputs[docs.GENERATED / "repository-index.json"])
        self.assertEqual({r["path"] for r in inventory["files"]}, set(expected))

    def test_navigation_edit_does_not_cascade_but_missing_link_still_fails(self):
        self.put("docs/a.md", "[navigation](b.md)\n[result](../work/result.md)\n")
        self.put("docs/b.md", "# Another maintained guide\n")
        self.put("work/result.md", "# Evidence\n")
        guide = {"document": "docs/a.md"}
        maintained = frozenset({"docs/a.md", "docs/b.md"})
        saved = {guide["document"]: {"sources": docs.review_inputs(self.root, guide, maintained)}}
        self.put("docs/b.md", "# Updated navigation\n")
        self.assertEqual(docs.check_reviews(self.root, [guide], saved, maintained), [])
        self.put("work/result.md", "# New result\n")
        self.assertIn("work/result.md", docs.check_reviews(self.root, [guide], saved, maintained)[0])
        (self.root / "docs/b.md").unlink()
        self.assertIn("missing link", docs.check_reviews(self.root, [guide], saved, maintained)[0])

    def test_explicit_dependency_on_maintained_guide_still_requires_review(self):
        self.put("docs/a.md", "[definitions](b.md)\n")
        self.put("docs/b.md", "# Required definitions\n")
        guide = {"document": "docs/a.md", "sources": ["docs/b.md"]}
        maintained = frozenset({"docs/a.md", "docs/b.md"})
        saved = {guide["document"]: {"sources": docs.review_inputs(self.root, guide, maintained)}}
        self.put("docs/b.md", "# Changed definitions\n")
        self.assertIn("docs/b.md", docs.check_reviews(self.root, [guide], saved, maintained)[0])

    def test_scoped_cli_checks_relevant_evidence_without_global_inventory(self):
        self.put("docs/a.md", "[navigation](b.md)\n[result](../work/a/result.md)\n")
        self.put("docs/b.md", "[result](../work/b/result.md)\n")
        self.put("work/a/result.md", "# A evidence\n")
        self.put("work/b/result.md", "# B evidence\n")
        guides = [{"document": "docs/a.md"}, {"document": "docs/b.md"}]
        maintained = frozenset(g["document"] for g in guides)
        self.put(str(docs.MAP), json.dumps({"guides": guides}))
        self.put(str(docs.REVIEW), json.dumps({g["document"]: {
            "sources": docs.review_inputs(self.root, g, maintained)} for g in guides}))
        self.put("work/b/result.md", "# Unrelated new result\n")
        output = io.StringIO()
        with patch.object(docs, "ROOT", self.root), patch.object(docs, "inventory") as scan, contextlib.redirect_stdout(output):
            self.assertEqual(docs.main(["--check", "--guide", "docs/a.md"]), 0)
            self.assertEqual(docs.main(["--check", "--guide", "docs/b.md"]), 1)
            self.put("work/a/result.md", "# Relevant new result\n")
            self.assertEqual(docs.main(["--check", "--guide", "docs/a.md"]), 1)
            scan.assert_not_called()
        self.assertIn("other guides were not checked", output.getvalue())
        self.assertIn("work/a/result.md", output.getvalue())

    def test_scoped_cli_rejects_unknown_guide_and_incompatible_mode(self):
        self.put(str(docs.MAP), '{"guides": []}')
        with patch.object(docs, "ROOT", self.root), contextlib.redirect_stderr(io.StringIO()):
            for argv in (["--check", "--guide", "docs/typo.md"],
                         ["--refresh", "--guide", "docs/a.md"]):
                with self.subTest(argv=argv), self.assertRaises(SystemExit) as raised:
                    docs.main(argv)
                self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
