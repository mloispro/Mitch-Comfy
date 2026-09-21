# Where behavior lives

Source-inspected during the September 9 documentation rebuild. This describes local code and
saved workflow wiring; it does not certify live worker state or author training compatibility.
[STATUS](STATUS.md) supplies the qualifications on image acceptance.

## Public entry points and shared implementation

The ComfyUI directories are linked to this repository. [Package initialization](../custom_nodes/ComfyUI-AIToolkit-Training/__init__.py)
exposes [nodes.py](../custom_nodes/ComfyUI-AIToolkit-Training/nodes.py) and `web/`.
The public registry, six original [production workflow files](../workflows/production), and three separate
[Production Speed files](../workflows/production-speed) define the curated visible surface.
Old classes remain for implementation reuse and historical graphs; presence in the registry is not proof of current recommendation.

| Public class | Implementation path | Shared behavior to inspect before changing it |
| --- | --- | --- |
| `Flux2Klein9BMitchIdentityStudioVisualPresetsV11` | [visual wrapper](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_mitch_identity_studio_visual_presets.py) → [Identity engine](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_mitch_identity_studio.py) | Wrapper resolves scene and reference profile, delegates generation and augments saved reports |
| `Flux2Klein9BMitchGroupSceneStudioVisualPresetsV11` | [visual wrapper](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_group_scene_studio_visual_presets.py) → [Group engine](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_group_scene_studio.py) | Preset source/target geometry and the face-free layout builder are part of the recipe |
| `Flux2Klein9BPhotoRealismUpgradeV11` | [Upgrade engine](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_photo_realism_upgrade.py), mapped to internal `Flux2Klein9BPhotoRealismUpgradeV1` | Uses Identity model constants/3090 guard; adds four references and optional post-generation treatments |
| `Flux2DevMitchSceneStudio` | [Dev engine](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_dev_mitch_studio.py) and [presets](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_dev_mitch_studio_presets.py) | Separate Dev model/encoder/LoRA and scene-restage semantics |

### Separate Production Speed integration

The [Speed guide](production-speed.md) defines the bounded interface and acceptance state. Actual ordinary Comfy
Run integration completed for all three routes; [rollout evidence](../work/production-speed-rollout/RESULTS.md)
separates exact graph/runtime checks from photo acceptance. Original Production workflow JSONs, defaults and
recipes are unchanged; this is not new model training.

- **Individual Cocktail / Upgrade Source Preserve Turbo:** ordinary core graphs with four adapters in
  [speed_guard.py](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_speed_guard.py). UNET, CLIP and VAE each check
  RTX 3090 / port 8188 / default dynamic VRAM and minimum available RAM/commit before their own core loader call.
  Submission validation rechecks cached loaders. The sampler checks again on every execution while preserving
  upstream model caches; native sampler arguments/math are unchanged. Labels/output paths are new, while the
  accepted default graphs and genuine-input hashes are preserved in [package provenance](../config/production-speed-solo-upgrade.json).
- **Group Lounge Faster Quality:** [group_speed.py](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_group_speed.py)
  reuses the native preset/source resolver and RTX3090 guard with a fresh per-call runner. The
  [Group engine](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_group_scene_studio.py) adds preparation/output/report
  hooks whose defaults preserve original behavior. Only the separate Speed runner applies the
  [guarded cache](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_guarded_cache.py): 50 Euler/CFG 4, warmup 10,
  interval 3, no Turbo. CFG partitions and condition/reference state are guarded. This is approximate replay,
  not a new model or upstream CacheDiT installation; fallback status is saved, not silently treated as a speed pass.

No deployed Speed node imports the laboratory controller or monkeypatches a shared model-forward function.
The curated [library helper](../scripts/comfy-workflow-library.ps1) links only `production` and `production-speed`.
Both worker `Mitch` junctions point to `local/comfy-workflow-library`; the live Speed section was verified to contain
only its three workflow files. Hidden experiments keep their original disk paths and dependencies; all 235 original
Production/experiment files passed the preservation check. [Visibility switching](../scripts/set-comfy-workflow-visibility.ps1)
is independent of GPU/runtime activation.

The Klein engines also call retained helpers in [one_reference_photo.py](../custom_nodes/ComfyUI-AIToolkit-Training/one_reference_photo.py).
Its old public workflow is retired, but deleting the file would break current imports.
[Training integration](../custom_nodes/ComfyUI-AIToolkit-Training/aitk_integration.py) supports the utility
nodes; it is a separate submission/publication path, not part of normal photo inference.

## Image conditioning and generation

These descriptions trace the inspected implementation, rather than predicting that any image slot guarantees identity.

