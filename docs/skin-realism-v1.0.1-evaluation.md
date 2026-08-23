# Easy Social Photos v1.0.1 realism evaluation

This fixed local suite promoted the smallest change that corrected the smooth, uniformly shaded face: a more
specific natural-skin instruction and `896×1344` primary generation. It did not add a face swap, enhancement
model, inpaint, upscale, or low-denoise finishing pass.

## Controlled action A/B

| Candidate | Canvas | Face pixels | Identity | Chroma variation | Micro variation | Time |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Frozen smooth control | 768×1024 | 85×120 | 0.7576 | 3.616 | 2.444 | 28.3 s |
| Balanced wording only | 768×1024 | 87×123 | 0.7922 | 3.635 | 2.447 | 28.5 s |
| Balanced wording + detail canvas | 896×1344 | 121×179 | 0.8246 | 6.559 | 4.043 | 34.9 s |

The near-identical 768 micro scores isolate face pixel budget as the main blocker. The balanced wording improves
color/identity, while the larger canvas restores detail. Raw-phone wording was rejected because it reduced
identity and micro variation relative to the balanced profile.

## Final production suite

| Preset | References | Identity signal | Face width | Chroma variation | Micro variation | Winning pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Smartphone, looking | 1 | 0.7996 against three other genuine photos | 204 px | 5.382 | 4.554 | 36.5 s |
| Professional, looking | 4 | 0.8827 supplied centroid | 314 px | 5.308 | 5.012 | 35.0 s |
| Smartphone candid | 4 | 0.7985 supplied centroid | 262 px | 5.085 | 5.433 | 38.2 s with winning seed first |
| Smartphone full-body action | 4 | 0.7230 supplied centroid | 103 px | 6.097 | 3.126 | 35.2 s |

Two genuine comparison photos measured chroma variation `3.174–5.303` and micro variation `4.132–6.041`.
These diagnostics flag extreme smoothing or oversharpening; they do not prove realism, and absolute sharpness
cannot be compared without accounting for face pixel size. Contact sheets and identity scoring were reviewed
alongside the complete images.

The one-reference path automatically uses stronger LoRA conditioning. Candid uses an explicit off-frame gaze,
stronger difficult-angle conditioning, and tries the validated winning seed first. Action uses a lower `0.70`
identity floor because its detected face is much smaller. Every mode retains a second deterministic candidate
only as a rejection fallback.
