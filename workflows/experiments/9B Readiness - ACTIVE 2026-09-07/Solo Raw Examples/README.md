# Raw Solo examples — experimental, not public v1.1

[Workflow JSON](<C:/projects/AI-Tools/Mitch-Comfy/workflows/experiments/9B Readiness - ACTIVE 2026-09-07/Solo Raw Examples/Solo - Rooftop Cocktail - PASSED SINGLE CASE - EXPERIMENT.json>) · [Previously verified image](C:/projects/AI-Tools/Mitch-Comfy/work/9b-readiness-resume-20260907/solo-six-scene-smoke/runs/ready-rooftop-cocktail-city-lights/rooftop-cocktail-city-lights-seed315982047_00001_.png)

The cocktail JSON exposes the **exact 31-node recipe of one completed passing
image** as ordinary editable ComfyUI nodes. Load the JSON into ComfyUI; it includes
the full prompt, model filenames, three genuine inputs, fixed seed315982047 and
all sampling settings. No new model download or hosted service is required.

This is not the two-reference public Solo workflow. The actual public same-seed
cocktail separately failed its closed-lip requirement. This raw case passed
independent native/thumbnail review and the unchanged six-genuine-reference
floor (centroid.7705, minimum.5818). It is one scene/seed, not a universal identity
lock or general readiness claim; other raw scenes and public profiles differ.

**Do not press Run on an arbitrary worker.** Ordinary nodes contain no GPU lock.
Root must first admit the isolated legacy4070 experimental worker and check both
GPUs, queues and host RAM. Loading the file is safe but is not queue authorization.
The production3090 lock, workers, caches and workflows are unchanged.

The example preserves every execution input, even the historical SaveImage prefix;
ComfyUI normally increments output numbering. Never overwrite the historical
image. Changing seed, text, references or settings makes an unvalidated variation.
No face swap, upscaler, restoration, mask or second pass has been added.

The existing project serializer and reverse checker verified exact API/widget/
link equivalence against live core schemas. Browser import/export is still a
separate root check before this artifact is advertised as frontend-validated.
No rerender was used to package it.

Audit and reproducible read-only verification:
`work/9b-readiness-resume-20260907/solo-cocktail-ui/package_ui.py verify`.
Its `equivalence.json` pins the artifact, source API, reused serializer, live-schema
capture and actual historical image/evidence. Restaurant/canyon are not packaged
here yet; this first case proves the bounded conversion path only.
