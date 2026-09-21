# Current workflow and model status

Last audited: **2026-09-04**

**PAUSED by Mitch, 2026-09-07: "lets pause this for now".** Stronger High remains
unfinished and experimental; this is a user-requested pause, not completion or
proof that the goal is impossible. All September 7 results and downloaded models
are retained. Both Comfy queues were empty and all research agents completed at
pause time. No further testing, downloads or automatic continuation should occur
until Mitch explicitly resumes. Production stays unchanged: Low default,
Phone ON / Turbo OFF. Start from the
[pause/resume note](../workflows/experiments/Upgrade%20High%20-%20PAUSED%202026-09-07/README.md)
when resuming. The investigation details below are historical, not active work.

**Resumed by Mitch, 2026-09-07: "git it done".** The September 4 checkpoint remains
preserved. A genuine-source native Klein control retained likeness without the
character LoRA (0.815 versus0.826 with it), but made skin harsher; removal alone
is not a successful High. The native stronger-beauty prompt improved skin but
changed eyes/brows and dropped likeness to 0.574, so it is rejected. The supported
existing-character fallback at0.9 **with its trained m1tch_person token** restores
0.826 likeness but suppresses most beauty changes; the weight-only preparation
was superseded without execution. The sole matched-token0.45 midpoint completed
at **0.774718** likeness, with modest brow improvement but coarser/dotted skin and
no clearly compelling stronger High. The native prompt/strength line is closed
after this controlled midpoint; none of these results is promoted. The compatible
BeautyGRPO investigation remains separate. Its first full-precision genuine-photo
pilot completed with 0.757 likeness (source 0.818), close head/pupil direction and
good whole-frame integration, but cosmetic-looking eyelid rims and no improved
smile. The sole prompt-only refinement gives a modestly warmer closed-lip smile
at 0.748 likeness, but dark eye rims remain. The fixed canyon check failed High:
likeness fell from0.753 to0.708 and skin/lid rendering became harsher without a
better smile. The causal adapter-off control preserves0.752 likeness but supplies
no compelling beauty gain. Correcting native T5 padding256 to the author's
default512 improves the beauty candidate only to0.716; dark eyelid rims, etched
skin and an unimproved smile remain. This corrected tested recipe is also not
accepted as High; it is not a bit-identical author-pipeline reproduction.
Mitch's verdict on source /256 /512: **"all of them look about the same"**.
This route is closed as insufficient High differentiation, not awaiting approval.
No further generation is queued; no production or three-photo success is claimed. Fourteen focused CPU
tests pass for the new correction and its safety guards. Production files remain
unchanged from the start of this resumed turn.

The separate base-Kontext explicit-feature test also completed and is rejected:
likeness is0.755352 versus source0.753158, but eyes, cheek/jaw shape and closed
smile remain essentially unchanged at full size and thumbnail. Its sole
prompt-only refinement permitted the requested feature changes with
nativeT5/seed/models/source fixed. Preservation succeeded, stronger beauty did
not. Eight focused offline tests pass. This closes that route without reopening
BeautyGRPO or Klein grids. No further jobs are queued. See the
[explicit-feature result and research gate](upgrade-high-explicit-features-2026-09-07.md).
Existing authorized downloads and the no-new-character-training constraint apply.
See [resumed investigation](upgrade-high-resume-2026-09-07.md).

Historical pause, 2026-09-04: the unfinished stronger-High investigation and
rejected PixelSmile probe are saved in
[Experiments — Upgrade High](../workflows/experiments/Upgrade%20High%20-%20PAUSED%202026-09-04/README.md),
with a checksum-verified code/settings/results checkpoint. No automatic resume
or additional generation is scheduled. Production stays unchanged: Low default,
Phone ON / Turbo OFF. The results below describe the saved work, not active work.

Current update: downloads are explicitly approved. PixelSmile preview is installed
and checksum-verified. Its first isolated, genuinely character-LoRA-free test
completed, but fails visual identity/expression review: enlarged/different eyes,
narrower nose, lost slight smile, and soft face. Five-reference likeness is
0.328812 versus genuine source 0.797263. The sole fixed-seed neutral-expression
control also completed and fails visually (likeness 0.365971). Expression score
zero does not restore the original face. This local PixelSmile configuration is
rejected, not promoted or expanded to three photos. This is not a stronger-High success.
Five CPU support-node tests pass. Only the owned idle 3090 worker was reloaded
to expose the experimental node; 4070 unchanged. No new training, dependency
changes, photo uploads or production recipe changes. Phone ON / Turbo OFF stay.

Latest user constraint: **no new character LoRA training**. Prefer a genuinely
character-LoRA-free full workflow; the existing character LoRA is allowed only
as an evidence-supported fallback. Saved `source_only` house/canyon/third runs
still used it at 0.9, so those runs do not demonstrate that it is necessary.
No production adapter was removed and no training started. Generic expression
adapters are distinct from person-specific character LoRAs.

The earlier three-turn download-approval blocker is resolved. Stronger High is
still **unfinished**, not blocked on that approval and not production-accepted.
See the [PixelSmile research and live evidence](upgrade-pixelsmile-research-2026-09-04.md).

