# Mitch Comfy Workbench

This repository is the source of truth for Mitch's ComfyUI workflows and locally maintained custom nodes.

## How ComfyUI sees these files

The repository is connected to ComfyUI with Windows directory junctions:

- `workflows` → `C:\projects\AI-Tools\ComfyUI\user\default\workflows\Mitch`
- `assets\comfy-input` is synchronized into `C:\projects\AI-Tools\ComfyUI\input` with `mitch-workbench-` filenames by `scripts\setup-links.ps1`
- `custom_nodes\ComfyUI-AIToolkit-Training` → the corresponding ComfyUI custom-node folder
- `custom_nodes\ComfyUI-AlwaysRunImage` → the corresponding ComfyUI custom-node folder

Workflow and custom-node files are used in place. Version-controlled scene templates are synchronized into ComfyUI's input folder because its image picker does not follow directory junctions.

## FLUX.2 One Reference Photo — primary workflow

Open `Mitch/production/FLUX.2 One Reference Photo` in ComfyUI. The workflow has two visible nodes:

1. Upload one genuine face photo and describe the new photo in plain language.
2. Queue once and use the previewed result.

Internally, the node uses the official FLUX.2 Klein Base 4B FP8 model plus the locally trained `m1tch_person` identity LoRA selected from six checkpoints. It derives a full-photo reference and an automatic 2x face crop at one megapixel each, so the user never has to crop or wire reference nodes. The validated production setting is checkpoint 1,250 at strength `0.6`, 20 Euler steps, and guidance `4.0`. A local InsightFace check scores the result against the uploaded face. A second attempt runs only if the first result falls below `0.75`; the higher-scoring result is returned. Photos stay local.

Phone, professional, camera-facing, candid, and action looks are requested directly in the scene prompt. The workflow deliberately does not expose model, sampler, crop, refiner, or scoring controls.

The old five-node Social Photo Studio is preserved under `checkpoints/legacy-workflows/production` and is no longer the production recommendation.

Mitch visually accepted this exact v1 baseline on 2026-08-22. It is frozen under the annotated Git tag
`flux2-one-reference-v1.0.0`; `config/frozen-baselines.json` records exact workflow and identity-core hashes,
and `scripts/verify.ps1` fails if either changes. New presets and multi-reference work belong in separate
workflow/node files so the winning one-reference route remains available for direct comparison and rollback.

## Easy Social Photos — candidate

`Mitch/experiments/FLUX.2 Easy Social Photos - 1-4 References` is a separate bookmarked candidate. It accepts
one clear primary face photo, up to three optional genuine photos of the same person, a scene prompt, and
three small preset menus for style, framing, and moment/gaze. With one photo it delegates directly to frozen
v1. With two to four photos it keeps the accepted full-photo + 2x-face-crop generation path, rejects likely
mixed identities, and uses all detectable uploaded faces to rank/retry the result against a multi-photo
centroid.

Native 2–4-latent experiments were deliberately rejected: they scored only `0.7285–0.7344` and took
`124.6–164.1` seconds. The final candidate stayed near v1 speed (`46.5–49.2` seconds) and scored `0.8879`
professional, `0.8896` phone, `0.8233` on the validated action prompt, and `0.7908` on an explicit
three-quarter no-eye-contact candid. It remains under `experiments` until Mitch visually accepts it.

## Validated production result

On the local RTX 3090, the production 20-step LoRA path produced 768×1024 images in about 45–46 seconds. Against four held-out genuine photos excluded from training, it scored `0.8714` on the professional portrait, `0.8913` on the phone candid, and `0.8216` on the walking three-quarter-profile action prompt. All calibrated as strong matches. The 30-step quality reference scored `0.9205`, `0.9078`, and `0.8369`, but required about 66 seconds per image.

For comparison, the native four-step 9B KV path scored `0.8089` professional, `0.7505` phone, and only `0.4737` action/profile. Three native seed retries did not close the difficult-angle gap. The trained 4B LoRA therefore became production despite its higher latency. Alternate action seeds scored `0.8565` and `0.8755`, confirming that the identity improvement was not a single lucky seed. Automated scores rank and reject identity drift; they are not proof of identity or a substitute for the subject's final judgment.

Superseded Qwen, Z-Image, face-swap, and multi-node Social Photo graphs remain under `checkpoints` for regression history only. Generated identity fixtures are never accepted as training or evaluation truth.

## Everyday workflow

1. Open `Mitch/production/FLUX.2 One Reference Photo` in ComfyUI.
2. Upload one face photo, enter the scene prompt, and queue it.
3. Do not edit or overwrite this accepted graph. Build new behavior under `workflows/experiments` with a new node module.
4. Validate new work against the frozen graph before promoting it.
5. Run `scripts\checkpoint.ps1 -Message "Describe the working change"` to verify and commit it.

Production filenames stay stable. Git history replaces duplicate files named `v2`, `final`, or `final-final`.

## What is intentionally not tracked

- Models, LoRAs, and Python environments
- Generated datasets and outputs
- Personal input/reference photographs
- Scene templates outside `assets\comfy-input`
- Logs, caches, and compiled Python files
- Machine-local settings such as the live AI-Toolkit `settings.json`

Tracked manifests record important external revisions and hashes without copying large files into Git.

See [docs/HOW-TO.md](docs/HOW-TO.md) for restoration and maintenance details.
