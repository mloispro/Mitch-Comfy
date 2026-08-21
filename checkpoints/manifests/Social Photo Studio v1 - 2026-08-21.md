# Social Photo Studio v1 validation

## Supported path

- Workflow: `workflows/production/Social Photo Studio - FLUX Klein.json`
- Five visible nodes; three user steps: add 1–4 references, choose prompt/presets, queue once.
- Modes: one photo, six-photo dating pack, nine-photo Instagram pack.
- Camera looks: authentic phone, professional, 35mm lifestyle.
- Relationship controls: camera-facing, candid/action, automatic mix.
- Outputs: finals, contact sheet, and privacy-safe JSON report under `ComfyUI/output/social-photo-studio/<run-id>`.

## Locked external models

- FLUX.2 Klein 4B FP8: `97ed34fe0567e436200f2faee3939b88f2b5d99f8af2a4dc16532c4245c0ccb6`
- FLUX.2 VAE: `d64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5`
- Qwen 3 4B mixed FP8 encoder: `72450b19758172c5a7273cf7de729d1c17e7f434a104a00167624cba94f68f15`
- Optional Mitch-specific Klein LoRA: `54841471807f55799c255a244333673fe85542c7050a0b551bedff9e86d868f2`

## Live validation on RTX 3090 24 GB

- One-reference professional candid/action photo: 8.1 seconds, photorealistic biking scene.
- Four-reference phone portrait: front/left/right roles inferred; face-less full-body reference recorded as unverified soft context.
- Six-photo reference-only dating pack: 111.7 seconds total (18.6 seconds/photo); five initial finishes accepted, then the crowded-scene crop check was corrected and the rejected night scene passed its focused retest.
- Nine-photo 4:5 Instagram pack with optional identity LoRA: 121.9 seconds total (13.5 seconds/photo), all nine finishes accepted, no OOM fallback. Mean InsightFace cosine was 0.381 before the guarded finish and 0.713 after it.
- Native-only and LoRA-only paths were also executed successfully.

The historical Qwen v8 score of 80.81 is preserved separately. It is not directly comparable with the cosine values above because the reporting scales differ.

## Safety and truthfulness invariants

- Mixed-person face references below the configured similarity threshold are rejected.
- Automatic finishing edits only the isolated subject crop and is accepted only after identity improvement plus pose/position/scale checks.
- Force mode can bypass the improvement threshold but not geometry or target-detection safety.
- A body image without a verified face is never reported as grounded identity.
- Reports retain reference hashes and inferred roles, not private source paths or images.
