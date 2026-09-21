"""Build a local, static project index and check documentation freshness.

Standard library only. Never imports project code, contacts services or runs tests.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
GENERATED = Path("docs/generated")
MAP = Path("docs/documentation-map.json")
REVIEW = Path("docs/documentation-review.json")
ROOTS = ("scripts", "custom_nodes", "workflows", "docs", "config", "templates",
         "patches", "archive", "checkpoints/legacy-scripts", "checkpoints/manifests", "work")
SKIP = {".git", "__pycache__", "node_modules", ".venv", "venv", "vendor", "models", ".downloads"}
CODE = {".py", ".ps1", ".js", ".mjs", ".sh", ".bat", ".cmd"}
DATA = {".json", ".yaml", ".yml"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def digest(path: Path) -> str:
    # Text hashes intentionally survive Git's CRLF/LF conversion.
    return hashlib.sha256(read(path).encode("utf-8")).hexdigest()


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def files(root: Path) -> list[Path]:
    found = {root / name for name in ("README.md", "AGENTS.md", ".ignore") if (root / name).is_file()}
    for directory in ROOTS:
        for current, dirs, names in os.walk(root / directory, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in SKIP and not (Path(current) / d).is_symlink()
                             and (Path(current) / d).resolve() != (root / GENERATED).resolve())
            for name in names:
                path = Path(current) / name
                if path.is_symlink():
                    continue
                rel = path.relative_to(root).as_posix()
                if path.suffix in CODE or path.suffix == ".md":
                    found.add(path)
                elif path.suffix in DATA and (rel.startswith(("config/", "templates/", "workflows/production/", "workflows/production-speed/"))
                        or rel == "custom_nodes/ComfyUI-AIToolkit-Training/web/assets/scene-presets/manifest.json"):
                    if not name.startswith("local-"):
                        found.add(path)
    return sorted(found, key=lambda p: p.relative_to(root).as_posix())


def describe(path: Path, root: Path, verifier: str) -> dict:
    rel = path.relative_to(root).as_posix()
    source = read(path)
    kind = "code" if path.suffix in CODE else "document" if path.suffix == ".md" else "configuration/workflow"
    test = path.suffix in CODE and bool(re.match(r"test[_-]", path.name))
    record = {"path": rel, "kind": "test" if test else kind,
              "scope": "local evidence" if rel.startswith("work/") else
                       "experiment" if rel.startswith("workflows/experiments/") else
                       "archive" if rel.startswith(("archive/", "checkpoints/")) else "project",
              "sha256_text": hashlib.sha256(source.encode("utf-8")).hexdigest(),
              "lines": len(source.splitlines())}
    if path.suffix == ".md":
        record["title"] = next((s.lstrip("# ").strip() for s in source.splitlines() if s.startswith("# ")), path.stem)
    elif path.suffix == ".py":
        try:
            tree = ast.parse(source, filename=rel)
            record["symbols"] = [n.name for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]
            record["imports"] = sorted({("." * n.level + (n.module or "")) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
                                        | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names})
            record["test_functions"] = sorted(n.name for n in ast.walk(tree)
                                               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_"))
        except SyntaxError as exc:
            record["parse_error"] = f"{exc.msg} at line {exc.lineno}"
    if test:
        # An explicit reference is not proof of execution or successful coverage.
        record["referenced_by_main_verifier"] = (
            rel.startswith(("scripts/", "custom_nodes/ComfyUI-AIToolkit-Training/"))
            and path.name in verifier)
    return record


def inventory(root: Path) -> list[dict]:
    verifier = read(root / "scripts/verify.ps1") if (root / "scripts/verify.ps1").exists() else ""
    return [describe(p, root, verifier) for p in files(root)]


def cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").replace("`", "'")


def link(record: dict) -> str:
    return f"[{cell(record['path'])}](<../../{record['path']}>)"


def render(records: list[dict]) -> dict[Path, str]:
    counts = Counter(r["kind"] for r in records)
    outputs = {GENERATED / "repository-index.json": dumps({"schema_version": 1, "counts": dict(sorted(counts.items())), "files": records})}
    intro = ("Generated by `python scripts/project-docs.py --refresh`; do not edit by hand.\n\n"
             "Static discovery only: entries, names and imports are not executed-test results or acceptance decisions. "
             "`work/` is ignored by Git and local to this machine. Vendor/model directories, binaries, run receipts "
             "and generated indexes are excluded. Full symbols/imports and normalized-text hashes are in "
             "[repository-index.json](repository-index.json). Use search within these indexes.\n\n")
    for name, title, predicate in (
        ("CODE-INDEX.md", "Current source and configuration", lambda r: r["scope"] == "project" and r["kind"] in {"code", "configuration/workflow"}),
        ("LOCAL-CODE-INDEX.md", "Historical and experimental code and tests", lambda r: r["scope"] != "project" and r["kind"] in {"code", "test", "configuration/workflow"}),
        ("TEST-INDEX.md", "Current test file index", lambda r: r["scope"] == "project" and r["kind"] == "test"),
        ("EVIDENCE-INDEX.md", "Documentation and evidence index", lambda r: r["kind"] == "document"),
    ):
        selected = [r for r in records if predicate(r)]
        content = f"# {title}\n\n{intro}{len(selected)} files.\n\n"
        if name in {"CODE-INDEX.md", "TEST-INDEX.md"}:
            content += ("Directory scope only: current source locations can still contain unintegrated experiments. "
                        "Archived/local/experimental-directory entries are in "
                        "[LOCAL-CODE-INDEX](LOCAL-CODE-INDEX.md); all entries remain in the JSON inventory.\n\n")
        if name == "TEST-INDEX.md":
            content += ("Naming rule: code filenames starting `test_` or `test-`; other checks/runners remain in the code indexes. "
                        "Main verifier = explicit filename reference in `scripts/verify.ps1`, not transitive coverage. "
                        "Unlisted tests are not automatically missing requirements. Review effects before running historical tests.\n\n"
                        "| File | Main verifier reference | Python test functions (first six) |\n| --- | --- | --- |\n")
            for r in selected:
                names = r.get("test_functions", [])
                detail = ", ".join(names[:6]) + (f" (+{len(names)-6})" if len(names) > 6 else "")
                content += f"| {link(r)} | {'yes' if r['referenced_by_main_verifier'] else 'no'} | {cell(detail or r.get('parse_error', 'inspect file'))} |\n"
        elif name == "EVIDENCE-INDEX.md":
            content += "| File | Recorded title (not a verified conclusion) |\n| --- | --- |\n"
            for r in selected:
                content += f"| {link(r)} | {cell(r['title'])} |\n"
        else:
            content += "| File | Scope | Top-level Python symbols (first six) |\n| --- | --- | --- |\n"
            for r in selected:
                symbols = r.get("symbols", [])
                detail = ", ".join(symbols[:6]) + (f" (+{len(symbols)-6})" if len(symbols) > 6 else "")
                content += f"| {link(r)} | {r['scope']} | {cell(detail or r.get('parse_error', 'inspect file'))} |\n"
        outputs[GENERATED / name] = content
    return outputs


def local_links(root: Path, document: str) -> list[Path]:
    text = re.sub(r"```.*?```", "", read(root / document), flags=re.S)
    targets = re.findall(r"\[[^\]]*\]\((<[^>]+>|[^)\s]+)\)", text)
    paths = []
    for target in targets:
        target = target.strip("<>")
        if target.startswith("#") or urlsplit(target).scheme:
            continue
        target = unquote(target.split("#", 1)[0])
        resolved = ((root / document).parent / target).resolve()
        if not resolved.is_relative_to(root.resolve()):
            raise ValueError(f"{document}: local link escapes repository: {target}")
        paths.append(resolved)
    return paths


def review_inputs(root: Path, guide: dict, maintained: frozenset[str] = frozenset()) -> dict[str, str]:
    selected = {root / guide["document"]}
    for pattern in guide.get("sources", []):
        matches = [p for p in root.glob(pattern) if p.is_file()]
        if not matches:
            raise ValueError(f"{guide['document']}: source pattern has no files: {pattern}")
        selected.update(matches)
    # Active evidence can be absent at review time. Its later arrival must still
    # invalidate the guide, without treating a missing future result as an error.
    for pattern in guide.get("watch", []):
        selected.update(p for p in root.glob(pattern) if p.is_file())
    # Maintained-guide links are navigation. Watch their content only when an
    # explicit source/watch pattern declares a factual dependency. Dated reports
    # and linked code remain automatic dependencies; all links must still exist.
    for path in local_links(root, guide["document"]):
        if not path.exists():
            raise ValueError(f"{guide['document']}: missing link: {path.relative_to(root)}")
        if (path.is_file() and (path.suffix in CODE | DATA | {".md"} or path.name == ".ignore")
                and path.relative_to(root).as_posix() not in maintained
                and path.relative_to(root) != REVIEW and GENERATED not in path.relative_to(root).parents):
            selected.add(path)
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted(selected)}


def check_reviews(root: Path, guides: list[dict], saved: dict,
                  maintained: frozenset[str] = frozenset()) -> list[str]:
    errors = []
    for guide in guides:
        name = guide["document"]
        try:
            current = review_inputs(root, guide, maintained)
        except (ValueError, OSError) as exc:
            errors.append(str(exc))
            continue
        previous = saved.get(name, {}).get("sources", {})
        changed = sorted(p for p in current.keys() | previous.keys() if current.get(p) != previous.get(p))
        if changed or name not in saved:
            errors.append(f"Review {name}: {len(changed)} added/changed/missing sources: " + ", ".join(changed[:8]))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--refresh", action="store_true", help="Regenerate static indexes only; does not certify guide accuracy")
    mode.add_argument("--check", action="store_true", help="Check index drift, guide sources and local links; no writes")
    mode.add_argument("--record-review", action="append", metavar="DOCUMENT", help="Record sources after reading/updating this guide; repeat per reviewed guide")
    parser.add_argument("--guide", action="append", metavar="DOCUMENT",
                        help="With --check, check only these guides and their evidence; skip global indexes (repeatable)")
    parser.add_argument("--review-note", help="Required with --record-review: what was actually checked")
    args = parser.parse_args(argv)
    if args.guide and not args.check:
        parser.error("--guide requires --check")
    guides = json.loads(read(ROOT / MAP))["guides"]
    by_name = {g["document"]: g for g in guides}
    maintained = frozenset(by_name)
    requested = args.guide or args.record_review or []
    for name in requested:
        if name not in by_name:
            parser.error(f"Unknown guide: {name}")
    saved = json.loads(read(ROOT / REVIEW)) if (ROOT / REVIEW).exists() else {}
    if args.record_review:
        if not args.review_note:
            parser.error("--record-review requires --review-note")
        for name in args.record_review:
            saved[name] = {"reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
                           "note": args.review_note, "sources": review_inputs(ROOT, by_name[name], maintained)}
        write(ROOT / REVIEW, dumps(saved))
        print(f"Recorded {len(args.record_review)} guide reviews. This records human/agent review, not proof of prose correctness.")
        return 0
    if args.guide:
        selected = [by_name[name] for name in dict.fromkeys(args.guide)]
        errors = check_reviews(ROOT, selected, saved, maintained)
        if errors:
            print("\n".join(errors))
            return 1
        print(f"Scoped documentation check passed: {len(selected)} guides; local links and recorded evidence hashes agree.")
        print("Global indexes and other guides were not checked. Prose correctness and image quality are not certified.")
        return 0
    records = inventory(ROOT)
    outputs = render(records)
    if args.refresh:
        for path, value in outputs.items():
            write(ROOT / path, value)
        print(f"Indexed {len(records)} text files into {len(outputs)} files; no project code executed.")
        return 0
    errors = []
    for path, expected in outputs.items():
        if not (ROOT / path).exists() or read(ROOT / path) != expected:
            errors.append(f"Stale generated index: {path.as_posix()} (run --refresh)")
    errors.extend(check_reviews(ROOT, guides, saved, maintained))
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Documentation check passed: {len(records)} indexed files, {len(guides)} guides; local links and recorded source hashes agree.")
    print("This checks freshness, not model quality, live runtime state, test success or completeness of prose.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
