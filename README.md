# Mitch Comfy Workbench

This repository is the source of truth for Mitch's ComfyUI workflows and locally maintained custom nodes.

## How ComfyUI sees these files

The repository is connected to ComfyUI with Windows directory junctions:

- `workflows` → `C:\projects\AI-Tools\ComfyUI\user\default\workflows\Mitch`
- `assets\comfy-input` is synchronized into `C:\projects\AI-Tools\ComfyUI\input` with `mitch-workbench-` filenames by `scripts\setup-links.ps1`
- `custom_nodes\ComfyUI-AIToolkit-Training` → the corresponding ComfyUI custom-node folder
- `custom_nodes\ComfyUI-AlwaysRunImage` → the corresponding ComfyUI custom-node folder

Workflow and custom-node files are used in place. Version-controlled scene templates are synchronized into ComfyUI's input folder because its image picker does not follow directory junctions.

## FLUX.2 Easy Social Photos — primary workflow

Open `Mitch/production/FLUX.2 Easy Social Photos v1.0.4 - Auto Scene Routing` in ComfyUI. Upload one to four genuine
photos in any order, describe the new scene, choose clean phone / slight phone-lens haze / professional,
framing, and gaze/action, then queue.
The graph stays at two visible nodes. All face detection, input-quality/angle selection, identity conditioning,
scene routing, retry ranking, and saving happen locally.

The node automatically chooses the clearest, most frontal usable face for FLUX.2, rejects likely mixed
identities, and uses every detected supplied face to rank the result. It intentionally sends only the selected
photo's full view and derived face crop into the identity model: direct 2–4-identity-latent tests were both slower
and less accurate. Every reference count uses the same `896×1344` output and hidden stronger identity profiles
for one-photo, candid, action, and full-body requests. There is no face swap or refiner.

v1.0.4 automatically infers car, traffic, crowd, group, reflection, action, held-object, and signage contexts and
adds compact preventive scene rules. Ordinary solo scenes use the fast Base 4B + identity LoRA route. Prompts with
secondary people, groups, or reflections use Z-Image Base for a deep-focus scene first. A local YOLO detector
checks explicit people/vehicle counts and can retry layout seeds; a face-aware crop and local human segmentation
then isolate the main subject. FLUX.2 Base 4B plus the identity LoRA regenerates only that masked subject while
leaving the accepted people, vehicles, furniture, architecture, and depth structure untouched. The graph still
requires no extra user control and never uses a face-swap overlay.

Every v1.0.4 route treats the environment as real photographic content rather than backdrop filler. It asks for
recognizable foreground, midground, and major distance structure with material texture, ordinary wear, and small
irregular detail under realistic moderate-to-deep focus. Distance can soften naturally, but portrait-mode cutout
blur, fake bokeh, smeared scenery, and featureless color washes are rejected unless shallow focus is explicitly
requested. Phone-lens haze changes contrast and light scatter only; it never replaces scene detail.

The realism fix remains primary-generation conditioning plus enough face pixels: unretouched spatially varied skin,
coherent face/neck/body lighting, and no separate facial sharpening. Typical successful passes take about
35–38 seconds on the RTX 3090 for the fast route; a second deterministic seed runs only when the local identity
gate rejects the first. The fixed complex café regression took `105.0` seconds after a clean service restart;
subsequent exact-prompt runs can reuse its process-local layout cache. Final production validation scored `0.7996` against three other genuine photos for a one-reference phone
result, `0.8827` against the supplied centroid for professional, `0.7985` for a clear off-camera candid, and
`0.7230` for a head-to-feet action result whose face was only 103 pixels wide. Local texture measurements for
the close/waist-up results fell inside the genuine-photo comparison range. Scores rank identity and flag
texture extremes; the subject's visual judgment remains authoritative.

Human review rejected the original `0.7946` café candidate because the masked identity pass removed part of the
crown even though InsightFace and object counts passed. The complex route now unions a full-head safety ellipse
with the segmented subject before generation and runs a separate U2Net head-integrity check on every final seed.
The broken candidate is rejected at `0.1301` crown clearance; all four genuine calibration photos pass. The live
fixed café regression completed in `105.0` seconds, scored `0.8678`, preserved exactly three people and two
vehicles, expanded the mask from raw `y=502` to `y=393`, and passed at `0.2208` crown clearance with `0.7848`
head-core coverage. This is a narrow missing-head gate, not a claim that automation certifies general realism.

The global background-detail regression passed on both routes. A solo professional bookstore scene correctly
stayed on the direct route, completed in `37.6` seconds at `0.7656` identity, and showed gradual physical focus
falloff instead of uniformly sharp scenery or fake bokeh. The constrained café test retained readable masonry,
pavement, furniture, two distinct bystanders, and two coherent parked cars while the identity pass changed only
the protected foreground subject region.

Every smartphone result receives a restrained, deterministic zero-model-pass finish that slightly reduces the
synthetic saturation/local crispness and unifies subject and scene with mild sensor noise and quality-95 phone
compression while retaining structural detail. Use `Smartphone — slight lens haze` when the photo should also
have the washed film seen through an everyday handled phone lens near a window or sun. v1.0.4 generates the same clean smartphone base, then applies a
deterministic highlight-driven optical scatter in under a second. It lifts blacks and compresses contrast more
near bright sources without blurring the face, changing composition, or running another AI model. The final
car-window test scored `0.8921` identity in `35.4` seconds; its mean luminance moved from `0.33944` to `0.38369`
and contrast from `0.25728` to `0.24452` before the shared phone finish.

## FLUX.2 One Reference Photo — frozen rollback baseline

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

## Validated production result

On the local RTX 3090, the production 20-step LoRA path produced 768×1024 images in about 45–46 seconds. Against four held-out genuine photos excluded from training, it scored `0.8714` on the professional portrait, `0.8913` on the phone candid, and `0.8216` on the walking three-quarter-profile action prompt. All calibrated as strong matches. The 30-step quality reference scored `0.9205`, `0.9078`, and `0.8369`, but required about 66 seconds per image.

For comparison, the native four-step 9B KV path scored `0.8089` professional, `0.7505` phone, and only `0.4737` action/profile. Three native seed retries did not close the difficult-angle gap. The trained 4B LoRA therefore became production despite its higher latency. Alternate action seeds scored `0.8565` and `0.8755`, confirming that the identity improvement was not a single lucky seed. Automated scores rank and reject identity drift; they are not proof of identity or a substitute for the subject's final judgment.

Superseded Qwen, Z-Image, face-swap, and multi-node Social Photo graphs remain under `checkpoints` for regression history only. Generated identity fixtures are never accepted as training or evaluation truth.

## Everyday workflow

1. Open `Mitch/production/FLUX.2 Easy Social Photos v1.0.4 - Auto Scene Routing` in ComfyUI.
2. Upload one to four real photos in any order, enter the scene prompt, choose the three presets, and queue it.
3. Use Easy Social Photos v1.0.3 or `FLUX.2 One Reference Photo` for rollback/direct comparison. The accepted
   v1.0.3 core remains hash-frozen and unchanged while v1.0.4 is visually evaluated.
4. Build new behavior under `workflows/experiments` and validate it before promotion.
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
See [docs/scene-routing-v1.0.4-evaluation.md](docs/scene-routing-v1.0.4-evaluation.md) for the accepted/rejected scene tests.
