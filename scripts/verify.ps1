param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$errors = [System.Collections.Generic.List[string]]::new()

function Check-Junction {
    param([string]$Path, [string]$Target)
    if (-not (Test-Path -LiteralPath $Path)) {
        $errors.Add("Missing link: $Path")
        return
    }
    $item = Get-Item -LiteralPath $Path -Force
    if (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        $errors.Add("Not a directory link: $Path")
        return
    }
    $junctionTarget = @($item.Target)[0]
    if (-not $junctionTarget) {
        $errors.Add("Directory link has no target: $Path")
        return
    }
    $resolvedPath = (Resolve-Path -LiteralPath $junctionTarget).Path
    $resolvedTarget = (Resolve-Path -LiteralPath $Target).Path
    if ($resolvedPath -ne $resolvedTarget) {
        $errors.Add("Wrong link target: $Path -> $resolvedPath (expected $resolvedTarget)")
    }
}

Check-Junction (Join-Path $ComfyRoot "user\default\workflows\Mitch") (Join-Path $RepoRoot "workflows")
Check-Junction (Join-Path $ComfyRoot "custom_nodes\ComfyUI-AIToolkit-Training") (Join-Path $RepoRoot "custom_nodes\ComfyUI-AIToolkit-Training")
Check-Junction (Join-Path $ComfyRoot "custom_nodes\ComfyUI-AlwaysRunImage") (Join-Path $RepoRoot "custom_nodes\ComfyUI-AlwaysRunImage")

$expectedWorkflows = @(
    "workflows\production\FLUX.2 One Reference Photo.json",
    "workflows\production\FLUX.2 Easy Social Photos - 1-4 References.json",
    "checkpoints\legacy-workflows\production\Social Photo Studio - FLUX.2 Klein 9B KV (superseded).json",
    "workflows\production\Dataset gen - QWEN 2511 - 3-photo.json",
    "workflows\production\ReActor Multi-Person Identity Finish - Sharper Face.json",
    "workflows\production\Train Generated Dataset - AI Toolkit.json",
    "checkpoints\legacy-workflows\production\Qwen + ReActor Single-Person Scene Match.json",
    "checkpoints\legacy-workflows\production\Qwen 2512 + ReActor - 9 Dating Photos.json",
    "checkpoints\legacy-workflows\experiments\EXPERIMENTAL - Qwen Identity + Build - 9 Dating Photos.json",
    "checkpoints\legacy-workflows\experiments\legacy-z-image\Generate 9 Social Photos - Z-Image LoRA + Qwen Identity Lock.json",
    "checkpoints\legacy-workflows\experiments\legacy-z-image\Generate 9 Social Photos - Z-Image LoRA.json",
    "checkpoints\workflows\Qwen Easy Identity + Build - unsafe-body-v3.json",
    "checkpoints\workflows\Qwen Experimental Identity Build v5 - face detail 0.32.json",
    "checkpoints\workflows\Qwen Experimental Identity Build v6 - CodeFormer identity-first.json",
    "checkpoints\workflows\Qwen Experimental Identity Build v7 - GPEN identity finish.json",
    "checkpoints\workflows\Qwen Experimental Identity Build v8 - streamlined GPEN.json"
)
foreach ($relativePath in $expectedWorkflows) {
    $path = Join-Path $RepoRoot $relativePath
    if (-not (Test-Path -LiteralPath $path)) {
        $errors.Add("Missing tracked workflow: $relativePath")
    }
}

$oneReferenceWorkflowPath = Join-Path $RepoRoot "workflows\production\FLUX.2 One Reference Photo.json"
if (Test-Path -LiteralPath $oneReferenceWorkflowPath) {
    try {
        $oneReferenceWorkflow = Get-Content -Raw -LiteralPath $oneReferenceWorkflowPath | ConvertFrom-Json
        if ($oneReferenceWorkflow.nodes.Count -ne 2) {
            $errors.Add("FLUX.2 One Reference Photo must contain exactly 2 visible nodes; found $($oneReferenceWorkflow.nodes.Count).")
        }
        foreach ($requiredNode in @("Flux2OneReferencePhoto", "PreviewImage")) {
            if ($requiredNode -notin @($oneReferenceWorkflow.nodes.type)) {
                $errors.Add("FLUX.2 One Reference Photo workflow is missing node: $requiredNode")
            }
        }
        $identityNode = @($oneReferenceWorkflow.nodes | Where-Object { $_.type -eq "Flux2OneReferencePhoto" })[0]
        if ($identityNode -and @($identityNode.inputs).Count -ne 2) {
            $errors.Add("FLUX.2 One Reference Photo must expose only face_reference and scene_prompt.")
        }
        if ($identityNode -and $identityNode.widgets_values[0] -ne "Upload one face photo") {
            $errors.Add("FLUX.2 One Reference Photo must open without a preselected identity image.")
        }
        if ((Get-Content -Raw -LiteralPath $oneReferenceWorkflowPath) -match "mitch(?:-workbench)?-qwen-id-(front|left|right)") {
            $errors.Add("FLUX.2 One Reference Photo contains a generated identity fixture.")
        }
    } catch {
        $errors.Add("FLUX.2 One Reference Photo workflow JSON is invalid: $($_.Exception.Message)")
    }
}

