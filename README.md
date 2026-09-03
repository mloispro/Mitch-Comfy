# Mitch Comfy Workbench

This repository is the source of truth for Mitch’s local ComfyUI workflows and locally maintained custom nodes.

Start here:

- `docs/STATUS.md` — canonical list of current workflows, installed LoRAs, and retired routes.
- `docs/HOW-TO.md` — normal operation, verification, rollback, and maintenance.
- `docs/lora-cleanup-2026-09-01.md` — exact LoRA keep/delete record.

## Current photo workflows

| Need | Workflow |
| --- | --- |
| Create a completely new solo, full-body, or lifestyle photograph | `Mitch/production/FLUX.2 Klein 9B Mitch Identity Studio v1.1 - Visual Presets` |
| Match one of the prepared or custom group compositions | `Mitch/production/FLUX.2 Klein 9B Mitch Group Scene Studio v1.1 - Visual Presets` |
| Improve an existing one-person Mitch image without intentionally changing its layout | `Mitch/production/FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1.1` |
| Restage one of the validated dating templates with FLUX.2 Dev | `Mitch/production/FLUX.2 Dev LoRA - 9 Dating Scenes v1` |

`Dataset gen - QWEN 2511 - 3-photo` and `Train Generated Dataset - AI Toolkit` are utilities, not
normal photo-generation recommendations.

The primary new-image workflow is Klein Base 9B with the protected V3 step-1600 Mitch LoRA and genuine native
reference photographs. The Dev workflow is a validated specialty route using the protected Dev V2 step-1000 LoRA.
All four photo workflows are local and require visual review; none uses a hosted generator or face swap.

## Repository layout

- `workflows/production` — visible Production workflows; the three Klein 9B entries are all v1.1 with no duplicate v1 sheets.
- `custom_nodes/ComfyUI-AIToolkit-Training` — local nodes used by the current workflows and retained internal generation engines.
- `custom_nodes/ComfyUI-AIToolkit-Training/web/assets/scene-presets/manifest.json` — canonical Identity and Group
  visual-preset data shared by the Python shells, browser gallery, verification, and preview-candidate tooling.
- `docs` — current instructions plus dated evaluation evidence.
- `checkpoints/legacy-workflows` — hidden rollback, rejected, and superseded graphs.
- `checkpoints/legacy-scripts` — retired experiment tooling; archive only, not runnable in place.
- `checkpoints/manifests` — historical hashes and acceptance records.
- `checkpoints/loras/mitch` — Git-LFS-backed copies of the four protected Mitch-trained keeper LoRAs.
- `patches` — retained training provenance.

The repository is linked into ComfyUI:

- `workflows` → `C:\projects\AI-Tools\ComfyUI\user\default\workflows\Mitch`
- `custom_nodes\ComfyUI-AIToolkit-Training` → the matching ComfyUI custom-node directory
- `assets\comfy-input` is synchronized into the ComfyUI input directory by `scripts\setup-links.ps1`

Refresh the ComfyUI Workflows sidebar after adding or moving a workflow. Reopen a workflow after its JSON changes.

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
.\scripts\verify.ps1
git diff --check
git status --short
```

The full verifier checks workflow JSON, locked assets and hashes, linked ComfyUI nodes, synchronized inputs, and
the local unit tests. Specialized verifier commands are listed in `docs/STATUS.md`.

Production filenames stay stable. Git history and the hidden archive replace duplicate `v2`, `final`, or
`final-final` files.
