# 9B Readiness — paused experiment checkpoint

**Paused at Mitch's request on September 4, 2026. Unfinished; not production-ready.**
Do not resume generation, unload models, change production, or promote any of
these cases until Mitch explicitly asks to return to this experiment.

This folder preserves seven exact experimental **API graphs**, not newly
polished Studio/canvas workflows. The six existing payloads were copied without
changing their bytes. The rejected Upgrade graph was extracted from its saved
experiment record and checked for exact graph equality. No generation was run
while making this checkpoint.

## What was saved

| Case | State when parked |
| --- | --- |
| Solo angle discovery | One credible downtown image: six-photo centroid 0.7009, weakest 0.5656. Its original comparative-improvement STOP is preserved; reliable performance is not yet proven. |
| Solo consistency seeds 315982047 and 315982061 | Prepared, verified, **never run**. Same frozen recipe; only seed/output prefix differ. |
| Group angle discovery | Centroid 0.712473, weakest 0.553026. Preserved historical STOP, marginal diagnostic-floor miss, and incomplete scene/seed coverage. Not approved for promotion. |
| Public downtown original and framing | Prepared, **never run**. Actual v1.1 engine comparison; explicit RTX 3090 lock must be preserved. |
| Upgrade background scene-reference | **Rejected; route closed.** Centroid 0.665583 versus the 0.70 Upgrade target, replaced house scenery and visible person halo. Retained only as failure evidence, not a recommended setup. |

The scores are cosine-similarity diagnostics, not percentages. Six genuine-photo
checks and native/thumbnail visual review remain required. A high score alone
does not establish a good photograph or identity lock.

## Evidence and dependencies

The [evidence checkpoint](../../../checkpoints/artifacts/9b-readiness-paused-20260904/README.md)
contains 182 byte-verified copies (about 54 MB): current experiment records,
source snapshots, reports, example outputs, review images and the resume rules.
Its [manifest](../../../checkpoints/artifacts/9b-readiness-paused-20260904/manifest.json)
records original paths, saved paths and SHA-256 hashes. Source files were left in
place, and production workflow hashes were unchanged during archiving.

Large models, the original genuine-reference photographs, native ComfyUI/runtime
and older experiment history remain at their recorded local paths. This is a
selected checkpoint, **not a portable full-environment backup**. The evidence
folder is local and Git-ignored; keep it if cleaning `work/` or moving machines.
The original `work/9b-readiness-20260903` research tree is also still intact.

## Resume another day

1. Start with the saved [acceptance clarification](../../../checkpoints/artifacts/9b-readiness-paused-20260904/snapshot/work/9b-readiness-20260903/ACCEPTANCE-CLARIFICATION-20260904.md)
   and [readiness matrix](../../../checkpoints/artifacts/9b-readiness-paused-20260904/snapshot/work/9b-readiness-20260903/evaluation/READINESS-MATRIX.md).
2. Verify the original working files against their frozen manifests. Archived
   scripts keep original path assumptions: do not run relocated copies blindly
   or restore them over newer code without reviewing the differences.
3. Recheck both GPUs, queues, shared physical RAM and model/reference/source
   hashes. The last hold was retained memory, not a running generation. Do not
   assume that old resource snapshot still describes today's machine.
4. The next selected test is the two frozen Solo consistency seeds using the
   [saved instructions](../../../checkpoints/artifacts/9b-readiness-paused-20260904/snapshot/work/9b-readiness-20260903/solo-angle-consistency/README.md).
   Keep both results and independently review complete images and all six scores.
5. The separate public original/framing pair uses its own locked-3090 runner and
   [instructions](../../../checkpoints/artifacts/9b-readiness-paused-20260904/snapshot/work/9b-readiness-20260903/public-framing-confirmation/README.md).
   Successful Solo API tests would not establish public-node parity.

Do not restart the closed background, OmniGen2, Krea retouch or prior parameter
sweeps as if they were new ideas. Remaining Group, Upgrade and mode coverage is
still required for the original overall goal. **No automatic production rollout.**
