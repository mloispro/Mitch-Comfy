# 9B Readiness — paused September 7, 2026

**Parked at Mitch's request. Unfinished and not production-ready.**
Resume only when Mitch explicitly asks to return. No automatic tests or
production rollout. This is the latest checkpoint; the September 4 archive is
preserved as historical evidence.

## Saved state

| Experiment | Status |
| --- | --- |
| Solo angle discovery | Promising single example; previous results and limitations preserved. |
| Solo consistency, seeds 315982047 and 315982061 | Both images generated successfully, in 33.841 and 32.916 worker seconds. **Likeness scoring and final acceptance unfinished.** First image visually reviewed; second review pending. |
| Group angle discovery | Partial evidence only; identity consistency and broader coverage unfinished. |
| Public v1.1 downtown original/framing | Prepared, **never run**. Explicit RTX 3090 lock retained. |
| Upgrade background scene-reference | **Rejected / closed route**, retained so it is not repeated as a new idea. |

The seven JSON files are exact experimental **API payloads**, not newly polished
canvas/Studio workflows. `UNSCORED` means generated but not accepted. Do not
interpret execution success or a plausible-looking face as proven identity.

## Preserved evidence

The [local checkpoint](../../../checkpoints/artifacts/9b-readiness-paused-20260907/README.md)
contains 212 byte-verified copies (about 55 MiB): all selected September 4
evidence, the latest two actual images and execution receipts, frozen settings,
the unrun scoring script, and current pause/resume notes. The
[manifest](../../../checkpoints/artifacts/9b-readiness-paused-20260907/manifest.json)
records paths, sizes, hashes and unchanged production workflow hashes during
archiving. Existing source files and the earlier archive were preserved.

Both queues were empty at the parking check. No generation, evaluation, model
unloading, cancellation or service restart was performed while archiving.

## Pick up another day

1. Read the current
   [pause notes](../../../checkpoints/artifacts/9b-readiness-paused-20260907/snapshot/work/9b-readiness-resume-20260907/PAUSED.md).
   They supersede the earlier resumption plan and all old "never run" labels for
   the two Solo consistency seeds. Older resource holds are historical too.
2. Verify saved hashes and current source/reference/model compatibility.
   **Review and score the existing two Solo images first; do not regenerate them.**
   Use the prepared evaluator from its original project location after checking
   its assumptions. Compare all six genuine references and inspect full images
   and thumbnails, including identity, skin, hands, shoes and background.
3. Only then consider the separate actual-public original/framing comparison.
   Recheck both GPUs, queues and available RAM, and preserve its RTX 3090 lock.
   Solo API success does not establish public-node parity.
4. Group, Upgrade and scene/mode coverage still need work. Keep rejected routes
   closed unless new evidence supports a genuinely different mechanism. Current
   Upgrade findings are also saved; the separate
   [Upgrade High checkpoint](../Upgrade%20High%20-%20PAUSED%202026-09-07/README.md)
   records that work in detail.

Models, original genuine photographs and the ComfyUI installation remain external
local dependencies. This is not a portable full-environment backup. The evidence
directory is Git-ignored; keep it when cleaning `work/` or moving the project.
Archived scripts retain their original path assumptions: do not execute them
from relocated folders or restore them over newer code blindly.
