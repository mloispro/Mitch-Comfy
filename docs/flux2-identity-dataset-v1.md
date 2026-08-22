# FLUX.2 identity dataset v1

This local-only training set contains ten genuine photos selected for identity diversity rather than volume.
The images live under the ignored `datasets/flux2-klein-identity-v1` directory and are never committed.

Included source coverage:

- mirror/full-body and torso framing;
- close front, front, three-quarter, and high camera angles;
- indoor, outdoor, car, and beach lighting;
- several outfits plus a wetsuit/full-body example;
- photos spanning multiple dates and cameras.

Excluded on purpose:

- near-duplicates from the May 2026 apartment burst;
- `IMG_2961(1).jpg`, because strong smoothing and colored lighting obscure real facial texture;
- generated identity references, previous workflow outputs, and every synthetic dataset image.

The trigger is `m1tch_person`. The completed production training run used FLUX.2 Klein Base 4B, rank 16,
learning rate `8e-5`, 1,500 steps, and checkpoints every 250 steps. The checkpoints are ranked after training
using held-out genuine photos; the final checkpoint is not assumed to be best.

The four evaluator references are held out of training: `20260508_123156.jpg`, `20260815_165446.jpg`,
`20260815_165449.jpg`, and `20260818_173106.jpg`.

Base 9B was the original maximum-quality training target, but its Hugging Face gate denied the configured
account on 2026-08-21. The public Apache-licensed Base 4B variant was trained instead. Initial inference used
the matching undistilled Base 4B model at the official 50-step, guidance-4.0 baseline; measured sweeps then
reduced production to 20 steps after it retained strong held-out identity and visual quality.

The completed six-checkpoint sweep selected step 1,250 at LoRA strength `0.6`. The production sampler uses 20
steps and guidance `4.0`: professional, phone-candid, and action/profile held-out centroid scores were `0.8714`,
`0.8913`, and `0.8216`. The corresponding 30-step quality reference scored `0.9205`, `0.9078`, and `0.8369`.
The step-1,500 checkpoint was rejected because action/profile identity regressed to `0.7694` at the comparison
strength. These metrics are local ranking diagnostics, not an identity guarantee.
