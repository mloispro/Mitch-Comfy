# FLUX.2 Klein 9B visual-preset studios v1.1

## Decision

The public v1.1 workflows provide one consistent Klein 9B surface without modifying the proven internal generators:

- `Mitch/production/FLUX.2 Klein 9B Mitch Identity Studio v1.1 - Visual Presets`
- `Mitch/production/FLUX.2 Klein 9B Mitch Group Scene Studio v1.1 - Visual Presets`
- `Mitch/production/FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1.1`

Upgrade has no scene gallery; its v1.1 node name maps directly to the unchanged validated Upgrade engine.

## Identity Studio

Click one of the 15 scene cards. The card supplies its prepared scene prompt and selects the matching genuine
reference profile: group-safe frontal, the useful solo angle, or full-body. The backend also resolves the preset's
profile, so API calls and stale UI state cannot silently use a mismatched reference profile. The preset combo is
hidden visually but still serialized by ComfyUI. Use `Custom — write your own scene` to type a new prompt; for
prepared cards, the prompt box is optional extra direction.

The prompt is labeled **Modify this scene (optional)** below the gallery. Choose a card and describe small changes such as clothing or setting details; leave the box empty to retain the preset. Custom changes the label to **Describe your scene**. The September 4 [UI repair](visual-scene-prompt-repair-2026-09-04.md) reserves separate space for the gallery and prompt and preserves widget values across reloads.

**Prompt helper**, beneath that box, adds editable examples for hair, clothes, a flattering expression, and holding a puppy with two separate hands. Examples are inserted only when selected and keep the text already entered. Edit the examples to fit the scene, removing any contradictory instructions. **Flattering appearance** labels the existing appearance-polish switch; the helper shows whether it is on or off.

**Edit full preset scene** copies the selected Identity preset's complete scene and your added directions into Custom. This lets you replace its original clothing or pose instead of appending conflicting instructions. The current effective reference profile is retained.

**Choose face angle…** offers **Nose toward picture LEFT** and **Nose toward picture RIGHT**. Either choice keeps the full scene, switches to Custom, selects the corresponding genuine front-plus-angle references, and adds an explicit nose-direction sentence. Changing sides replaces the helper's earlier direction sentence. Review other pose instructions in the editable scene and describe gaze separately. Choosing a prepared card again restores that card's reference policy.

This addresses the observed puppy-preset issue: a text-only request for the other cheek retained the prepared card's left-facing reference. The September 5 Custom run with the right-facing reference showed the opposite cheek. This is evidence from one portrait, not a guarantee that every scene will obey pose or hand-anatomy requests. Prompt helper changes only the existing inputs; it does not alter the generator or add processing stages.

The gallery retains Ragdoll cat, removes tabby cat, includes the selected canyon-overlook and small Golden Shepherd
results, and includes the supplied rooftop cocktail source as a visual target. Clicking a card does not use that
thumbnail as an identity reference or img2img source.

The boat card is now **St. Barts yacht — Caribbean escape**: white linen and sunglasses on
a yacht outside Gustavia, with Caribbean water, low hills, waterfront villas and other yachts.
It replaces the Italian lake card; reselect this card in older saved graphs that still name
the Italian lake preset. Selecting it turns **Flattering appearance off**, retaining natural age/texture,
and describes the original forward lean, bent legs and both hands gripping the boat rails.
The switch remains editable and its saved value survives reload; other cards keep their existing behavior.
FULL BODY references and gallery sampling settings are unchanged. The
[current final image and deterministic composition](../work/st-barts-exact-foreground-20260920/RESULT.md)
retain original person/boat pixels in a Caribbean setting. The prior native Quality50 result was
approximate. Gallery thumbnails are not pose conditioning, and its text has not had a separate
generation check. Use the final PNG or saved composition for this exact pose.
Likeness remains qualified: centroid .5380/minimum .4211, near_match but below the original .5443/.4310
and the genuine-pair floor. No identity-lock or exact geographic reproduction claim. Prior rejected
pose/anatomy variants and the new Turbo likeness failure remain preserved in their dated reports.

## Group Scene Studio

Click one of five cards: Custom upload, approved lounge, Night out A, Night out B, or amber booth. Prepared cards load
their preserved source-layout image, tested target coordinates, `0.92` head scale, and prompt. The source enters only
through the existing face-interior-free Canny composition path; the separate genuine Mitch photograph and protected
step-1600 LoRA continue to supply identity.

Choose `Custom — uploaded group photo` to use the visible Load Image node and manual target controls.

Group Scene Studio also has the editable prompt examples and appearance status. Its helper does not offer the solo-angle or full-preset-to-Custom actions: switching Group to Custom changes its source photograph and requires a deliberate user choice. The helper explains that large pose changes can conflict with the source layout.

## Locked engine and validation

The Identity and Group interfaces call unchanged generation-locked internal engines. Model, LoRA order and strength, reference policy, sampling,
resolution, GPU lock, identity mechanism, and output paths are unchanged. The selector was verified on the local
RTX 3090 ComfyUI instance: 15/15 Identity thumbnails and 5/5 Group thumbnails loaded, saved defaults restored
correctly, and clicking cards updated their selected states. The manifest and wrapper refactor did not queue a new
generation or modify either internal engine.

`custom_nodes/ComfyUI-AIToolkit-Training/web/assets/scene-presets/manifest.json` is the single runtime source for
labels, prompts, thumbnails, reference profiles, group source assets, target coordinates, and head scales. Python,
the browser gallery, verification, and preview-candidate tooling consume that manifest rather than maintaining
parallel copies. The PNG retains the generation-locked engine report; `report.json` extends it with a clearly nested
`visual_preset_shell` provenance block.
