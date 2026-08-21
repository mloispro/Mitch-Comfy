# ComfyUI AI-Toolkit Training

## Social Photo Studio

`Social Photo Studio - FLUX.2 Klein 9B KV.json` is the supported everyday dating-app and Instagram generator. Its three functional nodes accept one to four same-person references, a plain-language brief plus a few presets, and produce a single photo or a six-/nine-photo pack in one queue.

The custom node validates same-person inputs, sends every usable face angle through native FLUX.2 `ReferenceLatent` conditioning, applies full-body evidence only to proportion-sensitive scenes, and samples the official Klein 9B KV FP8 model in four Euler steps. The production path has no face swap, restorer, subject LoRA, or synthetic identity fixture. It records an InsightFace diagnostic but requires human likeness review against genuine originals. See [the maintenance guide](../../docs/HOW-TO.md) for normal use and the validated baseline.

## Qwen identity-locked social workflow

`Generate 9 Social Photos - Z-Image LoRA + Qwen Identity Lock.json` keeps the existing editable Z-Image draft/final workbench and adds a separate final-only Qwen Image Edit 2511 identity pass. Stage 3 indexes the 15 successful Qwen angle portraits in `ComfyUI/output/lora-dataset`, scores them against the three genuine photos, and automatically selects exactly one pose-matched portrait for each final. Candidate A edits the complete scene; Candidate B edits an expanded full-head crop. Both are aligned and feathered into the untouched Z-Image final, and Auto mode retains the original unless a candidate safely improves genuine-photo similarity.

Normal use:

1. Queue Stage 1 with Stage 2 off and review the drafts.
2. Edit any scene card, seed, global setting, or per-scene enable switch.
3. Turn Stage 2 on. Stage 3 is enabled by default and runs only after real finals exist.
4. Review the original head, selected pose reference, raw candidate heads, aligned full-image candidates, mask, locked final, and before/after contact sheet.

Stage 3 exposes scope, `Auto / Original / Candidate A / Candidate B`, reference-angle override, prompt instruction, full-head crop expansion, feathering, Qwen resolution/steps, separate candidate seeds, minimum identity improvement, and one target-position override for each scene. Manual Candidate A/B selection still enforces hard face-count, seam, and mask safety checks. Originals and candidates are saved separately and never overwritten. The identity-bank analysis is cached in `lora-dataset/.identity-lock-index.json` and rebuilt automatically when a portrait changes.

This custom node package submits Z-Image LoRA training to AI-Toolkit's existing durable job queue. A ComfyUI workflow never waits for training to finish.

## One-click generated-dataset workflow

Use **AI-Toolkit: Train Generated Dataset** for the fixed dataset at
`C:\projects\AI-Tools\ComfyUI\output\lora-dataset`. It has no inputs. The first run validates and submits a
3,000-step Z-Image Base job. A live panel polls the durable job every five seconds without running the workflow again.
It shows model-download activity while preparing, then step percentage, speed, ETA, and AI-Toolkit's current message.
When training completes, the same monitor idempotently publishes the final LoRA into ComfyUI.
The dataset fingerprint prevents duplicate jobs. The node never searches or uses `multiref-v2`.
Refresh the ComfyUI browser page after installing or updating the custom node so its live panel is loaded.

## Local configuration

`settings.json` is configured for this machine:

- AI-Toolkit: `C:\projects\AI-Tools\ai-toolkit\AI-Toolkit`
- AI-Toolkit Python: `C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe`
- AI-Toolkit UI/API: `http://127.0.0.1:8675`
- Base model: `Tongyi-MAI/Z-Image` (`arch: zimage`)
- Published LoRAs: `C:\projects\AI-Tools\ComfyUI\models\loras\aitk`

If AI-Toolkit is configured with `AI_TOOLKIT_AUTH`, launch ComfyUI with the same environment variable. The token is not stored in this package.

## Use

1. Start `C:\projects\AI-Tools\ai-toolkit\Start-AI-Toolkit.bat`. The UI and queue worker must be available when submitting or checking jobs; training itself survives a UI restart.
2. Restart ComfyUI.
3. Add **AI-Toolkit: Submit Z-Image Training** from `training/AI-Toolkit`.
4. Point `dataset_path` at a flat folder where every supported image has a same-stem `.txt` caption. Submission rejects missing, empty, or orphan captions and does not edit them. AI-Toolkit injects `trigger_word` at load time if a caption does not already contain it.
5. Run the workflow once. Save the returned `job_id`.
6. Use **AI-Toolkit: Training Status** in a later ComfyUI run to read status, step, total steps, info, and the log tail.
7. After status is `completed`, use **AI-Toolkit: Publish Completed LoRA**. It atomically copies the final `.safetensors` to `models/loras/aitk` and returns its ComfyUI-relative LoRA name.

Job names are unique in AI-Toolkit, which prevents an accidental repeat execution from creating duplicate training jobs.

## Nine-photo social workbench

`Generate 9 Social Photos - Z-Image LoRA.json` is an editable two-stage workflow. It contains one
global-settings node, nine separate scene cards, a fast Draft renderer, a nine-image preview, and a
gated Final renderer.

1. Select the completed LoRA and adjust global style, negative prompt, LoRA strength, CFG, dimensions,
   or step counts if desired.
2. Edit any scene prompt, negative additions, seed, reference preset, ControlNet strength, or enable switch.
3. Leave `render_final` off and queue to make 576×832, 10-step drafts. Use `draft_scope` to render
   either all enabled scenes or one scene while refining it.
4. Review the drafts and iterate until identity, composition, clothing, and setting look right.
5. Turn `render_final` on, choose all scenes or one scene with `final_scope`, and queue again to create
   the 832×1216, 25-step final output. Unchanged draft
   nodes remain cached.

Drafts and finals are saved separately below `ComfyUI/output/zimg-social-pack`. The older one-click
generator remains available as an advanced convenience node. Neither generator modifies the dataset or
training workflows.
