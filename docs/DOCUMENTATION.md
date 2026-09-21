# Keeping this documentation useful

The maintained guides are registered in [documentation-map.json](documentation-map.json).
The recorded review state is [documentation-review.json](documentation-review.json).
The checker is [scripts/project-docs.py](../scripts/project-docs.py), a Python standard-library tool.
It statically reads text; it does not import project modules, run tests, load models or contact a worker.

## Two different maintenance actions

```powershell
# Normal task: check the affected guides and their actual evidence; no global scan.
python scripts/project-docs.py --check --guide docs/STATUS.md --guide docs/DECISIONS.md

# Full maintenance/release audit: includes all guides and generated inventory.
python scripts/project-docs.py --check

# Rebuild discoverability from actual files. This does not accept guide changes.
python scripts/project-docs.py --refresh

# Only after reading the changed sources and updating/verifying the guide:
python scripts/project-docs.py --record-review docs/ARCHITECTURE.md --review-note "Checked the changed reference path against engine and tests"
```

Repeat `--record-review DOCUMENT` in one command when multiple guides have actually been reviewed.
Review notes should say what was checked. Do not mechanically record reviews to silence a failure.
Finish a bounded task with `--check --guide` for its affected guides. Refresh the inventory when
needed for discovery or a full audit; index drift elsewhere does not require unrelated prose reviews.
Use `--refresh` followed by full `--check` when maintaining the complete inventory.

## What the checks mean

- The inventory records current code, conventional test filenames, configuration/workflows and Markdown.
  Python symbols/imports/test functions come from AST parsing. Parse failures are exposed, not hidden.
- CODE-INDEX and TEST-INDEX cover source directories. LOCAL-CODE-INDEX holds code/tests from `work/`,
  `workflows/experiments/`, archives and checkpoints. Full JSON inventory retains every entry.
  This classification describes location, not acceptance or proof that every source utility is integrated.
- [.ignore](../.ignore) filters routine ripgrep searches; the inventory scans explicitly and remains
  complete for its declared roots. The search policy itself is indexed. Explicit evidence links and
  direct `--no-ignore` searches still reach historical records.
- Text hashes normalize UTF-8 BOM and CRLF/LF so a checkout newline conversion does not create false drift.
- Generated outputs are compared with a fresh scan; added/deleted/changed indexed files are detected.
- Each maintained guide watches its own text, declared source globs and linked local code/evidence files.
  Additions/deletions within globs and source-content changes require another guide review.
- Links to other registered maintained guides are navigation: their existence is checked, but their
  content does not automatically require reviewing the linking guide. Declare a real content
  dependency in `sources` or `watch` when another guide's definitions support a claim. Linked dated
  reports remain watched automatically. This prevents navigation-only review cascades.
- `--check --guide DOCUMENT` may be repeated. It checks only the named guides, direct local links,
  required sources and optional future evidence. It skips the global inventory and does not imply
  other guides are current. Unknown guides or use with a non-check mode fail rather than silently
  widening or skipping the requested check.
- A guide's optional `watch` globs also track future evidence. They may initially match no files;
  a later result or release receipt then triggers review even if it was never linked before.
  Add the active experiment's result paths when beginning that work. These watches are checked when
  the tool runs; they are not background monitors and do not automatically resume experiments.
- Local Markdown file/directory targets in the maintained guides must exist. Heading anchors, external URLs,
  historical report links, image authenticity and prose correctness are not automatically validated.
- A successful check does not prove that every relevant dependency was declared, every test passed,
  model/node compatibility is current, or every documented result generalizes.

The full inventory includes local `work/` evidence but excludes vendor/model trees, binaries and generated
run-receipt JSON. A clone without ignored `work/` should report missing evidence; do not silently remove its
provenance links to make that clone pass. The portable source of truth and local evidence have different backup needs.

Scan roots are `scripts`, `custom_nodes`, `workflows`, `docs`, `config`, `templates`, `patches`,
`archive`, `checkpoints/legacy-scripts`, `checkpoints/manifests` and `work`, plus root README/AGENTS.
Code and Markdown are indexed throughout those roots; structured configuration is limited to config,
templates, production and production-speed workflows and the scene manifest. Hidden caches, `.audit`, `local`, raw image/data
directories and other checkpoint binaries are outside this inventory. Historical result links still lead
to their exact graphs/receipts without copying all run JSON into the index.

## Which page to update

| Change | Documentation action |
| --- | --- |
| Public recipe/default/interface | Update STATUS, HOW-TO and the affected ARCHITECTURE/TESTING rows; preserve historical acceptance |
| New experiment result | Add a concise DECISIONS row or update its current conclusion; link completed result, exact recipe, diagnostics and visual review |
| New active experiment | Add its prospective result/release patterns to the affected guide's `watch` list so later evidence cannot be hidden by an index-only refresh |
| Better-supported next approach | Update OPTIMIZATION with evidence, uncertainty and a stopping criterion |
| New file/test or renamed symbol | Refresh generated indexes; update task routing if it creates a new entry point |
| Old claim superseded | Correct the current guide; keep dated evidence intact and link the newer result |

## Record an experiment compactly

Use the following fields in the experiment's own result note:

1. Observed failure and hypothesis; primary sources/conditioning mechanism when a new workflow is involved.
2. Exact control/candidate paths and hashes, changed variable, genuine reference roles/order and exclusions.
3. Runtime completion, immutable output/recipe references and measurement cohort.
4. Native-size and thumbnail review; raw numerical diagnostics separately.
5. Decision: accepted for a stated scope, qualified, rejected, or unresolved; reason and explicit limits.
6. Next action or closed-route condition. Update one current index row rather than appending competing “latest” paragraphs.

The previous long STATUS was copied byte-for-byte to
[STATUS-history-before-doc-rebuild-2026-09-09.md](STATUS-history-before-doc-rebuild-2026-09-09.md).
It remains a historical record with its original relative links. The current STATUS now carries concise conclusions.

[Practical validation](documentation-practical-check-2026-09-09.md) records three source-checked development
questions, the future-evidence gap found/fixed, and the separate trial needed to measure development speed.
