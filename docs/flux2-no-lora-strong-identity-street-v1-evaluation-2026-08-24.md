# FLUX.2 no-LoRA strong-identity street v1 — 2026-08-24

> **Historical record — not current instructions.** This workflow and its runners are archived and are not a current recommendation. See `docs/STATUS.md`.

## Outcome

The best tested identity/background balance is a **two-stage native FLUX.2 workflow on the RTX 3090**:

1. distilled Klein 9B generates the realistic, busy street from two genuine face-angle references;
2. undistilled Klein 4B Base regenerates the whole frame at 50 steps, using the complete 9B image as scene reference 1 and three genuine photographs as identity references 2–4.

There is no character LoRA, PuLID, face swap, crop, mask, inpaint, compositing, restoration, or selective face processing. The tested one-prompt graph completed without OOM in `345.705 s` at `832×1248` on ComfyUI port `8188`.

The selected output scored `0.7584` against the five-photo held-out centroid. Its weakest held-out comparison was `0.6262`, above the genuine-reference pairwise floor of `0.6206`. This is the first tested FLUX.2 no-character-LoRA result in this project whose score against **every** held-out photograph cleared that floor. Full-size visual review by Mitch remains authoritative.

## Speed profile

Reducing only the 4B Base identity scheduler from 50 to 30 steps cut wall time from `345.705 s` to `215.528 s`: **3m 35.5s instead of 5m 45.7s**, a `37.65%` reduction. The 30-step result retained a `0.7511` centroid versus `0.7584` at 50 steps. Its weakest held-out comparison was `0.6095` versus `0.6262`, so it is the fast default while 50 remains the quality option.

Full-size inspection found the same coherent face/body/background integration, and the bystander audit passed with seven detected faces, maximum secondary identity similarity `0.0982`, and maximum secondary pair similarity `0.2072`. In the production workflow, node 36 is labeled `Fast: 30 steps | Quality: 50 steps`; the runner exposes the same choice as `-IdentitySteps`, defaulting to 30.

## Smartphone-camera refinement

The original fast result was still uniformly crisp and looked more like a polished generated photograph than a casual phone capture. One controlled prompt refinement changed only the 9B scene's camera description. It now specifies an ordinary rear 1× camera at roughly 26 mm equivalent, handheld eye-level perspective, automatic exposure and white balance, restrained computational HDR, deep but imperfect phone focus, subtle edge sharpening, mild corner softness and lens distortion, faint shadow noise, gently compressed highlights, and slight motion blur restricted to moving hands and pedestrians. It explicitly rejects studio light, beauty retouching, creamy bokeh, perfect global sharpness, and cinematic grading.

The 4B identity settings remained frozen at 30 steps / CFG 4. The result completed in `230.048 s` (`3m 50.0s`) and scored `0.7494` against the five-photo centroid. Its weakest held-out view was `0.6204`, effectively tied with the genuine-photo floor `0.6206`. The crowd-leakage audit passed: maximum secondary identity similarity was `0.0358`. Because the camera character is generated natively across the whole frame, no filter, LoRA, relighting, selective face work, or post-processing stage was added.

## What the supplied Inline Studio workflow actually contributes

The screenshot is the official Inline Studio portable-character workflow. Its useful ideas are:

- normalize each reference to about 1 MP;
- use varied face angles instead of treating a body shot as an equal face anchor;
- state image order and roles explicitly in the prompt; and
- use undistilled Klein 4B Base at 50 steps / CFG 4 for the showcased quality route.

The audited `.char` file is packaging, not a secret FLUX identity adapter. At repository commit `7679e668e3bb87cfeb8de92043a45d0ab9b0e7ea`, it stores normalized images, a character description, and SFace/DINO embeddings. SFace and DINO are used to score or flag generated faces; neither embedding reaches the FLUX denoiser. The actual generation signal is native FLUX.2 multi-reference token conditioning.

This agrees with Black Forest Labs' image-editing documentation: multiple images are supported, and prompts should assign each one an explicit ordinal role. The project therefore uses the same native mechanism without installing another UI layer.

## Controlled findings

All candidates used seed `9472363`, `832×1248`, genuine references, untouched whole-frame outputs, and local InsightFace AntelopeV2 evaluation against five held-out genuine photos.

| Route | Identity centroid | Weakest held-out | Decision |
| --- | ---: | ---: | --- |
| Klein 9B, supplied-method face + body, 4 steps / CFG 1 | 0.5388 | 0.4195 | Reject: body photo diluted face identity |
| Klein 9B, two complementary face angles, 4 / 1 | 0.6786 | 0.5096 | Better face, still below the genuine floor |
| Klein 4B Base, two face angles, 50 / 4 | 0.7157 | 0.5741 | Better identity, insufficient weakest view |
| Klein 4B Base, three face references, 50 / 4 | 0.7713 | 0.6042 | Strong identity; background visibly softer |
| 4B Base scene → FLUX.2 Dev whole-frame detail pass | **0.7828** | 0.6242 | Highest identity score; inherited scene remains soft |
| **Klein 9B street → Klein 4B Base whole-frame identity** | **0.7584** | **0.6262** | **Selected: best realistic-background / identity balance** |
| Same selected route, scene seed `9472364` only | 0.7564 | 0.6073 | Generalization alternate: strong match and clean integration, weakest view 0.0133 below floor |

