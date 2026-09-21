# Production Speed — bounded RTX 3090 alternatives

These three workflows are separate ordinary-Comfy **Run** options under `Mitch/production-speed`.
They package specific accepted experiments; the original `Mitch/production` workflow files and recipes
remain unchanged. No new model, training, hosted service or identity-reference mechanism was added.

## Rollout state

All three workflows completed actual ordinary Comfy **Run** on the normal RTX 3090 worker. Their submitted
graphs and saved image hashes were verified. The [rollout results](../work/production-speed-rollout/RESULTS.md)
hold the final, separate visual/likeness acceptance decisions; successful execution alone is not a photo pass.
Group's fresh full-size/thumbnail and six-reference checks passed, and its decoded pixels exactly reproduce
the previously accepted cached seed. [STATUS](STATUS.md) remains the current release summary.

| Actual integration run | Observed worker time | Timing qualification |
| --- | ---: | --- |
| [Individual Cocktail](../work/production-speed-rollout/individual-run/runtime.json) | 24.829s | One normal-3090 run; no measured gain versus Production Individual |
| [Upgrade Source Preserve Turbo](../work/production-speed-rollout/upgrade-run/runtime.json) | 18.668s | About 19s with models warm after Individual; not a cold-load or paired Production benchmark |
| [Group Lounge](../work/production-speed-rollout/group-run/runtime.json) | 209.141s | One integration run; the matched speed claim comes from the separate three-pair experiment |

These worker times include execution/loading/saving as applicable, not browser/queue waiting or later evaluation.
The runs shared a normal-worker session; model/cache conditions were not controlled for a new speed comparison.

