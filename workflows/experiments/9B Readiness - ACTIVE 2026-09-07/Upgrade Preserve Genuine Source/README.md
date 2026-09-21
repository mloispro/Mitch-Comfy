# Upgrade — Preserve Genuine Source (QUALITY 50, experiment)

[Open the ordinary-node workflow](<C:/projects/AI-Tools/Mitch-Comfy/workflows/experiments/9B Readiness - ACTIVE 2026-09-07/Upgrade Preserve Genuine Source/Upgrade - Preserve Genuine Source - EXPERIMENT.json>).
This is an exact byte copy of the frozen UI, not a rebuilt or newly tuned graph.
SHA256: `7DFCDC692C50CD608AB738A75BE80234623320218AA816BAB6F08B85D1AFC102`.

One genuine-photo example passed native/thumbnail review and unchanged identity,
pose and closed-lip diagnostics on a root-tested **isolated RTX4070** worker.
The result preserves the source with modest believable hair/fabric/wall cleanup.
This is **SOURCE-FAITHFUL BASE, not High**, universal enhancement or production
promotion. Small collar/closet details are reconstructed, not recovered facts.

## Use and limits

- Load/import the JSON in ComfyUI. Its LoadImage already names the staged
  [genuine Mitch example](<C:/projects/AI-Tools/ComfyUI/input/mitch-upgrade-third-genuine-fef084d6.png>).
  The source must already depict the correct person, expression, gaze and pose;
  this option is not intended to repair a wrong synthetic identity.
- The frozen example uses **50 Euler steps, CFG4, 816×1088, seed8675412**. The
  prompt specifically describes this navy-sweatshirt/closet photograph. A new
  source needs deliberate prompt and both dimension-field review; other photos
  are unvalidated. Do not treat these fixed settings as a universal preset.
- It still requires the genuine-trained **Mitch V3 rank32 step1600 LoRA .9**,
  compatible Klein Base9B, Qwen/Flux VAE and Phone v13 LoRA .25 from the
  [frozen source package](<C:/projects/AI-Tools/Mitch-Comfy/work/9b-readiness-resume-20260907/upgrade-source-faithful-option/README.md>).
  This is not LoRA-free identity preservation. No Turbo, face restoration,
  masks, upscaling or second pass is added.
- **Ordinary nodes do not enforce a GPU lock.** Do not queue on an arbitrary
  worker: first check ownership, both GPUs/queues, model choices and available
  host memory. The tested isolated4070 worker has been stopped. The production
  public Upgrade node remains3090-locked and uses a different reference layout;
  it is not an equivalent way to run this graph.

## Actual evidence

See the [completed root result](<C:/projects/AI-Tools/Mitch-Comfy/work/9b-readiness-resume-20260907/upgrade-source-faithful-option/ROOT-RESULT.md>),
[evaluated photo](<C:/projects/AI-Tools/Mitch-Comfy/work/9b-readiness-resume-20260907/upgrade-source-faithful-option/runs/ready-val03-parity/raw_00001_.png>)
and [independent result audit](<C:/projects/AI-Tools/Mitch-Comfy/work/9b-readiness-resume-20260907/upgrade-source-faithful-option/INDEPENDENT-RESULT-AUDIT.md>).
The source package's preparation README predates execution; ROOT-RESULT records
the subsequent one-image completion. The frozen UI/source files and all failed
evidence remain unchanged. This folder adds discoverability only.
