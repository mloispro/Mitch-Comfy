# Results that should guide the next change

These are bounded conclusions from the linked reports, not freshly repeated experiments.
Preserve their original acceptance rules and cohorts. New evidence can justify a new prospective test;
it must not silently rewrite an old failure. Search [all evidence](generated/EVIDENCE-INDEX.md) for other routes.

## Solo and public behavior

| Observation | Consequence for future work | Evidence |
| --- | --- | --- |
| St. Barts original pose: user repeated the request after approximate native edits. Direct foreground composition now preserves person interior and entire hands/legs/rails/boat region with zero RGB error. Final .5380/.4211 near_match inherits the original's qualified likeness | Preserve original foreground pixels when this exact pose is required. Saved final PNG/deterministic composition provide it; gallery text and earlier native source-edit workflow do not guarantee exact preservation. Empty-background generation fixed a local-inpaint halo; retain failures and avoid more pose-generation grids | [September 20 exact foreground result](../work/st-barts-exact-foreground-20260920/RESULT.md) |
| Downtown and Kitchen have qualified holdouts; several other named scenes have one-image passes; other scenes fail or remain uncertain | Reuse a proven scene-specific recipe as the control. Avoid calling all scenes ready or globally swapping references | [Coverage matrix](../work/9b-readiness-resume-20260907/COVERAGE-MATRIX.md) |
| Public Cocktail passed likeness diagnostics but failed teeth/gaze. Completed source comparison finds unchanged public resolution/engine, with three differing variable groups versus accepted Speed: references, surrounding prompt and diffusion precision | Use the completed Speed handoff for this exact case. No isolated cause or wrapper defect is established; pasting the three-reference prompt into the two-reference preset cannot reproduce it | [Public result](../work/9b-readiness-resume-20260907/public-cocktail-parity/ROOT-RESULT.md), [comparison](solo-cocktail-comparison-2026-09-21.md) |
| Removing the lake appearance block decreased five of six comparisons and supplied no clear visual gain | No evidence for globally disabling appearance to fix skin/identity | [Lake refinement](../work/9b-readiness-resume-20260907/solo-lake-natural/ROOT-RESULT.md) |
| Cat crop refinement added a paw; night square diagnostic added an arm and still clipped hands | Better likeness or wider framing cannot waive anatomy failures; no further blind prompt/seed sweep of these recipes | [Coverage and exact result links](../work/9b-readiness-resume-20260907/COVERAGE-MATRIX.md) |

## Group

