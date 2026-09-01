# Qwen experimental pose-safe dating pack

> **Historical record — not current instructions.** Terms such as “production,” “current,” “selected,” or “recommended” below describe the decision on 2026-08-20. See `docs/STATUS.md` for current state.

Historical v4 mutable workflow at validation time (no longer present): *workflows/experiments/EXPERIMENTAL - Qwen Identity + Build - 9 Dating Photos.json*

Workflow SHA256: `60502AE47288ADCC923EADDB8CA894A73664B30B7E8FEF4C857E57AC18C13ECE`

This manifest describes the pose-safe v4 run. The same stable experimental filename now contains v5 with the measured blended face model; see `Qwen Experimental Blended Identity v5 - 2026-08-20.md`.

New golfer scene SHA256: `17EF25B672D8CF7F9995CAB5A22B0DA1C6F46F8AA6D8468765BDB211823D0612`

The workflow was rebuilt after a nine-scene audit rejected whole-frame body correction. The rejected version is
preserved at `checkpoints/workflows/Qwen Easy Identity + Build - unsafe-body-v3.json`; its current archive
SHA256 is `D7E433FB7F350E990357A09D086ED4CD93433BC1FBEC3A8CC0E0284DCCA119F8`.

## Routing

- Night Out A and B: targeted ReActor only to avoid identity duplication in groups.
- Golfer, Amalfi, Lake Boat, and Night City: pose-safe ReActor only to preserve gaze, limbs, hands, clothing, proportions, and composition.
- Cat/Ragdoll, Cat/Tabby, and Restaurant: Qwen Edit 2511 full-head identity followed by ReActor; visual audit found these close scenes safe.
- The strong-body silhouette branch and its user toggle were removed, not merely disabled.

## Validated run

The `final_00002_` set under `ComfyUI/output/dating-app-easy-experimental-v4` completed on 2026-08-20 with no prompt validation errors or missing-node warnings.

Visual review of all nine images confirmed:

- The intended man remains the only replaced identity in both lounge groups.
- The golfer has attached arms, a complete club and glove, and plausible leg proportions.
- The Amalfi railing pose and crop are preserved.
- The lake-boat pose has complete attached arms and no invented elongated lower body.
- The night-city subject keeps the downward, away-from-camera gaze and both hands on the railing.

For the four pose-critical solo scenes, a pixel comparison between the approved Stage 1 image and `final_00002_` showed that changes were confined to a head-region rectangle:

- Golfer: 1.40% of pixels changed; bounding box `(456, 305, 613, 462)` in a 1056 × 1584 image.
- Amalfi: 8.65%; `(267, 247, 600, 580)` in 832 × 1216.
- Lake Boat: 4.06%; `(332, 274, 543, 486)` in 832 × 1216.
- Night City: 1.72%; `(327, 484, 494, 651)` in 832 × 1216.

## Preserved stable workflow hashes

- `Qwen + ReActor Single-Person Scene Match.json`: `2C04D28733A02ACC62B6BFA812516F2C8DCC37FD6DBDC36DC43E7023DB234072`
- `Qwen 2512 + ReActor - 9 Dating Photos.json`: `35EC491F5C8F29B60BE4E1D2B7495D090C40EA6F6503F09D79D419797808F9C7`
- `ReActor Multi-Person Identity Finish - Sharper Face.json`: `E8E3A3B387C84BAA944298D73A6B3BC180ECF2F3B72CF608B430FA994A3BDB2D`

Exact body-identity validation is not claimed. Only waist-up genuine references are available; a neutral full-body front and side reference would be required to verify leg and build identity rather than anatomical plausibility.
