# FLUX.2 Klein 9B production revalidation — 2026-09-03

## Decision

The three shipped workflows passed fresh default-path validation and are suitable for a known-good Git milestone:

- Identity Studio v1.1 — Visual Presets
- Group Scene Studio v1.1 — Visual Presets
- Upgrade Photo Detail & Realism v1

This record validates the exact current defaults, not every preset or arbitrary user input. InsightFace scores are local drift diagnostics rather than proof of identity; each result also received full-size and thumbnail visual review.

## Preflight and static verification

- All local ComfyUI queues were idle immediately before every submission: ports `8188`, `8189`, and `8190` each reported zero running and zero pending jobs.
- Port `8188` reported an NVIDIA GeForce RTX 3090; port `8189` reported an NVIDIA GeForce RTX 4070. Port `8190` shares the RTX 3090.
- Forge progress at port `7860` was `0.0`, with no job in progress.
- The RTX 3090 was idle at P8 before submission. The RTX 4070 remained idle throughout.
- `scripts/verify.ps1`: 124 tests passed; workflow, preset, asset, model-hash, live-link, and required-node checks passed.
- The Identity, Group, and Upgrade specialized read-only verifiers all passed against the live RTX 3090 worker.
- `git diff --check` reported no whitespace errors. Its only messages were the repository's existing LF-to-CRLF checkout warnings.

The six held-out genuine reference photographs were:

1. `datasets/mitch-identity-stills-v3/validation/val_01_surf_full_body.jpg`
2. `datasets/mitch-identity-stills-v3/validation/val_02_body_mirror_sleeveless.jpg`
3. `datasets/mitch-identity-stills-v3/validation/val_03_navy_upper_body.jpg`
4. `datasets/mitch-identity-stills-v3/validation/val_04_window_small_smile.jpg`
5. `datasets/mitch-identity-stills-v3/validation/val_05_balcony_opposite_angle.jpg`
6. `datasets/mitch-identity-stills-v3/validation/val_06_car_daylight.jpg`

Their local calibration was pairwise minimum `0.5533` and pairwise mean `0.6931`. The calibrated `strong_match` gate was centroid at least `0.5333` and mean at least `0.5033`.

## Identity Studio v1.1 shipped default

- Preset: `rooftop-cocktail-city-lights`
- Prompt input: blank; the manifest supplied the full scene prompt.
- Effective reference profile: `SOLO — front + left-facing angle`
- Conditioning references: genuine front-neutral and left-three-quarter photographs, in that order
- Appearance polish: on
- Turbo: on, 8 Euler steps, CFG 1
- Seed: `8675411`
- Resolution: `832 × 1216`
- Prompt ID: `d8a62b8b-1e15-490d-9649-16524cf467cb`
- Engine time: `22.819 s`; observed wall time: `27.120 s`
- Output: `C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-mitch-identity-studio-v1\20260903-011653-707945\photo_00001_.png`
- Output SHA-256: `2635B23B0C562D32AD1F17956246238002C77AC36743E584D765F0658A5F226A`
- Sidecar SHA-256: `75CC903D95DF878ED569CF9E4A09147019CB63410EBD183B8C2B9954E3DDE630`

Six-reference result: centroid `0.7354`, mean `0.6344`, minimum `0.5544`, maximum `0.6822`; calibrated status `strong_match`. Two faces were detected. The main face passed at `0.6918`; the bystander scored `-0.0583` to the Mitch centroid and `-0.0713` to the selected main face, so no identity leakage gate failed.

Visual review passed: recognizable adult Mitch identity at full size and thumbnail, appropriate head direction and restrained expression, coherent hand/glass/watch, plausible body proportions, distinct background patrons, legible city depth, natural phone-flash integration, and no pasted edge or halo.

The sidecar recorded the visual-shell name, preset key, manifest SHA-256 `70CEAF391CEDD1A7B3F76FEA8CD22815A963820F319BA2763F7C801D667AF7CF`, effective left-facing profile, and both effective genuine references.

## Group Scene Studio v1.1 shipped default

- Preset: `approved-lounge-center`
- Source: hash-locked manifest asset `group-approved-lounge-center.png`
- Effective target: `(0.50, 0.44)`; head scale `0.92`
- Appearance polish: off
- Turbo: off, 50 Euler steps, CFG 4
- Seed: `8675412`
- Resolution: `832 × 1216`
- Prompt ID: `2492b875-1297-4eb3-8205-77984b5cb779`
- Engine time: `260.682 s`; observed wall time: `270.629 s`
- Output: `C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-mitch-group-scene-studio-v1\20260903-011543-355172\photo_00001_.png`
- Output SHA-256: `B07500298CABD38BA5A0E998B1899EA6830372CEE23E89E0F4A8A10F2548A9F8`
- Guide SHA-256: `189A6D08AC073573037DBC6502BCD03EC3323A2C4AB2985E1C26A98D41E79DF8`
- Sidecar SHA-256: `90BF8346E12C23E86293049445DA00124D88EB55A2E181CCEAA0D32D4BCF6F0F`