| Observation | Consequence for future work | Evidence |
| --- | --- | --- |
| Regional 0.90 pilot reduced bystander similarity but weakened main identity; partial fifth person was lost | Runtime success and bystander success do not make this a valid image | [Completed pilot](../workflows/experiments/group-masked-pilot-resume-20260908/ROOT-RESULT.md) |
| Sole 1.10 refinement improved centroid .5225→.5557, but weakest reference remained .4005 and edge-person preservation failed | Strength-only refinement is closed for this recipe. Face-mask interior was already 1.0; missing face coverage is not the established cause | [Refinement and mechanism limits](../workflows/experiments/group-masked-strength110-20260908/ROOT-RESULT.md) |
| Regional mixing shares full-frame latents and is not identity-token attention isolation | A future mechanism must explain main identity retention and secondary-face independence; do not rename this failed mixture an identity lock | [Mechanism diagnosis](../workflows/experiments/group-masked-pilot-resume-20260908/ROOT-RESULT.md) |
| Inspected Klein feature-transfer masks reference tokens but applies transfer across generated tokens; no output-person isolation | Candidate is not admitted for the current Group failure. Source hook availability does not establish current-stack runtime or photo compatibility | [September 21 input/mechanism gate](high-group-gate-2026-09-21.md) |
| Explicit-layout regional V3 passes CPU and real FP8 execution, but its one image lowers main centroid .613633→.539730 and minimum .457710→.433664; bystander limits pass | Reject this exact recipe. Direct delta locality does not preserve identity or freeze bystanders. A new mechanism must retain main identity and explain secondary independence before another image; no automatic strength/seed grid | [Token-delta image, exact scoring replay and visual result](../work/group-token-pilot-20260921/RESULT.md), [CPU proof](../work/group-lora-token-gate-20260921/RESULT.md) |
| Dual-context asymmetric routing passes CPU/CUDA/full9B FP8 isolation and all60 image forwards. Main centroid .636146 and minimum .509190 improve over both earlier controls, but three genuine comparisons still fail and an extra head has no coherent body | Reject the exact photo recipe. Bystander similarity passes even for the extra head, so numerical independence cannot accept anatomy. Diagnose text/context/region interaction before another image; no automatic seed/strength sweep or production installation | [Executed recipe, exact control replay and visual rejection](../work/group-dual-context-pilot-20260921/RESULT.md), [mechanism proof](../work/group-dual-context-gate-20260921/RESULT.md) |
| Sole separate-scene-text refinement removes the extra head, but introduces leg/table interpenetration; main centroid falls .636146→.553841 and minimum .509190→.452120. All six genuine comparisons fail; bystander diagnostics pass | Close this exact routing/text recipe. Scene context affects composition and main identity despite outward isolation; removal of one defect is not photo acceptance. No further prompt/seed/strength, mask/resolution or postprocessing sweep | [Spatial diagnosis,19 CPU tests, actual FP8, image and three exact control replays](../work/group-region-text-pilot-20260921/RESULT.md) |
| Mitch rejects both UMO images for the oversized-looking head and unnatural, pasted-on face. Offline comparison finds raw main-face boxes enlarged 20.97%/9.44% in width versus the source; input sizing has no comparable direct stretch. Earlier reviews understated the decisive proportion/integration failure | Close the tested route. The initial visual failure should have stopped the trial before stronger guidance. The shared image-guidance coefficient is not an independent head-scale/lighting control. No further guidance/prompt/seed/resolution or finishing sweep; keep raw/converted adapter and failed evidence | [User rejection](group-umo-visual-rejection-2026-09-21.md), [raw-image and mechanism diagnosis](group-umo-failure-diagnosis-2026-09-21.md), [source/load gate](../work/group-umo-gate-20260921/RESULT.md), [refinement and exact replay](../work/group-umo-guidance3-20260921/RESULT.md) |
| Qwen 2.1 provides a distinct released grounded-vision/latent editing path; its required nodes are visible on an isolated CPU core. No weights loaded or image generated | Compatibility is established only through source and schema. Neither author claims nor an available runtime prove natural proportions or face integration. Keep UMO closed; a future first image must face visual rejection before likeness diagnostics | [Compatibility gate, exact pins and remaining limits](qwen21-compatibility-gate-2026-09-21.md) |
| Later training reassessment corrects the "two small-face full-body photographs" explanation: surf is cropped near upper legs; sleeveless mirror has a large face but upper/waist framing | Inspect actual framing before using coverage as a training rationale. No clean head-to-toe coverage in those two photos; no new training authorization or proven sole cause | [Corrected reassessment](../work/9b-readiness-20260903/REASSESSMENT-20260904.md) |

## Upgrade

