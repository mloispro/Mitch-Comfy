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
    "workflows\production\Social Photo Studio - FLUX.2 Klein 9B KV.json",
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

$socialWorkflowPath = Join-Path $RepoRoot "workflows\production\Social Photo Studio - FLUX.2 Klein 9B KV.json"
if (Test-Path -LiteralPath $socialWorkflowPath) {
    try {
        $socialWorkflow = Get-Content -Raw -LiteralPath $socialWorkflowPath | ConvertFrom-Json
        if ($socialWorkflow.nodes.Count -gt 9) {
            $errors.Add("Social Photo Studio must remain at or below 9 visible nodes; found $($socialWorkflow.nodes.Count).")
        }
        foreach ($requiredNode in @("SocialPhotoSubjectReferences", "SocialPhotoSettings", "SocialPhotoGenerate")) {
            if ($requiredNode -notin @($socialWorkflow.nodes.type)) {
                $errors.Add("Social Photo Studio workflow is missing node: $requiredNode")
            }
        }
        $subjectNode = @($socialWorkflow.nodes | Where-Object { $_.type -eq "SocialPhotoSubjectReferences" })[0]
        if ($subjectNode -and $subjectNode.widgets_values[0] -ne "Upload reference 1") {
            $errors.Add("Social Photo Studio must open with an empty required reference, never a preselected identity image.")
        }
        if ((Get-Content -Raw -LiteralPath $socialWorkflowPath) -match "mitch(?:-workbench)?-qwen-id-(front|left|right)") {
            $errors.Add("Social Photo Studio production workflow contains a generated identity fixture.")
        }
    } catch {
        $errors.Add("Social Photo Studio workflow JSON is invalid: $($_.Exception.Message)")
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
    @{ Path = "models\diffusion_models\flux-2-klein-9b-kv-fp8.safetensors"; Sha256 = "33F7DA5625A00798349A719742999D3C7DD20C1A7EDA14663922C363640728F1" },
    @{ Path = "models\text_encoders\qwen_3_8b_fp8mixed.safetensors"; Sha256 = "ABAD16806E0CBABC54E0325D6565847443FE396D5F0BE38BB3CD3FE75A1201D6" },
    @{ Path = "models\vae\flux2-vae.safetensors"; Sha256 = "D64F3A68E1CC4F9F4E29B6E0DA38A0204FE9A49F2D4053F0EC1FA1CA02F9C4B5" }
)) {
    $modelPath = Join-Path $ComfyRoot $model.Path
    if (-not (Test-Path -LiteralPath $modelPath)) {
        $errors.Add("Missing Social Photo Studio model: $($model.Path)")
        continue
    }
    $actualHash = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash
    if ($actualHash -ne $model.Sha256) {
        $errors.Add("Unexpected SHA256 for Social Photo Studio model: $($model.Path)")
    }
}

Push-Location (Join-Path $RepoRoot "custom_nodes\ComfyUI-AIToolkit-Training")
try {
    & python -m unittest test_integration.py test_social_photo_core.py
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
        "SocialPhotoSubjectReferences",
        "SocialPhotoSettings",
        "SocialPhotoGenerate",
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