| Route | Actual image path and role | Identity source / limitation |
| --- | --- | --- |
| Solo | Selected genuine files → resize each to `512*512` target pixels → VAE encode → append ordered `reference_latents` to both positive and negative conditioning | V3 identity LoRA plus genuine native reference latents. Profile order comes from [reference presets](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_mitch_identity_studio_presets.py); not face embeddings |
| Speed Individual Cocktail | Genuine front 448×592 → body 512×512 → angle09 432×576, separately VAE encoded and appended in that order to both branches | Same V3 identity LoRA; different raw reference profile from public Solo. Body-only wording does not hard-isolate identity |
| Group | Uploaded/preset scene → target selection and face-interior-free Canny layout → 250,000 target pixels → VAE → first reference. Genuine training04 portrait → 1,000,000 target pixels → VAE → second reference; both enter both CFG branches | V3 identity LoRA plus second reference. First reference provides layout/pose constraints; clearing face edges does not isolate model attention or prevent bystander identity leakage |
| Public Upgrade | Source image → first reference at 1 MP; face-free Canny → second at .5 MP; genuine identity → third at .5 MP; isolated genuine hair → fourth at .1 MP. Each is VAE encoded and appended to both CFG branches | V3 identity LoRA plus third reference; hair is material guidance. The full first source contains its face, so its identity influence is not isolated or proven absent |
| Speed Upgrade Source Preserve Turbo | One genuine source → bicubic 1 MP → VAE encode → single reference appended to both branches | V3 identity LoRA plus source's own identity, expression, pose and scene; source-specific prompt, not the public four-reference or finishing route |
| Dev restage | Scene image → resize/VAE → native reference conditioning; prompt-only mode omits the scene | Dev V2 step1000 LoRA supplies trained identity; scene is intended as composition, pose, crop and environment guidance |

All three public Klein engines sample from `EmptyFlux2LatentImage`, not a source-image starting latent.
They decode a new whole frame with Euler / `Flux2Scheduler`. Preserve the exact reference order and
conditioning of each route. The Speed graphs also start from an empty latent, not the source image's latent;
regenerated details are not factual recovery. Group Speed keeps the Group reference path fixed to Lounge.

Klein shared files:

- [Turbo](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_turbo.py): exact adapter/hash, 8 steps/CFG1 versus 50/CFG4. Applied before identity when enabled.
- [Smartphone style](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_smartphone_style.py): v13 style adapter at .25 and prompt trigger, applied after identity. It is not identity conditioning.
- [Appearance prompt](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_appearance_polish.py): Solo prompt treatment; Group defines a narrower rendering treatment in its engine.
- Identity's `_assert_rtx3090` is reused by Group and Upgrade. An ordinary-node experimental 4070 success does not remove this lock.

## Upgrade finishing is separate from sampling

[Upgrade presets](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_photo_realism_upgrade_presets.py)
compose prompt and whole-frame dimensions. After raw decode:

1. Low or High applies [deterministic face/hair polish](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_deterministic_polish.py).
   Current profile is v5; CodeFormer ParseNet hair is class **13**, not neck class 17.
2. [Source gaze lock](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_source_gaze_lock.py) measures source-relative pupil placement and moves generated iris material.
3. High adds [attractiveness treatment](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_attractiveness.py).
4. Phone-off may use [foreground masking/background blur](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_upgrade_masking.py); phone-on skips that blur.

Off skips the face/hair/gaze treatment. Raw, intermediate and final artifacts/reporting matter:
final face quality cannot establish that raw generation preserved source geometry.
The stronger-High objective remains unproven; code exposing a High mode is not acceptance evidence.

## Browser and preset contract

[manifest.json](../custom_nodes/ComfyUI-AIToolkit-Training/web/assets/scene-presets/manifest.json) is the
shared scene-data source. [Python resolver](../custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_scene_presets.py),
[gallery/prompt helper](../custom_nodes/ComfyUI-AIToolkit-Training/web/visual_scene_presets.js), thumbnails,
verifiers and saved workflow defaults must agree.

Prepared Identity cards select their own reference profile. Editing a profile widget alone is not proof
that a named preset will use it. The helper converts the full scene to Custom when choosing a face angle;
see [tested helper behavior](visual-scene-prompt-helper-2026-09-05.md).

An Identity record may also supply `appearance_polish_default`. Clicking that card sets the existing
appearance switch to the boolean default. St. Barts uses `false` to retain natural age/texture. This
is a click-time preference: users may override it, saved workflows retain their value, and explicit
API inputs remain authoritative. Other cards do not change the switch. No engine behavior changed.

[Attractiveness UI](../custom_nodes/ComfyUI-AIToolkit-Training/web/upgrade_attractiveness.js) handles widget migration.
[GPU guard UI](../custom_nodes/ComfyUI-AIToolkit-Training/web/production_gpu_guard.js) prevents wrong-worker submission;
the Python lock remains authoritative. A passing mock DOM test does not replace browser interaction review.

## Reproducibility boundaries

[frozen-baselines.json](../config/frozen-baselines.json) preserves active and superseded artifact hashes.
[dependencies.lock.json](../config/dependencies.lock.json) records historical dependencies; it is not a live inventory.
`scripts/verify*.ps1` checks selected current assets and node visibility. Do not repin historical artifacts
to make a check pass. Exact recipes include working-file contents, runtime/model versions, reference cohort,
precision, source dimensions and mode—not only the workflow filename or Git commit.