Latest [shape plus CodeFormer composition](upgrade-shape-restoration-composition-2026-09-04.md)
is also rejected, not deployed. House has cleaner skin but an over-soft face,
weaker brows and an insufficiently improved closed expression (likeness 0.629029
versus CPU Low 0.737938). The identical policy aborts safely on canyon and the
genuine third because the geometry folds; neither produces a final candidate.
These are CPU component checks, not three successful live renders. Existing
Phone ON / Turbo OFF defaults and production implementations remain unchanged.
PixelSmile was subsequently downloaded and tested as described above; the
earlier shape-composition rejection is preserved. The complete stronger-High
objective remains unfinished.

Latest isolated [whole-face source-shape probe](upgrade-whole-face-shape-probe-2026-09-04.md)
is not promoted. Dense478-point mapping failed a fold check; the sole115-control
semantic-cage refinement passed and visibly changed lower-face proportions,
but retained the worried brow/serious smile. Equal existing skin/hair cleanup
did not make it a convincing stronger High (candidate likeness0.685309,
actual Low0.739620, equally finished unwarped control0.772648). Detailed background
survived; no invented teeth or obvious new halo. Rejection is visual, not solely
the score. No three-photo expansion, generation, cache release or public change.
This route is closed; the complete stronger-High objective remains unfinished.

2026-09-04 current source update: the [ParseNet hair-label repair](upgrade-parsenet-hair-label-bug-2026-09-04.md)
is implemented as Low v5. Actual installed-parser/Low/High CPU replay passes on
house, canyon and the genuine third, with exact agreement to the reviewed
corrected-mask evidence. Only the Low module behavior changes (neck17 -> hair13);
High's source docstring, the main report's historical comparison wording, and
active version/hash checks are updated. Generation,
PhoneON/TurboOFF, default Low, public workflow and UI are unchanged. An authorized
primary-worker reload and public-node house render verified the live v5 hair
repair. Raw pixels exactly match the historical sampling control; final Low is
not identical to the quantized CPU replay and was scored separately (0.739620).
No new visible hairline halo or background loss was found. This is narrow
hair-repair validation, not the complete stronger-High acceptance. Earlier
unchanged-hash statements below describe their historical experiment checkpoints.
The stronger-High objective is not achieved. The single masked source-geometry
reference correction completed (likeness0.788, detailed background), but eyes,
expression and skin remain too Low-like. It is closed as a stronger-High route,
not promoted. See [native result](upgrade-local-inpaint-research-2026-09-04.md).

The [installed CodeFormer preview](upgrade-codeformer-feasibility-2026-09-04.md)
cleans house skin at weight 0.7 (corrected full-frame likeness 0.719649 versus
Low 0.737938). The sole 0.4 refinement looks smoother and less defined, with
weaker brows and persistent cheek fullness (0.670791); it is rejected as High.
Neither result fixes the preferred source expression/shape, so neither is
deployed. Two follow-up scoring scripts were corrected to honor genuine JPG
EXIF orientation; saved candidate pixels and old audit records were preserved.
No further weight sweep or three-photo success is claimed.

A subsequent fixed-alignment input-stage diagnosis feeds the raw house render
directly to CodeFormer 0.7: likeness 0.744679 versus 0.719649 after Low. Cleanup
is less damaging without the stacked Low treatment, but still does not restore
the source's preferred expression or cheek shape. It is not promoted. The next
[native portrait-detail probe](upgrade-portrait-reference-detail-2026-09-04.md)
changes only the genuine portrait reference from 0.5 to 0.1 MP, keeping the
identity LoRA and all other native settings. Job
`ff61023b-21bd-4b3d-a02a-6d3b40ff7373` completed on3090/8188 in438.936seconds:
likeness0.726706, detailed background and closed lips, but tense brow/hooded eyes,
full cheeks and coarse skin remain too Low-like. It is rejected visually, not
solely on score/pose thresholds; no resolution sweep or production change.

The [background-only repair pilot](upgrade-background-detail-research-2026-09-04.md)
uses the earlier better source-preserving person as its protected edit target.
This tests whether the observed background softness can be repaired independently
of the face, not whether another face mask makes High more attractive. Its
reviewed CPU human-silhouette mask and native codec control use installed models
only. Job `a604aade-2954-4a16-aba0-bfb07dc141a2` completed on3090/8188 in367.623s,
but replaced the house with a waterfall scene and left a conspicuous halo.
Protected-person tone also changed (meanRGB9.616/255 versus codec); similarity
0.658 versus resized input0.689. It is rejected. No production/default change
or three-photo success. The sole concrete-background-reference refinement,
job `3cb18d51-fff0-4a5c-a757-8fbe272dc82f`, also completed and failed: invented
waterside setting, conspicuous halo, person tone shift. Saved source/final
latents prove protected-person equality to numerical precision (max5.96e-8),
while decoded person RGB differs8.129/255 from codec. This is not a mask-polarity
bug; latent anchoring does not guarantee final pixels. The route is closed.
No further background prompt/reference/mask/seed sweep or cosmetic finish on
these failed whole frames. The complete stronger-High objective remains open.

