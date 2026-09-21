# Current project status

Documentation audit: **September 9, 2026**; bounded validation/cleanup review **September 21, 2026**. This page reconciles saved code and completed
reports through September 8, the September 9 Group cache release and all three matched pairs,
and the subsequent three-route [Production Speed rollout](../work/production-speed-rollout/RESULTS.md).
The linked rollout contains fresh normal-worker runs and image reviews; this page is not a live GPU/queue snapshot. Start development at
[START-HERE](START-HERE.md); use [HOW-TO](HOW-TO.md) for operation.

## What is established

- Six workflow JSON files are present under [production](../workflows/production): four photo
  routes and two dataset/training utilities. Their presence is not proof that every scene/mode passes.
- Three separate [Production Speed](production-speed.md) workflows are now available in
  `Mitch/production-speed`: Individual Cocktail, Upgrade Source Preserve Turbo and Group Lounge.
  Each completed an actual normal Comfy Run on3090/8188; exact image acceptance and timing are
  recorded in the rollout. These are bounded recipes, not general approval of every input/preset.
- The Klein public workflows are explicitly **RTX 3090 locked** (normal endpoint 8188).
  Port 8189 is the normal 4070 endpoint. Qualified ordinary-node experiments used separately
  owned workers; those results do not remove production locks.
- The full 9B suite is **not proven ready**. Solo has bounded successes and failures;
  Group identity/bystander/source-preservation issues remain; useful stronger High is unproven.
- Generation engines and all six production JSON files are unchanged. The September 19
  boat gallery update replaces the Italian lake label/prompt/preview with **St. Barts yacht — Caribbean escape**;
  its FULL BODY reference profile is unchanged. Selecting it sets appearance off; the September 20 text/preview
  restores the original forward lean and both rail grips. [The current composite](../work/st-barts-exact-foreground-20260920/RESULT.md)
  directly preserves original foreground pixels after the native edit remained approximate. The gallery itself remains text-only, with qualified
  sunglasses likeness rather than full identity acceptance. The September 21
  [actual browser check](../work/st-barts-gallery-check-20260921/RESULT.md) passes card selection,
  preview loading, Full Body profile, appearance-off and editable prompt behavior. Group
  received tested default-no-op extension hooks for its separate accelerator. Experiments are
  hidden from the curated library but preserved at their original paths; all235 original
  production/experiment files passed the final byte-for-byte check.

## Public workflows and saved behavior

| Workflow | Saved recipe / role | Qualification |
| --- | --- | --- |
| Klein 9B Mitch Identity Studio v1.1 - Visual Presets | New whole-frame generation; Base9B + V3 step1600 identity .90 + native genuine refs + Phone v13 .25; 832x1216; Turbo8/CFG1 and appearance on by default; quality fallback 50/CFG4 | Scene-specific results vary. Raw successes do not establish actual public/profile/mode parity |
| Klein 9B Mitch Group Scene Studio v1.1 - Visual Presets | Source-matched layout using face-free Canny first reference and genuine identity second; Base9B + V3 .90 + Phone .25; 832x1216; 50/CFG4, Turbo and appearance off by default | Historical production acceptance remains historical. Later Group tests do not establish general readiness; masked refinements were rejected |
| Klein 9B - Upgrade Photo Detail & Realism v1.1 | One-face source; four ordered native references; 50/CFG4, Low default, Phone on, no Turbo; Low v5 hair-label repair | Public source fidelity and stronger High are not established across all required sources/modes. Different from the source-preserving ordinary-node experiments |
| FLUX.2 Dev LoRA - 9 Dating Scenes v1 | Dev V2 step1000 LoRA; saved defaults strength1.1, 28 Euler steps, guidance4; specialty restage route | Keep its own recipe/acceptance; do not generalize Klein results to Dev |
| Dataset gen - QWEN 2511 - 3-photo | Generated dataset utility | Synthetic images cannot become genuine identity evaluation truth |
| Train Generated Dataset - AI Toolkit | Training utility | Job completion is not photo acceptance or permission for new character training |

Exact filenames and node wiring are indexed in [CODE-INDEX](generated/CODE-INDEX.md).
Model/reference paths, roles and shared code are in [ARCHITECTURE](ARCHITECTURE.md).

## Latest completed evidence

