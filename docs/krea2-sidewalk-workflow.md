# Krea2 Mitch Busy-Sidewalk Workflow

## Locked approach

This is a one-pass Krea2 Turbo identity workflow. Krea2 creates Mitch, his hair, body, light,
clothes, sidewalk, and pedestrians together. It does not paste a face into a finished plate and it
does not relight, restore, sharpen, or upscale one person separately. That is the best direct answer
to the head-cutout and "Photoshopped in" failures seen in the earlier workflows.

The prepared graph remains archived at
`archive/krea2-workflows/Krea 2 Mitch - Busy Sidewalk (Unavailable Personal LoRA).json`. Its filename
records its original blocked state, but the character LoRA is now published. The Save Image node
stays bypassed until the controlled strength comparison is run, so the graph remains research
evidence and does not appear in the active ComfyUI workflow menu prematurely.

## Reused character LoRA

Do not retrain by default. Inline Studio run `36d539e7-e05d-48ed-a74e-ddb1db3ab684` is the completed
character run. Its historical `outputName` was the misleading `emmy-s500-v2`, but its training data,
captions, embedded metadata, and canonical published filename all identify it as Mitch. The evidence
that matters is:

- architecture: `krea2`
- base mode: `turbo_adapter`
- dataset: 22 Mitch reference photos
- caption trigger on all 22 items: `m1tch_person`
- rank/alpha: 16/16
- training resolution: 1024
- completed steps: 500/500, with a valid intermediate snapshot at step 250 and the final LoRA at 500
- final LoRA: 191,896,264 bytes, 696 tensors
- SHA-256: `44753AFAADAB3A8CE97597CCECE21252F85BD700C33C788F2900E58A7C8FD094`

Publish or re-verify it idempotently with:

```powershell
.\scripts\publish-krea2-character-lora.ps1
```

The guarded publisher refuses a non-Krea2 run, a non-Turbo-adapter run, the wrong trigger/dataset,
anything other than a completed 500/500 run, or an invalid safetensors file. Its stable ComfyUI
destination is `models/loras/aitk/mitch-krea2-identity-v1.safetensors`.

## First controlled test

1. Use `scripts/start-comfy-4070.ps1` for read-only setup validation on port 8189. For the actual
   controlled generation, prefer the RTX 3090 when it is idle; use the 4070 only when the 3090 has
   other work, because its 12 GB VRAM requires heavier model offloading.
2. Run `scripts/verify-krea2-sidewalk.ps1`. It performs read-only file, hash, workflow, API, and GPU
   checks and never submits a prompt.
3. Open the prepared workflow through the `Mitch` workflow junction on port 8189.
4. Enable only the Save Image node after the LoRA exists.
5. Generate one image each at LoRA strengths `0.70`, `0.85`, and `1.00`, holding prompt, resolution,
   seed, steps, CFG, sampler, and scheduler fixed. Pick the lowest strength that is unmistakably Mitch.
6. With that strength locked, generate a four-seed batch and select for both identity and natural
   scene integration. Do not repair a weak identity with face swap.

The production settings are 896 x 1344, 8 steps, CFG 1, Euler, simple scheduler, batch size 1. The
prompt uses ambient late-afternoon light; flash was deliberately removed because it is not necessary
for the requested result.

## Acceptance gates

A candidate passes only if all of these are true:

- Mitch is immediately identifiable at thumbnail size and full size.
- His current short light-brown hair is generated naturally rather than inherited from a host.
- He is clearly the subject without being isolated from the sidewalk.
- His exposure, sharpness, noise, depth, and edge quality match nearby pedestrians.
- Pedestrians vary in face, clothing, pose, direction, distance, and attention.
- There is no face boundary, halo, selective sharpness, portrait blur, or arranged-group look.

## Minimal fallback ladder

Use the next step only if the preceding controlled test identifies a specific failure:

1. **Identity weak, scene good:** compare LoRA strengths 0.70 / 0.85 / 1.00, then compare the final
   checkpoint with the step-250 snapshot. Do not change the prompt at the same time.
2. **Identity good, crowd weak:** change only the crowd/action sentence or seed. Keep the identity
   settings fixed.
3. **Composition weak:** use one Krea style/composition reference at low strength, never an identity
   reference plus the character LoRA in the same first test.
4. **Local correction needed:** use Krea Edit on the whole coherent image for one bounded instruction.
   Do not mask or regenerate the head alone.
5. **Resolution insufficient:** upscale the accepted whole frame uniformly at the end. Never sharpen
   Mitch separately.
6. **LoRA fails at every tested strength/checkpoint:** only then consider one retrain with corrected
   captions or dataset balance. Retraining is not the starting assumption.

No face swap, ReActor, full-head mask, face restoration, Qwen relighting, hard-flash pass, or selective
upscale belongs in the clean baseline.

## Primary references

- [Official ComfyUI Krea2 guide](https://docs.comfy.org/tutorials/image/krea/krea-2)
- [Official ComfyUI Krea2 Turbo workflow JSON](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_krea2_turbo_t2i.json)
- [Official ComfyUI-optimized Krea2 model repository](https://huggingface.co/Comfy-Org/Krea-2)
