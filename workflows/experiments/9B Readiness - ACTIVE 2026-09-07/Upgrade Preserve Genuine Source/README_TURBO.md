# Upgrade — Preserve Genuine Source (TURBO8, experiment)

[Open Turbo8](<C:/projects/AI-Tools/Mitch-Comfy/workflows/experiments/9B Readiness - ACTIVE 2026-09-07/Upgrade Preserve Genuine Source/Upgrade - Preserve Genuine Source - TURBO8 EXPERIMENT.json>) beside the unchanged [Quality50 option](<C:/projects/AI-Tools/Mitch-Comfy/workflows/experiments/9B Readiness - ACTIVE 2026-09-07/Upgrade Preserve Genuine Source/README.md>).

For this one genuine-photo test, Turbo took **54 seconds versus322 seconds** on the same type of fresh isolated RTX4070 worker—about6x faster in this pair. It passed independent native/thumbnail review and the unchanged source-fidelity diagnostics. The tradeoff: slightly lower likeness (**.80417 versus .81779**; genuine source .82585) and somewhat smoother skin. This is not better recovered facial detail, High beauty, a universal enhancement preset, or production promotion. The previous house/canyon and production Turbo failures remain failures.

## Use

Import the Turbo8 JSON in ComfyUI. The one source is the already-staged [genuine navy-shirt/closet example](<C:/projects/AI-Tools/ComfyUI/input/mitch-upgrade-third-genuine-fef084d6.png>), not a generated identity reference. The source must already show the correct person, pose, gaze and expression. The prompt is specific to that photo. Other images require deliberate prompt and both dimension-field review and are unvalidated.

This UI represents the exact executed21-node API graph: **8 Euler steps, CFG1, seed8675412,816x1088**, full VAE, source bicubic1MP latent conditioning, with Base9B -> installed BF16-source Turbo rank256 strength1 -> genuine-trained Mitch V3 identity .9 -> Phone v13 .25. It retains Base FP8 runtime loading; the BF16-extracted adapter on that runtime is a locally tested combination, not full author BF16 precision parity. No face restoration, masks, upscaler, warp, new training or second pass. Required models and exact hashes are in the [frozen package](<C:/projects/AI-Tools/Mitch-Comfy/work/9b-readiness-resume-20260907/upgrade-source-faithful-turbo/README.md>).

**Ordinary nodes do not enforce a GPU lock.** Before queueing, verify ownership, both GPUs/queues, model availability and available host memory. The tested isolated4070 worker was stopped. Do not queue onto an arbitrary or active worker; production Upgrade remains3090-locked and is not the same graph. UI schema and exact API equivalence are checked offline against the captured installed-node schema; interactive browser import itself has not been tested.

## Evidence and boundaries

Actual job `ac58eb1a-77b7-4cbc-87cf-8b7f8854e327`; [native image](<C:/projects/AI-Tools/Mitch-Comfy/work/9b-readiness-resume-20260907/upgrade-source-faithful-turbo/runs/ready-val03-turbo/raw_00001_.png>) SHA `5A02FA91E24AD61D43AE1DC9085CF773485E40691F31851718038CB2889D4FA9`.

The unchanged [five-genuine-reference evaluation](<C:/projects/AI-Tools/Mitch-Comfy/work/9b-readiness-resume-20260907/upgrade-source-faithful-turbo/evaluation-val03-turbo/audit.json>) excludes the actual val03 source only: likeness loss from source .02169 (limit .03), weakest-reference similarity .59741, source pose error .3994 degrees, center shift .6385%/.2767%, and closed-lip ratio .000578. No metric failures. These are diagnostics, not an exact identity or gaze lock; the eye-coordinate diagnostic was .04707 and is not an exact-gaze guarantee.

[Independent pre-metrics visual review](<C:/projects/AI-Tools/Mitch-Comfy/work/9b-readiness-resume-20260907/upgrade-source-faithful-turbo/INDEPENDENT-BLIND-VISUAL-REVIEW.md>) found recognisable identity and whole-frame integration with the smoother-skin caveat. Hair, wall and clothing read photographically; small closet/collar details are regenerated, not recovered facts. Keep the genuine source and review every output. Prefer Quality50 when its modestly better likeness/skin texture matters more than this measured time saving; no other photograph or seed is proven by this pair.

The separate scorer admission retains `turbo:true` and validates exact hashes, order and settings; it changes only the old Turbo-off refusal, not identity/expression/geometry math. Both comparison slots use the actual accepted Quality50 PNG, with an explicit QUALITY50 presentation label. The legacy internal `CANDIDATE HIGH` key does not change this option into High. Production, the frozen Quality UI/README and all failed evidence remain unchanged.
