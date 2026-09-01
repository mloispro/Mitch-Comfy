# HiDream-O1 workflow sources

`image_hidream_o1_dev.source.json` and `image_hidream_o1_full.source.json` are
unmodified official Comfy-Org templates used as the starting points for the
local two-reference identity tests. Tested graphs now live under
`checkpoints/legacy-workflows/experiments`; none is a visible Production workflow.

The local graph defaults to the tested 1728x2304 portrait canvas. The required
832x1248 smoke test produced no scene, while the trained-resolution run produced
strong aggregate identity but visibly smooth skin/hair and an overly close crop.
See `docs/hidream-o1-reference-dating-evaluation-2026-08-28.md` before treating
the experiment as a reusable dating-photo recipe.

The undistilled Full comparison is documented in
`docs/hidream-o1-full-reference-dating-evaluation-2026-08-28.md`. Full improved
the scene composition but weakened identity, increased runtime, and did not fix
smooth facial rendering. Its no-seam refinement exposed severe patch-grid
artifacts. Neither variant is approved as a final dating-photo workflow.
