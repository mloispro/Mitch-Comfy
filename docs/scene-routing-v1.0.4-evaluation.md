# Easy Social Photos v1.0.4 scene-routing evaluation

## Goal

Make the whole social photo believable—not only the face—without adding controls to the two-node workflow or
changing the accepted v1.0.3 rollback. The motivating failures were a fused car headrest, repeated identities and
shirt colors, wrong-way/repeated cars, uniformly artificial background sharpness, fake bokeh, and a foreground
person that looked composited into a separately rendered scene.

## Shipped design

The node infers scene contexts from the ordinary prompt and selected moment. Every route receives one physical
camera/lens contract, gradual distance-dependent focus, coherent supports/occlusion, healthy unretouched skin,
and explicit bans on cutout halos and selfie arms unless a selfie is requested.

Ordinary solo scenes stay on the validated FLUX.2 Klein Base 4B plus identity-LoRA route. Scenes containing
secondary people, groups, or reflections use the following hidden complex route:

1. Z-Image Base creates an `896×1344` deep-focus scene with a generic main subject. Hard count instructions and a
   layered composition map keep secondary people, the curb, requested vehicles, and architecture in separate
   depth zones. Parked vehicles in one curb row share one legal direction.
2. Local YOLO11n counts visible people and vehicles. If an explicit count is missed, the route can try another
   deterministic layout seed and records every attempt. This is a narrow object-count gate, not a claim that a
   detector can certify realism.
3. InsightFace finds the largest layout face. A framing-aware crop promotes a small layout subject but leaves an
   already-close subject alone.
4. Local U2Net human segmentation selects only the connected person overlapping that face. Implausibly small or
   frame-filling masks are rejected during layout selection.
5. The layout face is strongly obscured and reduced to a tiny `192×288` structural reference. FLUX.2 Base 4B plus
   the selected identity LoRA regenerates only the masked main subject from the genuine full-photo/face references.
   Unmasked bystanders, vehicles, furniture, buildings, and depth geometry remain owned by the accepted layout.
6. InsightFace ranks identity seeds. Smartphone presets receive a restrained zero-model-pass finish that slightly
   reduces synthetic saturation/crispness and adds mild sensor/compression coherence. Optional phone haze follows.

Complex-scene failures never fall back to the known unsafe full-frame identity route. The layout cache is keyed by
the complete prompt, models, dimensions, sampling settings, and seed; identical reruns reuse only an exact
deterministic scene and still run identity evaluation.

## Controlled results on RTX 3090

| Test | Route | Time | Identity | Result |
| --- | --- | ---: | ---: | --- |
| Solo professional bookstore after lens-contract fix | direct 4B | 37.6 s | 0.7656 | Gradual depth falloff; no uniform hyper-sharp backdrop |
| Direct multi-person regression | direct 4B | about 37 s | high main face | Rejected: LoRA cloned the subject into bystanders |
| FLUX.2 9B KV layout + masked identity | two stage | about 90 s | usable | Rejected: malformed/headless extras and repeated cars already existed in layout |
| Qwen Image 2512 four-step layout | scene proof | about 15 s | n/a | Coherent extras, but persistent shallow-focus/bokeh background |
| Z-Image Base scene proof | scene proof | about 60 s | n/a | First materially detailed deep-focus environment with coherent furniture/people |
| Detector-gated café before final traffic direction rule | complex | 143.1 s | 0.6882 | Counts passed, but identity weak and arm marks exaggerated |
| Final new café construction | complex | 105.4 s | **0.7946** | Passed exactly 3 people/2 cars, distinct bystanders, same-direction cars, 28.4% subject mask, first identity seed |
| Identical cached café rerun | complex/cache | **40.4 s** | **0.7946** | Count gate and identity passed with exact deterministic layout reuse |

The final accepted test is
`ComfyUI/output/flux2-reference-studio-v104/4-references/20260823-042038-606256/photo_00001_.png`.
Its report records exact object boxes/confidences, count targets, mask bounds/area, layout/identity settings, cache
status, identity score, timing, and phone-finish parameters.

## Rejected approaches

- Prompt rules alone cannot localize a full-frame identity LoRA; bystanders inherited the main identity.
- FLUX.2 9B KV improved some layouts but produced malformed extras and repeated vehicles on the hard café test.
- Qwen Image generated people/occlusions quickly, but repeated attempts kept a large-camera shallow-focus signature.
- Z-Image Turbo obeyed close framing quickly but also returned to shallow background blur.
- Qwen-to-Z-Image ControlNet introduced visible edge-map/HDR artifacts.
- A Z-Image focus edit oversharpened the frame rather than creating physical depth.
- Qwen3-VL 4B and Qwen3.5 4B critics falsely accepted known defects and hallucinated evidence.
- An SDXL refiner cannot reason about identity scope, person counts, headrests, or traffic direction and is excluded.

## Limits

YOLO validates requested people/vehicle counts, not anatomy, traffic law, or photographic truth. InsightFace is an
identity-drift filter, not proof of identity, and off-angle faces can score lower. Novel prompts can still require a
layout retry or final human rejection. The frozen v1.0.3 workflow remains unchanged for exact rollback and direct
comparison.
