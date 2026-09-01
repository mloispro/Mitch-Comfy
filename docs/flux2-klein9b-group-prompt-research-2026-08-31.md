# FLUX.2 Klein 9B group-prompt research — 2026-08-31

> **Supporting research, not the final operating contract.** Candidate 10 was an intermediate result; candidate 18 and the current Group Scene Studio supersede it. See `docs/flux2-klein9b-mitch-group-scene-studio-v1.md` and `docs/STATUS.md`.

## Decision

The corrected group recipe uses a Canny edge map for composition, one genuine neutral Mitch photograph
at `0.50 MP` for identity, and a concise positive role-based prompt that explicitly matches the source's
relative head scale and shared camera response. It keeps the protected Klein 9B V3 step-1600 LoRA at
`0.90`. Candidate 10 passed the held-out identity and bystander-leakage gate at `0.5507`, and its measured
central-to-neighbor face-height ratio is `1.242` versus `1.235` in the source (a `0.6%` relative error).
Mitch's visual approval remains the publication gate.

Longer facial inventories and a separate expression reference were rejected. They reduced main-face
identity to `0.4803`–`0.4849`. The earlier `1.00 MP` automated identity leader was also rejected in visual
review because Mitch looked composited and his head was oversized relative to the group. The corrected
recipe is therefore the default in `scripts/run-flux2-klein9b-group-layout-reference.ps1`, with Canny
enabled, the neutral identity reference at `0.50 MP`, and no third reference.

The selected strategy is recorded as `bfl-flux2-edge-layout-concise-role-prompt-v1`. It describes the
desired expression through lip, cheek, jaw, and eye positions without using `smile`, `closed-mouth`, or
`teeth`; the genuine neutral photograph anchors the face and head geometry.

## Primary-source basis