The decisive change was architectural, not “more steps on 9B.” Klein 9B owns the street and crowd. The 4B Base model, which performed better with the Inline-style identity references, owns the identity edit. Passing the entire 9B image as a normal reference preserves integration and avoids the pasted-face failure seen with localized approaches.

## Exact conditioning trace

Stage 1:

`LoadImage(face) → 1.0 MP → VAEEncode → ReferenceLatent(image 1)`

`LoadImage(angle) → 1.0 MP → VAEEncode → ReferenceLatent(image 2) → Klein 9B`

Stage 2:

`complete stage-1 image → 0.5 MP → VAEEncode → ReferenceLatent(image 1: scene)`

`three genuine photos → 1.0 MP each → VAEEncode → ReferenceLatent(images 2–4: Mitch) → Klein 4B Base`

The stage-2 positive and negative conditionings receive the references in the same fixed order. The prompt says image 1 owns composition, pose, clothing, lighting, crowd, and street detail; images 2–4 own the main man's identity.

## Crowd and integration audit

The selected frame contains 11 YOLO-detected people and 7 InsightFace-detected faces. Excluding the main subject:

- maximum bystander-to-Mitch identity similarity: `0.0975`;
- maximum bystander-to-main-face similarity: `0.0793`;
- maximum pairwise bystander similarity: `0.247`.

Those values are far below the project's leakage thresholds. The identity signal did not spread into the crowd. Visual inspection also found one coherent whole-frame lighting/lens treatment rather than a face-shaped cutout or halo.

The controlled second scene seed also passed the leakage check: five faces were detected, maximum bystander-to-Mitch similarity was `0.1237`, maximum bystander-to-main similarity was `0.0906`, and maximum pairwise bystander similarity was `0.1606`. Its identity centroid stayed essentially flat at `0.7564` while only the 9B scene seed changed. This supports the mechanism generalizing across street layouts, although the selected seed remains the metric winner because all five of its held-out scores clear the genuine-photo floor.

## Reproducible artifacts

- Archived workflow: `checkpoints/legacy-workflows/production/FLUX.2 No-LoRA Strong Identity Street Corner v1.json`
- Archived API runner: `checkpoints/legacy-scripts/native-no-lora/run-flux2-no-lora-strong-identity-street-v1.ps1`
- Archived workflow builder: `checkpoints/legacy-scripts/native-no-lora/build-flux2-no-lora-strong-identity-street-v1-workflow.ps1`
- Archived settings and hashes: `checkpoints/legacy-scripts/native-no-lora/flux2-no-lora-strong-identity-street-v1.lock.json`
- Selected image: `output/flux2-no-lora-strong-identity-street-v1/winner-balanced.png`
- Fast 30-step image: `output/flux2-no-lora-strong-identity-street-v1/winner-fast-30step.png`
- Fast 30-step identity report: `output/flux2-no-lora-strong-identity-street-v1/speed-test-30step-identity.json`
- Production smartphone image: `output/flux2-no-lora-strong-identity-street-v1/winner-smartphone-30step.png`
- Smartphone identity report: `output/flux2-no-lora-strong-identity-street-v1/smartphone-prompt-30step-identity.json`
- Highest-identity alternate: `output/flux2-no-lora-strong-identity-street-v1/alternate-identity-max.png`
- Second-seed generalization image: `output/flux2-no-lora-strong-identity-street-v1/generalization-seed9472364.png`
- Second-seed identity report: `output/flux2-no-lora-strong-identity-street-v1/generalization-seed9472364-identity.json`
- Crowd audit: `output/flux2-inline-author-method-crowd-audit.json`

The UI workflow has 41 nodes and 53 links. Node IDs, link IDs, input slots, and output slots were structurally validated. Its graph is the same graph executed end to end by the API runner.

## Limits and next acceptance test

This is a strong candidate, not a universal identity lock. Two scene seeds have completed the full two-stage loop; the second retained nearly the same centroid but fell slightly below the conservative floor on one held-out angle. Small signs, shirt texture, and individual bystander faces may change during the second generation. A smaller main face will also make identity harder to preserve and judge.

The next meaningful test is not another adapter or a step increase. It is Mitch's full-size visual verdict on the selected and second-seed results. If accepted, the identity stage should remain frozen while prompts and 9B seeds are varied for new scenes.

## Primary sources

- [Inline Studio Characters](https://inlinestudio.art/characters)
- [Inline Studio portable consistent-character workflow](https://inlinestudio.art/workflows/flux-2-portable-consistent-characters-without-lora-training)
- [Inline Studio author repository](https://github.com/inlineresearch/Inline-Studio/tree/7679e668e3bb87cfeb8de92043a45d0ab9b0e7ea)
- [Black Forest Labs FLUX.2 image editing](https://bfl.mintlify.app/flux_2/flux2_image_editing)
- [Black Forest Labs FLUX.2 repository](https://github.com/black-forest-labs/flux2)