| Area | Current conclusion | Source |
| --- | --- | --- |
| Solo | All 14 original named scene prompts have bounded observations with differing qualifications. Downtown/Kitchen include holdouts; cocktail/restaurant/canyon and several others have one-image passes; other cases fail or remain uncertain. The newer boat replacement is recorded separately below | [Finite coverage](../work/9b-readiness-resume-20260907/COVERAGE-MATRIX.md) |
| Boat original pose | Repeated request required direct preservation. Current composite copies original person interior and whole frame from y760 down with zero RGB error, retaining hands, legs, rails and boat. Caribbean background only; narrow silhouette/water blending. Final .5380/.4211 near_match versus original .5443/.4310. Gallery remains illustrative; earlier native Quality50 is approximate | [Exact foreground, verification and final image](../work/st-barts-exact-foreground-20260920/RESULT.md) |
| Actual public cocktail | Likeness diagnostics passed; teeth/gaze failed. September 21 source comparison confirms the public recipe is unchanged and differs from accepted Speed in references, surrounding prompt and diffusion precision. Use the existing Speed Cocktail for its bounded case; no isolated cause or public fix is established | [Public result](../work/9b-readiness-resume-20260907/public-cocktail-parity/ROOT-RESULT.md), [completed comparison](solo-cocktail-comparison-2026-09-21.md) |
| Group masked pilot | Runtime completed; reduced bystander similarity but failed main likeness and partial fifth-person preservation | [0.90 result](../workflows/experiments/group-masked-pilot-resume-20260908/ROOT-RESULT.md) |
| Group sole strength refinement | 1.10 improved centroid to .5557 but weakest genuine comparison .4005 and partial-person preservation still failed; rejected, no further strength grid | [1.10 result](../workflows/experiments/group-masked-strength110-20260908/ROOT-RESULT.md) |
| Upgrade second genuine source | Balcony/white-shirt val05 qualified pass: .787830 centroid, .022217 source loss, 1.188 degrees pose drift, closed lips; source excluded from five genuine comparisons. Some smoothing/regenerated detail remains; no universal enhancement or stronger High | [September 21 result](../work/upgrade-generalization-20260921/RESULT.md) |
| Production Speed integration | All three normal Run-button jobs completed: Cocktail24.829s, source-preserving Upgrade18.668s and Lounge209.141s. These are single integration observations, not new matched speed gains. See the release for separate visual/likeness acceptance | [Rollout results](../work/production-speed-rollout/RESULTS.md), [operating guide](production-speed.md) |
| Group Lounge acceleration | Three matched 3090 pairs took 24.5–26.2% less worker time, about 4m32s to 3m24s. Now also installed as a separate normal-worker Speed workflow; its new image exactly matches the accepted cached seed. Small clothing details can change versus uncached. No improved-identity or general-scene claim | [Matched results](../work/group-cache-20260909/RESULTS.md), [normal-worker rollout](../work/production-speed-rollout/RESULTS.md) |
| Source-preserving Upgrade QUALITY50 | One genuine-photo pass; .817792 centroid versus source .825853; 322.387 seconds on isolated4070. Source excluded from the five-reference comparison | [Quality result](../work/9b-readiness-resume-20260907/upgrade-source-faithful-option/ROOT-RESULT.md) |
| Source-preserving Upgrade TURBO8 | Qualified fast option on the same case; .804167 centroid, 54.063 seconds, visibly smoother/less detailed skin. About6x in one pair, not stable median performance | [Turbo result](../work/9b-readiness-resume-20260907/upgrade-source-faithful-turbo/ROOT-RESULT.md) |
| Stronger High | Remains unproven. Native prompt/strength, BeautyGRPO/Kontext, PixelSmile, restoration/shape and LaTo outcomes remain limited/rejected for their tested scope | [September 7 results](upgrade-high-resume-2026-09-07.md), [explicit-feature result](upgrade-high-explicit-features-2026-09-07.md), [decision index](DECISIONS.md#upgrade) |
| Evaluation efficiency | Within-run raw-face reuse is integrated in the existing likeness CLI: median 5.619→4.942s across three six-reference pairs; separate source-excluded pair also passed. Raw records and reports match exactly. Broader cross-tool sharing and specialized Group evaluation are unchanged | [New measurement](../work/face-likeness-cache-20260909/results.json), [scorer](../scripts/evaluate-face-likeness.py), [earlier broader replay](../work/9b-readiness-20260903/evaluation/feature-reuse-coverage/RESULTS.md) |

The source-preserving Quality/Turbo and raw cocktail experiment files were imported/exported against
their executed API graphs: [UI verification](<../workflows/experiments/9B Readiness - ACTIVE 2026-09-07/UI-BROWSER-VERIFIED.md>).
This established historical file usability; the later Production Speed rollout separately
packages and checks Cocktail and source-preserving Turbo on the normal3090 worker. It does not validate new inputs.
Some frozen experiment READMEs predate that browser check; the linked UI verification records the
later completion without rewriting their historical preparation notes.

The available handoffs already exist: [Solo raw example](<../workflows/experiments/9B Readiness - ACTIVE 2026-09-07/Solo Raw Examples/README.md>),
[Upgrade Quality](<../workflows/experiments/9B Readiness - ACTIVE 2026-09-07/Upgrade Preserve Genuine Source/README.md>),
[Upgrade Turbo](<../workflows/experiments/9B Readiness - ACTIVE 2026-09-07/Upgrade Preserve Genuine Source/README_TURBO.md>),
and [Group Lounge cache](<../workflows/experiments/Group Quality Cache - 2026-09-09/README.md>).
Those historical handoffs keep their exact input, worker and recipe limits. For ordinary Comfy
operation use the new [Production Speed guide](production-speed.md); the old files remain preserved.

## Unresolved work and constraints

The September 21 [cleanup](CLEANUP.md) retains every unresolved route, installed model
and unique candidate weight. Dependency review and fresh full hashes cleared twelve
redundant staging copies for removal, recovering about 61.6 GiB; restoration paths
are recorded and pinned evidence remains intact. The subsequent
[Solo comparison](solo-cocktail-comparison-2026-09-21.md) is complete: use the already
accepted Speed Cocktail without changing the original card. The subsequent
[second-source Upgrade test](../work/upgrade-generalization-20260921/RESULT.md) and
[actual St. Barts interaction](../work/st-barts-gallery-check-20260921/RESULT.md) are complete.
The [remaining-route disposition](../work/final-validation-20260921/DISPOSITION.md) retains
all 15 unique weights (54.654 GiB), installed models and frozen evidence. Stronger High
and general Group remain unresolved; LaTo image stages remain unexecuted after failed
geometry admission. A subsequent [input/mechanism review](high-group-gate-2026-09-21.md)
found no new stills in the known folder and no admitted external expression target;
the inspected Klein reference-mask node does not isolate the intended output person.
No new image was admitted by that review. No further blind grids or unique-asset deletion follows.
The preceding validation pass used one authorized Upgrade image; the subsequent review
saved only public source text. Neither involved training, reference upload, model download
or worker restart.

A distinct [Group token-delta compatibility gate](../work/group-lora-token-gate-20260921/RESULT.md)
now passes ten CPU checks: all224 V3 tensor shapes map, explicit generated/reference/text
token routing works, and a small real Comfy transformer agrees with a merged-weight
control. The prototype is isolated under `work/`, not installed. Next is exact-loader/FP8
and memory admission before one prospective image; no Group image improvement is established.

The September 9 [Group acceleration package](../work/group-cache-20260909/RESULTS.md) is complete
for its tested Lounge scope. Its [replay instructions](../work/group-cache-20260909/README-REPLAY.md)
use a separately started private 3090 worker on8191. They are historical replay instructions;
the new Production Speed Lounge workflow runs through ordinary3090/8188 without that worker.
Neither changes the original production card or adds a production toggle.
The release records all three runtime/quality/visual checks. Do not queue its completed confirmation
pairs again as unfinished work. New seeds remain unvalidated and other scenes/settings are unsupported
by that handoff. Saved cleanup evidence is not current GPU/queue state.

The stronger-High stream's September 7 pause is preserved in its
[pause note](<../workflows/experiments/Upgrade High - PAUSED 2026-09-07/README.md>).
The separate readiness stream has later completed evidence. Folder names such as ACTIVE/PAUSED
are historical labels; use latest user instructions and actual results for the specific stream.

The preserved constraint is **no new character LoRA training**. The
[corrected training reassessment](../work/9b-readiness-20260903/REASSESSMENT-20260904.md)
records that the surf and sleeveless mirror examples are not clean head-to-toe photographs.
The older photo audit's description of the surf framing is superseded. Missing coverage is a
future hypothesis, not a training authorization or a proven sole cause.
The rollout used installed models and three authorized integration images; no downloads, uploads,
purchases or training were performed. Further experiments require their own authorization.

## Models, verification and historical evidence

- [Protected baseline registry](../config/frozen-baselines.json): active and superseded artifact records;
  do not rewrite old hashes to make a new implementation pass.
- [LoRA keep/delete record](lora-cleanup-2026-09-01.md): protected identity adapters and historical cleanup.
- [Recorded dependencies](../config/dependencies.lock.json): historical versions, not current runtime discovery.
- [Testing map](TESTING.md): select checks appropriate to the changed component; image acceptance remains separate.
- [Decision history](DECISIONS.md) and [optimization priorities](OPTIMIZATION.md): avoid repeating failed approaches.
- [Previous STATUS, preserved byte-for-byte](STATUS-history-before-doc-rebuild-2026-09-09.md): detailed older updates
  and their original relative links. Its multiple “latest”/pause/resume statements are historical.

Evidence under ignored `work/` exists locally and requires a separate backup. A documentation link
or Git commit does not itself preserve the underlying photos, models or reports.
