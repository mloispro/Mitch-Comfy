# FLUX.2 Klein 9B visible appearance enhancement evaluation — 2026-09-01

## Decision

Promote the shared `Visible flattering enhancement` Boolean as a default-on prompt-conditioning option in the three
production Klein 9B workflows. Turning it off removes the optional clause and restores the previous effective
prompt. The change does not add or alter a model, LoRA, reference image, mask, sampler, resolution, face pass,
restoration stage, or post-processing step.

The final best-day clause permits conservative same-person improvements to the whole presentation: roughly 3–5
years younger, a slightly stronger natural jaw and chin, modestly higher cheekbones, improved facial balance, a
slight confident closed-lip expression with every tooth covered, clearer natural eye catchlights and balanced
eyelids, finer-but-visible pores, tidier stubble, reduced fine-line and under-eye emphasis, and a noticeable light
bronze tan. Core face width, feature spacing, natural eye size/color/spacing, nose, mouth, ears, and hairline remain
identity anchors. Each workflow's gaze, facial perspective, and scene intent remain authoritative.

## Controlled Identity Studio A/B

The test used the exact same `SOLO — front + left-facing angle` profile, scene prompt, genuine references, seed
`8675411`, LoRA `0.90`, `832×1216` canvas, 50 Euler steps, CFG `4.0`, and `Flux2Scheduler`. The toggle was the
only changed variable.

| Candidate | Held-out centroid | Mean vs six | Minimum vs six | Status | Skin chroma | Skin micro |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| Enhancement off | 0.8057 | 0.6951 | 0.5950 | strong_match | 3.689 | 4.938 |
| Initial mild clause | 0.8021 | 0.6920 | 0.6284 | strong_match | 3.377 | 4.895 |
| Visible complexion clause v2 | 0.7848 | 0.6771 | 0.6036 | strong_match | 3.498 | 5.110 |
| Final best-day clause v3 | 0.8106 | 0.6993 | 0.6156 | strong_match | 3.952 | 5.564 |

User review first found the initial clause too mild, then requested that bone structure, expression, pores, stubble,
and apparent age become enhancement targets rather than hard locks. The final prompt removes those conflicting
locks only when the toggle is enabled. Relative to off, best-day v3 improved centroid similarity by `+0.0049`, mean
similarity by `+0.0042`, and the weakest held-out comparison by `+0.0206`. It ranked first; all candidates remained
`strong_match` and above the `0.5533` genuine-photo pairwise floor.

Full-size and thumbnail review found best-day v3 recognizably Mitch with a stronger jaw/chin, fuller cheek
definition, a warmer relaxed expression, tidier stubble, finer visible pores, a modestly younger presentation, and
natural skin rather than a plastic beauty-filter surface. Forehead-line reduction remains less deterministic than
the other traits. The stronger prompt also changed framing toward a larger face despite the fixed seed and scene;
new results still require composition review.

Local artifacts are under `work/flux2-klein9b-appearance-polish`, including the off, visible-v2, and best-day-v3 raw
outputs and reports, `identity-best-day-v3.json`, `skin-best-day-v3.json`, and
`skin-best-day-v3-contact-sheet.png`.

## Group Studio smoke

The initial mild clause was smoke-tested with the approved lounge source, target position, `0.92` head scale, seed
`8675412`, genuine front-neutral identity reference, and all locked generation settings. The enabled result
detected four complete faces and passed the identity-scope gate:

- main Mitch similarity: `0.5603` with a `0.55` production smoke floor;
- maximum bystander similarity to the genuine Mitch centroid: `0.1938`;
- maximum bystander similarity to the selected Mitch face: `0.2490`;
- maximum pairwise bystander similarity: `0.2900`.

Full-frame review found one Mitch, three distinct detected friends plus the expected partial edge person, coherent
seated integration, usable hands, natural skin, and no pasted-head boundary or halo. The result and report are
preserved as `group-appearance-on.png` and `group-appearance-on-report.json` in the local work directory.

## Upgrade Studio smoke

The source-locked canyon smoke used the four documented reference roles, seed `8675412`, and the initial mild clause.
It scored `0.7622` against the six genuine held-outs with a `0.5834` weakest view, producing a calibrated
`strong_match` above the `0.5533` genuine-photo pairwise floor. Full-size and thumbnail review found the source
composition, head direction, gaze, expression, clothing silhouette, and canyon layout intact, with natural pores
and stubble and no repair patch, halo, or plastic face. Its micro-luma diagnostic was `5.530`; the higher detail is
visible across the whole source-locked render rather than as a selective face-sharpening stage.

The result, face-free guide, report, held-out identity report, and skin report are preserved under the same local
work directory.

## Closed-lip expression refinement

The first same-seed straight-on wording used the phrase `closed-mouth smile`. It produced a larger toothy smile and
was rejected even though identity remained a calibrated `strong_match`. The accepted prompt removes the word
`smile` and instead defines the visible geometry: upper and lower lips meet across the full mouth width in one
unbroken line, every tooth remains behind the lips, and only the corners lift slightly. It also asks for relaxed eye
openness, clean catchlights, clear irises, and balanced eyelids while preserving natural eye size, color, spacing,
and gaze.

The accepted same-seed straight-on frame had no visible teeth and retained a confident pleasant expression. It
scored `0.7897` centroid, `0.6813` mean, and `0.6175` weakest-view similarity against six genuine held-out photos,
remaining `strong_match` with every comparison above the `0.5533` genuine-photo floor. Evidence is preserved under
`work/flux2-klein9b-appearance-polish/pose-ab-v3` as `front-after-closed-lips-v4.png`, the rejected toothy attempt,
their run reports, and `identity-closed-lips-v4.json`.

## Limitations

The final best-day clause is controlled and measured on one solo portrait. The earlier mild clause, shared wiring,
and identity mechanism were also smoke-tested in the Group and Upgrade workflows; the final wording was not
regenerated in those two contexts. This does not make attractiveness objective or guarantee the same visible
effect at every face scale and lighting condition. Each result still requires full-size and thumbnail review, and
automated similarity remains a ranking and rejection diagnostic rather than proof of identity.