Upgrade High experiments: [identity scheduling](upgrade-identity-schedule-evaluation-2026-09-03.md)
is rejected after the sole timing refinement and equal final-finish comparisons;
recognizable faces still have coarse skin and tense expressions. The
[local Dev native-edit pilot](upgrade-dev-native-high-evaluation-2026-09-03.md)
retained about0.79 likeness and improved skin, but still failed eye/expression,
cheek-shape and source-pose requirements after its sole strength refinement.
It is not accepted as a High replacement. No production recipe/default changed and the stronger-High
three-photo objective is not yet achieved.

The subsequent [RefControl source-contour/self-reference test](upgrade-refcontrol-high-evaluation-2026-09-03.md)
is also closed as a stronger-High route (2026-09-04). The beauty prompt generated
a different-looking face with teeth (likeness0.245); its sole author-trigger-only
diagnostic recovered likeness0.764 and closed lips but retained Low-like eyes,
tense expression and coarse/dotted skin. It was not promoted. All results and
the exact one-variable comparison are retained; no further RefControl prompt/
weight grid is planned. Production PhoneON/TurboOFF and all six protected
implementation/UI/workflow hashes remain unchanged.

The [source-upper-lid TPS component](upgrade-source-lid-curve-evaluation-2026-09-04.md)
also remains unpromoted: fixed house/canyon tests achieve the requested tiny curve
changes and retain likeness0.775/0.755, but still look too similar to Low; house's
pupil diagnostic is above its existing bound. An earlier Gaussian pupil-core
prototype had the same visibility limitation. Both are closed as stronger-High
solutions; no further guard/curve strength sweep. Upper-orbit measurements also
do not support blanket crease smoothing. No production/default or GPU change.

The [iris/brow contrast component](upgrade-eye-definition-evaluation-2026-09-04.md)
was tested at one frozen strength on house/canyon (2026-09-04). It measurably
increases existing iris/brow definition and preserves all non-eye/brow pixels,
but the normal-size Low/High difference is still insufficient. Likeness is
0.757/0.741; source-smile, cheek-fullness and skin problems remain. It is closed
as a stand-alone stronger-High solution, not promoted. No lower-strength retry,
third-photo validation, production/default change or GPU generation is claimed.

The [native High alternate-seed diagnostic](upgrade-seed-variation-evaluation-2026-09-04.md)
completed on house (2026-09-04). Changing only seed8675416 to8675417 makes a
noticeable, more source-like face/eye/brow change, but likeness falls0.741 ->0.696,
skin/hair issues remain and PhoneON background detail still fails. It is not a
complete High or a production seed-selection policy. The labeled comparison was
shown for beauty/likeness feedback; no response is assumed. No more seed rolling,
third-photo claim, promotion or default change. Full three-photo goal remains open.

The matched [BF16 diffusion-weight diagnostic](upgrade-weight-precision-evaluation-2026-09-04.md)
also completed on house (2026-09-04): actual runtime BF16 was verified with the
same seed, prompts, references and adapters as that FP8 control. Likeness changes
0.696 ->0.701, but full-size and thumbnail review show no material fix for brow
tension, speckled skin, bundled hair or blurred PhoneON background. Closed lips
remain intact. This precision hypothesis is closed without further dtype/seed
rolling. No production/default change or three-photo success is claimed.

A [ParseNet label bug](upgrade-parsenet-hair-label-bug-2026-09-04.md) was subsequently
verified on all three photos: production v4's hair selector uses class17 (neck)
instead of class13 (hair). Old Low replay exactly matches house/canyon's saved
pixels. Corrected experimental masks select hair and keep other regions stable;
production repair/versioned integration was pending at that earlier checkpoint
and is completed in the v5 update above. Prior reports that
called the class17 region "hair" do not prove actual hair editing. This does not
explain or resolve every High/skin/expression failure.

The [first local masked High pilot](upgrade-local-inpaint-research-2026-09-04.md)
completed on house with actual BF16, PhoneON and TurboOFF. Its detailed background
is retained (native-vs-codec outside-region MAE0.186/255), similarity is0.766,
and lips stay closed. Eyes remain Low-like and the warmer smile adds cheek
fullness/lines; source pose/gaze are not fully preserved. It is not promoted.
The pilot does not receive the original source, only the drifted raw and genuine
portrait: the next correction is explicit source geometry/expression conditioning,
not a strength/seed grid. It is not prepared or submitted. The full two-photo/
genuine-third and end-to-end requirements remain open.

This file is the canonical current-state inventory. Workflow JSON, the linked custom-node code, and the
verification scripts are the implementation authority. Dated evaluation reports and checkpoint manifests are
historical evidence; words such as “current,” “production,” or “selected” inside those reports describe the
decision at that time unless their status banner says otherwise.

Fresh shipped-default runs of Identity v1.1, Group v1.1, and native Upgrade all passed on 2026-09-03. The exact
prompt IDs, output hashes, six-genuine-reference scores, leakage results, structure diagnostic, report invariants,
and visual checks are recorded in `docs/flux2-klein9b-production-revalidation-2026-09-03.md`. The frozen registry
tracks the three internal generation engines separately from the public v1.1 workflow surface.

