# FLUX.2 Klein 9B visual-preset studios v1.1

## Decision

The v1.1 workflows add a clickable thumbnail gallery without modifying either hash-frozen v1 generator:

- `Mitch/production/FLUX.2 Klein 9B Mitch Identity Studio v1.1 - Visual Presets`
- `Mitch/production/FLUX.2 Klein 9B Mitch Group Scene Studio v1.1 - Visual Presets`

The Upgrade Photo workflow is intentionally unchanged and has no scene gallery.

## Identity Studio

Click one of the 15 scene cards. The card supplies its prepared scene prompt and selects the matching genuine
reference profile: group-safe frontal, the useful solo angle, or full-body. The preset combo is hidden visually but
still serialized by ComfyUI. Use `Custom — write your own scene` to type a new prompt; for prepared cards, the prompt
box is optional extra direction.

The gallery retains Ragdoll cat, removes tabby cat, adds separate toddler and small Golden Shepherd choices, and
includes the supplied rooftop cocktail source as a visual target. Clicking a card does not use that thumbnail as an
identity reference or img2img source.

## Group Scene Studio

Click one of five cards: Custom upload, approved lounge, Night out A, Night out B, or amber booth. Prepared cards load
their preserved source-layout image, tested target coordinates, `0.92` head scale, and prompt. The source enters only
through the existing face-interior-free Canny composition path; the separate genuine Mitch photograph and protected
step-1600 LoRA continue to supply identity.

Choose `Custom — uploaded group photo` to use the visible Load Image node and manual target controls.

## Locked engine and validation

Both shells call the unchanged hash-frozen v1 generators. Model, LoRA order and strength, reference policy, sampling,
resolution, GPU lock, identity mechanism, and output paths are unchanged. The selector was verified on the local
RTX 3090 ComfyUI instance: 15/15 Identity thumbnails and 5/5 Group thumbnails loaded, saved defaults restored
correctly, and clicking cards updated their selected states. No generation was queued for this UI-only change.