| Observation | Consequence for future work | Evidence |
| --- | --- | --- |
| Source-preserving QUALITY50 reproduced one genuine-photo case: .817792 centroid versus source .825853; Turbo8 .804167 with smoother skin | Useful qualified source-preservation controls. Neither is stronger High, LoRA-free, a universal enhancer or equivalent to public four-reference Upgrade | [Quality](../work/9b-readiness-resume-20260907/upgrade-source-faithful-option/ROOT-RESULT.md), [Turbo](../work/9b-readiness-resume-20260907/upgrade-source-faithful-turbo/ROOT-RESULT.md) |
| Second genuine-source Turbo test passes: balcony val05 .787830 centroid, source loss .022217, pose drift1.188 degrees; native/thumbnail review retains source with smoothing/detail regeneration | Two genuine-source observations now support bounded preservation. No universal enhancement, improved identity or stronger High claim; all five source-excluded comparisons remain | [September 21 result](../work/upgrade-generalization-20260921/RESULT.md) |
| Native stronger beauty prompt hurt identity; corrected character fallback/midpoint did not produce compelling High. BeautyGRPO/T5 correction and explicit-feature Kontext refinement also failed their High goals | Do not restart the same strength/prompt/adapter grids without a new causal reason | [September 7 investigation](upgrade-high-resume-2026-09-07.md), [explicit features](upgrade-high-explicit-features-2026-09-07.md) |
| PixelSmile candidate and neutral-expression control failed identity/visual review | This tested configuration is rejected; a zero expression score did not restore the source face | [PixelSmile evidence](upgrade-pixelsmile-research-2026-09-04.md) |
| CodeFormer softened/changed face without fixing the target expression; shape/CodeFormer composition folded on other sources | Do not add restoration or geometry stages to hide a failed generation mechanism | [CodeFormer](upgrade-codeformer-feasibility-2026-09-04.md), [composition](upgrade-shape-restoration-composition-2026-09-04.md) |
| Background repair changed scenery, created a halo and failed preservation. Protected latent values did not guarantee unchanged decoded RGB | Judge actual source/codec-relative pixels and whole-frame integration; edge count is not recovered detail | [Background investigation](upgrade-background-detail-research-2026-09-04.md) |
| LaTo predictor attempts moved/resized facial geometry | Route closed for this source; downloaded assets do not establish a working image-edit pipeline | [Final predictor failure](../work/9b-readiness-resume-20260907/lato-compat/ROOT-FINAL-PREDICTOR-RESULT.md) |
| PerformRecast author-aligned512px zero-motion reconstruction completes and passes six-reference diagnostics (.747549 centroid; .004246 source loss), but softens native skin/hair detail | Reject this exact recipe before expression transfer. Different training/input geometry did not meet the detail gate on this source; no sharpening workaround or automatic sweep. Keep five isolated weights (0.941GiB); High remains unresolved | [Pinned mechanism, runtime, original-score replay and visual decision](../work/high-performrecast-gate-20260921/RESULT.md) |
| MirrorPPR has a distinct trained operation-pair/query-photo mechanism, but its inspected public Face release has eight simulated eye/nose/mouth operations; jaw/face-shape and smile belong to the professional taxonomy | Conditional candidate, not an image rejection. No accessible Pro checkpoint was established in inspected author listings; HTTP401 alone is inconclusive. Require author-supported full-task capability, exact runtime compatibility and a suitable operation pair before downloading or generating. No eye-only stand-in for full High | [Pinned source, release and local compatibility gate](../work/high-mirrorppr-gate-20260921/RESULT.md) |
| Author's actual predictor example is unannotated; fresh hashes find the same 55 known stills and no admitted external expression target | Adding overlays is not an evidenced repair. External driving is a distinct author-supported but locally unexecuted mechanism; do not repair failed coordinates | [September 21 input/mechanism gate](high-group-gate-2026-09-21.md) |
| ParseNet hair-class 17 was wrong; class 13 correction is current Low v5 and had a live public-node check | Retain the precise regression check; don't describe current v5 as unchanged v4 | [Hair-label repair](upgrade-parsenet-hair-label-bug-2026-09-04.md) |

## Speed and evaluation

| Observation | Consequence for future work | Evidence |
| --- | --- | --- |
| Existing likeness CLI now reuses raw detections within one invocation: six-reference/two-candidate case fell from 14 to 8 actual inferences. Three paired runs measured median 5.619→4.942s (12.1% less instrumented process time). A separate five-reference source-excluded case fell from 12 to 7 calls, 5.328→4.805s | Implemented in the existing tool. All four pairs matched raw Face records, normalized embeddings, raw cosines and complete JSON bytes exactly. Same CPU-only providers; no image-generation speed or total-development claim. Group-specific evaluation and skin diagnostics are unchanged | [Measured results](../work/face-likeness-cache-20260909/results.json), [declared schedule and inputs](../work/face-likeness-cache-20260909/plan.json), [implementation](../scripts/evaluate-face-likeness.py), [focused tests](../scripts/test_face_likeness.py) |
| Earlier feature-reuse pilot preserved exact diagnostics and saved 9.093s in one instrumented CPU observation (15.382→6.289s) | Its broader cross-tool sharing remains a candidate. The new narrower within-CLI integration above has its own measurement; do not transfer the pilot's 59% figure to it | [Pilot](../work/9b-readiness-20260903/evaluation/feature-reuse-pilot/RESULTS.md) |
| Follow-up covers actual Group/Upgrade raw-feature replay while retaining caller-specific selection/exclusions and review sheets | Reuse raw face features only; keep separate selectors, cohorts, calibrations and acceptance rules | [Coverage proof](../work/9b-readiness-20260903/evaluation/feature-reuse-coverage/RESULTS.md) |
| September 9 Group forward cache completed all three matched pairs: 24.5–26.2% less worker time with relative likeness and visual preservation; subsequently integrated as a separate normal-worker Speed node | Use Production Speed Lounge on3090/8188 within its fixed scope. New normal-Run pixels match the accepted cached seed; confirmations are complete. It does not improve identity, validate new scenes, or change production defaults; minor clothing details can change versus uncached | [Matched results](../work/group-cache-20260909/RESULTS.md), [rollout](../work/production-speed-rollout/RESULTS.md), [original visual review](../work/group-cache-20260909/VISUAL-REVIEW.md) |
| Individual Cocktail, source-preserving Upgrade Turbo and Group Lounge now have separate ordinary Comfy workflows and actual normal Run-button checks | Preserve original production. Use only the published bounded recipes and their recorded acceptance. Individual is not a new measured production speed win; Upgrade's historical6x compares experimental50/8 on4070, not public production. Experiment visibility is curated without deleting evidence | [Production Speed rollout](../work/production-speed-rollout/RESULTS.md), [guide](production-speed.md) |