The subsequent reuse review kept all three workflows separate and hardened only shared, non-generative plumbing:
manifest/path/hash validation, exact frontend/backend manifest parity, prepared-source geometry resolution, maintenance
checks, GPU-service preflight, reporting, and the specialized verifiers. The generation recipes and shipped defaults
were not changed. Rationale, exact conditioning roles, upstream references, and deferred v2 performance experiments
are recorded in `docs/flux2-klein9b-reuse-hardening-2026-09-03.md`.

The duplicate Identity and Group v1 sheets were then removed, Upgrade was promoted to a direct v1.1 public alias,
and the old v1 node names were removed from the public node registry. Fresh default runs through all three cleaned
v1.1 entries passed identity, leakage/duplication, structure, report, and full-size/thumbnail visual review. Identity
was pixel-identical to its prior accepted default; Upgrade's raw, final, and guide decoded hashes were exact; Group
kept identical inputs and guide with only `0.3196 / 255` mean CUDA/VAE variation. Exact evidence is in
`docs/flux2-klein9b-v1.1-production-cleanup-2026-09-03.md`.

## Visible Production workflows

| Workflow | Current role | Identity mechanism | Worker |
| --- | --- | --- | --- |
| `FLUX.2 Klein 9B Mitch Identity Studio v1.1 - Visual Presets` | **Default** new solo/full-body/lifestyle workflow; clickable scene gallery | Generation-locked internal engine: Klein Base 9B + protected V3 step-1600 identity LoRA + genuine native references + smartphone-realism LoRA at `0.25` | RTX 3090, port `8188` |
| `FLUX.2 Klein 9B Mitch Group Scene Studio v1.1 - Visual Presets` | **Default** source-matched group workflow; clickable layout gallery | Generation-locked internal group engine: face-interior-free Canny layout + protected V3 step-1600 identity LoRA + separate genuine identity photograph + smartphone-realism LoRA at `0.25` | RTX 3090, port `8188` |
| `FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1.1` | One-person upgrade; attractiveness Off / Low / High, default Low; phone style on | Unchanged generation path: four ordered native references + V3 step-1600 identity LoRA; Low retains face/iris/hair polish, optional High adds source-guided upper-lid and eye/brow refinement after gaze lock; Smartphone v13 at `0.25`; optional phone-off background finish | RTX 3090, port `8188` |
| `FLUX.2 Dev LoRA - 9 Dating Scenes v1` | Validated specialty workflow for the nine dating-scene templates or controlled scene restaging | FLUX.2 Dev + protected Dev V2 step-1000 LoRA; optional scene image is composition conditioning, not identity | RTX 3090 |
| `Dataset gen - QWEN 2511 - 3-photo` | Dataset-generation utility | Qwen Image Edit 2511 Lightning + multiple-angle LoRA | Local ComfyUI |
| `Train Generated Dataset - AI Toolkit` | Training submission/monitoring utility | AI-Toolkit durable job queue | Local AI-Toolkit |

The first four create or edit photographs. The last two are utilities and are not evidence that a generated
dataset or newly trained adapter is approved.

Upgrade High remains an optional subtle postprocess, not an accepted solution to stronger attractiveness.
Mitch found its Low/High difference too small and reported smile/cheek drift. See
`docs/flux2-klein9b-high-expression-investigation-2026-09-03.md` for the separate controlled tests;
the defaults remain Low, phone on, Turbo off.

Earlier experimental check: editing the original directly with local Qwen2511 and
one genuine identity photo did not solve High. Full strength lost likeness badly;
the one lower-strength refinement retained the original's more appealing presentation
but still produced rendered-looking skin/hair and blurred background. These are
explicitly **native phone-prompt-only tests**, not active/inherited smartphone LoRA.
Neither is promoted; production files/defaults are unchanged. Exact evidence and
the pending eyes/expression-only visual question are in
`docs/upgrade-qwen-high-evaluation-2026-09-03.md`.

The subsequent CPU brow/crease ablation was tested on canyon, house and a corrected
third-photo base. It preserves eyes/background exactly and reduces local frown-crease
contrast with97–99% measured fine-band retention, but the overall High effect remains
modest and the generation policy is not yet unified across those bases. It is NOT
promoted or production-validated. Evidence, caveats and the canyon landmark-detector
diagnosis: `docs/upgrade-brow-expression-evaluation-2026-09-03.md`.

The next CPU skin/eye checks rejected patchy added warmth and excessive eye
narrowing. A single no-narrowing contour refinement passes the horizontal gaze
check on all3 corrected baselines and preserves other regions, but stronger overall
beauty is still unproven. Small spot cleanup is not complete freckle removal.
These remain experimental; production/defaults are unchanged. Exact results,
failed variants and remaining limits: `docs/upgrade-skin-eye-contour-evaluation-2026-09-03.md`.

