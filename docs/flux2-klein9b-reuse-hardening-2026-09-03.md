# FLUX.2 Klein 9B reuse and hardening — 2026-09-03

## Decision

Keep Identity Studio, Group Scene Studio, and Upgrade Photo Detail & Realism as three separate user-facing workflows. Share only infrastructure whose meaning is identical across all callers.

This is not duplication for its own sake. The workflows have different conditioning contracts, reference order, image preparation, output geometry, sampling defaults, and post-sampling behavior. Combining those contracts behind one general-purpose node would make a plausible-looking wiring error easier and provenance harder to audit.

The freshly validated generation recipes remain unchanged by this hardening pass. The known-good pre-hardening state is commit `b32ecb9deab3a9d139bbfafc69c5eeb240ac3d4f`, tagged `milestone-klein9b-production-revalidated-2026-09-03`.

## Actual conditioning contracts

| Workflow | Ordered image conditioning | Identity basis | Sampling/output contract |
| --- | --- | --- | --- |
| Identity Studio v1.1 | One or two genuine photographs selected by a named profile; each is resized, VAE-encoded, and appended as a `ReferenceLatent` in profile order | Protected step-1600 Mitch LoRA plus genuine Mitch reference photographs | Fixed `832 × 1216`; validated default is Turbo at 8 Euler steps / CFG 1 |
| Group Scene Studio v1.1 | Picture 1 is a Canny layout guide made from the group source with the target face interior cleared; Picture 2 is a separate genuine Mitch photograph | Protected step-1600 Mitch LoRA plus the separate genuine identity photograph; the group source is structural composition conditioning | Fixed `832 × 1216`; validated default is 50 Euler steps / CFG 4 |
| Upgrade Photo Detail & Realism v1 | Picture 1 is the full source photograph, Picture 2 its face-interior-free Canny guide, Picture 3 a genuine Mitch photograph, and Picture 4 a genuine isolated hair-material crop | Protected step-1600 Mitch LoRA plus Picture 3. Picture 1 contains the source face and is also encoded as a `ReferenceLatent`, so its identity contribution is unisolated and cannot be claimed absent | Native source aspect/size; 50 Euler steps / CFG 4; deterministic appearance work occurs after decode |

ComfyUI's `ReferenceLatent` implementation appends encoded latents to an ordered conditioning list; it does not attach a typed identity, style, pose, or composition role. Those roles therefore have to be established by the trained recipe, source preparation, reference order, prompt, and local evidence—not inferred from the node name. See the [ComfyUI implementation](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_edit_model.py) and the [official FLUX.2 Klein 9B edit template](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_flux2_klein_image_edit_9b_base.json).

## Reuse implemented safely

- One canonical visual-preset manifest remains the authority for Identity and Group card labels, prompts, reference profiles, source assets, hashes, and target geometry.
- Manifest loading now rejects invalid schema, engine-incompatible reference profiles, duplicate labels/keys/thumbnails, surrounding-whitespace ambiguity, unsafe paths, malformed hashes, wrong types, non-finite/out-of-range geometry, and a Custom Group card that tries to lock a source. Decorative files are checked by maintenance verification, while the selected prepared source is checked immediately before queuing; a missing thumbnail cannot disable unrelated custom nodes at import time.
- Group validation and execution now resolve the same effective manifest geometry and verify a prepared source before queuing.
- The shared asset verifier rehashes every prepared source before use. The files are small relative to generation time, and avoiding a process-wide size/mtime cache closes a same-size, restored-timestamp integrity gap.
- The browser gallery fetches the manifest without stale caching, retries once after a transient request failure, verifies its byte hash and labels/profiles against the live Python node, confines thumbnail URLs to the visual asset root, and preserves the user's explicit reference profile when Custom Identity is selected.
- Thumbnail maintenance now has a read-only `--check` mode, requires exact manifest coverage, and permits placeholders only for the two Custom cards.
- The candidate runner checks the RTX 3090 worker, the 4070 worker, the second service sharing the 3090, Forge state, conservative 3090 utilization/memory thresholds, and exact local/live/report manifest hashes. It records those snapshots and rechecks all 3090 signals immediately before each submission while allowing unrelated 4070 work to continue. `-PreflightOnly` exercises the complete read-only gate without creating a run directory or queuing an image.
- The Identity and Group specialized verifiers now cover both frozen v1 engines and shipped v1.1 wrappers, exact saved defaults, live input choices, provenance fields, the manifest and prepared-source hashes, and the Base 9B / Qwen 3 8B / FLUX.2 VAE hashes.
- Upgrade report schema v2 now distinguishes intended reference roles from proven influence, rather than asserting that the full source cannot contribute identity. It also distinguishes the old approval milestone from the freshly revalidated phone-on default, reports the phone-off route as not freshly exercised in that run, and scopes optional post-decode changes accurately.

