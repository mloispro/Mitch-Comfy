# FLUX.2 Klein 9B – Upgrade Photo Detail & Realism v1

This production workflow re-renders an existing one-person Mitch photograph as a realistic, materially detailed whole-frame photograph while preserving the source pose and layout. Its sampling and conditioning path is restored from Git milestone `d58732a` / `milestone-good-identity-workflows-2026-09-01`.

Open `Mitch/production/FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1` in the standard RTX 3090 ComfyUI instance at `http://127.0.0.1:8188`.

## Use

1. Load the exact source photo.
2. The included example selects the exact 2,621-character prompt embedded in the approved milestone PNG. Replace its source-specific pose, clothing, and material description in `detail_instructions` whenever you change the source; changed text selects the generic four-role template instead. Generic “preserve everything” wording did not reproduce the approved example.
3. Keep `Subtle handsome polish` on for the default tested face/iris/hair-local treatment, including source-relative pupil direction. Turn it off to skip that treatment; the camera-rendering choice remains independent.
4. Leave `Phone-camera realism` on for the accepted deep-focus Smartphone Snapshot v13 rendering; phone-on skips background blur entirely. Turn it off only when you want the optional natural larger-lens look with gentle background separation.
5. Queue seed `8675416` first. If the result fails identity or visual review, use seed `8675412` as the one controlled retry.
6. Inspect the result and its automatically saved structure guide at full size and thumbnail.

The source must contain exactly one detectable face. The node rejects zero-face and multi-face inputs; use Group Scene Studio for groups.

## Deterministic appearance toggle

The default-on `deterministic_face_and_hair_local_v4+mediapipe_refined_iris_source_lock_v1` profile runs only after the unchanged milestone generation. The on/off states use the same effective prompt, graph, model, LoRA stack, references, reference resolutions, sampler, CFG, seed, and 50-step model pass. This avoids the pose, forehead, gaze, and blurred-background failures observed when appearance or gaze wording was left solely to the generative prompt.

The enabled profile uses the generated face's detected box and five facial landmarks to apply:

- a four-pixel-scale upward mouth-corner adjustment for a slight confident closed-mouth expression; it cannot generate teeth;
- restrained forehead-line and under-eye fatigue attenuation while retaining most fine texture and visible pores;
- subtle warm/tan color within detected facial skin only;
- modest eye clarity and brightness without resizing or relocating the eyes;
- source-relative pupil direction measured with MediaPipe's refined 478-landmark face/iris model; only generated iris material is locally warped, with no source-pixel copy and no eyelid-boundary movement;
- local detail contrast over existing stubble;
- cheek highlight and jaw-contour lighting that reads the existing bone structure more cleanly without reshaping it.
- sparse local-median replacement over isolated cheek/nose dots and freckles; it avoids broad inpainting patches, excludes the mouth, eyes, and stubble region, and leaves all unselected skin texture exact;
- semantic hair parsing with CodeFormer ParseNet, followed by a deterministic luminance-frequency correction that reduces broad artificial grooves, retains fine texture, and gives a slight lift only to existing brighter hair material.

The active handsome-polish mask stays inside the face, eroded eye interiors, and deep semantic-hair interior. The first eight pixels inside the complete hair boundary and the complete eyelid boundary are hard-protected. Pixels outside that mask—including the background, hairline, hair silhouette, forehead outline, ears, outer jaw/head silhouette, clothing, and scene geometry—are copied back exactly from the raw generation. Turning the handsome toggle off skips this treatment; phone-off can still apply the separate background finish below.

This is restrained retouching, not a new face generator: it can make apparent age read slightly younger by reducing fatigue and some line contrast, but it does not replace facial anatomy or promise a particular age.

## Locked milestone mechanism

Reference order remains part of the lock:

1. source photo at `1.00 MP`: scene, pose, expression intent, clothing, lighting, and composition;
2. automatically generated face-interior-free Canny guide at `0.50 MP`: geometry only;
3. protected genuine frontal Mitch photograph at `0.50 MP`: identity and facial geometry;
4. protected isolated genuine hair crop at `0.10 MP`: hair material only.

All four reference latents enter both positive and empty-negative conditioning in that order. The model is FLUX.2 Klein Base 9B loaded as `fp8_e4m3fn`, with the protected V3 step-1600 identity LoRA at `0.90`, Qwen 3 8B FP8, FLUX.2 VAE, 50 Euler steps, CFG `4.0`, and `Flux2Scheduler`.

