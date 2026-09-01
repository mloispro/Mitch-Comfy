# Krea2 vs FLUX.2 lounge identity-edit evaluation — 2026-08-25

> **Historical record — not current instructions.** This comparison predates the current Klein 9B V3 workflows. See `docs/STATUS.md`.

## Decision

The angle-matched Krea2 follow-up is the best edited candidate, but the untouched lounge source remains the overall identity and candid-realism winner.

The original front-reference Krea2 result was believable and clean, but its four-reference identity score fell from `0.5732` to `0.4275`. Replacing only the person reference with a genuine angle-matched portrait raised Krea2 to `0.5245`. FLUX.2 produced a stronger side profile but fell to `0.3947`. None of the edits leaked Mitch's identity into either friend.

## Controlled inputs

- Scene, supplied first to both models: `C:\projects\AI-Tools\ComfyUI\input\lounge-clean-geometry-scene-for-identity-edit.png`
- Genuine identity photograph, supplied second to both models: `C:\projects\AI-Tools\ComfyUI\input\20260815_165446.jpg`
- Resolution: `1344x896`
- Seed: `9472103`
- GPU: RTX 3090 worker at `http://127.0.0.1:8188`
- RTX 4070 worker at `http://127.0.0.1:8189` remained idle
- No character LoRA, face swap, output mask, restoration, sharpening, relighting, or post-processing was used.

## Results

| Candidate | Four-genuine-reference identity | Exact supplied portrait identity | Maximum friend/background identity | Time | Visual result |
|---|---:|---:|---:|---:|---|
| Untouched source | **0.5732** | 0.4471 | 0.1518 against exact portrait | n/a | Best identity and strongest candid moment; clean hands and separate bodies. |
| Krea2 Identity Edit v1.2 | 0.4275 | **0.4754** | 0.1312 exact / 0.0923 four-ref | 89.270 s | Best edit. Believable three-quarter face, clean anatomy, distinct friends, but broader identity regressed. |
| Krea2 angle-matched reference follow-up | **0.5245** | n/a; single-reference face selection was unreliable | 0.0867 four-ref | 87.569 s | Best edited candidate. Much stronger identity and clean anatomy; expression is stiffer and less candid than the source. |
| Krea2 reduced-turn, slight-smile, natural-skin prompt | 0.4582 | n/a | 0.0775 four-ref | 88.614 s | Less head turn, both eyes visible, restrained smile, and improved fine skin detail; skin remains smoother than the source and identity regressed from the angle-matched leader. |
| FLUX.2 Dev native edit | 0.3947 | 0.4033 | 0.0903 exact / 0.0753 four-ref | 301.134 s | Clean and coherent side profile, but the central face became more generic and identity regressed on both tests. |

The four-reference centroid is the primary diagnostic because it is less dependent on one source photo's expression, lens, and angle. Visual review still outranks the score. The exact-angle single-reference check selected a small background face in the full images; isolated central-face crops also showed that this one reference is an embedding outlier, so it was not used to select the winner.

## Krea2 angle-matched follow-up

This was a one-variable refinement of the Krea2 workflow above. Everything remained fixed except image 2:

- Previous image 2: `C:\projects\AI-Tools\ComfyUI\input\20260815_165446.jpg`
- New image 2: `C:\projects\AI-Tools\ComfyUI\input\flux2-dev-ref-02-face-angle.jpg`
- Output: `C:\projects\AI-Tools\ComfyUI\output\identity-edit-ab\krea2-lounge-angle-matched-ref_00001_.png`
- Runtime: `87.569 s`
- Four-reference identity: `0.5245`, an absolute gain of `0.0970` over the front-reference Krea2 edit
- Maximum secondary identity: `0.0867`; no identity leakage
- Visual result: coherent whole frame, clean hands and chair boundaries, distinct friends, no pasted-head boundary, and more recognizable identity. The sideways expression is slightly stiff compared with the source's natural downward smile.

Conclusion: matched reference yaw materially helps Krea2 Identity Edit, but this run still trails the untouched source by `0.0487` on the robust identity diagnostic.

## Krea2 reduced-turn, slight-smile, natural-skin prompt follow-up

This retained the angle-matched reference and every Krea2 parameter. Only the text prompt changed. The requested head angle and expression landed, but prompt-only skin instructions did not fully recover the source photograph's coarse phone-camera texture, and the four-reference identity score fell by `0.0663` from the angle-matched leader.

- Output: `C:\projects\AI-Tools\ComfyUI\output\identity-edit-ab\krea2-lounge-subtle-turn-smile-real-skin_00001_.png`
- Runtime: `88.614 s`
- Four-reference identity: `0.4582`
- Maximum secondary identity: `0.0775`; no identity leakage
- Visual result: near-frontal off-camera gaze, both eyes visible, subtle closed-mouth smile, visible forehead and under-eye detail, clean hands and chair boundaries, and distinct friends. Skin is still somewhat smoother than the untouched source at face-crop size.

Exact prompt:

