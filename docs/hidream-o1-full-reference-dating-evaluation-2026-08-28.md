# HiDream-O1 Full native-reference dating-photo evaluation

> **Historical record — not current instructions.** This experiment was rejected and its runnable files are archived. See `docs/STATUS.md`.

Status: completed experiment. The official Full workflow and its one controlled
refinement are **not approved for dating-profile use**.

## Why this experiment exists

The Dev checkpoint proved that native two-reference subject personalization can
preserve Mitch's identity, but its coherent 1728x2304 result failed the requested
dating-photo quality bar: the face dominated the frame and skin/hair looked
painted and smooth. This Full-model arm tests the highest-confidence native
quality path without hiding those failures behind a face swap or refiner.

## Official Full recipe

- Source workflow: Comfy-Org `image_hidream_o1.json`.
- Checkpoint: `hidream_o1_image_fp8_scaled.safetensors`.
- 40 steps, CFG 5.0, model noise scale 8.0, `normal` scheduler, denoise 1.0.
- `dpmpp_2m_sde_gpu` sampler.
- Official late `HiDreamO1PatchSeamSmoothing`: 0.8 to 1.0,
  `single_shift`, `ramp_2_4`, `median`, strength 1.0.
- Empty negative prompt and no optional prompt-enhancement model.
- 1728x2304, an explicitly documented trained portrait resolution.

The HiDream authors' repository describes the undistilled Full model as the
quality-oriented 50-step path. The current official ComfyUI template uses the
40-step recipe above, which is used unchanged because this is a ComfyUI-local
compatibility test.

## Frozen comparison controls

- Same two genuine photographs, in the same order.
- Same 0.81/0.82 MP source files; neither exceeds the official 4 MP reference
  scaling threshold, so no resizing node is needed.
- Same prompt, seed 8675601, and 1728x2304 output canvas as the coherent Dev run.
- The change is the documented Full checkpoint and its required official sampling
  recipe. No character LoRA, face embedding, face swap, mask, restoration,
  relighting, upscaler, SDXL/Z-Image refinement, or output composite is present.

## Primary sources

- https://github.com/HiDream-ai/HiDream-O1-Image
- https://github.com/HiDream-ai/HiDream-O1-Image/blob/main/README.md
- https://docs.comfy.org/tutorials/image/hidream/hidream-o1
- https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_hidream_o1.json
- https://huggingface.co/Comfy-Org/HiDream-O1-Image/blob/main/checkpoints/hidream_o1_image_fp8_scaled.safetensors

## Acceptance checks

1. Live 4070-only preflight verifies model hash, nodes, both genuine inputs, and
   all queues; no queue is submitted to either 3090 worker.
2. Full-size and 104/208-pixel thumbnail review covers identity, crop, apparent
   age, hair, skin, clothing/body, background people, depth, and halos.
3. Local InsightFace comparison ranks Full and Dev against five held-out genuine
   photos. It remains a diagnostic, not proof of identity.
4. The same normalized face-texture diagnostic and contact-sheet scale are used
   for both candidates.
5. At most one controlled Full refinement is allowed after inspecting its actual
   failure. Further prompt or post-processing stages are not added after that
   evidence is decisive.

## Results

### Verified model and live preflight

- Checkpoint bytes: 8,067,535,296.
- Checkpoint SHA-256:
  `05AD98BC4A94557697F31B839F6DBF6DBA293A353D9E3C52EEF7818B5802D206`,
  exactly matching the official Comfy-Org file record.
- The live preflight passed on the RTX 4070 worker at port 8189. It verified the
  model hash, all core nodes, both genuine references, and all three queues.
  Neither RTX 3090 worker received a prompt.

### Frozen official Full comparison

- Prompt ID: `efa8b5b3-70fd-48dd-9655-1d958a36cc0e`.
- Runtime: 369.939 seconds on the RTX 4070.
- Output SHA-256:
  `6C2C5C58D909D98513E609B97489B5495B913B9DBC84441D696BC7AEAE74423D`.
- Composition improved substantially over Dev: the output is a coherent waist-up
  restaurant-patio portrait rather than a tight selfie. Clothing, body, scene
  integration, practical lights, and depth are believable, with no cutout halo.
- The requested natural phone-camera rendering still failed. Skin and hair are
  smooth and painted, facial structure is simplified, the color is strongly
  green/cinematic, depth is more blurred than requested, and several background
  diners have smeared facial detail.
- Identity ranked below Dev against five held-out genuine photos: centroid 0.6855,
  mean 0.5890, minimum 0.5229, versus Dev's 0.7447/0.6398/0.5305. The calibrated
  diagnostic still says `strong_match`, but visual review and the weaker rank make
  it an approximate likeness, not an identity lock.
- Normalized micro-luma variation was 3.306 and Laplacian variance 67.328, both
  lower than Dev's already-smooth 3.402 and 97.5. The genuine inputs measured
  6.041/624.7 and 4.132/280.4. The contact sheet confirms the metric flag.

### One controlled refinement: disable experimental seam smoothing

- Prompt ID: `8d76bd50-8fce-4e84-96d9-2f5ccd24d49e`.
- Only change: `HiDreamO1PatchSeamSmoothing` was bypassed. Checkpoint, references,
  order, prompt, seed, size, steps, CFG, noise scale, scheduler, and sampler stayed
  frozen.
- Runtime: 269.405 seconds.
- Output SHA-256:
  `C6E07169CB2C0D7A8DAC8F0B9BAC150210B0BB8E86A57C4895C54BAD7ACA3F38`.
- Full-size review immediately rejected it: large square patch-grid artifacts are
  visible across the forehead, face, shirt, sky, and background. The slight rise
  in micro variation to 3.938 is artificial block structure, not natural skin.
- Identity dropped again: centroid 0.6067, mean 0.5213, minimum 0.4401. It ranked
  last of the three candidates and sits well below the genuine-photo minimum on
  at least one held-out view.

## Verdict

The native mechanism works, but **neither local HiDream-O1 variant meets the
combined dating-photo requirement**:

- Dev: best identity (0.7447), fastest coherent run (88.656 s), but an oversized
  selfie crop and conspicuously smooth skin/hair.
- Full official: much better composition, but weaker identity, even smoother
  facial texture, and a 369.939 s runtime.
- Full without seam smoothing: faster than official Full but unusable patch-grid
  artifacts and the weakest identity.

No prompt-only rerun is justified because Full already fixed composition while
the remaining failure is model rendering, and the prompt already explicitly asks
for unretouched skin and forbids smoothing. No face swap, restoration, mask,
upscale, SDXL/Z-Image pass, or other refiner was added. All outputs and exact
runners remain preserved so these approaches are not unknowingly repeated.
