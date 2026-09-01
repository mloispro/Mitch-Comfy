# FLUX.2 full-body proportion and expression evaluation — 2026-08-25

> **Historical record — not current instructions.** This branch was rejected. See `docs/STATUS.md` for the current workflow and LoRA inventory.

## Verdict

No candidate from this branch is approved. A genuine full-body reference fixed the visually oversized-head
failure, but the production v1 LoRA did not produce an attractive relaxed expression while retaining strong
held-out identity. Do not promote the pleasant-looking identity-drift outputs, add a face swap, or spend more
seeds and strength sweeps on this checkpoint for this full-body scene.

## Proven mechanism and remaining failure

The useful change was splitting the two compact 0.25 MP FLUX.2 references by role:

1. a genuine full-body photo establishes shoulder width, torso, limb length, and head-to-body scale;
2. a genuine current portrait establishes face identity and expression.

All candidates used FLUX.2 Klein Base 4B, the v1 step-1,250 LoRA, 20 Euler steps, CFG 4, a single whole-frame
generation, and no mask, face swap, restoration, selective sharpening, or compositing.

The split-reference candidate using `20260815_165446.jpg` retained identity at `0.7521` against three genuine
photos (`strong_match`) and visually corrected body scale, but its one-sided squint/smile was rejected by Mitch.
Changing only the seed and then changing only the smile wording did not remove the strained expression.

## Rejected controlled variants

| Variant | Proportion | Held-out identity | Decision |
| --- | ---: | ---: | --- |
| Full-body reference + `20260815_165446.jpg`, LoRA 0.5 | visually corrected | `0.7521` | Strong identity; rejected expression |
| Replace face reference with `20260818_173106.jpg`, LoRA 0.5 | `0.2911` face/person width | `0.6029` | Pleasant expression; identity drift |
| Raise only LoRA to 0.6 | `0.2836` | `0.5562` | Identity regressed |
| Official whole-frame expression edit, compact portrait | `0.3004` | `0.5614` | Integrated and calm; identity drift |
| Training-aligned closed-smile portrait `20240619_001913.jpg` | `0.2889` | `0.4998` | Best visual expression; different person |

Head-integrity checks passed on the measured outputs. The automated proportion and face scores remain
diagnostics; full-size visual review correctly rejected the expression even when identity passed.

## Existing LoRAs

`aitk/candidate-v2` is not an untried solution. Its documented evaluation rejected the best balanced checkpoint:
full-body action scored `0.5792`, with overly smooth skin and nose/neck distortion. The other unvalidated
`mitch-genuine-klein-*` files have no primary workflow, exact compatibility record, or held-out acceptance report,
so they must not be presented as proven alternatives.

## Next defensible path

The current v1 data is dominated by close and upper-body selfies and contains only one usable full-body training
photo. A new LoRA attempt requires new genuine camera photos, not generated references:

- multiple current non-mirror full-body and three-quarter walking photos at street-scene subject scale;
- relaxed closed-mouth and slight-teeth smiles from front and both three-quarter angles, with both eyes open;
- several backgrounds and sessions to avoid learning one room, selfie angle, or expression asymmetry;
- held-out full-body and smile photos reserved for evaluation.

First validate the new LoRA on a simple one-person walking frame. Add cars and secondary people only after body
scale, expression, identity, and integration pass together.

## Artifacts

- Strong-identity / rejected-expression base:
  `C:/projects/AI-Tools/ComfyUI/output/flux2-full-body-proportion-smile/seed-8675312/photo_00001_.png`
- Pleasant-expression / identity-drift output:
  `C:/projects/AI-Tools/ComfyUI/output/flux2-full-body-proportion-smile/seed-8675312/photo_00005_.png`
- Whole-frame edit / identity-drift output:
  `C:/projects/AI-Tools/ComfyUI/output/flux2-official-edit/proportion-expression/seed-9472401_00001_.png`
- Reproducible one-pass runner: `scripts/run-flux2-full-body-proportion-smile.ps1`
