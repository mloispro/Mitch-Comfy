# Mitch-Comfy Project Instructions

## Non-negotiable project scope

- This is a local ComfyUI project. Interpret model and workflow requests as local by default.
- Do not redirect to Krea.ai, another hosted generator, an API, a subscription, or an image-upload
  service unless Mitch explicitly asks for a hosted solution.
- Keep the terms distinct:
  - **Krea.ai** is the hosted service.
  - **Krea 2 / Krea2** is the local model family.
  - **Nano Banana** is Google's closed model and is not a local Krea 2 implementation.
- Never upload Mitch's reference photographs or initiate a purchase without explicit confirmation.
- Preserve active GPU work. Inspect both GPUs and queues before generation. If the preferred GPU is
  busy, use the other idle GPU whenever the workflow and its VRAM requirements are compatible; do
  not wait unnecessarily or interrupt either card. Never bypass a workflow's explicit GPU lock.

## Research gate before building a new image workflow

Do not invent a graph from node names or assume an image input provides identity control. Before
implementation:

1. Inventory the existing project workflows, scripts, models, custom nodes, GPU state, and prior
   evaluation results.
2. Search current primary sources: the model card, official or author-maintained node repository,
   shipped example workflow, and relevant training documentation. Inspect any source Mitch provides
   before proposing a replacement.
3. Write down the actual conditioning mechanism. Trace every reference image from `LoadImage` to the
   model. Classify it as identity, style, composition, pose, edit-source, face embedding, grounded
   vision encoding, or latent conditioning.
4. Reject the design if the requested identity signal is only entering through a style-reference,
   generic img2img, prompt, host-face swap, or unverified custom node.
5. Verify exact compatibility: base-model variant, adapter/LoRA version, custom-node version,
   reference order, trained resolution/aspect range, sampler, steps, CFG, and VRAM requirements.
6. Start from the author's minimal working workflow whenever one exists. Modify one variable at a
   time instead of constructing an unproven graph from scratch.

No generation should be queued until this research gate can answer: **why should this mechanism
preserve identity, and what primary-source evidence supports that prediction?**

## Identity-reference rules

- Use only genuine photographs for identity evaluation unless a test explicitly studies synthetic
  references.
- Multiple image slots are not automatically interchangeable. Preserve the order and semantics used
  in training. For Krea2 Identity Edit v1.2, image 1 is the scene and image 2 is the person in the
  trained two-input layout; two portraits are not two equal identity anchors.
- Prefer native whole-image generation or training-matched identity editing over face swap, head
  masks, face restoration, or selective sharpening.
- A character LoRA and an identity-edit adapter may be stacked only when their documentation and
  base-model compatibility support it.
- Do not describe a result as identity locked solely because it looks plausible. Report automated
  identity similarity as a diagnostic and still perform visual review at full size and thumbnail.

## Fast experimental loop

1. Build or adapt one minimal workflow.
2. Validate that every required node and model is visible through the live ComfyUI API.
3. Run one approximately 1 MP image on the available GPU.
4. Inspect identity, hair, apparent age, body, whole-frame integration, crowd diversity, depth,
   sharpness, noise, and the cutout/halo failure at full size and thumbnail.
5. Compare against at least two genuine reference photographs with the local face-similarity tool.
6. Make at most one controlled parameter refinement before deciding whether the mechanism works.
7. If it fails, diagnose the mechanism before changing models or adding post-processing.

## Results and communication

- Lead with what is proven, what failed, and the next highest-confidence experiment.
- Separate facts from predictions. Cite primary sources for model and node behavior.
- State limitations plainly. A calibrated `near_match` is not a final identity lock.
- Do not add lighting, flash, upscaling, restoration, relighting, masks, or extra stages unless they
  address an observed failure and have a measurable acceptance test.
- Preserve failed workflows and label them accurately so the same approach is not rediscovered and
  retried later.