$frozenBaselinesPath = Join-Path $RepoRoot "config\frozen-baselines.json"
if (-not (Test-Path -LiteralPath $frozenBaselinesPath)) {
    $errors.Add("Missing frozen baseline registry: config\frozen-baselines.json")
} else {
    try {
        $frozenBaselines = Get-Content -Raw -LiteralPath $frozenBaselinesPath | ConvertFrom-Json
        foreach ($baseline in @($frozenBaselines.baselines)) {
            foreach ($artifact in @($baseline.artifacts)) {
                $artifactPath = Join-Path $RepoRoot $artifact.path
                if (-not (Test-Path -LiteralPath $artifactPath)) {
                    $errors.Add("Frozen baseline $($baseline.id) is missing artifact: $($artifact.path)")
                    continue
                }
                $actualHash = (Get-FileHash -LiteralPath $artifactPath -Algorithm SHA256).Hash
                if ($actualHash -ne $artifact.sha256) {
                    $errors.Add("Frozen baseline $($baseline.id) changed: $($artifact.path). Build new work beside v1; do not edit the accepted core.")
                }
            }
        }
    } catch {
        $errors.Add("Frozen baseline registry is invalid: $($_.Exception.Message)")
    }
}

$easySocialWorkflowPath = Join-Path $RepoRoot "workflows\production\FLUX.2 Easy Social Photos - 1-4 References.json"
if (Test-Path -LiteralPath $easySocialWorkflowPath) {
    try {
        $easySocialWorkflow = Get-Content -Raw -LiteralPath $easySocialWorkflowPath | ConvertFrom-Json
        if ($easySocialWorkflow.nodes.Count -ne 2) {
            $errors.Add("FLUX.2 Easy Social Photos must contain exactly 2 visible nodes; found $($easySocialWorkflow.nodes.Count).")
        }
        foreach ($requiredNode in @("Flux2EasySocialPhoto", "PreviewImage")) {
            if ($requiredNode -notin @($easySocialWorkflow.nodes.type)) {
                $errors.Add("FLUX.2 Easy Social Photos is missing node: $requiredNode")
            }
        }
        $easyNode = @($easySocialWorkflow.nodes | Where-Object { $_.type -eq "Flux2EasySocialPhoto" })[0]
        if ($easyNode -and @($easyNode.inputs).Count -ne 8) {
            $errors.Add("FLUX.2 Easy Social Photos must expose 4 photo inputs, prompt, style, framing, and moment.")
        }
        if ($easyNode -and $easyNode.widgets_values[0] -ne "Upload one face photo") {
            $errors.Add("FLUX.2 Easy Social Photos must open without a preselected identity image.")
        }
        if ($easyNode -and @($easyNode.widgets_values[1..3] | Where-Object { $_ -ne "No additional reference" }).Count -gt 0) {
            $errors.Add("FLUX.2 Easy Social Photos optional references must open empty.")
        }
    } catch {
        $errors.Add("FLUX.2 Easy Social Photos workflow JSON is invalid: $($_.Exception.Message)")
    }
}

