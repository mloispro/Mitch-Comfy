# Choose checks by what changed

This is a test-routing guide, not a blanket passing-test claim. The generated
[test index](generated/TEST-INDEX.md) lists conventional test filenames and test functions in source
directories. Historical/experimental-directory tests remain in the [history index](generated/LOCAL-CODE-INDEX.md)
and full JSON inventory. Explicit inclusion in [verify.ps1](../scripts/verify.ps1) is recorded
separately from existence. An assertion about source text does not establish rendered-image quality.

Commands below run from the repository root in PowerShell unless a different directory is shown.
Use the runtime needed by the test: the Comfy environment is
`C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe`; plain `python` may be a different installation.

## Documentation-only changes

```powershell
python scripts/project-docs.py --check --guide docs/DOCUMENTATION.md --guide docs/TESTING.md
python -m unittest discover -s scripts -p test_project_docs.py
git diff --check
```

Substitute the guides actually affected. Run the unittest command when changing the checker;
prose edits alone need link/evidence checks, not new tests. Use full `--check` for inventory maintenance
or a release audit, not as a mandatory gate on unrelated work.

This needs only Python's standard library. Follow [maintenance](DOCUMENTATION.md) if source review
or regeneration is needed. Model loading, image generation and the full live verifier add no useful
coverage to a prose/index-only change.

## Presets and browser controls

```powershell
node scripts/test-visual-scene-presets-ui.mjs
node scripts/test-upgrade-attractiveness-ui.mjs
node scripts/test-production-gpu-guard.mjs
```

These use local test harnesses, not a live browser. They cover prompt-helper behavior and widget
save/reload/clone migration, attractiveness migration, and wrong-worker blocking. A UI/layout change
also needs actual browser review; mocks do not prove visual layout or image semantics.
The visual-preset suite also exercises St. Barts' natural-appearance selection, full-scene editing,
saved explicit overrides and preservation of the switch on cards without a default. The boat correction's
[September 20 exact-foreground result](../work/st-barts-exact-foreground-20260920/RESULT.md) separates
pixel equality, visual review, genuine likeness diagnostics and served-asset checks. The earlier
native UI handoff matched its executed API but remained an approximate edit. The current final
image uses deterministic composition; gallery text has not had a new generation check and its
thumbnail does not supply pose conditioning. Actual browser interaction remains unverified.

For scene/profile resolution and saved reporting, the relevant Python modules are
`test_flux2_klein9b_scene_presets.py`, `test_flux2_klein9b_visual_preset_support.py` and
`test_flux2_klein9b_mitch_identity_studio_presets.py` in the custom-node directory.

```powershell
Push-Location custom_nodes/ComfyUI-AIToolkit-Training
try {
    python -m unittest test_flux2_klein9b_scene_presets.py test_flux2_klein9b_visual_preset_support.py test_flux2_klein9b_mitch_identity_studio_presets.py
} finally { Pop-Location }
```

The canonical data is [manifest.json](../custom_nodes/ComfyUI-AIToolkit-Training/web/assets/scene-presets/manifest.json).
Thumbnail changes also use `scripts/build-flux2-klein9b-preset-thumbnails.py --check` with Comfy Python;
this verifies thumbnail provenance, not generated-photo acceptance.

## Upgrade and image finishing

| Changed area | Focused tests in custom-node directory | Limit of those checks |
| --- | --- | --- |
| Low hair/skin treatment | [deterministic polish tests](../custom_nodes/ComfyUI-AIToolkit-Training/test_flux2_klein9b_deterministic_polish.py) | Includes mocked ParseNet class selection and local pixel invariants; not real-photo acceptance across sources |
| Source-relative gaze | [gaze tests](../custom_nodes/ComfyUI-AIToolkit-Training/test_flux2_klein9b_source_gaze_lock.py) | Local math/synthetic behavior; inspect actual eyes at full size |
| High / protected eye geometry | [attractiveness tests](../custom_nodes/ComfyUI-AIToolkit-Training/test_flux2_klein9b_attractiveness.py) | Protected pixel/geometry behavior; does not establish useful stronger High |
| Phone-off background blur | [masking tests](../custom_nodes/ComfyUI-AIToolkit-Training/test_flux2_klein9b_upgrade_masking.py) | Synthetic foreground/background protection; no universal matte-quality proof |
| Prompt/dimensions/reference policy | `test_flux2_klein9b_photo_realism_upgrade_presets.py`, `test_flux2_klein9b_photo_realism_upgrade_reporting.py` | The latter executes the actual production reference block with encoder/loader doubles: order, resolution, interpolation and both conditioning branches; no identity guarantee |
| Report wording and optional paths | [reporting tests](../custom_nodes/ComfyUI-AIToolkit-Training/test_flux2_klein9b_photo_realism_upgrade_reporting.py) | AST/source contract assertions, not live execution of the rendering pipeline |