- [BFL Prompting Basics](https://docs.bfl.ai/guides/prompting_unified_basics): use clear natural
  language and adjust one important detail at a time.
- [BFL Building a Good Prompt](https://docs.bfl.ai/guides/prompting_unified_building): put the subject
  first, add only details that change the image, and avoid prompt bloat.
- [BFL FLUX.2 Prompting Guide](https://docs.bfl.ai/guides/prompting_guide_flux2): FLUX.2 has no negative
  prompts; describe the desired state instead.
- [BFL Multi-Reference Editing](https://docs.bfl.ai/guides/prompting_editing_multi_reference): name the
  role of every input image.
- [BFL Pose and Layout Guidance](https://docs.bfl.ai/guides/usecases_editing_controlnets): combine a
  structural reference with an identity reference and explicitly state which image supplies each role.
- [FLUX.2 Klein Base 9B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B):
  the local Base model is the undistilled, fine-tunable multi-reference variant.

## Controlled results

All generations used the RTX 3090, FLUX.2 Klein Base 9B, the protected V3 step-1600 LoRA at `0.90`,
`832×1216`, 50 Euler steps, CFG `4.0`, `Flux2Scheduler`, and seed `8675412`.

| Candidate | Conditioning change | Main identity | Max secondary | Result |
|---|---|---:|---:|---|
| `01-prompt-only-expression-fixed-identity-pass` | Positive prompt; one genuine identity reference | `0.5868` | `0.3211` | Identity and expression pass; seating layout too loose |
| `02-prompt-only-seating-fixed-identity-fail` | Added exact one-row seating language | `0.4801` | `0.2368` | Layout improved; identity failed |
| `03-layout-reference-id025-identity-fail` | Raw source layout `0.25 MP` + identity `0.25 MP` | `0.4909` | `0.1329` | Source match and expression good; identity failed |
| `04-layout-reference-id050-best-layout-identity-fail` | Increased only identity reference to `0.50 MP` | `0.5079` | `0.1532` | Identity improved but remained below `0.5333` |
| `canny-id050-slight-smile` | Edge layout + neutral identity; longer prompt, no suit instruction | `0.5332` | `0.2433` | Near gate; head width improved, but clothing and smile failed visual review |
| `canny-id050-slight-smile-v2` | Added suit and mechanical expression wording | `0.5012` | `0.3231` | Suit fixed; identity regressed and smile stayed too broad |
| `canny-id050-smile-ref050` | Added a separate genuine small-smile reference | `0.4803` | `0.3594` | Reference competition; rejected |
| `canny-single-smile-ref050` | Small-smile photo used as the sole identity reference | `0.4849` | `0.3490` | Cleaner frame, but identity failed |
| `05-canny-concise-neutral-head-shape-slight-smile` | Edge layout + neutral identity `0.50 MP` + concise role-based prompt | `0.5576` | `0.2606` | Passed; superseded by higher-resolution identity reference |
| `06-canny-concise-neutral-id100-head-shape-slight-smile` | Same candidate with only neutral identity resolution raised to `1.00 MP` | `0.5928` | `0.2561` | Passed; superseded by expression wording refinement |
| `07-canny-concise-small-smile-id100-rejected` | Replaced neutral photo with genuine small-smile photo at `1.00 MP` | `0.5599` | `0.1664` | Automated pass but smile became broader and clothing drifted; rejected |
| `08-canny-concise-neutral-id100-gentle-lips-winner` | Returned to neutral photo and changed only the expression phrase | `0.6096` | `0.1662` | Automated leader; visually rejected by Mitch for pasted-in appearance and oversized head (`1.272` scale ratio) |
| `09-canny-facecrop-id100-gentle-lips-head-shape-finalist` | Same winning settings; identity input is a hash-locked `2.5×` crop from the genuine neutral photo | `0.5954` | `0.1714` | Passed; head ratio closer to genuine neutral and smile slightly clearer; visual finalist |
| **`10-canny-id050-gentle-lips-integrated-scale-corrected`** | **Returned identity input to `0.50 MP`; added source-relative scale and shared-camera-response instructions** | **`0.5507`** | **`0.2076`** | **Passed; scale ratio `1.242` versus source `1.235`; corrected visual candidate pending Mitch approval** |

The identity-resolution refinement improved the raw-layout result by `0.0170`, but it did not clear the
held-out gate. No bystander leakage failure occurred.

## Gate used during this research

Do not run a seed sweep or add more identity references before visual review. Candidate 08 proved that the
highest automated identity score was not the best photograph: its central-to-neighbor face-height ratio was
`1.272`, compared with `1.235` in the source, and Mitch rejected its pasted-in appearance. Reducing only the
identity-reference resolution to `0.50 MP` brought the same seed to `1.249`; the shared-camera and explicit
relative-scale instruction then improved it to `1.242`.

Candidate 10 has four detected faces, a main-face similarity of `0.5507`, maximum bystander-to-Mitch
similarity of `0.2076`, maximum bystander-to-main similarity of `0.3191`, and no leakage failures. Both arms
and hands are coherent, the central expression is restrained, and the whole face has the same flash, texture,
edge softness, and focus treatment as the surrounding people. Full-size human review remains the final gate.

The attempted Klein 4B whole-frame identity refinement is preserved but visually rejected: it produced an
older, over-sharpened central face with a visible pasted/cutout boundary. Krea2 scene-first identity editing
was not rerun because the existing local evaluation explicitly rejects that mechanism for lounges and other
complex group scenes.

## Preserved artifacts

- `work/group-lounge-prompt-research-20260831/01-prompt-only-expression-fixed-identity-pass.png`
- `work/group-lounge-prompt-research-20260831/02-prompt-only-seating-fixed-identity-fail.png`
- `work/group-lounge-prompt-research-20260831/03-layout-reference-id025-identity-fail.png`
- `work/group-lounge-prompt-research-20260831/04-layout-reference-id050-best-layout-identity-fail.png`
- `work/group-lounge-prompt-research-20260831/05-canny-concise-neutral-head-shape-slight-smile.png`
- `work/group-lounge-prompt-research-20260831/05-canny-concise-neutral-head-shape-slight-smile.identity.json`
- `work/group-lounge-prompt-research-20260831/06-canny-concise-neutral-id100-head-shape-slight-smile.png`
- `work/group-lounge-prompt-research-20260831/06-canny-concise-neutral-id100-head-shape-slight-smile.identity.json`
- `work/group-lounge-prompt-research-20260831/07-canny-concise-small-smile-id100-rejected.png`
- `work/group-lounge-prompt-research-20260831/07-canny-concise-small-smile-id100-rejected.identity.json`
- `work/group-lounge-prompt-research-20260831/08-canny-concise-neutral-id100-gentle-lips-winner.png`
- `work/group-lounge-prompt-research-20260831/08-canny-concise-neutral-id100-gentle-lips-winner.identity.json`
- `work/group-lounge-prompt-research-20260831/09-canny-facecrop-id100-gentle-lips-head-shape-finalist.png`
- `work/group-lounge-prompt-research-20260831/09-canny-facecrop-id100-gentle-lips-head-shape-finalist.identity.json`
- `work/group-lounge-prompt-research-20260831/09-head-shape-expression-finalists.png`
- `work/group-lounge-prompt-research-20260831/09-head-shape-expression-finalists.json`
- `work/group-lounge-prompt-research-20260831/10-canny-id050-gentle-lips-integrated-scale-corrected.png`
- `work/group-lounge-prompt-research-20260831/10-canny-id050-gentle-lips-integrated-scale-corrected.identity.json`
- `scripts/run-flux2-klein9b-group-layout-reference.ps1`
- `scripts/build-group-head-shape-expression-sheet.py`
