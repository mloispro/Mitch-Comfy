# Easy Social Photos v1.0.3 deterministic phone-optics evaluation

> **Historical record — not current instructions.** Easy Social is now an archived rollback. See `docs/STATUS.md`.

v1.0.3 replaces unreliable prompt-only haze with a deterministic highlight-driven optical pass. The accepted
v1.0.2 core remains unchanged and available for rollback. The new production graph still exposes two nodes and
the same eight useful inputs.

## Exact Action A/B

The regular and haze Action renders used the same four genuine references, natural-phone generation prompt,
seed `8675310`, `action_identity` profile, LoRA strength `0.6`, guidance `4.0`, 20 Euler steps, and `896×1344`
canvas. Both scored `0.7230` identity. The haze side then received the deterministic optical pass; it did not
run another model or alter composition.

## Car-window target check

The final car-window haze render completed in `35.402` seconds with one generation attempt and identity
similarity `0.8921`. The optical pass changed mean luminance from `0.33944` to `0.38369` and standard-deviation
contrast from `0.25728` to `0.24452`, while black clothing remained black and facial detail stayed spatially
sharp. The pass adds zero model invocations.

## Implementation guardrails

- The regular smartphone and professional styles bypass the optics function exactly.
- Haze is derived from a broad blurred highlight mask, but the RGB image itself is never spatially blurred.
- A low base veil makes the option visible without a direct sun; local scatter increases near bright sources.
- Five unit tests cover bypass identity, dark-value lift, contrast compression, highlight localization, detail
  preservation, and invalid inputs.
