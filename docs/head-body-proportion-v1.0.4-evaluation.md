# Easy Social Photos v1.0.4 head/body proportion correction

> **Historical record — not current instructions.** Easy Social v1.0.4 is an archived rollback, not a visible Production workflow. See `docs/STATUS.md`.

## Observed failure

The three-reference waist-up Action run at seed `8675310` selected the close
`20260815_165449.jpg` portrait as its generation source. Both FLUX.2 reference latents were therefore
face-dominant (the complete close portrait plus its 2.4x face crop). The output passed identity at `0.7756`, but
visual review found an oversized head over a narrow neck, shoulders, and torso. The local diagnostic measured a
face/person width ratio of `0.3718`.

## Rejected corrections

- Extra anatomy and camera-distance wording left the ratio at `0.3718`.
- A forced 2x phone-camera description regressed the ratio to `0.3871`.
- Reducing only the face-crop expansion to 2.0x and 1.6x reached `0.3672` and `0.3647`; neither was a sufficient
  visual correction.
- Selecting the genuine body-context source and passing its complete frame fixed anatomy, but copied a
  three-quarter/full-body composition and failed the requested waist-up framing.
- Cropping the same body source from head through hips measured `0.3249`, but visual review correctly rejected it:
  the crop still contained the tilted head and reproduced a forward-projecting neck/head posture.
- Adding the upright genuine surf photo as a fourth reference corrected posture, but using that one source for both
  torso and face returned the width ratio to `0.3710` and copied its wet hair/older smile.

These trials were not retained.

## Accepted mechanism

For v1.0.4 solo waist-up requests only, torso and face sources are now selected independently. The torso source
rewards genuine body context; its deterministic shoulders-to-hips crop deliberately excludes the head. The face
source uses the highest local face-quality score and supplies the existing 2.4x identity crop. The prompt assigns
Picture 1 only to shoulder width, build, and torso alignment, and Picture 2 only to current face, hair, and age. It
also requires the generated head to remain centered over the neck and shoulder line on the torso depth plane.

All supplied genuine photos still form the identity centroid used for output scoring. Multi-person, head-and-
shoulders, and full-body routes remain unchanged. There is no face swap, mask, restoration, upscaler, hosted
service, or extra model pass.

## Controlled RTX 4070 result

The accepted comparison used the same three genuine references, scene, model, LoRA strength `0.6`, 20 Euler
steps, guidance `4.0`, output size `896x1344`, and seed `8675310` as the failure.

| Result | Primary source | Conditioning | Face/person width | Workflow identity |
|---|---|---|---:|---:|
| Original failure | close portrait | full + face 2.4x | `0.3718` | `0.7756` |
| Corrected | torso photo + independent close portrait | head-excluded torso + face 2.4x | `0.3340` | `0.7916` |

The corrected ratio is 10.2% lower than the original and falls inside the accepted natural comparison range. The
workflow identity score is also higher than the original and remains well above its calibrated `0.70` Action floor.
Full-size visual review confirms that the head is centered over a vertical neck and shoulder line instead of leaning
forward. The independent three-photo evaluator scored `0.7927` and classified the result as `strong_match`;
automated similarity remains a diagnostic rather than proof of identity.

## Artifacts

- Original: `C:/projects/AI-Tools/ComfyUI/output/gpu-4070/flux2-reference-studio-v104/3-references/20260824-075426-531768/photo_00001_.png`
- Corrected: `C:/projects/AI-Tools/ComfyUI/output/gpu-4070/flux2-reference-studio-v104/3-references/20260824-083940-398344/photo_00001_.png`
- Corrected report: `C:/projects/AI-Tools/ComfyUI/output/gpu-4070/flux2-reference-studio-v104/3-references/20260824-083940-398344/report.json`
- Local diagnostic: `scripts/evaluate-head-body-proportion.py`
