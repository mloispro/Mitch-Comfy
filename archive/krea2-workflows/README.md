# Archived Krea2 workflows

These graphs are intentionally outside `workflows/`, so they do not appear in the active ComfyUI
menu. They are retained to preserve negative results and prevent failed mechanisms from being
rediscovered.

- `Krea 2 ReID - One Reference iPhone Photo (Rejected for Mitch).json` is correctly wired but
  failed Mitch identity transfer (`0.0606–0.1406` centroid similarity).
- `Krea 2 One Reference Identity Experiment (Obsolete Style Reference).json` used a style-reference
  adapter as an identity diagnostic. It is superseded by the dual-conditioned Identity Edit route.
- `Krea 2 Mitch - Busy Sidewalk (Unavailable Personal LoRA).json` records the graph's original
  blocked state. The later character-LoRA test failed identity, and that weight was removed on 2026-09-01.
  The graph remains archival evidence only.

The former Face Attention graph is preserved as an archived fallback at
`checkpoints/legacy-workflows/production/Krea 2 Identity Edit - Face Attention v2.json`. Its builder source is
`templates/krea2-workflows/Krea 2 Identity Edit - Local Reference Restage.source.json`. Neither graph is a
current visible Production workflow; see `docs/STATUS.md`.
