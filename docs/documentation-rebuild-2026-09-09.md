# Documentation rebuild audit — September 9, 2026

This change reorganizes project knowledge and adds static discovery/freshness checks. It does not
change generation code, public workflow JSON, model weights, acceptance thresholds or frozen experiments.
Existing uncommitted project work was retained. No generation, model loading, worker restart, upload,
download, training, commit or publication was performed for this documentation change.

## Source review

The maintained guides were checked against public workflow defaults, node registration, public wrappers,
engine reference order and model/sampling constants, shared finishing/preset/UI files, verifier entry points,
representative test implementations, and the linked completed results.

The static inventory additionally discovers code/test/Markdown throughout its declared roots, including
ignored local experiment code. AST parsing is not a semantic audit. No claim is made that every source
file was read in full, every historical assertion revalidated, or every indexed test executed.

The previous STATUS was preserved byte-for-byte as
[STATUS-history-before-doc-rebuild-2026-09-09.md](STATUS-history-before-doc-rebuild-2026-09-09.md),
SHA256 `CB76EF64F37B2418B41AD1D7FC0E23A555212BC2C89925CC2B77D1D12BE2D81C`.
Its dated histories remain unchanged. Current STATUS separates saved production behavior, qualified
source-preserving experiments, failed Group refinements, unproven stronger High and unresolved caching work.

## Validation performed

- Seven documentation-tool tests passed: source edits/additions/deletions, missing evidence links,
  implicit linked-source tracking, normalized hashes, static-only indexing, exclusions, parse-failure visibility
  and refusal to accept an unreviewed guide edit merely because the index was refreshed.
- Twenty-two existing Python tests passed: scene presets, visual-preset reporting, genuine reference-profile
  presets and Upgrade source/report contracts.
- All three existing JavaScript suites passed: visual-scene/prompt/widget behavior, attractiveness migration
  and production GPU guard behavior in their local harnesses.
- Local links and recorded source hashes for the maintained guides were checked by `project-docs.py --check`.
- `git diff --check` passed; existing Git line-ending conversion notices are informational.

No full live environment verifier or image acceptance run was needed for this documentation-only change.
The test map distinguishes commands that read live services, offline checks and optional smoke generation.
The generated inventory holds exact current file counts; this audit avoids hard-coding counts that change
when documentation is added. Review timestamps and normalized source hashes live in
[documentation-review.json](documentation-review.json).

## Maintenance behavior

`--refresh` updates the indexes without accepting prose claims. `--check` fails when indexed contents
or a guide's watched sources change. `--record-review` requires an explicit guide and a review note.
Missing local evidence is reported instead of being silently treated as verified. See
[DOCUMENTATION](DOCUMENTATION.md) for scope and limitations.
