# FLUX.2 identity LoRA v2 evaluation

Status: **rejected; never promoted to an active workflow**.

The v2 training set was built only from real, user-owned media in `C:\projects\AI-Tools\Mitch photos`.
It contains 16 training images and six held-out validation images. No generated face, retouched output,
or validation image was used for training. The dataset fingerprint is
`ce1909a6b9324bc37c0d47262c95ff7f31a5e4b2f4ddcad50de3f3a13eeff6ef`.

AI Toolkit trained FLUX.2 Klein Base 4B through 1,600 steps with checkpoints every 200 steps. Checkpoints
were staged only under ComfyUI's isolated `aitk\candidate-v2` LoRA folder. The active workflow, production
LoRA aliases, and frozen v1 baseline were not changed.

## Acceptance test

`scripts\benchmark-flux2-lora-only.ps1` generates novel fixed-seed scenes from only the base model, LoRA,
and text prompt. It deliberately has no uploaded face, reference conditioning, face swap, InstantID,
PuLID, or other identity shortcut. The Full profile requires phone, professional, side-profile, and
full-body-action scenes to each score at least `0.70` without an `identity_drift` classification. Passing
that automated identity gate would still require a manual realism review before publication.

Four clean held-out validation faces calibrate the local InsightFace comparison. Their genuine pairwise
similarity ranges from `0.7723` to `0.8652`, with a mean of `0.8031`. The metric is a local ranking and
drift-rejection aid, not proof of identity or photo quality.

## Results

The best balanced 600-step candidate at strength `1.2` failed the Full profile:

| Scene | Centroid similarity | Result |
| --- | ---: | --- |
| Professional | 0.7314 | Near match |
| Phone portrait | 0.6711 | Identity drift |
| Side profile | 0.5895 | Identity drift |
| Full-body action | 0.5792 | Identity drift |

The final 1,600-step candidate at strength `1.2` also failed:

| Scene | Centroid similarity | Result |
| --- | ---: | --- |
| Professional | 0.7380 | Near match |
| Phone portrait | 0.6838 | Identity drift |
| Side profile | 0.6509 | Identity drift |
| Full-body action | 0.5689 | Identity drift |

The final candidate additionally showed subject leakage into background people, overly smooth facial
texture, and visible nose/neck distortion in profile. It is not approved for use.

## Root cause and next valid path

The available real media has enough close front and three-quarter views for portrait resemblance, but too
many images come from repeated selfie sessions. It lacks clean true left/right profiles and current,
non-mirror full-body photos across varied environments. Adding more frames from the same two videos would
increase session/background memorization instead of teaching the missing geometry.

Do not rerun this 4B configuration on the same source set. The next defensible training attempt requires
either (a) new real photos covering both true profiles, three-quarter views, and full-body framing across
several backgrounds, or (b) access to the gated FLUX.2 Klein Base 9B training model and a fresh controlled
experiment. The installed FLUX.2 Klein 9B KV inference checkpoint is not a substitute for the Base 9B
fine-tuning model.
