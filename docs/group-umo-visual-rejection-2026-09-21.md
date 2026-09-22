# UMO Group: user rejection and correction of visual judgment

September 21, 2026. **Reject both tested UMO recipes for the oversized-looking head
and unnatural, pasted-on face.** Mitch identified these defects and rejected the
direction. They disqualify the photographs independently of any likeness score.
The assistant re-opened both saved full images and agrees with that judgment.

The earlier reviews understated the integration failure as softness/processed
rendering and emphasized the absence of an obvious border or halo. A face can look
pasted on without a visible seam. Continuous legs and a restored glass do not make
the head/body proportions, facial shading or overall photograph convincing.
The initial image should have stopped this trial. Running stronger image guidance
without an evidenced explanation for those defects was the wrong decision.

## What was being tested

The [source/load gate](../work/group-umo-gate-20260921/RESULT.md) admitted a pretrained
UMO identity adapter on OmniGen2 with ordered scene/person image conditioning. This
was a whole-image generation experiment, with no face-swap, mask or finishing stage.
That explains its technical intent; it does not excuse the visual result or establish
that another setting would repair it. The underlying cause of the disproportion and
rendering mismatch has not been isolated.

| Saved trial | Exact image SHA256 | Current disposition |
| --- | --- | --- |
| [Initial imageCFG2](../work/group-umo-pilot-20260921/photo.png) | `fc63608038a3cc37bbb18d0351e349e6db5aa5c03cf5b612867af710e746e801` | Rejected for head/body proportion and face/scene integration |
| [Sole imageCFG3 refinement](../work/group-umo-guidance3-20260921/photo.png) | `1a944d7123c0118dea54af1747c1c5826f5ba84d9d2519ad78e71df22e830752` | Rejected for the same visual failure, with more processed rendering |

The original [pilot review](../work/group-umo-pilot-20260921/VISUAL-REVIEW.md) and
[refinement review](../work/group-umo-guidance3-20260921/VISUAL-REVIEW.md) remain frozen
as evidence of the mistaken assessment. This correction supersedes their favorable
integration/proportion implications. Their runtime records and unchanged numerical
diagnostics remain historical facts, not acceptance. Neither image passed the full
six-reference floor either; fixing that number would still not accept these pictures.

## Decision and retained state

Close the tested UMO route and its refinement. No more guidance, prompt, seed,
resolution or postprocessing sweeps follow. No new experiment, model download or
production promotion is proposed by this correction. Natural head/body proportions
and convincing whole-frame facial integration are immediate visual stop conditions;
do not reduce them to checking for extra heads, seams or halos.

Both owned private workers have [shutdown](../work/group-umo-pilot-20260921/shutdown.json)
[receipts](../work/group-umo-guidance3-20260921/shutdown.json). The failed images,
graphs, reviews, numerical results and verified local archives are preserved. All
unique weights and genuine references remain; this rejection authorizes no additional
deletion. General Group and stronger High remain unresolved features.
