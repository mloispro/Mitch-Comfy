# Qwen experimental pose-safe dating pack

Historical v4 workflow at validation time: `workflows/experiments/EXPERIMENTAL - Qwen Identity + Build - 9 Dating Photos.json`

Workflow SHA256: `60502AE47288ADCC923EADDB8CA894A73664B30B7E8FEF4C857E57AC18C13ECE`

This manifest describes the pose-safe v4 run. The same stable experimental filename now contains v5 with the measured blended face model; see `Qwen Experimental Blended Identity v5 - 2026-08-20.md`.

New golfer scene SHA256: `17EF25B672D8CF7F9995CAB5A22B0DA1C6F46F8AA6D8468765BDB211823D0612`

The workflow was rebuilt after a nine-scene audit rejected whole-frame body correction. The rejected version is preserved byte-for-byte at `checkpoints/workflows/Qwen Easy Identity + Build - unsafe-body-v3.json` with SHA256 `DA92834337B6E64E2BDD88CB898DB931D2AC7E0B7999BF9DCF9DE19979AF02DF`.

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

- `Qwen + ReActor Single-Person Scene Match.json`: `BAB42CD251644175AD170C4D8748A86614E83F4EEBED14A54633FCBE538CC54A`
- `Qwen 2512 + ReActor - 9 Dating Photos.json`: `C01EA3931C51E3E70F395EE918CA58E49B4783C6F323D59DE9F5D47BBC443003`
- `ReActor Multi-Person Identity Finish - Sharper Face.json`: `E8E3A3B387C84BAA944298D73A6B3BC180ECF2F3B72CF608B430FA994A3BDB2D`

Exact body-identity validation is not claimed. Only waist-up genuine references are available; a neutral full-body front and side reference would be required to verify leg and build identity rather than anatomical plausibility.
