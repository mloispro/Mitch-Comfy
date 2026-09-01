# FLUX.2 9B / 4B street-corner model-switch evaluation — rejected

> **Historical record — not current instructions.** The model-switch route and runnable entry points were deleted after visual rejection. See `docs/STATUS.md`.

**Final status (2026-08-29): deleted.** Its 9B-scene/4B-identity branch reused the rejected v1.0.5 masked
host-replacement route. Full-size review found oversized head proportions and a Photoshopped subject boundary.
The node, workflow, runner, and test were removed; this file remains only as failed-experiment history.

## Result

The selectable workflow worked technically, but neither route passed the complete street-corner acceptance
contract. The graph and runner were later deleted; the paths below identify their test-time locations only.

- Deleted workflow at test time: *workflows/experiments/FLUX.2 9B vs 4B Street Corner Comparison.json*
- Node: `Flux2EasySocialPhotoModelSwitch`
- Deleted test runner at test time: *scripts/run-flux2-model-switch-comparison.ps1*
- Test worker: RTX 4070 on port `8189`
- Shared inputs: four genuine photos, `896×1344`, full-body action, natural smartphone finish
- Required scene: Mitch plus four pedestrians and exactly two vehicles at a detailed street corner

The selector does not convert, merge, or reinterpret model weights. The 9B option runs the identity-free Klein 9B KV plate route and then the existing 4B Mitch-LoRA subject regeneration. The 4B option runs the existing single-pass Klein Base 4B Mitch-LoRA route.

## 9B scene to 4B identity

The corrected prompt produced compatible 9B plates, but all six frozen 4B identity attempts were rejected without saving a misleading final result.

- Identity range: `0.8161–0.8355`
- Best candidate: identity `0.8355`, detection `0.8156`, subject/neighbor edge ratio `0.9080`
- Best candidate people: `16` on the plate, `15` after identity regeneration
- Best candidate vehicles: `2` on the plate and `2` after identity regeneration
- Face height ratio: `1.2294` versus allowed `0.90–1.12`
- Face width ratio: `1.1953` versus allowed `0.90–1.12`
- Head integrity: rejected for insufficient crown clearance

Full-size review agreed with the automated rejection: the background was detailed and coherent, but the regenerated face/head was enlarged and more locally rendered than the host geometry supplied by the 9B plate. This is a cross-model handoff failure, not an identity-similarity failure.

## 4B direct identity

The strict count-gated run generated three candidates. All preserved identity well and placed the requested range of pedestrians, but all exceeded the two-vehicle target.

| Seed | Identity | People detected | Vehicles detected | Result |
| ---: | ---: | ---: | ---: | --- |
| `8675310` | `0.8211` | `6` | `5` | rejected: count mismatch |
| `8675311` | `0.8092` | `5` | `8` | rejected: count mismatch |
| `8675312` | `0.8813` | `7` | `4` | rejected: count mismatch |

An earlier run with an unparseable count phrase produced a visually reviewable frame at identity `0.8008`, but it contained eight vehicles. It is retained only as diagnostic evidence and is not an accepted result.

## Final decision

- Do not restore the model switch or its runner; both routes failed the complete contract.
- Do not promote the 9B-to-4B route: it repeatedly changes face/head geometry despite strong identity scores.
- The 4B direct route also failed this exact brief because it overpopulated traffic.
- The proposed independent Klein Base 9B LoRA campaign was later completed. Its selected V3 step-1600 adapter
  now powers the current whole-frame workflows listed in `docs/STATUS.md`; it does not validate this deleted handoff.
