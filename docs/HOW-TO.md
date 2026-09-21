# Mitch Comfy maintenance and operating guide

For canonical current status, read `docs/STATUS.md`. Dated evaluation reports record the decision at their date
and are not operating instructions unless STATUS links them as current.

For development, start with [START-HERE](START-HERE.md) and [TESTING](TESTING.md).
The following describes the public controls and saved recipes. Historical validation is limited to its
tested cases; [current status](STATUS.md) records later failures and incomplete scene/mode readiness.
The separate [Production Speed guide](production-speed.md) covers the ordinary-Run Cocktail,
source-preserving Turbo and Lounge alternatives. Their tested scope differs from the original public nodes;
the source-preserving Upgrade recipe is not public Upgrade High or its four-reference graph.

## Before generating

1. Check the RTX 3090 and RTX 4070 workers and queues.
2. Do not stop, restart, or repurpose a worker with running or pending work.
3. Refresh the ComfyUI Workflows sidebar after workflow files move.
4. Reopen an already-open graph after its JSON or custom node changes.
5. Use only genuine photographs for identity-sensitive evaluation.

The normal RTX 3090 worker is `http://127.0.0.1:8188`.

All three original production Klein 9B workflows and the Production Speed copies target this worker.
Port `8189` is the RTX 4070; its shared Workflows sidebar also lists the 9B graphs, but listing a graph does not make it
compatible with that GPU. Refresh the browser once to load the production GPU guard. On
the wrong worker it shows an `Open RTX 3090 ComfyUI (8188)` link and prevents submission.
Open the link and select the workflow again under `Mitch/production` or `Mitch/production-speed`; save any custom
edits before switching. The backend RTX 3090 lock remains enforced.

## Choose the correct workflow

### Production Speed: bounded alternatives

Open `Mitch/production-speed` on the RTX 3090 and select the needed recipe:

- **Individual — Cocktail (tested recipe):** the accepted raw rooftop Cocktail graph. Prompt and seed are editable;
  a different scene is an unvalidated variation, not approval of all Individual presets.
- **Upgrade — Source Preserve Turbo (tested example):** the one-source navy-shirt/closet example. Its prompt describes
  that photograph. Another genuine source requires reviewing the prompt and both output-dimension nodes; it is not
  a universal detail enhancer, factual blur recovery or stronger High.
- **Group — Lounge Faster Quality:** the fixed approved Lounge composition with a seed control. No uploaded/custom
  layouts here. Seeds `8675412`, `8675413` and `8675414` have matched experimental evidence; new outputs still need review.

Use ordinary **Run**, not a private worker or laboratory CLI. All three workflows have completed actual normal-worker
Run checks; see [observed timings, output paths and photo-acceptance evidence](production-speed.md). These are bounded
Cocktail/source-example/Lounge routes, not all-scene approval. Solo/Upgrade's historical legacy-4070 timings are not
current 3090 benchmarks. Existing Production recipes remain available below, unchanged.

### New photograph: Klein 9B Identity Studio

Open `Mitch/production/FLUX.2 Klein 9B Mitch Identity Studio v1.1 - Visual Presets`.

- Click a scene thumbnail; it selects the prepared prompt and matching genuine-reference profile.
- The boat card is **St. Barts yacht — Caribbean escape**, replacing Italian lake boat. Refresh
  ComfyUI and reselect the card in older saved boat graphs. Selecting it now turns **Flattering appearance off**
  for natural age/skin and describes the original forward lean with both hands gripping the rails.
  You can still re-enable that switch; save/reload preserves your choice. The
  [current preview, pixel verification and saved composition](../work/st-barts-exact-foreground-20260920/RESULT.md)
  preserve the original foreground directly, with qualified sunglasses likeness. The gallery remains text-only:
  use that final PNG or saved deterministic composition for this exact pose; the earlier native edit
  workflow only approximates it. FULL BODY references and gallery
  sampling settings remain unchanged; the new gallery wording has not had a separate generation check.
- Use `Custom — write your own scene` to type a scene not represented in the gallery.
- The default `Flattering appearance` on-state requests a 3–5 year younger best-day look, slightly stronger jaw/chin and
  cheekbones, a slight confident closed-lip expression with every tooth covered, clearer natural eye catchlights,
  finer visible pores, tidier stubble, light-bronze skin, and reduced fine-line emphasis; turn it off for the previous
  exact natural-appearance prompt.
- Leave `Fast Turbo — 8 steps` on for the historically tested fast route. Turn it off to restore the previous 50-step
  quality fallback exactly.
- With a prepared card, leave the prompt box empty or use it only for extra scene direction.
- Queue on the RTX 3090.

