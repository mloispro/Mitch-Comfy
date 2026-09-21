# Verified bug: Upgrade v4's hair mask selects neck

Status: confirmed on house, canyon and genuine third. Production source now
contains the versioned v5 repair, verified by actual-parser/Low/High CPU replay
on all three photos. The primary worker was reloaded with explicit approval;
live v5 house runtime verification is complete (details below).
This is not a complete stronger-High fix and does not
explain all expression/skin failures.

## Cause and evidence

`flux2_klein9b_deterministic_polish.py` loads the existing CodeFormer ParseNet
weights, but `build_semantic_hair_mask` selects class17. The
[author's ParseNet example](https://github.com/xinntao/facexlib/blob/master/inference/inference_parsing_parsenet.py)
defines class13 as hair and17 as neck. The
[different BiSeNet example](https://github.com/xinntao/facexlib/blob/master/inference/inference_parsing.py)
uses17 for hair. Equal class counts do not make those label schemas interchangeable.
The installed parser/model class, normalization and hash were verified. No model
or dependency was downloaded. The separate isolated-hair reference in native
slot4 was visually inspected and does contain hair; that asset is not the bug.

The old unit tests passed synthetic masks directly into the hair material
function, so they never exercised ParseNet label selection. The new regression
test constructs both hair13 and neck17 labels and rejects a neck-only result.

Artifacts: `work/upgrade-source-faithful-20260903/parsenet-label-audit/`.
The old Low replay exactly matches the saved production Low pixels on both
house and canyon. The genuine third uses the separately corrected native raw
and excludes its own original photograph from likeness scoring. This is a
three-photo postprocess diagnosis, not evidence of a universal native policy.

| Case | Old mask overlapping neck | Old mask overlapping hair | Corrected similarity | Old similarity |
| --- | ---: | ---: | ---: | ---: |
| House | 99.884% | 0% | 0.738273 | 0.738950 |
| Canyon | 99.609% | 0% | 0.749748 | 0.746137 |
| Genuine third | 99.984% | 0% | 0.818384 | 0.819508 |

All corrected masks have0% overlap with ParseNet's neck class. Full-frame
overlays and Low comparisons were reviewed for all three: class13 covers hair,
class17 covers neck; the corrected finish enhances existing hair highlights
without obvious new head/body seams. Outside the union of old/new masks and
the respective gaze-correction regions, maximum RGB difference is0/255.
This does not prove exact gaze geometry; the gaze stage can respond to changed
photometry. Fine hair texture and High attractiveness still need native review.

Audit metadata caveat: nested hair-report strings come from the unchanged v4
function and still say class17 even for the injected corrected mask. The
top-level `corrected_hair_class:13`, saved masks and exact label intersections
record what was actually used. Do not treat the inherited string as runtime proof.

A second exact-morphology audit is saved separately at
`work/upgrade-source-faithful-20260903/parsenet-label-exact-repair-audit/`.
It restores the same5x5 closing and largest-component cleanup as production,
isolating the class-number repair. Corrected similarities are0.737938 house,
0.749569 canyon and0.818007 third. The old branch still replays actual house/
canyon Low pixels exactly. Unrelated-region RGB error is0 and corrected masks
contain no neck-class pixels. Full native corrected outputs plus the earlier
mask and thumbnail comparisons were reviewed. No facial geometry improvement
or full stronger-High completion is claimed from this repair.

## Integration requirements

Correct the production selection and report together, explicitly version the
appearance profile, and add an actual-parser regression rather than merely
changing the numeric hash assertion. Preserve historical v4 checksums/reports;
do not silently rebase their earlier frozen output evidence. Validate the new
common finish and High/gaze ordering on both photos plus the genuine third.
Then update the current implementation contract and perform a live end-to-end
run. Do not restart a worker during another task's generation. The full stronger
High and PhoneON/background requirements remain active throughout.

## Versioned v5 code repair and actual-code replay

The production module selects `HAIR_PARSER_HAIR_CLASS=13`, reports the same
class correctly, and declares `deterministic_face_and_hair_local_v5`. All skin,
smile, hair strength, morphology and gaze-order parameters remain unchanged.
Production module SHA256:
`3F37FD5632D4AE1236314DF795AADDBF73FA55EF74CAE2BAB62C7359A5778676`.
The existing High module changes only its stale Low-v4 docstring; no High math
was altered. The main Upgrade module changes only the report's historical
comparison wording so v5 is not falsely reported as unchanged v4. Its source SHA
is `DAF621973E8B3EBBC555DADC293E1C74EDC1BA42930D6883616970E1E55DFC24`.
The active source contract and verifier are versioned accordingly.
Inactive historical v4 checksums/reports are unchanged, and exact v4 source bytes
are retained as `parsenet-label-exact-repair-audit/legacy_v4.py`.

Three unit tests pass, including the actual production mask entrypoint with
ParseNet-shaped logits containing both hair13 and neck17. The CPU integration
runner `scripts/verify-upgrade-parsenet-v5.py` also uses the installed real parser
on all three saved raw photos. Its masks and Low outputs match the previously
reviewed exact-repair audit pixel for pixel. The frozen v4 branch independently
replays the earlier legacy pixels. Correct v5 report metadata is asserted.
The usual Low -> source gaze -> High order runs in both branches; pixels outside
the High edit mask remain unchanged by High.

Evidence: `work/upgrade-source-faithful-20260903/parsenet-v5-production-code-replay/`.

| Case | v4 Low | v5 Low | v4 High | v5 High |
| --- | ---: | ---: | ---: | ---: |
| House | 0.738950 | 0.737938 | 0.727175 | 0.724741 |
| Canyon | 0.746137 | 0.749569 | 0.724661 | 0.723774 |
| Genuine third | 0.819508 | 0.818007 | 0.807145 | 0.805719 |

These scores use six genuine references, excluding the third's own original
from its score. The third still uses a different native raw policy, so this is
common postprocessing proof, not universal generation proof. Thumbnail views
show localized hair-highlight/neck corrections, not a stronger beauty result.
Full-size v5 High images were also inspected: no obvious new hairline/head-body
halo; body, clothing and detailed environment remain coherent. Skin still has
coarse/dotted areas and house eyes/expression remain Low-like. This is a label
repair, not evidence that stronger attractiveness is solved. Five report tests,
four attractiveness tests and eight masked-graph tests pass alongside the three
polish tests. The read-only workflow verifier initially deferred at its
active3090-queue guard, then passed after that render completed. All active
implementation registry hashes match. This checks source and live input/default
schemas, not whether the running Python module has reloaded v5.
No live worker restart or new production render has occurred at this checkpoint.

## Completed public-node runtime check

After explicit approval, the task's primary worker was reloaded to activate the
tested v5 code. The secondary worker was not restarted. Audit and logs are in
`work/upgrade-source-faithful-20260903/v5-live-reload-20260904-015316/`.

The actual public `Flux2Klein9BPhotoRealismUpgradeV11` node completed house job
`52348431-764b-407b-bc74-8da6c055ca66` on the 3090: native 1680x1008, Low,
Phone on, Turbo off, 50 Euler steps, CFG 4, seed 8675416. Saved output:
`ComfyUI/output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260904-020400-003998/`.
The persisted submission, terminal history and saved graph match; the PNG's
embedded report exactly matches its sidecar. The actual runtime report confirms
v5 and hair class 13, with 58,476 active inner-hair pixels. Model, adapters and
four-reference configuration match the pinned validation record.

Raw generated pixels exactly reproduce the historical native control, proving
this repair did not change sampling for the test. Final Low pixels are NOT
identical to the quantized-PNG CPU replay: mean RGB difference is 0.0422/255,
maximum 168 in the eye area, maximum 17 outside the expanded eye region.
The live pipeline processes the unquantized decoded tensor; the CPU replay
starts from an 8-bit PNG. This is a known input difference, not yet a proven
complete explanation of every pixel discrepancy. Do not reuse the CPU score.

Separately measured live likeness is 0.739620 against the same six EXIF-oriented
genuine references (CPU control 0.737938). Closed lips remain intact. Full image,
same-window face crops and normal-size comparison show no new visible head/hair
halo or background loss. Existing coarse skin, tense brow and source-pose/gaze
differences remain. This validates the narrow hair-repair integration, NOT a
source-faithful or stronger-High success across three photos.

Evidence in `v5-live-house-native/`: `output-audit.json`,
`visual-and-identity-audit.json`, `source-cpu-live-full.jpg`, and
`source-cpu-live-face.jpg`. Original submission/validation reports are unchanged
historical records, including their pre-review pending labels.
