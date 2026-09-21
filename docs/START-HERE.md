# Development entry point

Read this page and [current status](STATUS.md), then open only the relevant row below.
The aim is to find the implementation, its acceptance evidence and its smallest useful
check before making a change. Detailed history is retained; it is not required startup reading.

The repository skill [mitch-comfy-development](../.agents/skills/mitch-comfy-development/SKILL.md)
routes development through these existing guides and the [pinned image cases](../config/evaluation-cases.json).
Use `python scripts/evaluation-cases.py list --area solo` (or `group` / `upgrade`) to find a starting
comparison; `show <case-id>` checks its evidence before displaying it. The five cases cover bounded
accepted/qualified and rejected examples, not the whole project. See [review preparation](TESTING.md#pinned-image-review-cases)
for an existing candidate. Other changes keep their ordinary focused checks.

## Find the next file

| Task | Read first | Implementation / evidence | Check |
| --- | --- | --- | --- |
| Solo identity, reference angle, prompt behavior | [Architecture](ARCHITECTURE.md) | `flux2_klein9b_mitch_identity_studio*.py`, `flux2_klein9b_scene_presets.py`; [scene coverage](../work/9b-readiness-resume-20260907/COVERAGE-MATRIX.md) | [Preset and UI checks](TESTING.md#presets-and-browser-controls), then actual public-mode evidence |
| Group likeness, wrong person, bystander leakage | [Group decisions](DECISIONS.md#group) | `flux2_klein9b_group_scene_studio*.py`; [latest masked result](../workflows/experiments/group-masked-strength110-20260908/ROOT-RESULT.md) | Preserve geometric face selection and every bystander score; [test map](TESTING.md) |
| Upgrade source drift, hair, eyes or High | [Upgrade decisions](DECISIONS.md#upgrade) | `flux2_klein9b_photo_realism_upgrade.py`, deterministic polish / gaze / attractiveness modules | [Upgrade checks](TESTING.md#upgrade-and-image-finishing); compare source, raw and final |
| Gallery, custom prompt, widget migration, wrong GPU UI | [Architecture](ARCHITECTURE.md#browser-and-preset-contract) | `web/visual_scene_presets.js`, `web/upgrade_attractiveness.js`, `web/production_gpu_guard.js` | Three focused Node commands in [TESTING](TESTING.md#presets-and-browser-controls) |
| Faster diagnosis or generation | [Optimization priorities](OPTIMIZATION.md) | Start from the feature-reuse proof or existing speed evidence | Exact scoring parity for diagnostic changes; matched quality/timing for generation |
| Use the separate Production Speed section | [Speed operating guide](production-speed.md) | Three bounded workflows under `workflows/production-speed`; [normal-Run release](../work/production-speed-rollout/RESULTS.md) | Runtime, visual and genuine-reference checks are recorded separately; original production is unchanged |
| Models, hashes, worker visibility, rollback | [Operating guide](HOW-TO.md) | [Baseline registry](../config/frozen-baselines.json), [recorded dependencies](../config/dependencies.lock.json), `scripts/verify*.ps1` | [Environment checks](TESTING.md#environment-and-public-workflow-checks) |
| Disk cleanup, unfinished experiments, recovery copies | [Cleanup decisions](CLEANUP.md) | Exact duplicate inventory, retained routes and local snapshot scope | Preserve unresolved dependencies; a duplicate hash alone does not prove a path is unused |
| Unknown file / old experiment | Search the indexes below | Open the actual code and completed result | Do not execute a runner because its name contains `test` |

Python module names above are under `custom_nodes/ComfyUI-AIToolkit-Training/`.
Use [the code index](generated/CODE-INDEX.md) to jump to exact paths.

## Evidence order

1. Latest user instructions and [project rules](../AGENTS.md) define the authorized scope.
2. Current files establish implementation and saved defaults; live API checks establish what a worker exposes.
3. A completed result plus exact recipe, raw diagnostics and visual review establishes a bounded outcome.
4. Plans, preparation notes, directory names such as `ACTIVE`, and old acceptance labels do not prove completion.

[STATUS](STATUS.md) resolves the main current-versus-historical distinctions. A public workflow
being present does not establish readiness of every scene/mode. Documentation is a route to evidence;
if it disagrees with code or a later result, investigate and update it.

## Efficient change loop

1. State the observed failure and intended improvement. Find the closest completed experiment in
   [DECISIONS](DECISIONS.md); identify what new evidence would justify revisiting a closed route.
2. Check `git status --short` and the relevant diff. This workspace contains substantial existing
   uncommitted research; a commit ID alone is not an exact description of the working files.
3. Read the implementation and its relevant tests. Separate a source-string assertion from actual behavior.
4. Make one bounded change. Run the smallest relevant offline checks; expand only for shared dependencies
   or unresolved risk. Model/reference/sampling changes still require the AGENTS research and image gates.
5. Judge image changes against both the previous accepted result and the genuine source/references,
   with the original selection/cohort/thresholds. Keep failed results and distinguish runtime from photo acceptance.
6. Update the affected guide and result row in the same change. Check those guides with `--guide`.
   Unrelated index or experiment changes belong to their own maintenance; they do not require a
   full-project review before completing a bounded change.

## Search without reading the whole repository

- [Project code/configuration](generated/CODE-INDEX.md): source-directory files and Python entry symbols; excludes archive/experiment directories.
- [Tests](generated/TEST-INDEX.md): source-directory tests and explicit membership in the main verifier; historical tests are in the history index.
- [Evidence](generated/EVIDENCE-INDEX.md): reports throughout `docs/`, workflows and local `work/`.
- [Historical and experimental code/tests](generated/LOCAL-CODE-INDEX.md): `work/`, archived code and workflow experiment directories, including frozen copies.
- [Machine-readable inventory](generated/repository-index.json): full symbols, imports and text hashes.

These are static inventories, not a claim that every file was behaviorally audited or every test ran.
Source directories named `vendor` or `models`, binary artifacts and run-receipt JSON are excluded.
Links into ignored `work/` require this workstation's evidence; they are not backed up merely by committing docs.

The [.ignore](../.ignore) search rules exclude archives, workflow experiments, generated indexes and
dated reports from routine searches. They do not move files, change imports or affect Git tracking.
Source locations still include some experimental utilities; a file's location is not readiness evidence.
Do not infer that a helper is unused from a filtered search. Read its dependencies before retiring it.

```powershell
python scripts/project-docs.py --check --guide docs/STATUS.md --guide docs/DECISIONS.md
rg -n "feature-reuse|PixelSmile|Group" docs/generated/EVIDENCE-INDEX.md
rg -n "test_.*hair|test_.*source" docs/generated/TEST-INDEX.md
rg -n "reference_latents" custom_nodes scripts workflows/production
rg --no-ignore -n "identity_reference_megapixels" archive/klein9b-upgrade-reference-policy
```

If stale, follow [documentation maintenance](DOCUMENTATION.md). Refreshing an index does not
approve changed guide claims. Read only the affected evidence, then record that review.
Choose the actual affected guides; the example checks current outcomes. Use full `--check` when
maintaining the generated inventory or preparing a release.