Latest native check: a compact High prompt retained likeness0.756 but introduced
teeth,8.81-degree source-pose drift and a softer background. Its one controlled
negative-conditioning refinement restored closed lips/source-like expression and
0.98-degree source pose, with a clearly stronger appearance change, but likeness
fell to0.422 versus raw0.752. It is an unaccepted tradeoff, not a fix. No further
grid or additional-photo generation was queued; production remains unchanged.
The comparison and complete conditioning/provenance evidence are recorded in
`docs/upgrade-compact-prompt-evaluation-2026-09-03.md`.

A subsequent read-only texture diagnosis found that the older two-reference Qwen
High retained most fine-band contrast on canyon/house, while its common cleanup
removed another10–12%. One High-only ablation skips duplicate skin/forehead/under-eye
smoothing; all3 revised-Low PNGs remain byte-identical and final fine-band ratios
improve to94–97% of native High. This does not fix rendered appearance, house's
tense expression/pose drift or third-photo fullness. Final likeness is0.684/0.761/
0.806. Nothing is promoted and no generation was queued. See
`docs/upgrade-texture-finish-evaluation-2026-09-03.md`.

The active three-photo repair effort is tracked in `docs/upgrade-source-faithful-plan-2026-09-03.md`.
The latest bounded fallback registers and blends the two existing generated canyon
faces, preserving the raw background/hair rather than pasting genuine photo pixels.
Amount0.4 gives a more source-like closed smile/eye presentation and likeness0.677;
the sole0.3 refinement reaches0.699880 but reduces visible separation from Low.
Mitch chose stronger beauty while remaining recognizable, so0.4 was frozen for the
house generalization test, with phone on/Turbo off. The completed house blend
scores0.758 but stays too similar to Low, retains the tense brow expression and
has3.53-degree source-pose error. This route is not a reliable cross-photo fix;
no third-photo render was queued after that failure. This is an experimental
composite, not an identity lock or shipped High, and freckles/creases remain unresolved.
See `docs/upgrade-registered-blend-evaluation-2026-09-03.md` for exact scope and results.

A subsequent isolated identity-LoRA strength test (0.9 ->0.6, all four references
unchanged) did not improve the house expression: likeness0.741 ->0.705, nearly
unchanged brow/smile and a soft background. That strength hypothesis is closed;
no strength grid or production change follows. A separately labeled angle-matched
genuine reference3 test at the original0.9 strength improves likeness to0.765 and
keeps closed lips, but still retains a tense expression and soft background.
Its empty numeric failure list is not a visual pass; neither route is promoted. See
`docs/upgrade-identity-strength-evaluation-2026-09-03.md` for the provenance,
controlled differences, reference tooth-line caveat and acceptance conditions.

A motion-only LivePortrait experiment avoided decoder-texture pasteback by using paired
reconstructions only to estimate a2D flow, then remapping the detailed raw's own pixels.
Seven CPU mapping tests pass. Canyon full-strength motion was too small; its sole2x
refinement made the closed smile more asymmetric at likeness0.688 (raw0.752), with exact
background/hair preservation. The same2x recipe fails on house: the analysis reconstruction
opens the mouth and changes gaze, and the flow consistency guard aborts before native RGB
remapping. No house final or third-photo inference, no production promotion and no further
strength grid. See `docs/upgrade-expression-flow-evaluation-2026-09-03.md`. The score near0.69
is not by itself a rejection; the failure is cross-photo expression reliability.

The next semantic-control calibration also fails house: the author smile/brow/lip controls
plus a bounded local solve predict improvements that the decoder does not deliver. A sole
close-only refinement still worsens measured expression-target error; no native final RGB.
Six formula/solver tests and seven map tests pass but do not establish image quality.
See `docs/upgrade-semantic-expression-evaluation-2026-09-03.md`. No further slider grid.

A native Klein4-reference follow-up also fails visually: editing the detailed raw with
an exact original-expression crop as slot2 retains likeness0.754 and background detail,
but adds coarse skin, speckles and creases without fixing the tense expression. The
sole controlled refinement removes only the SECOND phone adapter application, retaining
the PhoneON upstream raw. It scores0.759 but looks similarly rough and keeps3.75-degree
original-source pose error. No canyon/third repeat, further phone grid or promotion.
The repeated-phone explanation is unsupported for this route. See
`docs/upgrade-native-expression-reference-2026-09-03.md` for exact graph/provenance
verification and completed visual review. Public defaults and production hashes remain
unchanged; stronger High is still not fixed or validated across all three photographs.