> Image 1 is the exact existing candid lounge photograph and defines the complete composition, three seated people, central man's seated body pose, navy jacket, white shirt, body, hands, chairs, lighting, focus, crop, and every background detail. Image 2 is a genuine photograph of Mitch and defines the identity of only the central man in image 1. Replace only the central man's identity, head angle, gaze, and expression so he is unmistakably Mitch from image 2. Keep his head mostly forward relative to his torso with only a slight natural turn toward the conversation, roughly ten degrees rather than a side profile; both eyes and both cheeks remain clearly visible, and he looks just off camera rather than into the lens. Give him a very subtle relaxed closed-mouth smile with the mouth corners only slightly raised and no teeth. Preserve Mitch's current apparent age, forehead, eye shape and spacing, nose, mouth, jaw, ears, hairline, short light-brown hair, faint stubble, and natural skin. Render ordinary realistic skin at this scene scale: visible pores, fine forehead and eye creases, faint beard shadow, slight under-eye texture, subtle uneven tone, and soft natural highlight rolloff consistent with the lounge light. No waxy skin, plastic sheen, airbrushing, beauty filter, makeup effect, de-aging, or selectively sharpened face. Preserve the central man's clothing, hands, body proportions, scale, and seated pose from image 1. Preserve the older Black male friend and dark-haired female friend as completely distinct people; do not change their faces, bodies, clothing, hands, or positions. Preserve all chair boundaries, hands, background patrons, lamps, depth, color, sensor texture, and framing. The result must remain one coherent unedited phone photograph with no second Mitch, repeated face, pasted head boundary, halo, portrait blur, text, or watermark.

## Krea2 workflow

- Base: `krea2_turbo_fp8_scaled.safetensors`
- Adapter: `krea2_identity_edit_v1_2.safetensors`, strength `1.0`
- Text/vision encoder: `qwen3vl_4b_fp8_scaled.safetensors`
- VAE: `qwen_image_vae.safetensors`
- Trained two-input order: image 1 scene, image 2 person
- Scene reference boost: `1.0`
- Person reference boost: `6.0`
- Grounding: `768 px`
- Reference-token face-attention mask enabled; this was not an output-pixel face mask
- Fit mode: `fit`
- Sampler: Euler, `12` steps, simple scheduler, CFG `1.0`
- Output: `C:\projects\AI-Tools\ComfyUI\output\identity-edit-ab\krea2-lounge-face-attention_00001_.png`

Exact prompt:

> Image 1 is the exact existing candid lounge photograph and defines the complete composition, three seated people, central man's pose, head angle, gaze, expression, navy jacket, white shirt, body, hands, chairs, lighting, focus, crop, and every background detail. Image 2 is a genuine photograph of Mitch and defines the identity of only the central man in image 1. Replace only the central man's identity so he is unmistakably Mitch from image 2, preserving Mitch's current apparent age, forehead, eye shape and spacing, nose, mouth, jaw, ears, hairline, short light-brown hair, faint stubble, and natural skin. Keep the central man's existing seated pose, sideways gaze, closed-mouth expression, clothing, hands, body proportions, scale, and lighting from image 1. Preserve the older Black male friend and dark-haired female friend as completely distinct people; do not change their faces, bodies, clothing, hands, or positions. Preserve all chair boundaries, hands, background patrons, lamps, depth, color, sensor texture, and framing. The result must remain one coherent unedited phone photograph with no second Mitch, repeated face, pasted head boundary, halo, beauty filter, portrait blur, selective face sharpening, text, or watermark.

## FLUX.2 workflow

- Model: `flux2_dev_fp8mixed.safetensors`
- Text/vision encoder: `mistral_3_small_flux2_fp4_mixed.safetensors`
- VAE: `flux2-vae.safetensors`
- Native two-reference `ReferenceLatent` chain: scene first, person second
- Each reference scaled to `1.00 MP`
- Sampler: Euler through `Flux2Scheduler`, `20` steps, guidance `4.0`
- Output: `C:\projects\AI-Tools\ComfyUI\output\identity-edit-ab\flux2-dev-lounge-native-edit-20step-guidance4.0-2ref-1.00mp-seed9472103_00001_.png`

Exact prompt:

> Picture 1 is the exact existing candid lounge photograph and defines the complete composition, three seated people, the central man's seated pose, head angle, sideways gaze, closed-mouth expression, navy jacket, white shirt, body, hands, chairs, lighting, focus, crop, and every background detail. Picture 2 is a genuine photograph of Mitch and defines the identity of only the central man. Recreate Picture 1 as one coherent natural phone photograph, changing only the central man's identity so he is unmistakably Mitch from Picture 2. Preserve Mitch's current apparent age, forehead, eye shape and spacing, nose, mouth, jaw, ears, hairline, short light-brown hair, faint stubble, and natural skin. Preserve the older Black male friend and dark-haired female friend as completely distinct people; do not change their faces, bodies, clothing, hands, or positions. Preserve all chair boundaries, hands, background patrons, lamps, depth, color, sensor texture, and framing. No second Mitch, repeated face, pasted head boundary, halo, beauty filter, portrait blur, selective face sharpening, text, or watermark.

## Mechanism evidence

- Krea2 Identity Edit model card: https://huggingface.co/conradlocke/krea2-identity-edit
- Author-maintained Krea2 ComfyUI nodes: https://github.com/lbouaraba/comfyui-krea2edit
- Official Black Forest Labs FLUX.2 repository: https://github.com/black-forest-labs/flux2
- Official ComfyUI FLUX.2 image workflow template: https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_flux2.json

## Highest-confidence follow-up, if revisited

Change one variable only: keep the Krea2 graph and scene unchanged, but replace image 2 with a genuine three-quarter portrait of Mitch whose yaw matches the desired lounge head angle. This test is not recommended until such a reference is available; pushing the prompt further sideways did not improve identity here.