foreach ($asset in @(
    @{ Name = "amalfi-balcony-template.png"; Source = "assets\comfy-input\amalfi-balcony-template.png" },
    @{ Name = "night-city-balcony-template.png"; Source = "assets\comfy-input\night-city-balcony-template.png" },
    @{ Name = "dating-01-night-out-a.png"; Source = "assets\comfy-input\dating-scenes\dating-01-night-out-a.png" },
    @{ Name = "dating-02-night-out-b.png"; Source = "assets\comfy-input\dating-scenes\dating-02-night-out-b.png" },
    @{ Name = "dating-03-cat-ragdoll.png"; Source = "assets\comfy-input\dating-scenes\dating-03-cat-ragdoll.png" },
    @{ Name = "dating-04-cat-tabby.png"; Source = "assets\comfy-input\dating-scenes\dating-04-cat-tabby.png" },
    @{ Name = "dating-05-golfer.png"; Source = "assets\comfy-input\dating-scenes\dating-05-golfer.png" },
    @{ Name = "dating-05-golfer-safe.png"; Source = "assets\comfy-input\dating-scenes\dating-05-golfer-safe.png" },
    @{ Name = "dating-06-amalfi.png"; Source = "assets\comfy-input\dating-scenes\dating-06-amalfi.png" },
    @{ Name = "dating-07-lake-boat.png"; Source = "assets\comfy-input\dating-scenes\dating-07-lake-boat.png" },
    @{ Name = "dating-08-restaurant.png"; Source = "assets\comfy-input\dating-scenes\dating-08-restaurant.png" },
    @{ Name = "dating-09-night-city.png"; Source = "assets\comfy-input\dating-scenes\dating-09-night-city.png" },
    @{ Name = "qwen-id-front.png"; Source = "assets\comfy-input\identity\qwen-id-front.png" },
    @{ Name = "qwen-id-left.png"; Source = "assets\comfy-input\identity\qwen-id-left.png" },
    @{ Name = "qwen-id-right.png"; Source = "assets\comfy-input\identity\qwen-id-right.png" },
    @{ Name = "body-silhouette.png"; Source = "assets\comfy-input\identity\body-silhouette.png" }
)) {
    $name = $asset.Name
    $sourcePath = Join-Path $RepoRoot $asset.Source
    $livePath = Join-Path $ComfyRoot ("input\mitch-workbench-" + $name)
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        $errors.Add("Missing scene template: $name")
        continue
    }
    if (-not (Test-Path -LiteralPath $livePath)) {
        $errors.Add("Scene template is not available to ComfyUI: $name")
        continue
    }
    $sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
    $liveHash = (Get-FileHash -LiteralPath $livePath -Algorithm SHA256).Hash
    if ($sourceHash -ne $liveHash) {
        $errors.Add("ComfyUI scene template is out of sync: $name")
    }
}

foreach ($model in @(
    @{ Path = "models\diffusion_models\flux-2-klein-base-4b-fp8.safetensors"; Sha256 = "44BAB3A86FE98B85D21DD2A4729EBDC3AE51FB8A39F76E457E18C724219E6840" },
    @{ Path = "models\text_encoders\qwen_3_4b_fp8_mixed.safetensors"; Sha256 = "72450B19758172C5A7273CF7DE729D1C17E7F434A104A00167624CBA94F68F15" },
    @{ Path = "models\loras\aitk\m1tch-flux2-klein-4b-identity-v1-best.safetensors"; Sha256 = "8A7D1477914D0A5262BF219F71F303418130449841CF220226B4E979D7232F87" },
    @{ Path = "models\vae\flux2-vae.safetensors"; Sha256 = "D64F3A68E1CC4F9F4E29B6E0DA38A0204FE9A49F2D4053F0EC1FA1CA02F9C4B5" }
)) {
    $modelPath = Join-Path $ComfyRoot $model.Path
    if (-not (Test-Path -LiteralPath $modelPath)) {
        $errors.Add("Missing FLUX.2 One Reference Photo model: $($model.Path)")
        continue
    }
    $actualHash = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash
    if ($actualHash -ne $model.Sha256) {
        $errors.Add("Unexpected SHA256 for FLUX.2 One Reference Photo model: $($model.Path)")
    }
}

Push-Location (Join-Path $RepoRoot "custom_nodes\ComfyUI-AIToolkit-Training")
try {
    & python -m unittest test_integration.py test_social_photo_core.py test_reference_photo_presets.py
    if ($LASTEXITCODE -ne 0) {
        $errors.Add("Python unit tests failed.")
    }
} finally {
    Pop-Location
}

try {
    foreach ($nodeName in @(
        "AlwaysRunImage",
        "AIToolkitTrainGeneratedDataset",
        "Flux2EasySocialPhoto",
        "Flux2OneReferencePhoto",
        "Flux2IdentityLoraExperiment",
        "Klein9BKVIdentityProof",
        "KSampler"
    )) {
        $info = Invoke-RestMethod -Uri "$ComfyUrl/object_info/$nodeName" -TimeoutSec 5
        if (-not $info.$nodeName) {
            $errors.Add("ComfyUI did not expose node: $nodeName")
        }
    }
} catch {
    $errors.Add("Could not verify the running ComfyUI API: $($_.Exception.Message)")
}

if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Host "Verified workflows, presets, unit tests, synchronized assets, model hashes, live links, and required ComfyUI nodes."