This is one empty-latent whole-frame generation pass. It has no Turbo, source-latent initialization, generation mask, face swap, restoration, upscaling, generative compositing, or second model pass. When the appearance toggle is on, deterministic face-interior and eroded semantic-hair-interior masks are used only for the post-generation pixel treatment described above.

## Camera-rendering toggle

With `Phone-camera realism` off, the complete detailed image is generated first and retained as `before-background-blur`. A local hash-locked U2Net human-segmentation model then supplies a subject matte. The camera finish excludes subject colors from two normalized Gaussian background filters, ramps gently from near to far blur, feathers only outside a dilated safety rim, and finally copies every protected subject pixel back exactly. This is a deterministic post-decode finish—not identity conditioning, inpainting, or a second model pass—and it preserves a recoverable detailed background while presenting a more natural larger-lens depth of field.

With `Phone-camera realism` on, the node applies the hash-locked Smartphone Snapshot Photo Reality v13 LoRA at `0.25` after the Mitch identity LoRA and prepends its trained `casual snapshot` trigger. The background-blur stage is skipped completely, giving the crisper deep-focus phone rendering Mitch accepted. Neither state changes the sampler, steps, CFG, or four-reference order.

The output keeps source dimensions at or below `1.70 MP`; larger inputs are downscaled with aspect ratio preserved and dimensions rounded to multiples of 16.

## Acceptance gate

The integrated native RTX 3090 confirmation completed in `531.231 s`. Its raw generation remained a close reproduction of the accepted 4070 PNG (`3.3599 / 255` mean absolute pixel difference), with the detailed siding/tree, forehead, and three-quarter direction intact. The final v3 polish changed no pixel outside its active masks and retained a six-genuine-reference `strong_match` identity score of `0.7662` (raw: `0.7816`). Direct raw-to-polished pitch/yaw/roll changed by only `-0.3083° / -0.2602° / -0.0994°`. It reduced measured freckle response by `81.6%`; in the protected hair interior, broad mid-frequency variation fell `3.5308 → 2.4196` while fine micro-frequency variation remained `2.0902 → 2.1132`. The first eight semantic-hair boundary pixels and every background pixel stayed exact.

The native same-seed Smartphone v13 A/B completed in `531.133 s`, essentially the same runtime as phone-off. The adapter was compatible and left raw identity nearly unchanged (`0.7816 → 0.7791`), but after identical v3 polish identity was `0.7662 → 0.7397`, tolerant structure F1 was `0.3076 → 0.2961`, and facial microtexture became smoother. Background micro-luma detail rose modestly (`11.9536 → 12.3539`). These automated tradeoffs remain recorded, but Mitch later visually accepted the phone-on v4 rendering and selected phone-on as the workflow default on 2026-09-03.

A fresh handsome-v4 confirmation quantified the same automated tradeoff. Phone-on final identity was `0.7375` versus `0.7476` off; its weakest reference score was `0.5351`, below the `0.5533` genuine-photo floor. Background micro-luma rose `11.9536 → 12.3405`, but structure F1 fell `0.3076 → 0.2977`, facial micro-luma fell `5.541 → 5.191`, and normalized facial Laplacian variance fell `364.03 → 309.99`. Phone-on nevertheless opens by default because it is the visually accepted camera rendering; the measurements remain visible rather than being discarded.

A later clean same-seed Turbo A/B kept phone style off and changed only the locked rank-256 Turbo treatment (`1.0`, 8 Euler steps, CFG `1.0`). It was `9.54×` faster in-node (`55.694 s`), but polished identity fell `0.7662 → 0.6958`, raw yaw moved `+1.6934°`, background micro-luma detail fell `11.9536 → 4.5229`, and facial texture became visibly harsher. Because it failed both the automated and full-size visual gates, Turbo is not exposed in this production workflow.

The source-gaze correction was evaluated on the accepted 50-step output after its v3 polish. MediaPipe 0.10.14 measured each iris center relative to that eye's own corners and eyelid aperture in the source and generated images. A bounded smooth warp moved only the generated iris material: `1,606` pixels (`0.0948%` of the frame), with zero change outside the eroded eye interiors and no source-pixel copy. Mean normalized horizontal gaze error fell `0.038415 → 0.009968` (`74.1%`). Six-reference identity remained `strong_match` at `0.7508`, with the weakest view `0.5581` above the genuine-photo floor `0.5533`. Pitch/yaw/roll changed only `-0.1157° / +0.0808° / +0.0004°`. Full-size review retained natural irises, catchlights, eyelids, eye shape, face, hair, and background.

