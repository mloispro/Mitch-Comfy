# Krea2 Mitch character-LoRA state-fair evaluation — 2026-08-24

> **Historical record — not current instructions.** The character LoRA was later rejected and removed; the workflow and runner remain only in the archive. See `docs/STATUS.md`.

## LoRA verified

- File: `models/loras/aitk/mitch-krea2-identity-v1.safetensors`
- Architecture: Krea2
- Base mode: Turbo adapter
- Training set: 22 genuine Mitch photographs
- Trigger: `m1tch_person`
- Training: 500/500 steps, rank/alpha 16/16, resolution 1024
- SHA-256: `44753AFAADAB3A8CE97597CCECE21252F85BD700C33C788F2900E58A7C8FD094`
- Live visibility: verified on both ComfyUI workers

## Test 1: stack character LoRA into scene-first Identity Edit

The accepted Klein 9B state-fair plate, two-image Krea2 Identity Edit layout, identity reference,
prompt, seed, camera LoRA, face-attention mask, resolution, sampler, and phone finish were held fixed.
The only added mechanism was the Mitch Krea2 LoRA at strength `0.85`, with the required
`m1tch_person` trigger.

- Identity without character LoRA: `0.5606` (`identity_drift`)
- Identity with character LoRA `0.85`: `0.5834` (`identity_drift`)
- Visual result: slightly closer face, but the central person remained cleaner and more isolated
  than the crowd and still looked composited.

## Test 2: intended clean one-pass character-LoRA generation

To test the LoRA in its intended mode, the scene plate, Krea2 Identity Edit adapter, identity photo,
and all compositing mechanisms were removed. Krea2 Turbo generated the subject, crowd, fair,
lighting, body, hair, and edges together. The accepted smartphone LoRA `0.35` and uniform phone
finish were retained. Fixed settings were `896x1344`, eight Euler/simple steps, CFG `1`, and seed
`9472103`.

### Strength 0.85

- Runtime on RTX 3090: `20.135` seconds
- Identity centroid similarity: `0.2323`
- Status: `identity_drift`
- Visual result: coherent and naturally integrated state-fair photograph, but a different man.

### Strength 1.00

- Runtime on RTX 3090: `20.164` seconds
- Identity centroid similarity: `0.2632`
- Status: `identity_drift`
- Visual result: small identity increase, still plainly a different man.

## Verdict

Do not promote `mitch-krea2-identity-v1.safetensors` into production. It has a measurable effect but
does not provide usable Mitch identity at the documented strengths. In scene-first editing it does
not remove the pasted-subject impression; in clean one-pass generation it produces a coherent
photograph but fails identity by a large margin.

The experiment confirms the tradeoff:

- Klein 9B scene-first plate: strong crowd diversity and background detail.
- Krea2 scene edit: preserves the plate but fails identity and looks composited.
- Krea2 character-LoRA one-pass: integrates naturally but fails identity.

Further prompt expansion, negative conditioning, face-attention boost, or strength above the tested
documented range is not justified. The character LoRA was removed on 2026-09-01. The no-character Krea2
Identity Edit graph remains an archived fallback only; current identity-sensitive generation uses the
protected Klein 9B V3 workflow family.

## Artifacts

- Scene-edit plus character LoRA `0.85`: `output/scene-first-state-fair-krea2-mitch-lora-0p85-20260824.png`
- Clean one-pass `0.85`: `output/krea2-one-pass-state-fair-mitch-lora-0p85-20260824.png`
- Clean one-pass `1.00`: `output/krea2-one-pass-state-fair-mitch-lora-1p00-20260824.png`
- Scene-edit report: `work/identity-evals/scene-first-krea2-mitch-lora-0p85-20260824.json`
- One-pass `0.85` report: `work/identity-evals/krea2-one-pass-mitch-lora-0p85-20260824.json`
- One-pass `1.00` report: `work/identity-evals/krea2-one-pass-mitch-lora-1p00-20260824.json`
- Archived one-pass runner: `checkpoints/legacy-scripts/krea2-character-lora/smoke-krea2-character-lora.ps1`
