# Visual scene prompt repair — 2026-09-04

Mitch could not see the optional scene prompt in Identity Studio. The gallery's CSS minimum height overflowed the space reserved by ComfyUI and covered the prompt and appearance controls.

The shared Identity/Group frontend now reserves the gallery's actual height through ComfyUI's DOM widget layout hooks. It wraps the existing prompt textarea with a visible **Modify this scene (optional)** label and helper text. Custom mode uses **Describe your scene**. The original input, value callbacks and Python conditioning remain in place. Preset prompts still append the user's extra direction; this is not a new prompt override or hairstyle control.

The gallery uses scrollable rows with full card captions and only the selected card has a checkmark. A second defect affected saved state: the installed LiteGraph serializer used array indices and left a hole for the non-serialized gallery, while its loader consumed values sequentially. The frontend now saves original input order and restores named or positional values independently of the gallery's visual position, including the old leading-null layout.

Validation:

- `node --check custom_nodes/ComfyUI-AIToolkit-Training/web/visual_scene_presets.js` passed.
- `node scripts/test-visual-scene-presets-ui.mjs` passed for both production workflow defaults, original textarea binding, labels, repeated configure, clone, legacy leading-null restoration and named restoration.
- Local browser review confirmed the label and separate prompt/gallery rectangles. At the verification canvas scale, the gallery ended at y=343.05 and the prompt began at y=353.25; there was no overlap.
- The user's Identity tab was refreshed and its previously selected puppy scene, blank prompt, flattering enhancement, Quality mode and seed 8675411 restored after encountering an already-shifted browser session. A subsequent live reload retained those controls and fixed seed behavior correctly.

No generation was queued for this repair. Internal engines, production workflow files, manifests, models, reference conditioning, GPU locks and generation settings were not changed by this UI patch. Only the active public-surface frontend hash is revised; the historical visual-shell baseline remains unchanged.
