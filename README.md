# Mitch Comfy Workbench

This repository is the source of truth for Mitch’s local ComfyUI workflows and locally maintained custom nodes.

Start here:

- [Development entry point](docs/START-HERE.md) — task-to-code map, evidence order and efficient change loop.
- [Current status](docs/STATUS.md) — public workflows, qualified results and unresolved work.
- [Operating guide](docs/HOW-TO.md) — normal operation, verification, rollback and maintenance.
- [Production Speed](docs/production-speed.md) — three bounded, ordinary-Run alternatives and their rollout checks.
- [Decision history](docs/DECISIONS.md) — completed experiments, failed approaches and limits on what was proven.
- [Testing map](docs/TESTING.md) — focused regression checks and the distinction between code checks and photo acceptance.
- [Optimization priorities](docs/OPTIMIZATION.md) — next opportunities ranked by existing evidence.

The full 9B suite is not proven ready across scenes and modes. Public workflows, qualified experimental
successes and rejected recipes are distinguished in STATUS. For efficient development, start with the
short guides and follow their links into code/results; use `docs/generated` to find less familiar files.
Routine searches follow [.ignore](.ignore), keeping historical folders and generated inventories
out of ordinary results. Historical evidence remains available through explicit paths and the evidence index.

Check an affected guide with `python scripts/project-docs.py --check --guide docs/STATUS.md`
(substitute the guide changed). The full `--check` audits all guides and generated indexes.
See [documentation maintenance](docs/DOCUMENTATION.md) for refreshing indexes and reviewing stale claims.

## Current photo workflows

| Need | Workflow |
| --- | --- |
| Create a completely new solo, full-body, or lifestyle photograph | `Mitch/production/FLUX.2 Klein 9B Mitch Identity Studio v1.1 - Visual Presets` |
| Match one of the prepared or custom group compositions | `Mitch/production/FLUX.2 Klein 9B Mitch Group Scene Studio v1.1 - Visual Presets` |
| Improve an existing one-person Mitch image without intentionally changing its layout | `Mitch/production/FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1.1` |
| Restage one of the validated dating templates with FLUX.2 Dev | `Mitch/production/FLUX.2 Dev LoRA - 9 Dating Scenes v1` |

The separate `Mitch/production-speed` section contains **Individual — Cocktail**, **Upgrade — Source Preserve
Turbo**, and **Group — Lounge Faster Quality**. They target the normal RTX 3090 worker at port `8188`.
All three have completed actual ordinary Comfy Run checks. They package specific accepted recipes, not every
scene or source; the [Speed guide](docs/production-speed.md) links the final photo-acceptance evidence. The original
Production files and recipes remain unchanged. The Speed label does not establish that each route beats its
corresponding Production workflow.

`Dataset gen - QWEN 2511 - 3-photo` and `Train Generated Dataset - AI Toolkit` are utilities, not
normal photo-generation recommendations.

The primary new-image workflow is Klein Base 9B with the protected V3 step-1600 Mitch LoRA and genuine native
reference photographs. The Dev workflow is a historically validated specialty route using the protected Dev V2 step-1000 LoRA.
The original four photo workflows and the separate Speed alternatives are local and require visual review;
none uses a hosted generator or face swap.

## Repository layout

- `workflows/production` — visible Production workflows; the three Klein 9B entries are all v1.1 with no duplicate v1 sheets.
- `workflows/production-speed` — separate, bounded RTX 3090 Speed workflows; not replacements for the original Production graphs.
- `workflows/experiments` — preserved at their original disk paths but excluded from the curated ComfyUI library.
- `custom_nodes/ComfyUI-AIToolkit-Training` — local nodes used by the current workflows and retained internal generation engines.
- `custom_nodes/ComfyUI-AIToolkit-Training/web/assets/scene-presets/manifest.json` — canonical Identity and Group
  visual-preset data shared by the Python shells, browser gallery, verification, and preview-candidate tooling.
- `docs` — maintained guides plus dated evaluation evidence; generated file/test/evidence indexes live in `docs/generated`.
- `work` — ignored local experiment code/results; indexed for discovery but not backed up by Git.
- `checkpoints/legacy-workflows` — hidden rollback, rejected, and superseded graphs.
- `checkpoints/legacy-scripts` — retired experiment tooling; archive only, not runnable in place.
- `checkpoints/manifests` — historical hashes and acceptance records.
- `checkpoints/loras/mitch` — Git-LFS-backed copies of the four protected Mitch-trained keeper LoRAs.
- `patches` — retained training provenance.

The repository is linked into ComfyUI:

- `local\comfy-workflow-library` → both workers' `user\default\workflows\Mitch` and
  `user-4070\default\workflows\Mitch` entries; the curated library links only `production` and `production-speed`
- `custom_nodes\ComfyUI-AIToolkit-Training` → the matching ComfyUI custom-node directory
- `assets\comfy-input` is synchronized into the ComfyUI input directory by `scripts\setup-links.ps1`

Refresh the ComfyUI Workflows sidebar after adding or moving a workflow. Reopen a workflow after its JSON changes.
Hiding Experiments does not delete its graphs, images, code or receipts. The
[visibility script](scripts/set-comfy-workflow-visibility.ps1) can restore the old full-tree view with
`-Mode Legacy -Apply`; see [rollback instructions](docs/production-speed.md#visibility-and-rollback).

## Safety and quality rules

- Inspect the RTX 3090 and RTX 4070 queues before generation.
- Never interrupt active GPU work.
- If the preferred GPU is busy, use the other idle GPU when the workflow and VRAM requirements support it; keep explicit GPU locks intact.
- Identity references must be genuine photographs.
- Reference order and role are part of the workflow contract.
- Automated identity scores do not replace full-size and thumbnail review.
- Do not add face swap, masks, restoration, sharpening, relighting, or upscaling without an observed failure and
  measurable acceptance test.

## Verify before check-in

```powershell
python scripts/project-docs.py --check
.\scripts\verify.ps1
git diff --check
git status --short
```

The full verifier checks workflow JSON, locked assets and hashes, linked ComfyUI nodes, synchronized inputs, and
the local unit tests. Specialized verifier commands are listed in `docs/STATUS.md`.

Production filenames stay stable. Git history and the hidden archive replace duplicate `v2`, `final`, or
`final-final` files.
