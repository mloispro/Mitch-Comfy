# crowd_route_v1 portfolio — rejected

> **Historical record — not current instructions.** The final rejection below overrides every earlier automatic pass or selection in this report. See `docs/STATUS.md` for current state.

**Final status (2026-08-29): visually rejected by Mitch and removed from ComfyUI.** The automatic router,
model-switch workflow, portfolio runners, and active portfolio selection were deleted. The identity and detector
scores below did not catch the decisive defects: the main subject has an oversized head and a visibly composited,
Photoshopped boundary against the unchanged scene. The busy-city-sidewalk and restaurant-patio images are explicit
rejection examples, not approved masters. Do not restore or promote this masked host-replacement mechanism from
the numerical results in this document.

The crowd-first campaign completed its automatic gates: the state-fair proof passed first, the frozen mechanism
generalized numerically to the city sidewalk, boutique hotel lounge, and night market, and only then was the
nine-setting portfolio assembled. Later full-size visual review rejected the mechanism and the entire portfolio.

## Former automatic selection — all visually rejected

| Setting | Route | Identity | Detection | Face px | Edge ratio | People | Result |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Lead portrait | v1.0.4 solo | 0.7930 | 0.8673 | — | — | — | automatic gate only |
| Busy city sidewalk | crowd_route_v1 | 0.8483 | 0.9061 | 121.3 | 0.9489 | 10→9 | automatic gate only |
| Boutique hotel lounge | crowd_route_v1 | 0.7677 | 0.9067 | 142.1 | 0.7996 | 9→9 | automatic gate only |
| Gallery opening | crowd_route_v1 | 0.8320 | 0.8720 | 116.7 | 1.2629 | 13→14 | automatic gate only |
| Rooftop terrace | crowd_route_v1 | 0.7527 | 0.9108 | 127.7 | 1.3304 | 12→11 | automatic gate only |
| State fair | crowd_route_v1 | 0.8129 | 0.8739 | 101.2 | 0.7858 | 15→14 | automatic gate only |
| Restaurant patio | crowd_route_v1 | 0.8719 | 0.9039 | 129.7 | 0.9430 | 12→11 | automatic gate only |
| Lakefront activity | crowd_route_v1 | 0.8094 | 0.9273 | 129.6 | 1.0557 | 10→10 | automatic gate only |
| Night market/live music | crowd_route_v1 | 0.8152 | 0.9091 | 127.3 | 0.9365 | 14→13 | automatic gate only |

The authoritative values and source paths are in `output/crowd_route_v1/portfolio/portfolio-manifest.json`. The portfolio intentionally contains exactly two designated direct-eye-contact masters, seven activity/off-camera masters, three understated high-status settings, and no repeated selected wardrobe.

## Deliverable layout

The retained historical directories under `output/crowd_route_v1/portfolio/` contain:

- `master.png`
- `runner-up.png`
- master and runner-up JSON reports
- the master plate, host-core mask, transition mask, obscured plate, raw generation, and diagnostic overlay when the scene used the crowd route

The rejected six-image dating-app sheet is `output/crowd_route_v1/portfolio/best-six-contact-sheet.png`. It contains the former lead portrait, city sidewalk, hotel lounge, rooftop terrace, restaurant patio, and lakefront activity selections.

The deleted completion verifier produced `output/crowd_route_v1/completion-audit.json`; that automated result is historical evidence only. Audit crops preserve the original pixels for the state fair, restaurant patio, hotel lounge, and night-market rejection review.

## Rejection record

The timestamped manifests under `output/crowd_route_v1/portfolio-runs/` preserve every accepted and rejected candidate with prompt ID, GPU, runtime, output path, and exact exception. Visual review overruled several numerical passes for closed eyes, incorrect semantic host selection, repeated-looking wardrobe/background people, or a visibly weaker social moment.

The restaurant sequence was the decisive stress test:

- Early table-interaction plates failed because furniture interrupted U2Net subject segmentation or the identity landed on a seated diner.
- Walking three-abreast often pushed the host into profile, caused identity leakage to nearby friends, or scored below the identity threshold.
- Moving the two friends several paces behind and keeping the closest host unobstructed produced a coherent pass without changing identity settings.

Version 1.0.4 remains a separate workflow and did not produce this portfolio. The deleted `Flux2EasySocialPhotoV105` experimental router produced these images by applying `crowd_route_v1` to multi-person scenes.