For example, with Comfy Python for NumPy/OpenCV/Torch-dependent CPU tests:

```powershell
Push-Location custom_nodes/ComfyUI-AIToolkit-Training
try {
    & 'C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe' -m unittest test_flux2_klein9b_deterministic_polish.py test_flux2_klein9b_attractiveness.py test_flux2_klein9b_source_gaze_lock.py test_flux2_klein9b_upgrade_masking.py test_flux2_klein9b_photo_realism_upgrade_reporting.py
} finally { Pop-Location }
```

Choose only relevant files for a narrow change. Experimental `scripts/test_upgrade_*` modules
protect their associated probes; many are not included by the main verifier. Use the index to find
their source and read side effects/imports before execution. Frozen `work/` tests may depend on
specific snapshots and should not be swept into general discovery.

## Shared sampling, identity and training helpers

- `test_flux2_klein9b_turbo.py` and `test_flux2_klein9b_smartphone_style.py` protect sampling/style contracts.
- `test_identity_scope.py`, `test_identity_leakage.py`, `test_scene_constraints.py`, `test_head_integrity.py`
  and related geometry tests protect helper rules, not successful whole-image identity preservation.
- `test_integration.py` tests AI-Toolkit client/dataset/publication behavior with its test setup;
  it does not authorize training or prove a trained LoRA's quality.

The exact test names, imports and explicit verifier membership are in the generated index.
Some historical test files exist outside the verifier's explicit list. Their presence alone is not a
coverage failure; evaluate whether the behavior is still supported before changing the required suite.

## Environment and public workflow checks

### Production Speed and curated visibility

Run the focused CPU-only adapter/recipe tests with Comfy Python:

```powershell
Push-Location custom_nodes/ComfyUI-AIToolkit-Training
try {
    & 'C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe' -m unittest test_flux2_klein9b_speed_guard.py test_flux2_klein9b_group_speed.py test_flux2_klein9b_guarded_cache.py
} finally { Pop-Location }
python -m unittest discover -s scripts -p test_deploy_production_speed.py
.\scripts\test-comfy-workflow-library.ps1
node scripts/test-production-gpu-guard.mjs
```

- [Speed adapter tests](../custom_nodes/ComfyUI-AIToolkit-Training/test_flux2_klein9b_speed_guard.py) check every
  loading branch rejects before its core load, repeated submission/sampler guards, unchanged native calls,
  exact UI-to-accepted-graph parity and genuine default-input hashes. They do not generate an image.
- [Group integration tests](../custom_nodes/ComfyUI-AIToolkit-Training/test_flux2_klein9b_group_speed.py) execute the
  actual engine with CPU test doubles: default hook behavior, separate per-call cache state and saved fallback reporting.
  [Cache tests](../custom_nodes/ComfyUI-AIToolkit-Training/test_flux2_klein9b_guarded_cache.py) exercise separate/joint CFG,
  condition/reference changes and numerical replay guards with synthetic tensors, not photo quality.
- [Activation tests](../scripts/test_deploy_production_speed.py) mock ownership/idle checks. The actual
  [activation helper](../scripts/deploy-production-speed.py) can restart an explicitly selected idle worker; running its
  `reload` command is an operational change, not a unit test. It must preserve launch arguments and both workers' work.
- [Library tests](../scripts/test-comfy-workflow-library.ps1) use a temporary layout to test allowed junctions,
  dry runs, rollback, and preserved source content. The GPU-guard JavaScript test remains a browser mock.

The [actual rollout result](../work/production-speed-rollout/RESULTS.md) records ordinary **Run** completion for all
three routes, graph/hash receipts and the separate photo-acceptance decisions. After future changes, repeat the
affected original-file preservation, live-node/browser and actual-Run checks, then genuine-cohort diagnostics and
native/thumbnail review; passing unit tests alone is not a release. The [rollout plan](../work/production-speed-rollout/PLAN.md)
and [evaluation routing](../work/production-speed-rollout/EVALUATION-ROUTING.md) define the checks.
Solo retains six genuine references; Upgrade excludes its own source from its five-reference cohort; Group uses
the intended scene-selected face and bystanders. A new normal RTX 3090 run does not inherit historical legacy RTX 4070
timings or certify all 14 Individual scenes. See [the Speed guide](production-speed.md) for current acceptance status.

### Original Production workflows

```powershell
.\scripts\verify.ps1
.\scripts\verify-flux2-klein9b-mitch-identity-studio-v1.ps1
.\scripts\verify-flux2-klein9b-group-scene-studio-v1.ps1
.\scripts\verify-flux2-klein9b-upgrade-photo-detail-realism-v1.ps1
```

