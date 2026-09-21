# Upgrade High — PAUSED experiment

Parked at Mitch's request on **2026-09-04**. Unfinished, not approved, and not scheduled to resume.

## Open later

In ComfyUI, open **Mitch / experiments / Upgrade High - PAUSED 2026-09-04**.
Refresh the workflow list if the new folder is not yet visible. There are two different saved sheets:

- **Upgrade High - UNFINISHED**: the current Klein Upgrade graph with High selected in this experimental copy. Phone ON, Turbo OFF, seed 8675416, 50 steps. It still uses the existing character LoRA. This is not a new successful stronger-High recipe.
- **PixelSmile - REJECTED TEST**: the latest character-LoRA-free expression probe. Its 14-node computational graph round-trips exactly to the executed score-0.5 API graph. The neutral score-0 control is also preserved in the evidence bundle. Neither passed.

Production was **not moved, overwritten or changed**. Its default remains Low, Phone ON / Turbo OFF. These visible sheets use installed node code; the separate frozen code snapshot preserves this date's implementation if that code later changes.

## Saved state

[Checkpoint manifest](../../../checkpoints/artifacts/upgrade-high-paused-2026-09-04/manifest.json)
contains SHA256-verified copies of 198 files (about 21 MB): source code and tests,
investigation notes, original production graph, model/download receipts, exact
PixelSmile run settings/history/audits, both full outputs, before/after comparison
sheets, genuine references and the three Upgrade inputs. Large model weights
remain installed in ComfyUI; they were not duplicated.

[Frozen handoff](../../../checkpoints/artifacts/upgrade-high-paused-2026-09-04/README.md)
explains how to interpret and resume the snapshot. Earlier experiment artifacts
remain at their original locations; this archive does not delete or replace them.

## Why paused

High still did not reliably improve eyes, source-like closed smile and cheek shape
on both source scenes plus a genuine third image. PixelSmile altered eye/nose
identity and lost the slight smile: five-reference likeness 0.329 at score 0.5,
0.366 at score 0, versus genuine source 0.797. This was also a visual rejection,
not just a numeric threshold. No three-photo acceptance or production promotion.

## Resume only when requested

Read the archived source-faithful plan, PixelSmile research note and two-run review first.
Do not repeat the already failed expression/seed sweeps. Author BF16/bicubic parity
is unresolved; this is not proof that a character LoRA is necessary.

Keep the constraints: local only, no photo uploads or new character training;
prefer no character LoRA throughout the image lineage, existing one only as an
evidence-supported fallback. Keep source gaze/head direction, closed lips/no
invented teeth, realistic skin/hair, detailed coherent background, Phone default
ON and Upgrade Turbo OFF. Stronger High must be clearly useful and recognizable.

Before any deliberate rerun, inspect **both GPUs and both queues**. Upgrade stays
on **RTX 3090 / port 8188**. The native PixelSmile sheet has no automatic GPU
routing guard: do not queue it on 8189. Archived scripts keep their original
workspace path assumptions; do not run the copied scripts in place or blindly
restore them over newer work. Nothing was queued or restarted to make this archive.
