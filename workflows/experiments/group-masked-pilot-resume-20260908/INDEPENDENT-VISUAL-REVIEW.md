# Independent blind visual review — acceptance withheld

Reviewer: `/root/upgrade_next_mechanism`. This verdict was formed before opening any candidate metrics/evaluation or root review/opinions. No scoring or runtime action was performed.

Actual candidate: `runs/ready-amber-hook-pilot/group-amber-hook-pilot-seed8675412_00001_.png`, independently verified SHA256 `4100246734E15B8AF7F71E58EDB9C60268BE9BE87757C7319DC86ECC5AC78BB3`.

Reviewed the full native832x1216 candidate and the supplied `pre-score-visual-review/whole-frame-thumbnail.png`, `heads-native.png`, and `hands-body-native.png`. Compared identity only against `work/9b-readiness-resume-20260907/group-identity-hook-gate/runtime-3090/image-diagnostic-control-monitoring-failed/genuine-six-reference-sheet.png`, and layout only against `assets/comfy-input/klein9b-scene-presets/group-amber-booth-four-friends.jpg`. The latter is a composition source, not genuine identity ground truth. No historical control output or metric sheet was examined.

To resolve the right-edge person count, also inspected in-memory native-scale rightmost160px crops over y460–899 from candidate and composition source. These were preview-only JPEG encodings; no image files or pixels were edited or saved.

## Blocking visual concern

**The complete required four-principal-plus-partial-fifth composition does not receive a visual pass.** Four principal adults are clearly present. In the source, a substantial black-shirted fifth adult's shoulder/torso is readable at the right edge. That area becomes mostly empty booth in the candidate. A very small tan/dark edge sliver remains near head height and another possible hand sliver near the table, but these are too ambiguous to verify the fifth adult as a preserved visible person. This is substantial loss of the readable partial fifth figure, not proof that literally every pixel of that person vanished.

I would not convert that uncertainty into a people-preservation pass. Good identity scores cannot resolve this composition concern or waive the existing visual requirement. This is a verdict on this image, not a recommendation for another generation or a changed acceptance threshold.

## Other observations

- **Main identity, skin, hair and age:** the central navy-suited man is plausibly recognisable against the six genuine photographs. Hair colour, swept shape, face proportions and general features are reasonably consistent. Skin is smoother and presentation somewhat younger/more polished than the genuine examples, with less distinctive facial creasing. It is not a verified identity lock. This is a caveat rather than a separately decisive face-rejection from visual inspection alone.
- **Expression and eyes:** main lips are closed; no exposed teeth or obvious eye deformation. He looks approximately toward the camera. Exact pupil/gaze equivalence cannot be established visually here. The other three clear faces also have plausible closed-lip expressions.
- **Main body, arms and hands:** two main hands are visible on/near his knees, each connected plausibly through a white cuff to its corresponding suited forearm. Fingers are long but individually plausible in the native crop; no obvious extra main hand, fused forearm or severe digit failure. Seated torso, suit and leg placement read coherently. This is not an assertion that all occluded limb geometry is known.
- **Other people and contacts:** the brunette's visible glass grip is plausible, with fingers at the stem/bowl base; it does not appear to float. Her other visible hand and the blonde's table-level/dangling hand positions are plausible under the occlusion. The denim man's visible hand rests naturally near the table. No clear glass-through-hand or gross contact failure was visible.
- **Bystander distinctness:** the brunette, blonde and dark-haired bearded denim man look distinct from one another and from the main man. No obvious visual Mitch-clone bystander was apparent. Numeric leakage diagnostics remain separate and were not accessed.
- **Table and depth:** the main and foreground tables have plausible overlap and perspective. Their edges occlude legs and clothing coherently; no clear tabletop passing through a principal torso. Booth, people and tables share a coherent seating arrangement despite regenerated details.
- **Texture and integration:** warm wall lighting is strong and faces have a polished flash-like look, but there is no obvious pasted head, white fringe/halo, severe cutout, coarse noise or isolated oversharpened facial patch at full size or thumbnail. Wall/fabric texture remains visible. Photographic plausibility is better established than source-exact detail preservation.

## Bottom line

The principal group is visually plausible enough to warrant reporting unchanged diagnostics, but **full visual acceptance is withheld because the required partial fifth adult is not confidently preserved**. Identity polish/smoothing is an additional limitation. This review does not claim overall Group readiness, successful identity locking, or a runtime/speed comparison.

Only this new Markdown review was saved. No GPU, API, worker, process, queue, cache, model, scoring, production or frozen-file action was taken.