The shorter Group v1.1 approved-lounge prompt is intentionally retained. It differs from the frozen manual v1 prompt, but the exact manifest prompt passed the fresh default-path run and is now hash-locked by the Group verifier. Changing it merely for textual parity would discard tested evidence.

## Verification after hardening

- The RTX 3090 worker was reloaded only after ports `8188`, `8189`, and `8190`, Forge, and both hardware rows were confirmed idle. The 4070 worker, port `8190`, and Forge were left running and untouched.
- The Identity, Group, and Upgrade specialized read-only verifiers passed against the reloaded port `8188` worker. They confirmed the live v1/v1.1 contracts, exact manifest hash metadata, prepared-source provenance, and Base 9B / Qwen 3 8B / FLUX.2 VAE hashes.
- The repository-wide verifier passed `131` tests, all 20 thumbnail-source checks, frozen-baseline hashes, synchronized assets, live links, and required-node checks.
- Focused manifest, hash-integrity, preset, and Upgrade reporting tests passed; Python compilation, JavaScript syntax, PowerShell parsing, and `git diff --check` passed.
- The candidate runner's `-PreflightOnly` mode passed against all three live Comfy endpoints, Forge, hardware state, and manifest parity without creating a directory or queuing work.

No post-hardening image was generated. The hardening changes are validation, metadata, reporting, browser, and maintenance-tool changes; they do not change model/LoRA selection, prompts, ordered references, resize methods, sampler settings, decoded image processing, or saved workflow defaults. The fresh images and metrics in the revalidation record therefore remain the output-quality evidence.

## Optimizations deliberately deferred

### Small decoder

`full_encoder_small_decoder.safetensors` is already installed locally and selectable on all three workers (SHA-256 `EA4273F02D1FAFBF8E1D1C2CF6018ED8748652EB0BF34F2DD91171F16F15AB62`). It is not an output-preserving substitution. All three workflows need the full encoder for image references and decode only once, so the plausible saving is limited to the final decode while diffusion sampling dominates total runtime. Upgrade also derives deterministic masks and appearance decisions from decoded pixels.

The [official FLUX.2 small-decoder card](https://huggingface.co/black-forest-labs/FLUX.2-small-decoder) supports evaluating it, but promotion requires a new-version, same-latent A/B with full-size review and identity/structure checks. It is not being inserted into the validated v1 recipes.

### Model, LoRA, and reference-latent caching

The engines currently call standard ComfyUI loaders, which already participate in ComfyUI's model management. A deeper shared cache for patched model objects is unsafe without a complete key for base model hash, dtype, ordered LoRA names/hashes/strengths, device, and runtime version; sharing an already patched object can leak one workflow's LoRA stack into another.

Reference-latent caching could help repeated runs, but it must also key the exact decoded pixels, resize method and target, VAE hash, dtype, and ordered slot. It can retain substantial VRAM and has little value for a one-off source in Upgrade. Both ideas belong in a separately named v2 experiment with byte/metric parity checks and memory telemetry.

### Universal sampler defaults

There is no safe universal step/CFG setting. The [official Base 9B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) documents the quality-oriented 50-step / guidance-4 route, while the [author-maintained rank-256 Turbo LoRA card](https://huggingface.co/kalle07/FLUX.2-klein-9B-turbo-lora-set) targets a much shorter 4–8-step / CFG-1 route. Local evidence accepts Turbo for Identity, rejects it as the Group default, and rejects it for Upgrade. Those choices remain separate.

## Promotion rule

Future performance work must be introduced beside these versions, not silently inside them. A candidate is promotable only after:

1. identical conditioning role/order and hash-locked assets are demonstrated;
2. a same-seed approximately 1 MP comparison is run on an available GPU;
3. at least two genuine photographs are used for identity diagnostics;
4. full-size and thumbnail visual review passes; and
5. runtime and peak VRAM improve enough to justify a new output surface.

The upstream implementation references used for this decision are the [BFL FLUX.2 repository](https://github.com/black-forest-labs/flux2), [Base 9B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B), [ComfyUI FLUX nodes](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_flux.py), [ComfyUI edit-model nodes](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_edit_model.py), and the [official ComfyUI workflow template](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_flux2_klein_image_edit_9b_base.json).