The general verifier checks workflow shapes, junctions, active frozen hashes, model/input assets,
selected package versions, thumbnail provenance, three JavaScript suites, an explicit Python list,
and live node surfaces on both normal endpoints. It mixes environment validation and offline tests;
it is not a lightweight substitute for a focused unit command. It also uses both Comfy Python and
plain `python`, so interpreter differences can explain failures.

Specialized checks use live APIs and may hash large files. **Group and Upgrade `-Smoke` submit
generation.** Default invocations above do not request smoke. Before generation, use both GPUs/queues
and the workflow's exact lock/ownership rules from [AGENTS](../AGENTS.md). Check other consumers of
the same GPU where the runner requires it. No generic test sweep may restart or unload active work.

## Actual photo acceptance

### Pinned image review cases

The [five-case catalog](../config/evaluation-cases.json) links the three actual Production Speed
integration examples plus the rejected public Cocktail and masked Group1.10 observations. Each has
pinned photos, executed recipes, diagnostics, reviews and the applicable genuine-reference cohort.
These are historical acceptance examples; later current guides may supersede them. Changed settings,
sources or seeds require a new review. This is not a universal scoring or automatic photo-test suite.

```powershell
python scripts/evaluation-cases.py list --area group
python scripts/evaluation-cases.py show group-masked-110
python scripts/evaluation-cases.py check --case upgrade-navy-turbo
python -m unittest discover -s scripts -p test_evaluation_cases.py
```

The [standard-library helper](../scripts/evaluation-cases.py) reads/hashes only local evidence. `check`
without a filter verifies all five cases. Missing or changed evidence fails; it never refreshes pins.
The [seven synthetic tests](../scripts/test_evaluation_cases.py), also included in `verify.ps1`, check
drift/missing files, scoped selection, source exclusion, output preservation, API-graph admission and
unresolved new review state. They need no Comfy runtime, models, GPU, network or historical photo files.

For an already-generated candidate and its saved executed API graph:

```powershell
python scripts/evaluation-cases.py review solo-cocktail --candidate work/my-run/photo.png --candidate-recipe work/my-run/actual-api.json --change "Describe the intended improvement and changed variable" --output work/evaluation-reviews/my-run
```

This creates a new local `review.html` (320px thumbnail and expandable native image views) and
`review.json` with separate unresolved runtime, numerical, visual and decision fields. Open the HTML
locally; it references existing photos without copying or uploading them. Candidate hashes and API
shape do not prove that the graph generated that photograph. Verify attribution using the route's
existing safeguards, then apply its original evaluator and review contract. The helper never runs a
listed evaluator or frozen generation script. Some such scripts have fixed historical outputs or old
worker/source pins; their presence in the catalog is evidence, not permission to execute them.

The Upgrade case excludes val03 from the independent five-photo cohort. Group keeps geometric main
selection and all bystanders. Legacy filenames such as `val_01_surf_full_body` do not establish actual
framing. A passing hash check, old accepted image or numeric pass never fills a new candidate's verdict.
Keep scope/limitations and human-readable observations with the new review; do not rewrite historical
verdicts or inherit another case's numerical threshold.

### Likeness diagnostic

The [generic face scorer](../scripts/evaluate-face-likeness.py) uses CPU InsightFace AntelopeV2 and accepts
repeated `--reference` / `--candidate`, optional `--calibration-reference` and `--json-output`.
It is not a drop-in replacement for experiment-specific main-face selection or source exclusions.
Confirm its local weights exist before use. The scorer now reuses raw detections for identical decoded
pixels within one invocation; scoring/calibration lists and largest-face selection remain unchanged.
The cache has one prepared analyzer and returns independent raw Face records. Nothing persists across
invocations. This does not change Group-specific selectors or Upgrade source-exclusion rules.

For changes to that reuse or its caller:

```powershell
python -m unittest discover -s scripts -p test_face_likeness.py
```

These focused tests use synthetic arrays and a stub analyzer: no weights, GPU or network. They cover
changed pixels/shape/dtype, independent records/runs, failed versus empty inference, and exact reports
with distinct scoring/calibration cohorts. The general verifier includes this command. Real-input
timing and raw/report parity are separate evidence; use the completed result linked from DECISIONS.

- Keep the original genuine cohort, calibration and every raw comparison. Similarity is not a probability.
- Group needs the scene-selected intended person plus all bystander checks; never select the best-scoring face.
- Upgrade source photographs must stay excluded from their own held-out identity cohort when the experiment requires it.
- Review native full frame and thumbnail for identity, age, skin/hair, eyes/mouth, anatomy, partial people,
  framing, depth, halo and background/source fidelity. An unresolved visual category stays unresolved.
- Separate a test completing, runtime/provenance passing, numeric passing and visual acceptance.

Use [completed result protocols](DECISIONS.md) for exact per-experiment requirements. The six-reference
floor used in some readiness experiments is not a universal production law. Image-changing work needs
the project research and bounded image loop even when every offline test passes.