Removing the identity portrait failed likeness; adding sparse expression contours produced visible
teeth and was rejected. A separate native-generation High identity-presentation test also produced
teeth/hair drift and was rejected despite good identity scores. Stronger CPU retouch has not solved
the expression problem. LivePortrait zero-motion reconstruction lost visible fine detail; native second
passes and focused crop variants did not deliver acceptable skin/expression quality. These are rejected,
not production improvements. Replacing the tense frontal identity reference with a calmer genuine
photograph preserved likeness but did not materially improve the expression. Both standard non-Lightning
Qwen2511 native beauty edits failed likeness/realism and were rejected; see
`docs/upgrade-qwen-high-evaluation-2026-09-03.md`. Selective CPU crease repair retained likeness but did
not sufficiently improve the expression. Source-relative coupled expression geometry passed local deformation
and final horizontal-gaze checks, but failed the third-photo review: the base generation already moved the head
and opened the lips, and High remained too subtle. The evaluation now checks the actual source and absolute
closed-lip requirement instead of allowing an already-broken generated baseline to pass. A single documented
source-latent-retention diagnostic produced a visibly stronger change but only0.636 likeness versus0.752
raw, outside the existing diagnostic gate. It is awaiting exact visual tradeoff review, not approved;
no further sweep is queued and none of these experiments has been promoted.
Mitch explicitly prioritizes a stronger beauty edit for High, with a modest likeness tradeoff provided
the result remains recognizably him. Low remains the conservative option.
These experiments have not changed the public workflow or constituted three-photo validation.

The third genuine photo's separate base-fidelity test now succeeds with one native source reference plus
the same identity/phone LoRAs: source pose error0.154degrees, likeness0.825638 against five independent
genuine photos, closed lips and original scene/framing retained. The earlier four-reference run had
10.690degrees of source-pose drift. This validates a better treatment for an already-correct genuine face,
not a finished universal routing rule or High. No production change has been made. Stronger High's
appearance/likeness tradeoff and integrated three-photo/end-to-end verification are still outstanding.

The experimental Qwen0.35 stronger edit and complete common-polish/gaze finish have now been evaluated
on canyon, house and the corrected third base. Final likeness0.653/0.732/0.784; selected dark-dot contrast
reduced60–71%, closed lips retained, final gaze diagnostics improved, and finish-exterior pixels remained
exact. This is **not** three-photo acceptance: canyon loses likeness, house's expression change remains
restrained, and third retains some added cheek fullness. These saved comparisons use an experimental
revised Low without forced mouth lifting or cheek highlighting; public Low/High and defaults are unchanged.
See the Qwen evaluation document for native results, complete-finish audits and remaining limitations.

A newer bounded two-reference Qwen test adds one verified genuine training portrait during the High
edit. Its frozen stronger-prompt recipe now yields finished likeness0.696/0.761/0.805 on canyon/house/
third, with closed lips and final source-gaze checks retained. This improves the earlier identity tradeoff
but is not promoted: canyon still misses the conservative likeness diagnostic, house retains its base's
tense expression/source-pose drift, and third's cheek fullness needs visual judgment.
A true single-source Klein house base now retains source pose within 0.911 degrees and improves source
mouth-shape error, but scores 0.691 likeness. The same fixed High on that base finishes at 0.688 versus
matched revised Low 0.684, with 2.536-degree source-pose error and closed lips. Its source eye/mouth
presentation is closer than the old-base High, but Low/High remain relatively close and the original
soft background persists despite phone being on. It is not a production replacement. The comparison
has been shown to Mitch. The original-canyon source-only check is also complete: likeness 0.688,
source-pose error 4.605 degrees, and an undesirably soft background. It fails as a universal base
replacement and is preserved without applying High. This is not the earlier three-reference
no-portrait canyon experiment; the master plan distinguishes them.

The next bounded native Qwen test retains the accepted detailed house base and adds the original
source as its documented optional third input for head direction and expression. Genuine identity
remains a separate verified training portrait; original-source identity influence is explicitly
unisolated. This test changes conditioning, not the fixed High strength or production defaults.
Its author evidence, exact roles and guards are in the Qwen evaluation document. The 0.35 run
completed with final likeness 0.761 but still insufficient expression change. Its single full-native
refinement made the beauty edit more visible and retained 0.754 native likeness, but produced
overly uniform skin and a bottom-edge artifact, with source-pose error 3.619 degrees. That result
is rejected without postprocessing. Neither is promoted, and no further denoise grid is queued.

