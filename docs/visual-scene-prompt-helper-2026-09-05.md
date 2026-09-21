# Visual scene prompt helper — 2026-09-05

The puppy portrait exposed a useful distinction: prepared Identity presets resolve their own reference profile, so an added request for the opposite cheek can conflict with the reference used by the preset. The September 5 Custom portrait with front + right-facing references did show the opposite cheek. Its local evaluation is retained in `work/identity-puppy-right-angle-20260905/evaluation.md`.

## Interface changes

The existing prompt box now includes a visible **Prompt helper**:

- Editable examples for hair, clothes, a flattering expression, and holding a puppy. Selecting one appends text without replacing existing writing; repeated selection does not duplicate the exact example.
- Identity's **Edit full preset scene** copies the complete manifest prompt and added user direction into Custom, retaining the effective reference profile.
- Identity's **Choose face angle…** keeps that complete scene, switches to Custom, selects the genuine front + left/right profile, and inserts explicit picture-relative nose direction. Repeated changes replace only the helper's own direction line. Other prose remains editable rather than being deleted by heuristic rewriting.
- Contextual guidance separates head direction from gaze, asks users to replace conflicting pose/clothing wording, and recommends simple hand contact without claiming that wording guarantees anatomy.
- The existing `appearance_polish` control is labeled **Flattering appearance**, with its current on/off state shown beside the helper.

Group receives prompt examples and appearance status, with guidance about source-layout constraints. It does not receive the solo-angle or full-preset conversion actions, because Group's Custom choice changes the source photograph.

## Validation

`node scripts/test-visual-scene-presets-ui.mjs` passes: production defaults and existing save/reload/clone migration remain compatible; examples preserve text; complete preset conversion retains extra directions; left/right changes select matching profiles; helper direction does not accumulate; appearance status refreshes; unrelated sampling controls stay unchanged.

Live ComfyUI UI review confirmed the helper loads from the installed project junction. The Dog lover card was selected and an added black-hoodie instruction entered. Choosing picture-RIGHT visibly selected Custom, retained the complete puppy scene and added instruction, and showed the right-facing reference profile. The prompt's measured content height equaled its allocated height (379px), with no helper overflow. Screenshot review showed the helper above the original switches without covering them. The temporary test prompt was cleared and the original rooftop preset restored in the test tab.

The existing Identity and Group verification scripts both passed against the live RTX 3090 server, including protected engine/model hashes, default workflows, preset manifest, and frontend hash. The optional 8190 worker was unavailable; primary 8188 and secondary 8189 queues were inspected successfully. No smoke generation was requested. JavaScript syntax and whitespace checks also passed.

The active public frontend artifact hash is updated; historical baseline hashes and internal generation engines are untouched by this change. No new image generation, server restart, model change, or post-processing was performed for this UI feature. Its controls prepare editable prompts, not guaranteed pose or anatomy corrections.
