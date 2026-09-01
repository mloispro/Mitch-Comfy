# crowd_route_v1 state-fair proof — superseded and rejected

> **Historical record — not current instructions.** The final rejection below overrides every earlier automatic pass or “production” label in this report. See `docs/STATUS.md` for current state.

**Final status (2026-08-29): do not use.** Later full-size review of the same masked host-replacement mechanism
showed oversized head scale and an obvious composited subject/background boundary. The experimental
`Flux2EasySocialPhotoV105` router and its runnable entry points were deleted. The measurements below are preserved
only to document why automated identity, detection, edge-ratio, and crowd-retention gates were insufficient.

`crowd_route_v1` was initially frozen after an automated state-fair proof and second-seed confirmation. It used an identity-free FLUX.2 Klein 9B plate followed by contextual full-body regeneration with FLUX.2 Klein Base 4B and the validated Mitch LoRA. That acceptance was later overturned by Mitch's visual review.

## Passing mechanism

- Plate: Klein 9B KV FP8, four Euler steps, `896×1344`, seed `8675411`.
- Identity: Klein Base 4B FP8, 20 Euler steps, guidance `4`, LoRA `0.60`.
- References: face-obscured plate, automatically selected genuine full photo, derived 2.4× face crop.
- Mask: face-selected U2Net component restricted to the tallest YOLO person box containing that face, complete head support, complete body and shoes, contact-support ellipse, 18 px hard dilation, 36 px soft context ring.
- Finish: restrained whole-frame phone response only.

The confirmed winner scored identity `0.8129`, detection `0.8739`, face height `101.2 px`, crowd retention `14/15`, maximum bystander identity `0.0716`, maximum secondary duplicate `0.4040`, and subject/neighbor Sobel edge ratio `0.7858`. Head integrity and every automated gate passed. Visual review found coherent head/neck/body geometry, shared daylight and camera response, natural feet/contact, deep background detail, varied clothing, and no immediate pasted-subject boundary.

## Rejected experiments

1. Existing accepted 9B plate, whole-frame reference generation at LoRA `0.50` and `0.60`: rejected. Both preserved the deliberately obscured face instead of reconstructing identity. Identity scores were `0.0707` and `0.1077`.
2. Existing plate, contextual regeneration at LoRA `0.60` and `0.75`: technically strong identity (`0.8596` and `0.8509`) but visually rejected because the original host was too frontal, centered, and isolated. The regenerated face also grew from an 82 px plate face to about 122 px, reinforcing the inserted-hero impression.
3. Existing plate, context ring enlarged from 36 to 56 px: rejected because it did not materially improve the visual result or edge response.
4. Replacement plate `8675412`: rejected for two Ferris wheels.
5. Replacement plate `8675413`: rejected for frontal centered hero composition and a staged walking lane.
6. Replacement plate `8675414`: rejected for weaker depth and a more isolated host.
7. Replacement plate `8675411`, identity seed `8675310`: retained as runner-up. It passed identity at `0.7884` and visually established the mechanism, but the second seed produced a slightly smaller, better-proportioned head and stronger crowd retention.

The old Laplacian whole-mask diagnostic was replaced by mean 3×3 Sobel gradient magnitude. Laplacian response disproportionately penalized a smooth navy shirt even when the output matched the accepted plate. Sobel directly measures local edge response and the winner passes the specified `0.75–1.35` subject/neighbor range.

## Historical artifacts

- Lock at test time (deleted): `config/crowd-route-v1.lock.json`
- Winner and report: `output/crowd_route_v1/state-fair/winner/`
- Runner-up and report: `output/crowd_route_v1/state-fair/runner-up/`
- Selected plate: `output/crowd_route_v1/state-fair/selected-plate.png`
- Exact proof runner at test time (deleted): `scripts/run-state-fair-crowd-proof.ps1`
- Replacement plate runner at test time (deleted): `scripts/run-state-fair-replacement-plates.ps1`
- Deleted experimental UI route: `Flux2EasySocialPhotoV105`

Version 1.0.4 remains unchanged.

## Generalization result

The frozen mechanism passed its three required transfer scenes without changing the identity model, LoRA strength, reference order, mask dimensions, sampling settings, or acceptance thresholds:

- Busy city sidewalk: identity `0.8169`, detection `0.8894`, edge ratio `0.9535`.
- Boutique hotel lounge: identity `0.7985`, detection `0.9093`, edge ratio `0.8992`.
- Night market/live-music patio: identity `0.8152`, detection `0.9091`, edge ratio `0.9365`.

The exact validation record is `output/crowd_route_v1/generalization/20260824-021028/validation.json`.

## Historical hardening before final rejection

`Flux2EasySocialPhotoV105` now routes visitor, diner, walker, and cyclist scenes through `crowd_route_v1`; these terms previously allowed some multi-person prompts to fall through to the solo route. A failed U2Net/YOLO host preparation now rejects that ranked plate and continues to the next compatible plate instead of aborting the campaign. This changes orchestration only: identity settings and gates remain frozen.

The dual-GPU portfolio runner accepts `-AdditionalTasksPath` and `-OnlyTasks`, so a rejected named scene can be resumed without regenerating successful scenes. Every attempt remains recorded in the timestamped manifests under `output/crowd_route_v1/portfolio-runs/`.

## Automated portfolio result before visual rejection

The packaged portfolio contains nine masters and one runner-up per setting. Every crowd master passed the frozen identity and integration gate. The selected set contains exactly two direct-eye-contact masters, seven activity/off-camera masters, three understated high-status scenes, and nine distinct wardrobes.

- Selection contract at test time (deleted): *config/crowd-route-v1-portfolio-selection.json*
- Machine-readable results: `output/crowd_route_v1/portfolio/portfolio-manifest.json`
- Best-six contact sheet: `output/crowd_route_v1/portfolio/best-six-contact-sheet.png`
- Packaging tool at test time (deleted): *scripts/package-crowd-route-v1-portfolio.py*

Restaurant-patio experiments A through G were retained as documented rejections. They exposed semantic host selection, furniture/U2Net overlap, extreme head angle, identity leakage, or identity scores below `0.75`. Candidate H established a coherent runner-up. Candidate I retained the same successful clear-host topology while moving the gaze off lens and became the selected master. No acceptance threshold was weakened.
