# High texture diagnosis and duplicate-smoothing ablation

Status: experimental component improvement, **not** an accepted three-photo High.
The preceding compact-native turn made progress: its one negative-guidance test
restored source-like expression/pose but lost substantial genuine-photo likeness
(0.756 ->0.422). That route is closed pending Mitch's visual judgment; no negative
prompt/CFG/strength grid was started here.

## Why inspect texture before adding a stage

The earlier two-reference Qwen High has more useful likeness than that extreme
native candidate, but its face appears rendered/smooth. Before adding sharpening,
noise or transferring pixels, `scripts/diagnose-upgrade-texture-bands.py` measures
the already-recorded raw, native High and finished High on canyon, house and the
corrected third base. No candidate is edited by this diagnostic.

It verifies native-audit hashes, original image hashes, finished PNG provenance,
common-polish audit inputs and image dimensions. It reuses the existing anatomical
skin region, excluding protected features, the lower stubble area and nasal-tip
region. Mask overlays were inspected. Gaussian differences at face-scaled sigma
0.6/1.5/4/12 measure four spatial bands. Native/finished use the **same** native
mask/scale to isolate the finish. Raw/native use separately detected anatomical
regions; they are not pixel-registered and geometry can confound that comparison.

[OpenCV filtering documentation](https://docs.opencv.org/4.13.0/d4/d86/group__imgproc__filter.html)
documents these Gaussian operations. This is not a pore detector or a realism score:
noise, freckles, creases and synthetic detail all contribute to band contrast.
No source photograph is being classified as genuine from these measurements.

Four tests pass: constant-image response, known blur reducing fine-band contrast,
constant exposure-offset invariance, invalid mask/scale rejection. The diagnostic
does not mutate input pixels.

## Measured result

Fine-band standard-deviation ratios, not a percentage of authentic pores:

| Scene | Raw -> native High | Native -> old finish | Native -> no-duplicate-smoothing finish |
| --- | ---: | ---: | ---: |
| Canyon |0.945652|0.896722|0.958193|
| House |0.958073|0.875660|0.943324|
| Third |0.801684|0.902205|0.970984|

House separately loses substantial subpixel-band contrast during native editing
(ratio0.571139); canyon0.974821 and third0.999659. The fine band is already mostly
present in canyon/house. These findings do **not** support blindly adding generic
texture/sharpening as the explanation or solution for all rendered appearance.

Diagnostic evidence:

- `work/upgrade-source-faithful-20260903/qwen-texture-band-diagnostic/`
- `work/upgrade-source-faithful-20260903/qwen-texture-no-smoothing-canyon/`
- `work/upgrade-source-faithful-20260903/qwen-texture-no-smoothing-house-third/`

## One controlled policy change, on the same three saved native images

`evaluate-upgrade-final-gaze.py --common-polish --native-high-skip-skin-smoothing`
sets only three redundant High smoothing controls to zero: `SKIN_TEXTURE_BLEND`,
`FOREHEAD_WRINKLE_BLEND`, `UNDER_EYE_TEXTURE_BLEND`. The existing experimental
mouth-lift/cheek-highlight overrides remain zero. Freckle cleanup, warmth, stubble,
eye definition, hair treatment and final gaze operation are unchanged. No new
generation, source-pixel transfer, sharpening or synthetic grain was added.

The new `upgrade_common_polish_policy.py` context manager restores module values
even on failure. Three unit tests cover default Low controls, High's exact control
set and restoration after error. The opt-in flag affects High only; all three
matching revised-Low PNGs are byte-identical to the previous finish. The original
public Low is also unchanged; “revised Low” remains a separate experimental label.

Low hashes:

- Canyon `760B15C0C57221F848FBBDEA45914BE35445E39A68368A721D8BDCA97F575394`
- House `E37C521F3F4EC68E550081D397D685867C76C59A646B9FE3877A793426C812E0`
- Third `DAFFA10AA7EC785BE9891EE5E5D2B91BB1C86C87279C0BCA817625BD928CE440`

Every scene's new output/audit/comparisons are under
`qwen-genuine-strong-{canyon,house,third}/finish-no-duplicate-smoothing/`.

| Scene | Final likeness | Source pose error | Mouth opening | Max horizontal gaze error |
| --- | ---: | ---: | ---: | ---: |
| Canyon |0.684060|2.834110°|0.003563|0.012160|
| House |0.761261|3.766623°|0.000154|0.013893|
| Third |0.805845|0.309617°|0.003400|0.008099|

Canyon's old finish was0.696216, so this small component refinement is not an
identity improvement there. Genuine-reference evaluation uses six held-out photos
for canyon/house and the existing five-reference exclusion set for the genuine
third. Closed-lip/horizontal-gaze checks pass and exterior-of-finish pixels remain
exact on all three. These do not override native failures or establish vertical
gaze, stronger beauty, or identity lock.

## Visual conclusion and remaining work

All three were inspected at full size, face crop and thumbnail. Removing duplicate
smoothing retains a little more fine texture. Canyon still has a rendered-looking
face/hair and loses likeness compared with Low. House still looks too tense and
inherits its source-pose error. Third retains some cheek fullness. The new finish
does not meaningfully resolve those central issues, so it is **not promoted**.
No extra smoothing/texture-transfer/sharpening sweep is justified by this test.

No GPU generation was queued this turn. The last native job was verified terminal
and both queues empty. Production main/High/Low/gaze modules, frontend extension
and public workflow retain the same hashes. Defaults remain Low, Phone on, Turbo
off. Full goal completion still needs a useful stronger expression/likeness balance,
a coherent generation policy for all three photographs and actual production/end-
to-end verification. This experiment only removes an unnecessary finishing loss;
it is not a substitute for that outcome.
