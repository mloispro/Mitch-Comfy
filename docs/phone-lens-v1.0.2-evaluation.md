# Easy Social Photos v1.0.2 phone-lens evaluation

> **Historical record — not current instructions.** Easy Social is now an archived rollback. See `docs/STATUS.md`.

The optional `Smartphone — slight lens haze` preset reproduces the thin washed film in casual phone captures
near bright windows or sun. It describes the physical cause—uneven veiling glare and lifted blacks from stray
light on an everyday handled lens—instead of applying a flat white overlay or a face-smoothing postprocess.

## Controlled car-scene comparison

All promoted comparisons used the same four genuine references, scene, canvas, and deterministic first seed.
The regular-camera control stayed clean but missed the `0.75` identity gate after two attempts. Prompt-only
haze at the lighter `0.4` identity profile made the film visible but softened the face and required two passes.

| Candidate | Identity | LoRA / guidance | Passes | Time | Result |
| --- | ---: | --- | ---: | ---: | --- |
| Professional clean-camera control | 0.7383 | 0.4 / 2.0 | 2 | 65.7 s | clean optics; identity below gate |
| Prompt-only phone haze | 0.7583 | 0.4 / 2.0 | 2 | 66.4 s | visible film; face too smooth |
| Phone haze, strong identity | 0.8936 | 0.6 / 4.0 | 1 | 36.4 s | detailed but facial lines over-defined |
| **Promoted midpoint** | **0.8308** | **0.5 / 3.0** | **1** | **36.6 s** | visible optical film with balanced identity/detail |

## Texture check

The two genuine comparison photos spanned dynamic range `60–117`, chroma variation `3.174–5.303`, and micro
variation `4.132–6.041`. The promoted phone-lens result measured `102`, `4.296`, and `5.806`, respectively—all
inside those observed ranges. These local metrics flag extremes but do not prove photographic realism.

The clean phone and professional styles are unchanged. The haze profile is selected only when the user chooses
it, adds no model or postprocess pass, and retains the same automatic identity retry as the rest of production.
