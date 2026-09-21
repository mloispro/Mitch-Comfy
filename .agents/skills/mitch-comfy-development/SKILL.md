---
name: mitch-comfy-development
description: Develop and evaluate Mitch-Comfy's local Solo, Group, Upgrade and ComfyUI controls using existing code, prior experiments and pinned image cases. Use for changes, diagnosis or experiment design in this project; ordinary unrelated coding does not need it.
---

# Mitch-Comfy development

Project root: `C:/projects/AI-Tools/Mitch-Comfy`. Run the commands below there.
The repository's `AGENTS.md` owns project constraints and authorization; this skill supplies navigation
and reusable evaluation commands. It does not authorize new generation, training or deployment.

## Find the relevant evidence

Read `docs/START-HERE.md` and `docs/STATUS.md`, then only the affected implementation/tests.
Use `docs/DECISIONS.md` for the closest tried mechanism and open its actual result. For ideas, identify
the unsolved failure, what the proposed change could influence, and the smallest observation that would
distinguish it from the previous attempt. A different premise can justify revisiting an old failure;
the existence of an old failure alone is not a permanent ban on a model or method.

For image changes, select a relevant existing comparison:

```powershell
python scripts/evaluation-cases.py list --area solo
python scripts/evaluation-cases.py list --query "mouth gaze"
python scripts/evaluation-cases.py show solo-public-cocktail
```

`show` verifies pinned evidence and returns the exact image, executed recipe, original diagnostics,
visual review and genuine-reference cohort. The five cases are a small starting set, not all-preset
coverage. Use `docs/generated/EVIDENCE-INDEX.md` when no case fits; do not force a different task into
these recipes. Historical outcomes are scoped observations. Current release status comes from the
current guides, including `docs/production-speed.md` for the separate Speed routes.

## Make and evaluate the relevant change

Use `docs/TESTING.md` to select focused offline checks. Code/UI/documentation work does not automatically
require image generation. For a new image mechanism, follow the existing AGENTS research gate and trace
the actual conditioning rather than inferring identity support from an image input or filename.

Before a permitted generation, inspect current workers/GPUs using the existing route's safeguards.
Catalog recipes and evaluator paths are historical evidence, not ready-to-run commands: frozen runners
can require old workers, pins and output locations. Preserve their scoring math but review any new
candidate's attribution and runtime admission separately. A code branch alone does not isolate linked
ComfyUI custom nodes or an already-running worker.

For an existing new candidate and its saved executed API graph, prepare a review:

```powershell
python scripts/evaluation-cases.py review solo-cocktail --candidate work/my-run/photo.png --candidate-recipe work/my-run/actual-api.json --change "Describe the intended improvement and changed variable" --output work/evaluation-reviews/my-run
```

This creates a local `review.html` with native/thumbnail views and an unresolved `review.json`.
It verifies historical file hashes and records candidate hashes; it does not prove execution, score
images or decide acceptance. Review candidate visuals before its scores. Use the original route-specific
evaluator/acceptance contract: Solo's largest face, Group's geometric main plus every bystander, Upgrade's
genuine-source exclusion and source-relative fidelity are different. Never transfer thresholds between them.

Record runtime attribution, numerical diagnostics, native/thumbnail observations and the bounded decision
separately in the review. For a quality change, compare against genuine photographs and the previous result.
A diagnostic pass is not a photo pass; a preservation pass is not proof of improved identity or stronger High.
Keep unresolved criteria explicit. New prompts, sources or seeds do not inherit a historical pass.

Update only affected current guides and check them with `scripts/project-docs.py --check --guide <guide>`.
Keep historical cases frozen; add a replacement case for a new accepted baseline instead of overwriting
the evidence or accumulating contradictory instructions here. Retain this skill only while these routes
save repeated work; refine it from observed use rather than adding rules for hypothetical failures.