## Acceptance and development

The September 21 [cleanup decision](CLEANUP.md) preserves all unique and unresolved
model dependencies and recorded evidence. Twelve duplicate staging weights (61.638 GiB)
were removed after exact-path dependency review and fresh full hashes against retained
installed copies; the restore manifest records both sides. A tested failure
closes that recipe; it does not prove that every unexecuted stage or alternative is
finished. LaTo, High and general Group therefore remain explicit holds. The bounded
Solo source comparison and second-source Upgrade validation are now complete; retain
their accepted bounded handoffs. Actual St. Barts gallery interaction also passes.
The [final disposition](../work/final-validation-20260921/DISPOSITION.md) confirms
LaTo image stages are unexecuted and all 15 unique weights stay. Do not reopen failed
grids or describe unresolved High/Group features as achieved to justify cleanup.
This completed audit authorizes no further path removal.

The [acceptance clarification](../work/9b-readiness-20260903/ACCEPTANCE-CLARIFICATION-20260904.md)
corrects confusion between a usable photo and a visibly better photo than a control. Preserve the
requested outcome and regression requirements before a trial. A diagnostic score, technically valid
checkpoint or passing code test answers its own question; it does not establish the requested photo.

The [documentation checker](../scripts/project-docs.py) now supports affected-guide checks and avoids content dependencies from
navigation links between maintained guides. Dated evidence and explicitly declared dependencies still
trigger review. This removes identified review churn; it is not a measured total-development speedup.

The September 9 cleanup found no byte-identical source duplicates under `scripts/` and `custom_nodes/`.
Static package imports reached 51 of 52 non-test modules; this is not a full dynamic dependency proof.
The remaining [old Upgrade reference-policy helper](../archive/klein9b-upgrade-reference-policy/flux2_klein9b_upgrade_reference_policy.py)
was referenced only by its [standalone test](../archive/klein9b-upgrade-reference-policy/test_flux2_klein9b_upgrade_reference_policy.py)
and verification/documentation records in the inspected repository, including ignored history.
It described a Turbo identity-reference choice that the current Upgrade engine never called.
Both files were archived byte-for-byte and the obsolete test was removed from the main verifier.
The existing [production reporting test](../custom_nodes/ComfyUI-AIToolkit-Training/test_flux2_klein9b_photo_realism_upgrade_reporting.py)
now executes the real reference-conditioning block with test doubles and checks ordered source1.0,
guide0.5, identity0.5 and hair0.1MP inputs in both branches. Image generation code is unchanged.

Routine discovery fell from 900 to 486 files after [.ignore](../.ignore) excluded historical folders,
generated indexes and dated reports and the two files moved. This measures search scope, not developer
speed. Source directories still contain separate experimental utilities; they were not bulk-deleted.

## Earlier model routes

Krea 2, InfiniteYou, HiDream, alternative Klein/Dev/LoRA variants and older phone/detail experiments
remain searchable in [the evidence index](generated/EVIDENCE-INDEX.md),
[identity candidate screening](identity-candidate-screening.md) and the
[preserved previous status](STATUS-history-before-doc-rebuild-2026-09-09.md).
Those decisions apply to their tested versions, conditioning and photographs, not every future version of a model family.
