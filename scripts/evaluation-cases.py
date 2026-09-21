"""Find pinned image-evaluation cases and prepare local reviews; never run inference."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "config/evaluation-cases.json"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    with Path(path).open("rb") as stream:
        result = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
        return result.hexdigest()


def resolve(path, root=ROOT):
    result = (root / path).resolve()
    if not any(result.is_relative_to(base.resolve()) for base in (root, root.parent / "ComfyUI")):
        raise ValueError(f"Evidence is outside this project and its ComfyUI installation: {path}")
    return result


def pin(path, root=ROOT):
    resolved = resolve(path, root)
    return {"path": str(resolved), "sha256": digest(resolved)}


def load_catalog(path=CATALOG):
    data = read_json(path)
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported evaluation catalog version")
    ids = [case["id"] for case in data["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case id")
    for case in data["cases"]:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", case["id"]):
            raise ValueError("Invalid case id")
        if case["recorded_outcome"] not in ("qualified", "rejected", "accepted"):
            raise ValueError("Unknown historical outcome")
        refs = case["identity_reference_ids"]
        if not refs or len(refs) != len(set(refs)) or not set(refs) <= data["references"].keys():
            raise ValueError(f"Invalid reference cohort: {case['id']}")
        excluded = case.get("excluded_identity_reference_ids", [])
        if set(refs) & set(excluded) or not set(excluded) <= data["references"].keys():
            raise ValueError(f"Excluded source in scoring cohort: {case['id']}")
        for key in ("photo", "recipe", "diagnostics", "visual_review", "conclusion"):
            if key not in case["artifacts"]:
                raise ValueError(f"Missing {key}: {case['id']}")
        if "source" in case["artifacts"]:
            source_hash = case["artifacts"]["source"]["sha256"].lower()
            if any(data["references"][ref]["sha256"].lower() == source_hash for ref in refs):
                raise ValueError("Source bytes cannot also be an independent identity reference")
    return data


def select(data, case_id=None, area=None, query=None):
    cases = data["cases"]
    if case_id:
        cases = [case for case in cases if case["id"] == case_id]
    if area:
        cases = [case for case in cases if case["area"] == area]
    if query:
        words = query.casefold().split()
        cases = [case for case in cases if all(word in json.dumps(case).casefold() for word in words)]
    if not cases:
        raise ValueError("No matching case; this small catalog does not cover the entire project")
    return cases


def evidence(data, case):
    return {**case["artifacts"], **{
        f"identity_reference:{ref}": data["references"][ref]
        for ref in case["identity_reference_ids"]
    }, **{
        f"excluded_identity_reference:{ref}": data["references"][ref]
        for ref in case.get("excluded_identity_reference_ids", [])
    }}


def check(data, cases, root=ROOT):
    checked = set()
    for case in cases:
        for role, record in evidence(data, case).items():
            expected = record["sha256"].lower()
            if not re.fullmatch(r"[a-f0-9]{64}", expected):
                raise ValueError(f"Invalid evidence hash: {case['id']}/{role}")
            path = resolve(record["path"], root)
            key = (path, expected)
            if key not in checked:
                if not path.is_file() or digest(path) != expected:
                    raise ValueError(f"Missing or changed evidence: {case['id']}/{role}: {path}")
                checked.add(key)
    return len(checked)


def prepare_review(data, case, candidate, candidate_recipe, change, output, root=ROOT):
    check(data, [case], root)
    candidate_pin, recipe_pin = pin(candidate, root), pin(candidate_recipe, root)
    if Path(candidate_pin["path"]).suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        raise ValueError("Candidate must be an image")
    graph = read_json(recipe_pin["path"])
    graph = graph.get("prompt", graph) if isinstance(graph, dict) else None
    if not isinstance(graph, dict) or not graph or not all(
        isinstance(node, dict) and isinstance(node.get("class_type"), str)
        and isinstance(node.get("inputs"), dict) for node in graph.values()
    ):
        raise ValueError("Candidate recipe must be an executed API graph, not a UI workflow")
    destination = Path(output).resolve()
    if not destination.is_relative_to((root / "work/evaluation-reviews").resolve()):
        raise ValueError("Write review bundles under work/evaluation-reviews/<new-name>")
    if not change.strip():
        raise ValueError("Describe the proposed change before preparing a review")
    records = {role: {**record, "path": str(resolve(record["path"], root))}
               for role, record in evidence(data, case).items()}
    review = {
        "schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "case_id": case["id"], "change": change, "status": "pending_review",
        "historical_case": copy.deepcopy(case), "historical_evidence": records,
        "candidate": candidate_pin, "candidate_recipe": recipe_pin,
        "scope": "Preparation only. Hash agreement is not runtime attribution, a new score or image acceptance.",
        "runtime_attribution": {"status": "unreviewed", "evidence": None},
        "numerical_review": {"status": "unreviewed", "evidence": None},
        "visual_review": [{"criterion": criterion, "native": None, "thumbnail": None, "notes": ""}
                          for criterion in case["visual_checks"]],
        "decision": {"status": "unreviewed", "scope": "", "reason": ""},
    }
    esc = html.escape
    def picture(label, record):
        uri = esc(Path(record["path"]).as_uri(), quote=True)
        return (f'<section><h2>{esc(label)}</h2><img class="thumb" src="{uri}" alt="{esc(label)}">'
                f'<details><summary>Native size</summary><div class="native"><img src="{uri}" '
                f'alt="{esc(label)}"></div></details></section>')
    pictures = picture("Candidate — unreviewed", candidate_pin)
    pictures += picture("Historical comparison — " + case["recorded_outcome"], records["photo"])
    if "source" in records:
        pictures += picture("Genuine source — excluded from independent scoring", records["source"])
    for ref in case["identity_reference_ids"]:
        pictures += picture("Genuine identity reference: " + ref, records["identity_reference:" + ref])
    page = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Local image review</title>'
            '<style>body{font:16px system-ui;margin:24px;background:#fafafa;color:#222}'
            '.thumb{max-width:320px;max-height:320px}section{margin:24px 0}'
            '.native{overflow:auto}.native img{max-width:none}summary{cursor:pointer}</style>'
            f'<h1>{esc(case["label"])}</h1><p>{esc(change)}</p>'
            '<p>Review native and thumbnail views before opening candidate scores. '
            'This page records no verdict; fill the separate review.json after evaluation.</p>'
            '<ul>' + ''.join(f'<li>{esc(item)}</li>' for item in case["visual_checks"]) + '</ul>'
            + pictures + '</html>')
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    (destination / "review.html").write_text(page, encoding="utf-8")
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("list", "check"):
        command = sub.add_parser(action)
        command.add_argument("--area", choices=("solo", "group", "upgrade"))
        command.add_argument("--query")
        command.add_argument("--case")
    show = sub.add_parser("show")
    show.add_argument("case")
    review = sub.add_parser("review")
    review.add_argument("case")
    review.add_argument("--candidate", required=True, type=Path)
    review.add_argument("--candidate-recipe", required=True, type=Path)
    review.add_argument("--change", required=True)
    review.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        data = load_catalog()
        cases = select(data, args.case, getattr(args, "area", None), getattr(args, "query", None))
        if args.action == "list":
            for case in cases:
                print(f"{case['id']} | {case['area']} | historical {case['recorded_outcome']} | {case['label']}")
        elif args.action == "check":
            count = check(data, cases)
            print(f"Verified {count} unique evidence files for {len(cases)} cases. No new image acceptance or live checks.")
        elif args.action == "show":
            check(data, cases)
            print(json.dumps({"case": cases[0], "references": {
                key: data["references"][key] for key in cases[0]["identity_reference_ids"]
            }}, indent=2))
        else:
            print(prepare_review(data, cases[0], args.candidate, args.candidate_recipe,
                                 args.change, args.output))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(f"Evaluation cases: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
