# Upgrade High — paused by Mitch, 2026-09-07

User request: "lets pause this for now". Do not resume until explicitly asked.
This is unfinished experimental work, not a production release or Git checkpoint.
Existing September 4 checkpoint, all September 7 results and installed models
remain in place; no files were moved or deleted for this pause.

## Goal to resume

A visibly stronger High than Low: better eyes/brows and a natural, attractive
closed-lip smile, leaner rather than puffy cheeks, clearer realistic skin/hair,
while recognizably Mitch and preserving pupil focus/head direction. No new
character LoRA training; prefer no character LoRA. Local only, no photo uploads.
Production remains Low default, Phone ON / Turbo OFF. Upgrade's RTX3090 lock stays.

## Saved state

- [September 7 investigation](../../../docs/upgrade-high-resume-2026-09-07.md).
- [Final explicit-feature test and alternatives screened](../../../docs/upgrade-high-explicit-features-2026-09-07.md).
- All prepared graphs, execution receipts, comparisons, CPU scores and reviews:
  `C:/projects/AI-Tools/Mitch-Comfy/work/upgrade-high-20260907/`.
- Raw images: `C:/projects/AI-Tools/ComfyUI/output/upgrade-high-20260907/`.
- [Prior September 4 checkpoint](../Upgrade%20High%20-%20PAUSED%202026-09-04/README.md).

BeautyGRPO native256/512 and base-Kontext explicit-feature tests did not provide
meaningful High differentiation. Latest base-Kontext likeness0.755352 versus
source0.753158 indicates preservation, not beauty success. No result was promoted.
Earlier stronger native Klein edits either changed likeness or lost their visible
beauty effect with stronger identity conditioning. Preserve these failures; do not
restart the same blind prompt/strength/seed grids.

The last read-only audit ruled out accidental retention of the source latent:
the official basic Kontext template uses the same source/reference routing;
Flux full-denoise initialization starts at sigma1, so the initial source-latent
coefficient is zero. Reference tokens remain active through denoising. Replacing
the sampler input with an equal-sized empty latent is not a supported fix.
Model/prompt edit sensitivity remains a hypothesis, not a proven root cause.

## Resume boundary

Both queues8188/8189 were empty; all research agents were completed. No worker
was stopped, cache freed or generation interrupted. No new work is scheduled.
On explicit resume, read the evidence and establish a specific causal diagnostic
or primary-source-supported new mechanism before another render. The closed
experiments do not prove that the overall goal is impossible. Any eventual High
still needs visibly useful results, genuine-reference evaluation, three-photo
validation and public-workflow/default regression tests before production.
