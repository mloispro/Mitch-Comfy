# Fresh Group image evaluation — CPU only

`evaluate_fresh.py` is a separate attribution/path adapter. It does not change
the frozen runtime or original Group scoring function. Its separate
`EVALUATOR-PREPARED.json` must pin the reviewed watcher, WDDM helper and runtime
supplement; missing or changed pins fail closed. This is not execution approval.

After an actual successful image, root must first supply its real prompt ID and
PNG SHA and complete independent native-size and thumbnail reviews. Verify the
saved full graph, uncached history, native/copied PNG, fresh worker/parent
lifetimes, two native entry/return guards, all 36 execution events, continuous
resource observations and historical WDDM approvals before scoring. The fresh
worker's two saved prior-history receipts must both be exactly empty. Historical
control/interrupted runs remain offline evidence, never this worker's history.

Commands (replace both placeholders with actual owner-confirmed values):

```powershell
$env:CUDA_VISIBLE_DEVICES=''
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:TORCH_COMPILE_DISABLE='1'
& 'C:/projects/AI-Tools/ComfyUI/.venv/Scripts/python.exe' -B 'C:/projects/AI-Tools/Mitch-Comfy/workflows/experiments/group-masked-pilot-resume-20260908/evaluate_fresh.py' --prompt-id ACTUAL_PROMPT_ID --image-sha ACTUAL_PNG_SHA256 --verify
# Only after verification and explicit root authorization:
& 'C:/projects/AI-Tools/ComfyUI/.venv/Scripts/python.exe' -B 'C:/projects/AI-Tools/Mitch-Comfy/workflows/experiments/group-masked-pilot-resume-20260908/evaluate_fresh.py' --prompt-id ACTUAL_PROMPT_ID --image-sha ACTUAL_PNG_SHA256 --score
```

Default is verification only, without writes. Scoring uses CPUExecutionProvider
only and creates `evaluation-pilot/`; an existing directory is never overwritten.
No API, worker, cache, capture, download or generation operation is called.

## Unchanged diagnostic rules

- Select the central navy-suited man geometrically near normalized (.51,.45),
  maximum distance .10, before identity scoring. Confirm the selected bounding
  box visually; do not substitute the largest or most Mitch-like face.
- Use only the same six held-out genuine val01–06 photographs for identity and
  calibration. Exclude generated pilot/control images, the composition guide,
  and generation input photographs from this held-out cohort. Their hashes are
  disjoint. Reference decoding, face model and calibration remain unchanged.
- Main centroid similarity must be >=.55. Every bystander-to-genuine-centroid
  must be <.42; every bystander-to-main <.50; every distinct bystander pair <.72.
  Equality fails those exclusive limits. The selected main's self-to-main value
  near 1 is display-only and excluded from all secondary maxima; no pair compares
  a face with itself.
- Report all six raw main-reference values, mean, minimum and unchanged genuine
  calibration floor .5533463954925537. No score or classifier label rescues a
  visual failure or establishes an identity lock. Missing an expected visible
  bystander is not a pass.
- Require recognizable adult identity, closed lips, natural skin/hair, coherent
  own hands/contacts/anatomy, four principal adults plus the partial fifth,
  distinct bystanders, coherent scene/depth and no halo. Preserve every failure.

The historical control's automated watcher failed; it remains an image-only
comparison, not a successful runtime control. The fresh worker changes timing
and cache context. No matched-speed, cross-seed robustness, zero final leakage,
universal readiness or production promotion claim follows from one pilot.