Locked recipe: Klein Base 9B, rank-256 BF16 Turbo at `1.0`, V3 step-1600 identity LoRA at `0.90`, Smartphone
Snapshot Photo Reality v13 at `0.25` with its automatic `casual snapshot` trigger, genuine native references,
`832×1216`, 8 Euler steps, CFG `1.0`, and `Flux2Scheduler`. Turning Fast Turbo off omits only the Turbo LoRA and
restores 50 Euler steps / CFG `4.0`. This is whole-frame generation with no source-scene latent,
face swap, restoration, sharpening, or second identity pass.

Detailed visual-selector contract: `docs/flux2-klein9b-visual-preset-studios-v1.1.md`.

### Source-matched group: Klein 9B Group Scene Studio

Open `Mitch/production/FLUX.2 Klein 9B Mitch Group Scene Studio v1.1 - Visual Presets`.

1. Click a prepared group-layout card. It supplies the preserved source, prompt, target coordinates, and head scale.
2. Choose `Custom — uploaded group photo` only when you want to load a different genuine group source and set the
   target controls manually.
3. With a prepared card, leave the prompt box empty or use it only for extra scene direction.
4. Keep `head_scale` at `0.92` for custom sources unless a measured source-specific adjustment is necessary. The Canny guide supplies
   approximate outer-head scale and placement; the separate genuine Mitch photograph supplies identity and internal
   facial geometry.
5. Leave the appearance control off for the saved identity-first default. Its optional on-state is
   a short rendering-only treatment and does not request a younger age or changed bone structure.
6. Leave Fast Turbo off for the historical 50-step quality recipe. The production-node 8-step test reduced main
   identity `0.5958 → 0.5672`, so it remains an explicit speed experiment only.
7. Inspect the face-free guide before trusting the generated image.

The intended source face must have blank internal eye/nose/mouth edges in the guide. Keep the identity wording concise:
the validated contract says that Picture 2 supplies Mitch's identity and internal facial geometry, then describes the
scene and desired expression. Detailed instructions for exact skull measurements, younger age, stronger jaw/chin, or
idealized cheekbones reduced likeness and are intentionally excluded from the default. Reject a run if the wrong
person was selected, Mitch appears more than once, the head scale is wrong, or the frame looks composited.

The accepted Smartphone Snapshot Photo Reality v13 LoRA is applied automatically at `0.25`, after the identity
LoRA. It is not a user control and does not alter the Canny reference order.

Detailed visual-selector contract: `docs/flux2-klein9b-visual-preset-studios-v1.1.md`.

### Existing one-person image: Upgrade Photo Detail & Realism

Open `Mitch/production/FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1.1`.

1. Load an image containing exactly one detectable face.
2. Describe only the material/background detail to improve.
3. Leave `Attractiveness` at `low` for the previous default. It applies deterministic closed-mouth expression,
   fatigue/line, warmth, eye, stubble, cheek/jaw, dark-dot/freckle, hair-material/highlight, and source-gaze corrections after generation.
   A local MediaPipe iris measurement moves only generated iris material toward the source-relative pupil coordinates;
   source pixels are not copied. The eyelid boundary, head outline, hairline, hair silhouette, and unselected skin
   texture remain exact generated pixels; the separate phone-off camera finish may soften only the background.
   The `high` mode applies stronger brow/crease definition, source-guided upper-lid curvature, clearer eye contrast, and
   subtle extra warmth after the gaze lock. High fixes the eye corners and pupil position; it does not enlarge the
   eyes or copy source pixels. A useful stronger High has not been proven across required sources; this describes
   implementation, not acceptance. `off` skips the face/hair/iris treatment. Phone style is independent and stays on.
4. Leave `Phone-camera realism` on for the accepted deep-focus Smartphone Snapshot v13 look at `0.25`; phone-on skips
   the background-blur stage. Turn it off for optional gentle, optical-looking background separation. That path saves the
   complete detailed render first, then uses a local U2Net matte and edge-safe depth-ramped blur to preserve the subject exactly.
5. Use seed `8675416` first and queue only on the RTX 3090 worker at port `8188`.
6. Review the upgraded photo, raw before-polish image, polish mask, pre-background-blur image, background-blur mask,
   and structure guide at full size and thumbnail.

The workflow uses one whole-frame empty-latent Base 9B generation with four ordered references: source scene,
face-interior-free Canny geometry, genuine Mitch identity, and genuine isolated hair material. The final source-gaze
prototype reduced normalized horizontal pupil error by `74.1%`, retained a six-photo `strong_match` identity score of
  `0.7508`, and changed only `0.095%` of the frame inside eroded eye interiors. The historical v4 polish used sparse local
  median replacement to reduce visible cheek/nose dark-dot pixels by `35.9%` versus v3, slightly lifts only existing
  brighter hair material, protects the first eight pixels inside the semantic hair boundary, and the
