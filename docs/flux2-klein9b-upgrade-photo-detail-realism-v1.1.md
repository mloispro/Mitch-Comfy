# FLUX.2 Klein 9B – Upgrade Photo Detail & Realism v1.1

## Public interface

Open `Mitch/production/FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1.1` on the RTX 3090 worker at
`http://127.0.0.1:8188`.

The v1.1 node is a direct registry alias to the already validated Upgrade engine. There is no wrapper generation
code: sampling, model and LoRA selection, four-reference order, prompt construction, source-size policy, seed,
sampler, scheduler, and optional camera finish are unchanged. The attractiveness selector now exposes Off / Low / High;
Low v5 retains the previous finish constants but corrects the CodeFormer ParseNet hair label
from17 (neck) to13 (hair). High adds the existing optional postprocessing after gaze correction.
The hair repair is verified through actual-code CPU replay on three photos; live v5 end-to-end
validation is complete for the public-node house hair repair: actual v5/class13,
unchanged raw sampling pixels, and separately scored live Low (0.739620).
Final live pixels differ slightly from the quantized CPU replay; see the linked
repair audit. It is not the stronger-High solution requested in the ongoing experiments.
See [repair evidence](upgrade-parsenet-hair-label-bug-2026-09-04.md).

## Use

1. Load an image containing exactly one detectable face.
2. Replace the included source-specific `detail_instructions` when changing the source image.
3. Keep `Attractiveness` at `low` and `Phone-camera realism` on for the previous default treatment. Choose `high` for
   stronger brow definition, source-guided upper-lid curvature, clearer iris/sclera contrast, reduced under-eye shadow,
   forehead/under-eye crease attenuation, and slight extra warmth. Choose `off` for raw generation without face/hair/iris
   polish. High is optional and requires visual review, not a new default.
4. Start with seed `8675416`; use `8675412` only as one controlled retry.
5. Queue only on the RTX 3090 and review the photo, raw image, polish mask, and structure guide at full size and
   thumbnail.

The engine performs one 50-step, CFG `4.0`, Euler, whole-frame FLUX.2 Klein Base 9B pass. Its references remain:

1. full source photograph for scene, pose, expression, clothing, lighting, and composition;
2. face-interior-free Canny guide for geometry;
3. genuine Mitch photograph plus the protected identity LoRA for explicit identity conditioning;
4. genuine isolated hair crop for hair material.

The full source contains a face and enters as a `ReferenceLatent`, so its unintended identity influence has not
been isolated and must not be described as absent. The workflow uses no Turbo, source-latent initialization,
generation mask, face swap, restoration, upscaling, or second model pass.

## Provenance compatibility

Internal output folders, the embedded PNG report key, and parts of the engine report retain their historical `v1`
namespace. They identify the implementation lineage and keep reports comparable; they are not duplicate
public workflows or nodes.

Legacy boolean `appearance_polish` API values remain valid: `true` maps to `low`, `false` maps to `off`.
The browser migrates those saved widget values without changing phone style or seed. High never copies source facial
pixels, enlarges eyes, moves eye corners, or moves the pupil core. It may apply a bounded upper-lid-only warp toward
the source landmark curvature, plus symmetric iris and sclera contrast. The lip, hairline, head outline, and background
remain exact. Evaluation and limitations:
`docs/flux2-klein9b-attractiveness-levels-2026-09-03.md`.

Historical mechanism details and experiments remain in
`docs/flux2-klein9b-upgrade-photo-detail-realism-v1.md`. Current public-surface verification and fresh v1.1 results
are recorded in `docs/flux2-klein9b-v1.1-production-cleanup-2026-09-03.md`.

Verify without generation:

```powershell
.\scripts\verify-flux2-klein9b-upgrade-photo-detail-realism-v1.ps1
```

Use `-Smoke -Native` only after confirming that the RTX 3090, the shared 8190 worker, the RTX 4070, and Forge have
no running or pending work.