The v4 handsome refinement replaced the earlier narrow freckle treatment after the user still saw dark facial dots. A first broadened Telea-inpainting prototype created visible cheek/nose patches and was rejected. The accepted sparse local-median refinement reduced pixels above the fixed dark-dot threshold by `35.9%` (`3,915 → 2,509`) relative to v3 without a waxy region; its selected-dot response fell `72.5%`. Existing-luminance-guided hair highlights lifted active hair by `1.32 / 255` on average and `4 / 255` at the 90th percentile. Old-to-new changes remained completely inside the combined face/hair/iris masks, with zero protected-pixel error and the first eight hair-boundary pixels exact. Final six-reference identity remained `strong_match` at `0.7476`, with the weakest view `0.5546` still above the `0.5533` genuine-photo floor. Evidence is under `work/flux2-klein9b-upgrade-safe-polish-20260902/integrated-v7-handsome-v4-source-gaze`.

The phone-off natural-lens prototype was applied to that accepted v4 result without rerunning diffusion. At `1680×1008`, it used a `2.2176 px` near sigma, `5.544 px` far sigma, and `181.44 px` smooth depth ramp. It changed `64.4717%` of frame pixels in the exposed background while the protected subject's maximum error was exactly `0 / 255`. Full-size inspection found the face, hair, coat, and silhouette unchanged, with no subject-color halo; siding and branches softened progressively instead of collapsing into synthetic portrait-mode bokeh. Evidence is under `work/flux2-klein9b-upgrade-safe-polish-20260902/phone-off-natural-lens-v1`.

The reloaded production node then completed a fresh `1328×800` phone-off smoke on the RTX 3090 in `414.562 s`. The saved output confirms the production report, pre-blur image, and blur mask are wired correctly: `62.8935%` of pixels changed above the half-level threshold and protected-subject error remained `0 / 255`. Six-genuine-photo centroid identity changed only `0.703691 → 0.702229`, with before/after embedding similarity `0.998553`; the weakest view was already slightly below the genuine pairwise floor before blur (`0.549566`) and remained slightly below after (`0.547286`), so this smoke proves background-stage integration rather than replacing the stronger native identity acceptance. Visual review found natural separation and no cutout or subject-color halo. The small normalized gaze error was not improved by the existing gaze lock on this downscaled smoke, so its earlier native gaze acceptance remains the relevant gaze result. The live run is `ComfyUI/output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260902-194222-645341`.

These are diagnostics, not proof of attractiveness, identity, or realism. Review pose, gaze, forehead/hairline, identity, closed lips, skin texture, stubble, background detail, whole-frame coherence, and realism at full size and thumbnail.

The milestone anchor is `output/klein9b-existing-photo2-restage-4070/candidate-klein9b-iphone-structure-v4-seed-8675416.png`; the close 3090 reproduction is `ComfyUI/output/klein9b-realism-locked-v1/house-3090-seed-8675416_00001_.png`.

For the included source, the effective prompt now matches the approved prompt exactly (`2,621 / 2,621` characters), and the automatically rebuilt Canny guide is pixel-identical to `mitch-photo2-canny-face-interior-free.png` (`0` changed pixels).

With handsome polish on, each run saves the polished photo, raw `before-polish` image, and exact combined face/iris/hair `polish-mask`. With phone style off, it additionally saves `before-background-blur` and `background-blur-mask`. Every run also saves the structure guide, prompt graph, optional workflow snapshot, and report beneath `ComfyUI/output/flux2-klein9b-upgrade-photo-detail-realism-v1/`. The report records source-relative iris coordinates and shifts, gaze error reduction, freckle and hair-frequency diagnostics, protected-pixel error, camera-finish provenance and mask coverage, optional phone-LoRA provenance, and unchanged generation settings.

Verify without generation:

```powershell
.\scripts\verify-flux2-klein9b-upgrade-photo-detail-realism-v1.ps1
```

Pass `-Smoke` for the faster approximately 1 MP evaluation render. Use `-Smoke -Native` only for the final native-resolution confirmation after the preview passes.