combined handsome treatment changed zero pixels outside its face/iris/hair-interior masks. The phone-off blur has zero
protected-subject error and excludes subject colors from the background filter.
Current Low is **v5**, correcting CodeFormer ParseNet hair selection from neck class17 to hair class13.
The numerical v4/gaze claims above belong to their historical tests, not a new v5 benchmark.
See [the actual v5 repair and live check](upgrade-parsenet-hair-label-bug-2026-09-04.md).
It uses no Turbo, source-latent inpaint, face swap, restoration, sharpening, upscaling, or second model pass.

Detailed public-interface contract: `docs/flux2-klein9b-upgrade-photo-detail-realism-v1.1.md`.

### Validated dating templates: FLUX.2 Dev

Open `Mitch/production/FLUX.2 Dev LoRA - 9 Dating Scenes v1`.

- Choose one of the nine `mitch-workbench-dating-*` scene images or provide a controlled scene reference.
- Picture 1 supplies composition, pose, clothing category, props, location, lighting, and crop—not identity.
- The protected Dev V2 step-1000 LoRA supplies Mitch’s identity.
- Keep the active workflow default at LoRA `1.1`, 28 Euler steps, guidance `4.0`, unless running a documented A/B.
- In group scenes, verify every secondary face and confirm there is exactly one Mitch.

Detailed contract: `docs/flux2-dev-mitch-scene-studio.md`.

## Utility workflows

`Dataset gen - QWEN 2511 - 3-photo` creates controlled multi-angle dataset images with Qwen Image Edit 2511.
Generated images are not genuine identity truth and must not enter held-out identity evaluation.

`Train Generated Dataset - AI Toolkit` submits and monitors the fixed generated-dataset training job. A completed
job is not automatically approved or published for production; it still requires the normal held-out and visual gates.

## Review checklist

At full size and thumbnail, inspect:

- recognizable identity and the apparent-age treatment selected by the enhancement toggle;
- hairline, forehead, hair material, eyes, mouth, jaw, and ears;
- body/head proportion, anatomy, hands, and feet;
- exactly one Mitch and distinct bystanders;
- scene geometry, depth, materials, lighting, and camera consistency;
- halos, pasted-head boundaries, selective sharpness, fake bokeh, noise, or smoothing.

Automated similarity can reject or rank a candidate. It cannot certify identity or visual quality.

## Hidden rollbacks and failed experiments

The curated normal-use library exposes `workflows/production` and `workflows/production-speed`.
`workflows/experiments` remains intact at its original paths, including runtime helpers and frozen evaluation
dependencies, but is out of the Workflows sidebar. Exact legacy graphs under `checkpoints/legacy-workflows`
also remain hidden. This is visibility cleanup, not deletion.

Use [the visibility plan/rollback commands](production-speed.md#visibility-and-rollback) to restore the old full-tree
view deliberately. They change only the two allowed ComfyUI library junctions; they do not restart workers,
delete experiment data or clear unsaved browser tabs. Refresh the sidebar afterward.

Retired launchers/configs under `checkpoints/legacy-scripts` retain their original path assumptions. Do not run
them in place. Restore an archived experiment only for a deliberate regression investigation, and copy all of its
documented dependencies back to their original locations first.

The accepted One Reference rollback can also be restored from its tag:

```powershell
git restore --source flux2-one-reference-v1.0.0 -- "workflows/production/FLUX.2 One Reference Photo.json" "custom_nodes/ComfyUI-AIToolkit-Training/one_reference_photo.py" "custom_nodes/ComfyUI-AIToolkit-Training/__init__.py"
```

Restart ComfyUI after restoring Python files. Do not overwrite the archived copy.

## Verification and check-in

Run:

```powershell
.\scripts\verify.ps1
.\scripts\verify-flux2-klein9b-mitch-identity-studio-v1.ps1
.\scripts\verify-flux2-klein9b-group-scene-studio-v1.ps1
.\scripts\verify-flux2-klein9b-upgrade-photo-detail-realism-v1.ps1
git diff --check
git status --short
```

The specialized verifiers are read-only by default. The Group and Upgrade verifiers also accept `-Smoke`, which
queues a generation. Never use `-Smoke` while either GPU has running or pending work.

For a normal repository checkpoint:

```powershell
.\scripts\checkpoint.ps1 -Message "Describe the verified change"
```

Git history is not an off-computer backup. Models, LoRAs, datasets, genuine reference photographs, and generated
outputs require a separate private backup.
