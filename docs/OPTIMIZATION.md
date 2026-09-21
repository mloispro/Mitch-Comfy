# Where the next unit of work can help most

Priorities inferred from the local code and completed evidence. They are proposals, not new benchmark
results or permission to restart experiments. [STATUS](STATUS.md) records unresolved work.

| Priority | Candidate | Why it deserves attention | Smallest useful acceptance check |
| --- | --- | --- | --- |
| Complete | Second genuine-source Upgrade coverage | [Balcony val05](../work/upgrade-generalization-20260921/RESULT.md) passes fixed source-relative and visual gates in20.431s; small likeness loss/smoothing remain | Use the existing workflow within its two-source evidence. New sources still need their own review. No repeat of this probe or stronger-High claim |
| Conditional | Original Solo card parity, only if that card must reproduce the accepted Cocktail | [Source comparison completed](solo-cocktail-comparison-2026-09-21.md): references, surrounding prompt and diffusion precision differ; the public preset/engine is unchanged. The accepted Speed handoff already serves this case | Do not repeat the source audit or rerun the accepted image. If original-card parity is required, isolate one variable group; diffusion loading is the smallest mechanical change, with no proven improvement. Preserve all visual/likeness gates and Speed GPU/precision guards |
| 2 | Consider broader analyzer reuse only for a concrete chain that still repeats analysis | The existing likeness CLI's scoring/calibration duplication is now removed and measured below. The earlier [cross-tool pilot](../work/9b-readiness-20260903/evaluation/feature-reuse-pilot/RESULTS.md) and [Group/Upgrade replay](../work/9b-readiness-20260903/evaluation/feature-reuse-coverage/RESULTS.md) support a narrow raw-record boundary | Identify actual remaining repeated calls before adding a shared framework. Keep selectors/exclusions and raw diagnostics unchanged. Standalone Group/Upgrade already use one analyzer; do not assume a further speed gain |
| Conditional | Revisit Group identity limits when there is new mechanism/data evidence | [1.10 result](../workflows/experiments/group-masked-strength110-20260908/ROOT-RESULT.md) closed the tested strength refinement; [corrected photo assessment](../work/9b-readiness-20260903/REASSESSMENT-20260904.md) establishes the real framing limits | Specify the changed premise and primary-source compatibility before a new trial. New training remains deferred; missing coverage is not a proven sole cause |
| Input/research gate | Stronger High and target-specific Group identity | [September 21 review](high-group-gate-2026-09-21.md) establishes unchanged known stills, no admitted external High target, and no output-person isolation in the inspected Klein feature-transfer candidate | Inspect newer originals if available, or a changed source-supported mechanism. Admit a target/conditioning path before building or generating; preserve the rejected recipes and unique weights |

## Already completed; use the handoff

The existing [likeness scorer](../scripts/evaluate-face-likeness.py) automatically reuses detections
for repeated decoded pixels within each invocation. Its CLI and report schema are unchanged.
[Three paired six-reference measurements](../work/face-likeness-cache-20260909/results.json) show median
5.619→4.942s (12.1% less instrumented process wall time), with a separate source-excluded case also
passing exact raw/report parity. This includes startup and trace instrumentation, with alternating
run order. OS caches and other workstation activity were not controlled; it is not a generation
or total-development speed measurement.
The old cross-tool 59% pilot result is not the performance of this narrower implementation.

The [Group Lounge accelerator](../work/group-cache-20260909/RESULTS.md) completed its initial pair
and both confirmations: 24.5–26.2% less worker time across those three pairs, with relative quality
preserved and small clothing-detail changes. The separate [Production Speed rollout](../work/production-speed-rollout/RESULTS.md)
now runs it through ordinary3090/8188; its fresh image exactly matches the accepted cached seed.
The historical [private-worker commands](../work/group-cache-20260909/README-REPLAY.md) are preserved,
not required for normal Speed operation. Production defaults are unchanged. This is not an unfinished
confirmation task or proof of better identity; other scenes/settings require new evidence.

Individual Cocktail and Upgrade Source Preserve Turbo are also installed in the separate
[Production Speed section](production-speed.md), with normal-worker checks in the rollout report.
The original raw/Quality/Turbo experiments remain on disk, hidden from the curated library.
Use these handoffs; broader input/preset coverage is a distinct future task, not unfinished packaging.

## Questions that should select an experiment

- Is the failure in raw generation, the public preset resolution, or a later finish? Inspect those artifacts separately.
- Which conditioning path carries the needed information, and what evidence says the model was trained to use it?
- What did the closest previous attempt actually change? Was its failure numerical, visual, runtime or insufficient benefit?
- Can a source inspection or replay of saved outputs resolve the question before spending GPU time?
- Which single result would make us stop this approach? Record it before running.

## What to preserve when optimizing

Do not optimize an aggregate likeness score by changing face selection, dropping the weakest genuine reference,
including the source in its own held-out cohort, recalibrating a floor after seeing the candidate, or softening
visual requirements. The [readiness matrix](../work/9b-readiness-20260903/evaluation/READINESS-MATRIX.md)
distinguishes inherited requirements from prospective experimental guards.

Record loading-inclusive worker time, sampling time when available, CPU diagnostic time and manual review
separately. Compare the same model precision, recipe, worker class and declared cache state. One pair is
one observation; it is not a stable median or a speed guarantee. Count failures and recovery separately.

For source-preservation work, compare to the genuine source and the codec control when applicable. For
Group, choose the intended main geometrically before scoring and retain partial people, hand ownership and
all bystander diagnostics. A fast rejected image is still rejected.