The subsequent zero-diffusion Qwen codec check retains the base's texture and does not reproduce
the bottom-edge strip. The large smoothing/border failures therefore appear after encoding; their
exact denoising cause is not established. One same-recipe 40-step diagnostic (model-card setting,
versus the Comfy note's 20-step pilot) completed as `31d76126-4ea8-4cf8-9524-2fba4c61f8f9`:
0.750 likeness, but the same smooth skin and bottom strip. More steps did not fix the failure.
A separate source-code diagnosis found odd reference latent edges padded circularly by the native
packing path, unlike the author's aligned reference sizing. The isolated native-node packing test
completed: the strip disappeared and likeness rose to0.782525. This is a technical improvement,
not a finished High: smoothing/tense brow and3.376-degree source-pose error remain. The one focused
negative-text refinement is complete: more texture but also more freckles, without a satisfactory
expression improvement. Its common-polish/gaze finish scores0.748471 versus revised Low0.770816;
closed lips and improved gaze, but3.138-degree source-pose error and artificial facial texture remain.
It is not promoted; no further prompt grid is queued. The three-photo/production goal remains unfinished.

## Installed LoRAs to keep

Ten LoRA files are currently retained:

| LoRA | Current reason to keep |
| --- | --- |
| `m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors` | Current Klein 9B Identity, Group, and Upgrade workflows |
| `smartphone-snapshot\FLUX.2-klein-base-9B_SmartphoneSnapshotPhotoReality_v13.safetensors` | Accepted subtle realism layer for Identity and Group; visually accepted deep-focus default in Upgrade, with its automated tradeoffs documented |
| `flux2-klein9b-turbo\Flux_Klein_9b_Turbo_lora_rank_256_bf16_standard.safetensors` | Validated default 8-step acceleration for Identity Studio and optional speed experiment in Group; rejected for Upgrade quality |
| `flux2-dev-identity-v2-candidates\m1tch-flux2-dev-identity-v2-s1000.safetensors` | Current FLUX.2 Dev dating-scenes workflow |
| `aitk\m1tch-flux2-klein-4b-identity-v1-best.safetensors` | Accepted One Reference/Easy Social rollback |
| `aitk\m1tch-flux2-klein-4b-identity-v3-portrait-profile.safetensors` | Validated Klein 4B portrait/profile specialty adapter |
| `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` | Qwen dataset utility |
| `qwen-image-edit-2511-multiple-angles-lora.safetensors` | Qwen dataset utility |
| `krea2_identity_edit_v1_2.safetensors` | Archived no-character-LoRA Krea2 fallback |
| `krea-smartphone-photo-slider.safetensors` | Archived Krea2 fallback camera appearance |

Protected custom LoRA hashes:

- Klein 9B V3 step 1600: `D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC`
- Smartphone Snapshot Photo Reality v13: `1E0B419B1448F77CF7AEF430625325E46B16D1515CBF6C5C7E8C14D938CF1A90`
- Klein Base 9B rank-256 BF16 Turbo: `A3BFA40E936AF059C2D0814DE8E9E5531FA0EB135087ADD22C27510685585600`
- FLUX.2 Dev V2 step 1000: `7C0C4F1726189C51E19C8392C12FE3E03A26BD084FFFB8D84B907C966A77CC3E`
- Klein 4B V1 best: `8A7D1477914D0A5262BF219F71F303418130449841CF220226B4E979D7232F87`
- Klein 4B V3 portrait/profile: `C43D7C1FCA404A8B316A9D0C8756E140033E4763532628F62FACC791F0B8A149`

All four Mitch-trained keepers are also versioned through Git LFS under `checkpoints/loras/mitch`. The Qwen and
Krea2 files are third-party dependencies and remain installation-only.

See `docs/lora-cleanup-2026-09-01.md` for the removed families and disk totals.

## Archived and rejected routes

The following are not normal-use Production workflows:

- Easy Social Photos and One Reference Photo are exact, recoverable 4B rollbacks under
  `checkpoints/legacy-workflows/production`.
- Krea2 Identity Edit/Identity Anchor graphs are archived fallbacks, not the current primary workflow.
- ReActor, masked host replacement, native no-LoRA, HiDream-O1, InfiniteYou, Z-Image identity training,
  non-selected 9B LoRA versions, and Krea2 character-LoRA experiments remain historical evidence only.
- Retired launchers, configs, and templates are under `checkpoints/legacy-scripts` and must not be run in place.
- Failed or superseded LoRA weights were deleted. A historical report saying a rejected weight “remains
  preserved” is superseded by the 2026-09-01 cleanup record.

## Acceptance rules that still apply

- The v1.1 Identity and Group galleries are thin interfaces over unchanged generation-locked internal engines. Their labels,
  prompts, thumbnails, recommended identity profiles, group source assets, and target geometry come from the single
  canonical `web/assets/scene-presets/manifest.json`. Prepared Identity presets enforce their recorded reference
  profile on the backend; custom prompts retain the user's explicit profile selection.
- The three Klein 9B production workflows expose a `Visible flattering enhancement` prompt-conditioning toggle.
  Identity Studio and Upgrade open with it enabled. Group Scene opens in the separately validated identity-first
  natural-appearance mode; its optional enabled clause is short and rendering-only. The toggle never switches models
  or references.
- Identity Studio and Group Scene automatically load Smartphone Snapshot Photo Reality v13 after the identity LoRA at
  strength `0.25` and prepend its trained `casual snapshot` trigger. It is third when Turbo is active. Upgrade loads it
  by default when `Phone-camera realism` is on; its optional phone-off path uses the separate natural-lens background finish. The
  isolated same-seed 4070 A/B improved
  held-out identity centroid from `0.7891` to `0.8100` and weakest-view similarity from `0.6711` to `0.7029`, with
  a subtle realism gain and no visual hair or sharpening regression. This layer is independent of the appearance toggle.
- Identity Studio and Group Scene expose the reversible Fast Turbo control. Identity Studio opens with its validated
  8-step / CFG `1.0` route; Group defaults it off because selected-main identity fell `0.5958 → 0.5672`. Upgrade does
  not expose Turbo: its clean phone-style-off retest was `9.54×` faster, but polished identity fell `0.7662 → 0.6958`,
  yaw moved `+1.6934°`, and background micro-luma detail fell `11.9536 → 4.5229`. Evidence is under
  `work/flux2-klein9b-upgrade-safe-polish-20260902/clean-turbo-ab`.
- The current Upgrade acceptance run uses the restored four-reference 50-step whole-frame path and deterministic v4
  face/hair-interior polish. Sparse local-median dot removal reduced fixed-threshold dark facial dots `35.9%` versus v3,
  while existing-luminance-guided hair highlights added only `1.32 / 255` mean active-hair lift. Final gaze-locked identity
  is `0.7476` (`strong_match`) with a `0.5546` weakest view above the `0.5533` genuine floor. Protected pixels remain exact,
  and the detailed siding/tree, forehead, and three-quarter direction remain intact. It has no source-latent passes,
   generation masks, Turbo, face swap, restoration, or second model pass.
- Upgrade's report schema is now v2. Picture 3 plus the protected LoRA are the explicit identity mechanism. Picture 1
  is intended for scene, pose, expression, clothing, lighting, and composition, but it contains the source face and is
  encoded as a `ReferenceLatent`; its identity influence has not been isolated and must not be described as absent.
- Upgrade defaults to the accepted deep-focus Smartphone v13 phone rendering. Turning phone style off optionally applies
  a deterministic natural-lens finish after the full detailed render. A hash-locked local
  U2Net human matte excludes subject colors from normalized near/far Gaussian filters, uses a dilated safety rim, and
  copies protected subject pixels back exactly. On the accepted `1680×1008` v4 frame, `64.4717%` of the background was
  softened with `0 / 255` maximum protected-subject error and no visible cutout halo. Phone-on skips this stage and
  preserves the accepted crisper Smartphone v13 rendering.
- Upgrade's default handsome-polish path now also locks pupil direction to the source using MediaPipe refined iris
  landmarks and a bounded iris-interior warp. The accepted prototype reduced horizontal gaze error `74.1%`, changed
  only `0.0948%` of frame pixels, kept all eyelid/outside pixels exact, and retained `0.7508` six-photo identity with
  negligible pitch/yaw/roll change. It copies no source pixels and does not rerun the diffusion model.
- Separate 4070 rollout smokes passed both production Canny mechanisms. Group identity improved `0.5603 → 0.5626`
  on the established six-photo group gate with no bystander leakage; Upgrade identity stayed `strong_match` and
  improved `0.7575 → 0.7739`, while skin/sharpening metrics remained stable and source geometry was retained. Exact
  graphs and reports are under `output/smartphone-snapshot-klein9b-production-rollout-4070/20260901-210410`.
- Visual review found the first styled Group face too broad, but the attempted detailed skull/proportion lock made the
  internal face more generic and reduced six-photo likeness to `0.5465`. A controlled same-seed 3090 diagnostic kept
  the Canny guide, genuine reference, protected identity LoRA, Smartphone Snapshot v13 at `0.25`, and all sampling
  settings while restoring the concise approved identity prompt. Likeness rose to `0.6007`, above the original
  approved frame's `0.5946`; four faces remained distinct and every leakage gate passed. Group therefore defaults to
  the concise identity-first prompt, not exact-skull or best-day feature-editing instructions. Identity and Upgrade
  retain their separately accepted appearance behavior. The reloaded production Group node then reproduced the fix at
  `0.5958` with maximum bystander identity `0.3026` and no gate failure; exact evidence is under
  `output/group-identity-correction-3090/20260901-220033`.
- The final best-day controlled solo result passed the held-out identity gate on 2026-09-01 at `0.8106` centroid
  and `0.6156` weakest-view similarity, ranking above the enhancement-off baseline. It permits small same-person
  improvements to bone structure, expression, pores, stubble, and apparent age in addition to tan and fine-line
  treatment. See
  `docs/flux2-klein9b-appearance-polish-evaluation-2026-09-01.md`. A new scene still requires review at full size
  and thumbnail.
- The enabled expression uses closed-lip geometry rather than the word `smile`: a slight confident corner lift, one
  unbroken lip line, and every tooth behind the lips. The same-seed straight-on acceptance frame scored `0.7897`
  centroid and `0.6175` weakest-view similarity with no visible teeth and natural eye catchlights.
- Automated face similarity is a ranking and rejection diagnostic, not proof of identity.
- Full-size and thumbnail visual review remains mandatory.
- Use genuine photographs for identity evaluation.
- A scene/style reference is not automatically an identity reference.
- Do not add face swap, masks, restoration, relighting, or sharpening without a measured failure and acceptance test.
- Inspect both GPU queues before generation and never interrupt active training or generation.

## Verification

Run the repository verifier before check-in:

```powershell
.\scripts\verify.ps1
```

The specialized read-only workflow verifiers are:

```powershell
.\scripts\verify-flux2-klein9b-mitch-identity-studio-v1.ps1
.\scripts\verify-flux2-klein9b-group-scene-studio-v1.ps1
.\scripts\verify-flux2-klein9b-upgrade-photo-detail-realism-v1.ps1
```

Do not pass `-Smoke` during routine verification; that option queues a generation.
