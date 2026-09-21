# Production Klein 9B health check — 2026-09-04

**Result:** Identity, Group and Upgrade each completed a fresh end-to-end run at
their shipped defaults on the RTX 3090. Both workers finished with empty queues.

## Cause and fix

The supplied error is a worker mismatch: Identity Studio v1.1 ran on port 8189,
which reports an RTX 4070. All three production Klein 9B engines explicitly require
the RTX 3090 at port 8188. Both workers share the same workflow directory, so the
4070 sidebar lists these graphs even though it cannot execute them.

Added `web/production_gpu_guard.js` to the existing custom-node extension. It checks
the live `/system_stats` device, shows a wrong-worker notice with the 8188 link,
and checks again before `api.queuePrompt`. It blocks an incompatible or unverifiable
worker before submission. It does not redirect a prompt, alter a graph, or remove
the backend GPU lock. Refresh existing browser tabs to load it.

The production generation engines, reference order, settings, LoRAs and workflow
JSONs were not changed by this health check. Existing uncommitted Upgrade work was
preserved.

## Verification

- All three specialized read-only verifiers passed against port 8188, including
  live nodes, model hashes, protected references, preset assets and frozen settings.
- The guard regression test covers each production node on the 4070 and 3090,
  failed device checks, unchanged prompt/options forwarding, unrelated workflows,
  and graph changes. It is included in `scripts/verify.ps1`.
- Browser inspection confirmed that Identity, Group and Upgrade load their public
  interfaces and show the correct warning on the 4070. The 3090 displays the Group
  interface without that warning.
- The live wrong-worker Run-click test was blocked by automatic approval review:
  if the browser guard failed, that test could submit to a locked-out GPU. No bypass
  was attempted. The queue interception was tested without generation; actual
  production runs use the 3090.
- Both GPU queues and Python processes were inspected. Only the two ComfyUI
  workers were running; no Python training process was present. Idle model cache
  was released through `/free` before the first load. Neither worker was restarted
  or interrupted.

Fresh end-to-end results are recorded in `work/prod-9b-health-20260904/` with
workflow hashes, submission intent, prompt IDs, terminal histories and CPU-only
likeness diagnostics against six genuine held-out photographs.

### Completed default runs

| Workflow | Prompt ID | Engine time | Six-photo likeness | Baseline comparison |
| --- | --- | --- | --- | --- |
| Identity | `cbffecdd-f897-4918-8a67-7a6e89dde0e9` | 21.317 s | 0.7354, `strong_match` | Exact decoded pixels versus September 3 accepted default |
| Group | `fe692fcb-f024-4515-af15-101f9d4b2c7d` | 260.635 s | 0.5624, `near_match` | Exact decoded pixels versus September 3 accepted default |
| Upgrade | `5bef37fd-0197-4ee6-8911-32fbe1a81fe0` | 505.215 s | 0.7405, `strong_match` | Small pixel variation versus September 4 validated v5 Low output; not pixel-identical |

The separate Group leakage diagnostic is unchanged at main 0.5781 and reports
four detected faces with no leakage/duplicate failures at the existing 0.55 Group
gate. Its reference-image preparation differs from the likeness evaluator, so its
score should not be substituted for the six-photo likeness number. The intended
face is central in both the image and the diagnostic bounding box.

Identity and Group were reviewed at full size and thumbnail: one intended Mitch,
plausible hair and apparent age, coherent body and scene integration, distinct
background people, readable depth, and no obvious cutout/halo or broken-image
failure. Group's likeness is still only a calibrated `near_match`; successful
execution and exact baseline reproduction do not establish an identity lock.

Upgrade completed at native 1680 × 1008 with Low, phone style on, the v5 hair
parser class 13, four ordered references, 50 steps, CFG 4 and seed 8675416 confirmed
in its emitted report. Against the latest validated v5 Low image, the mean absolute
RGB difference is 0.3603 / 255 (maximum 122); before-polish difference is 0.3521 / 255
(maximum 92). This is not an exact-pixel reproduction claim. Full-size and thumbnail
review found coherent hair/coat boundaries, readable house/tree detail, closed lips
and no new obvious cutout halo. Coarse skin texture and a tense brow remain known
appearance limitations. The optional High appearance treatment was not changed or
newly accepted by this default-path health check.

Saved photos:

- Identity: `C:/projects/AI-Tools/ComfyUI/output/flux2-klein9b-mitch-identity-studio-v1/20260904-111800-684912/photo_00001_.png`
- Group: `C:/projects/AI-Tools/ComfyUI/output/flux2-klein9b-mitch-group-scene-studio-v1/20260904-112257-228440/photo_00001_.png`
- Upgrade: `C:/projects/AI-Tools/ComfyUI/output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260904-113212-116033/photo_00001_.png`

## Conditioning evidence

This is an operability check of existing recipes, not a new image workflow.

| Workflow | Conditioning and default sampling |
| --- | --- |
| Identity | Protected V3 step-1600 identity LoRA plus two genuine photographs, each resized, VAE-encoded and appended in the selected profile order. Rooftop preset; 832 × 1216; Turbo 8 Euler steps, CFG 1. |
| Group | Face-interior-free Canny layout is reference 1 (composition); a genuine Mitch photograph is reference 2 (identity), alongside the protected identity LoRA. Approved lounge preset; 832 × 1216; 50 Euler steps, CFG 4. |
| Upgrade | Source scene, face-interior-free Canny, genuine Mitch identity, then isolated genuine hair material, in that order. The source's identity influence is not isolated. Included source; native size; 50 Euler steps, CFG 4; Low appearance and phone style on. |

All use Klein Base 9B, Qwen 3 8B, FLUX.2 VAE and Flux2Scheduler. The engines retain
the proven identity LoRA at 0.90 and Smartphone Snapshot v13 at 0.25. The generated
default scene/source assets are fixtures, never genuine identity ground truth.

Primary-source basis: the [Base 9B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B)
supports native multi-reference editing and LoRA fine-tuning and gives the 50-step /
CFG-4 base example; the [official ComfyUI edit template](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_flux2_klein_image_edit_9b_base.json)
provides the native graph; the [Turbo author model card](https://huggingface.co/kalle07/FLUX.2-klein-9B-turbo-lora-set)
documents the separate acceleration adapter. The local conditioning audit and
prior evaluations are in `docs/flux2-klein9b-reuse-hardening-2026-09-03.md`.
These sources support the mechanisms, not a guarantee of identity in every image.
