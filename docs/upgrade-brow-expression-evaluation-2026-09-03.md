# Brow/expression ablation — experimental, not production

## Scope and mechanism

This follows the failed Qwen direct-original tests. Those restored the more appealing
source presentation but failed skin/hair realism and background detail. The prior
goal turn made progress by closing that route; it was not a blocked/waiting turn.

Current production High and the earlier source-contour geometry hold eyebrow pixels
fixed. A bounded CPU ablation now transfers source-relative brow coordinates into the
existing generated image with a thin-plate-spline backward map. It uses only candidate
pixels, not source pixels, and is **not identity conditioning**. The identity signal
remains the previously evaluated local Klein generation. No model, download, new
diffusion graph, face swap, head replacement, or GPU generation was introduced.

`scripts/experimental_upgrade_source_brows.py` keeps eyes, lips, nose tip, hair and
eroded face outline fixed, caps each brow field at10% of eye width, checks inverse
Jacobian>=.30 and requires at least60% of requested displacement after a deterministic
safety line search. Strength is fixed at.8. Source pose/roll are removed using a
local eye frame; source expression geometry is not a genuine identity reference.

The house brow-only test improved the measured source-relative brow coordinates but
left tense glabellar creases. A separately justified local frequency correction
targets that observed failure. It symmetrically attenuates positive/negative mid-band
contrast above/between the brows; this is not the previously rejected dark-trough or
morphological-closing filler. It is limited to15/255 per channel, protects features,
and retains candidate fine residual/broad base algebraically. Actual texture still
requires measurement and visual review.

## Experiments and exact outcomes

All paths below are under `work/upgrade-source-faithful-20260903/`.

- `source-brow-only-house`: likeness .748015 versus prior High .761173 and actual
  Low .738950. Source-relative brow errors .083795 -> .041513 and .147214 -> .103462.
  Max field5.5335px, Jacobian .317980, safety fraction .85. No folds or obvious
  eyebrow duplication; still visibly tense between brows.
- `source-brow-glabella-house`: first local crease correction failed the fixed
  fine-texture retention threshold (.850191 < .90). Likeness .723742. Preserved as
  rejected. Initial invocation raised before writing; identical rerun only changed
  failure reporting so failed pixels/metrics could be saved. It still exits1.
- The **one cutoff refinement** doubles the treatment's fine cutoff while leaving
  the measurement scale and .90 threshold unchanged. House treatment sigma1.588659,
  measurement sigma .794329, broad sigma8.605234. No strength grid.

The frozen .8 brow + refined crease recipe was then evaluated on all three:

| Photo/output folder | Low likeness | Prior High | New High | Fine-band retention | Mid-band std before -> after |
| --- | ---: | ---: | ---: | ---: | --- |
| `source-brow-glabella-micro-house` | .738950 actual | .761173 | .728138 | .970793 | .024697 -> .013789 |
| `source-brow-glabella-micro-canyon` | .746137 actual | .694568 | .684388 | .990393 | .019685 -> .013046 |
| `source-brow-glabella-micro-third` | .824368 revised | .812502 | .800576 | .977113 | .013796 -> .008624 |

Texture/exposure checks pass on the refined outputs; mean regional shifts are
-.568027/255, -.153459/255, -.336129/255 respectively. These tests do not establish
attractiveness, complete identity retention, freckle removal, or production readiness.
The stricter earlier likeness .70 / maximum-drop .03 tests must not be implied to
pass for canyon/house simply because these targeted texture checks pass.

Full-size, face-crop and thumbnail review performed for all three. The brow area is
less tense and the existing detailed scene is unchanged. No visible teeth, new halo,
head-direction change, or new hair distortion from these local additions. The
overall High effect is still modest, house/canyon retain visible spots/texture issues,
and the source's presentation remains more appealing in important respects. NOT an
accepted final solution. Skin/hair elsewhere are inherited, not repaired by this test.

## Third-photo qualification

The old third-photo baseline rotated the head and opened the lips. It was not reused.
`source-contour-corrected-third` replays the existing .85 source-eye/mouth geometry
and final gaze correction on the already validated **single-source** native base
`third-source-native-preserve/raw_00001_.png`, with common forced smile and cheek
highlight disabled. The genuine `val_03_navy_upper_body.jpg` source is excluded from
the five scoring references. The replay verified the native PNG graph and passed its
closed-lip check (.003286), with prior-High likeness .812502. All input/reference
hashes and CPU metrics are saved. The new brow/crease test then uses this prior High.

This third test verifies the same **postprocess** on a corrected base; it does NOT
prove one shared production generation recipe works on all3. Canyon/house still use
the original four-reference base. Choosing and integrating a general source-preserving
generation policy remains unresolved. The third comparison is correctly labeled
REVISED LOW, not current production Low.

## Canyon measurement diagnosis

Combined treatment redetected source-relative brow errors .079569 -> .091926 and
.056551 -> .070068 (worse). To avoid falsely attributing this to geometry,
`source-brow-only-canyon-diagnostic` replays just the identical brow stage:
.079569 -> .080847 and .056551 -> .055710 (essentially unchanged). Likeness .682669.
The larger redetection shift therefore appears only after local contrast changes.

Direct pixel checks confirm **zero difference across all3,205 selected brow pixels**
(brow polygons plus3x3 dilation) between this brow-only output and combined canyon
output. Thus the crease stage did not physically move/change those brow pixels;
the landmark detector responded to nearby tonal changes. Do not treat this as proof
of successful source-shape transfer either: brow-only improvement is not established
on canyon. No further brow-strength or crease-parameter sweep is approved by this test.

Independent final eye-pixel checks (pre-new-stage High versus refined result) are
exactly0/255 across2,230 canyon,2,220 house and1,033 third selected pixels, including
3x3 dilation. This confirms the added stages preserve the prior eyes, not that those
prior eyes already have perfect source gaze. Prior gaze/pose failures remain visible.

## Verification and outstanding work

`evaluate-upgrade-brow-edit.py` verifies native source/base hashes, pixel equality of
the parent raw and audited base, reproduction of the parent's recorded likeness,
genuine-reference hashes/scoring-set separation and exact pixels outside new edit
regions. It saves non-overwriting PNGs, masks, comparisons and audits. Failed local
texture/exposure refinements remain failed; they are not silently accepted.

Nine CPU safety tests pass (five new brow/crease tests and four imported existing
source-expression tests), including no-op, protected pixels, no folds, invalid input,
fixed measurement frequencies and an empty-region case that cannot claim success.

Production code/UI/workflow are unchanged. Phone-on/Turbo-off bases are retained;
no extra smartphone LoRA or prompt is being substituted in these CPU tests. No
end-to-end production run or promotion has occurred. Clearer consistent High beauty,
skin spots, general base-policy behavior on genuine inputs, full gaze/pose acceptance,
and final integration/default/off-low-high/phone-off verification remain outstanding.
The earlier user question concerns Qwen direct-original eyes/expression, not approval
of this new CPU version; no new reply was received during these tests.