The normal target is [RTX 3090 ComfyUI at port 8188](http://127.0.0.1:8188), with its existing default dynamic
VRAM settings. The RTX 4070 sidebar may show these entries, but its GPU is not supported by the published
Speed copies. Do not change normal 4070 launch flags or bypass a GPU lock.

## Choose a recipe

| Workflow in `Mitch/production-speed` | What it is for | Important boundary |
| --- | --- | --- |
| [Individual - Cocktail - Tested Recipe - RTX 3090](<../workflows/production-speed/Individual - Cocktail - Tested Recipe - RTX 3090.json>) | The accepted raw rooftop Cocktail portrait | One tested recipe, not the public Individual profile or all 14 scenes. New prompts/seeds need review |
| [Upgrade - Source Preserve Turbo - Tested Example - RTX 3090](<../workflows/production-speed/Upgrade - Source Preserve Turbo - Tested Example - RTX 3090.json>) | Fast regeneration that preserves the genuine navy-shirt/closet example | Source-specific prompt; smoother skin than Quality50, no proven factual background-detail recovery or stronger High |
| [Group - Lounge Faster Quality - RTX 3090](<../workflows/production-speed/Group - Lounge Faster Quality - RTX 3090.json>) | The fixed approved Lounge composition with guarded approximate caching | Seed control only; no uploaded/custom group layouts. Small clothing/scene details can change |

Before Run, inspect both GPUs and queues and preserve active work. Refresh the browser/sidebar after activation,
then reopen the saved workflow. The original Production fallback remains under `Mitch/production`.

### Individual — Cocktail

The prompt and seed are ordinary editable controls. Defaults retain seed 315982047, 832×1216, 8 Euler/CFG 1,
Base 9B FP8, Qwen FP8mixed, full Flux2 VAE, and Turbo 1 → Mitch V3 step1600 .90 → Smartphone v13 .25.
Keep the genuine references in order: front 448×592 → body 512×512 → angle09 432×576. Both CFG branches receive
the native VAE reference latents. Body-only wording is intent, not hard isolation of identity.

Changing the prompt, seed or reference profile creates an unvalidated variation. Check closed lips, slight
image-left gaze, plausible glass grip/railing contact and pocket hand, distinct patrons and whole-frame integration.
Outputs save under `ComfyUI/output/production-speed/individual-cocktail/`.

### Upgrade — Source Preserve Turbo

The default genuine source is `mitch-upgrade-third-genuine-fef084d6.png`. Its ordinary text prompt explicitly
describes the navy sweatshirt, white neckline and closet. For another genuine source, review/rewrite those
details and both output-dimension nodes before Run; that new source is not automatically accepted.

Defaults retain seed 8675412, 816×1088, 8 Euler/CFG 1 and the same FP8/LoRA chain as Cocktail. One genuine source,
scaled bicubic 1 MP, supplies the native whole-image reference on both CFG branches. Generation starts from an
empty latent; it does not upscale or copy the source pixels. Compare the entire new frame to its source for
likeness, age, lips, gaze, pose, clothing and room geometry. Exclude that source from independent likeness scoring.
Outputs save under `ComfyUI/output/production-speed/upgrade-source-preserve/`.

The [package provenance](../config/production-speed-solo-upgrade.json) records exact default-input
SHA256 values, source graphs and declared packaging differences for Individual and Upgrade. Guarded UNET,
CLIP and VAE nodes reject a wrong worker before each branch loads; the sampler checks again before sampling.
The 12 GiB available-RAM/commit floor is not a guarantee that arbitrary edited graphs fit. Default models/precision
are fixed, while upstream model caches remain reusable. Run samples again even when the seed is fixed.

### Group — Lounge Faster Quality

This fixed Lounge route keeps native face-interior-free Canny layout first, genuine training04 identity second,
V3 .90, Smartphone .25, 832×1216, 50 Euler/CFG 4, Turbo off and appearance treatment off. Guarded caching uses
warmup 10/interval 3 with separate CFG/conditioning state; it is approximate, not pixel-equivalent to Production.
Seeds 8675412/8675413/8675414 have three matched experimental passes. Another seed requires fresh review.

Inspect the saved composition guide, intended main face and every bystander. The node saves its photo and
report automatically under `ComfyUI/output/production-speed/klein9b-group-lounge-faster-quality/`.
The report's `sampling_adapter.execution_status` must say `cache_completed`. A
`cache_guard_fallback_unvalidated` result is not a validated Faster Quality pass; it is not automatically retried.

## What “Speed” proves—and does not

- [Cocktail's historical pass](../work/9b-readiness-resume-20260907/solo-six-scene-smoke/ROOT-RESULTS.md) took 46.395s
  on an isolated legacy RTX 4070 worker. It was not a matched Production speed comparison; Production Individual already uses Turbo.
- [Upgrade's historical pair](../work/9b-readiness-resume-20260907/upgrade-source-faithful-turbo/ROOT-RESULT.md) took 54.063s
  versus experimental Quality50's 322.387s on isolated legacy RTX 4070 workers, with a skin-texture/likeness tradeoff.
  This was not a comparison with the different public Upgrade graph.
- [Group's three matched pairs](../work/group-cache-20260909/RESULTS.md) used 24.5–26.2% less worker time with
  likeness and visual-preservation checks passing for Lounge. That does not establish better identity or skin detail.

Solo/Upgrade's historical `--disable-dynamic-vram` 4070 timings do not transfer to normal RTX 3090/default dynamic VRAM.
New integration timings are observations, not new paired speedups. A successful Run, passing diagnostics and
visual acceptance are separate checks; every new photograph still needs full-size and thumbnail review.

## Visibility and rollback

Both worker `Mitch` junctions now target `local/comfy-workflow-library`, which exposes only `production` and
`production-speed`. The live Speed section was verified to contain exactly three workflow files; its provenance
manifest lives separately in `config`. All 235 original Production/experiment files passed byte-for-byte preservation.
Source experiments remain at their original `workflows/experiments` and `work` paths, including code, failed graphs,
photographs, frozen receipts and runtime dependencies. Nothing was wiped. Old open browser tabs are not deleted
by hiding a library folder.

The [visibility script](../scripts/set-comfy-workflow-visibility.ps1) previews changes by default. To inspect or
deliberately restore the previous full-tree view:

```powershell
.\scripts\set-comfy-workflow-visibility.ps1 -Mode Legacy
.\scripts\set-comfy-workflow-visibility.ps1 -Mode Legacy -Apply
```

Use `-Mode Curated -Apply` to return to the two-section library. This only changes the two explicitly allowed
junctions, preserves originals/transaction receipts, and does not touch worker queues, source files or unsaved
browser state. It does not roll back code or generate images. Refresh the Workflows sidebar afterward.

For focused CPU checks and the separate actual-photo release gate, see [TESTING](TESTING.md#production-speed-and-curated-visibility).