Six-reference identity/leakage result: four complete faces detected; intended central face selected as main; main similarity `0.5769` against the `0.55` group gate. Maximum secondary-to-Mitch similarity was `0.2882` (limit `<0.42`), maximum secondary-to-main similarity `0.3365` (limit `<0.50`), and maximum secondary-pair similarity `0.3323` (limit `<0.72`). No leakage or duplicate-face gate failed.

Visual review passed: exactly one Mitch, four complete adults plus the expected partial fifth person at the extreme right, distinct bystanders, coherent hands and limbs, corrected central head scale, intact lounge composition, and no composite halo. The Canny guide preserved body, head-outline, booth, table, and hand structure while leaving the central eye/nose/mouth interior blank.

The sidecar recorded manifest SHA-256 `70CEAF391CEDD1A7B3F76FEA8CD22815A963820F319BA2763F7C801D667AF7CF`, source SHA-256 `1B26AC58A4FAD8D03F69DB7A4085C31B6682C71ACBE22D5AEE51F9E53FA0332B`, and identical input/effective geometry. The current manifest prompt is shorter than the frozen v1 default prompt; this run establishes that exact shorter prompt as a passing v1.1 result, but prompt parity remains an optimization-phase cleanup item.

## Upgrade Photo Detail & Realism v1 shipped default

- Source: native `1680 × 1008` included example
- Intended ordered roles: exact scene/source, face-interior-free Canny guide, genuine frontal identity photograph, isolated genuine hair-material crop
- Appearance polish: on
- Phone-camera realism: on (current accepted default)
- Sampling: 50 Euler steps, CFG 4; no Turbo, source-latent initialization, generation mask, restoration, sharpening, upscaling, or second model pass
- Seed: `8675416`
- Prompt ID: `9c37d18d-183c-46d6-95cd-e206258f0232`
- Engine time: `505.926 s`; observed wall time: `526.114 s`
- Output directory: `C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-upgrade-photo-detail-realism-v1\20260903-012645-379678`
- Raw SHA-256: `BC980717FCB5A3BF7CB8D3D1DE393AE325A808DB3A672002E38431FAB59A8BFD`
- Final SHA-256: `C46B804115D9FB8657CD7A93B6D23BCDE6E930E2B44CFEB018516C8D2339039B`
- Guide SHA-256: `1826F17AC98E4D922F0E849DAB0704145F708B81409326B1DCE4F3A92D860209`
- Prompt snapshot SHA-256: `441452979249A777B2E6F8E2632B2AF58ACC23ACC3E9EEC63724AEA1624FCAC4`
- Sidecar SHA-256: `5BF89D1C3A6B6C86E0578F3103CF734CB2795716CE1A16BB2EB652BA466D9F31`

Six-reference raw result: centroid `0.7791`, mean `0.6721`, minimum `0.5890`, maximum `0.7154`; `strong_match`.

Six-reference final result: centroid `0.7400`, mean `0.6384`, minimum `0.5377`, maximum `0.6813`; `strong_match`. It exceeds the project regression guard of accepted phone-on baseline minus `0.02` (`0.7175`). The weakest view is below the genuine pairwise floor, matching the previously documented accepted phone-on exception; this is not treated as a failure while centroid, mean, visual identity, and structure remain passing.

The raw tolerant Canny diagnostic was guide recall `0.6562`, candidate precision `0.1911`, F1 `0.2961`, mean edge distance `7.6923 px`, and p90 distance `23.3343 px`. This reproduces the previously measured phone-on structure result; it is a regression diagnostic, not an independent perceptual-quality gate.

Hard report invariants passed:

- `phone_camera_style=true`
- background mode `deep_focus_smartphone_lora`
- natural-lens blur `null`
- background postprocess mask `false`
- appearance profile `deterministic_face_and_hair_local_v4+mediapipe_refined_iris_source_lock_v1`
- protected-pixel maximum error `0 / 255`
- first eight semantic-hair boundary pixels protected
- no source pixels copied by gaze lock
- eyelid boundary and non-iris geometry protected
- mean horizontal gaze error reduced from `0.036160` to `0.023735`

Visual review passed: recognizable identity, source head yaw/pitch/roll and off-camera gaze, closed lips, pose and crop, coat silhouette and shirt opening, siding/roof diagonal, tree layout, hairline/temple/ear/back-head continuity, deep-focus environmental legibility, natural material detail, and no synthetic sharpening or repair seam.

## Reuse boundary established by this validation

Keep the three public workflows separate. Their reference semantics, order, resizing, dtype, LoRA recipes, output sizing, sampling defaults, and postprocessing differ materially.

Safe shared scope is neutral infrastructure: asset/hash validation, manifest parsing, additive provenance, queue/GPU preflight, ordered-reference primitives with explicit roles, explicit sampler plumbing, output/report helpers, and stage timing. Any loader or latent caching must be keyed by the complete model/hash/dtype/ordered-LoRA/reference recipe and parity-tested before promotion.
