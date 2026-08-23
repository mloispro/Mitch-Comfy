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
    "workflows\production\FLUX.2 Easy Social Photos v1.0.3 - 1-4 References.json",
    "workflows\production\FLUX.2 Easy Social Photos v1.0.4 - Auto Scene Routing.json",
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
            if ($baseline.active -eq $false) {
                continue
            }
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

$easySocialWorkflowPath = Join-Path $RepoRoot "workflows\production\FLUX.2 Easy Social Photos v1.0.3 - 1-4 References.json"
if (Test-Path -LiteralPath $easySocialWorkflowPath) {
    try {
        $easySocialWorkflow = Get-Content -Raw -LiteralPath $easySocialWorkflowPath | ConvertFrom-Json
        if ($easySocialWorkflow.nodes.Count -ne 2) {
            $errors.Add("FLUX.2 Easy Social Photos must contain exactly 2 visible nodes; found $($easySocialWorkflow.nodes.Count).")
        }
        foreach ($requiredNode in @("Flux2EasySocialPhotoV103", "PreviewImage")) {
            if ($requiredNode -notin @($easySocialWorkflow.nodes.type)) {
                $errors.Add("FLUX.2 Easy Social Photos is missing node: $requiredNode")
            }
        }
        $easyNode = @($easySocialWorkflow.nodes | Where-Object { $_.type -eq "Flux2EasySocialPhotoV103" })[0]
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

$easySocialNodePath = Join-Path $RepoRoot "custom_nodes\ComfyUI-AIToolkit-Training\reference_photo_studio.py"
if (Test-Path -LiteralPath $easySocialNodePath) {
    $easySocialSource = Get-Content -Raw -LiteralPath $easySocialNodePath
    foreach ($requiredSetting in @("OUTPUT_WIDTH = 896", "OUTPUT_HEIGHT = 1344")) {
        if ($easySocialSource -notmatch [regex]::Escape($requiredSetting)) {
            $errors.Add("FLUX.2 Easy Social Photos is missing frozen detail setting: $requiredSetting")
        }
    }
    if ($easySocialSource -match "baseline\._generate_photo") {
        $errors.Add("FLUX.2 Easy Social Photos must use one unified 1-4 reference generation path.")
    }
}

$routedSocialWorkflowPath = Join-Path $RepoRoot "workflows\production\FLUX.2 Easy Social Photos v1.0.4 - Auto Scene Routing.json"
if (Test-Path -LiteralPath $routedSocialWorkflowPath) {
    try {
        $routedSocialWorkflow = Get-Content -Raw -LiteralPath $routedSocialWorkflowPath | ConvertFrom-Json
        if ($routedSocialWorkflow.nodes.Count -ne 2) {
            $errors.Add("FLUX.2 Easy Social Photos v1.0.4 must contain exactly 2 visible nodes; found $($routedSocialWorkflow.nodes.Count).")
        }
        foreach ($requiredNode in @("Flux2EasySocialPhotoV104", "PreviewImage")) {
            if ($requiredNode -notin @($routedSocialWorkflow.nodes.type)) {
                $errors.Add("FLUX.2 Easy Social Photos v1.0.4 is missing node: $requiredNode")
            }
        }
        $routedNode = @($routedSocialWorkflow.nodes | Where-Object { $_.type -eq "Flux2EasySocialPhotoV104" })[0]
        if ($routedNode -and @($routedNode.inputs).Count -ne 8) {
            $errors.Add("FLUX.2 Easy Social Photos v1.0.4 must expose only 4 photo inputs, prompt, style, framing, and moment.")
        }
        if ($routedNode -and $routedNode.widgets_values[0] -ne "Upload one face photo") {
            $errors.Add("FLUX.2 Easy Social Photos v1.0.4 must open without a preselected identity image.")
        }
        if ($routedNode -and @($routedNode.widgets_values[1..3] | Where-Object { $_ -ne "No additional reference" }).Count -gt 0) {
            $errors.Add("FLUX.2 Easy Social Photos v1.0.4 optional references must open empty.")
        }
        if ((Get-Content -Raw -LiteralPath $routedSocialWorkflowPath) -match "quality gate|scene-checked") {
            $errors.Add("FLUX.2 Easy Social Photos v1.0.4 must not claim an automatic visual quality gate.")
        }
    } catch {
        $errors.Add("FLUX.2 Easy Social Photos v1.0.4 workflow JSON is invalid: $($_.Exception.Message)")
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
    @{ Path = "models\diffusion_models\z_image_bf16.safetensors"; Sha256 = "996A67D3FF666946B1C25CBC16D1B1918B6CC0AC166309E23FE3B3D830263DEE" },
    @{ Path = "models\diffusion_models\flux-2-klein-base-4b-fp8.safetensors"; Sha256 = "44BAB3A86FE98B85D21DD2A4729EBDC3AE51FB8A39F76E457E18C724219E6840" },
    @{ Path = "models\text_encoders\qwen_3_4b_fp8_mixed.safetensors"; Sha256 = "72450B19758172C5A7273CF7DE729D1C17E7F434A104A00167624CBA94F68F15" },
    @{ Path = "models\loras\aitk\m1tch-flux2-klein-4b-identity-v1-best.safetensors"; Sha256 = "8A7D1477914D0A5262BF219F71F303418130449841CF220226B4E979D7232F87" },
    @{ Path = "models\vae\flux2-vae.safetensors"; Sha256 = "D64F3A68E1CC4F9F4E29B6E0DA38A0204FE9A49F2D4053F0EC1FA1CA02F9C4B5" },
    @{ Path = "models\vae\ae.safetensors"; Sha256 = "AFC8E28272CD15DB3919BACDB6918CE9C1ED22E96CB12C4D5ED0FBA823529E38" },
    @{ Path = "models\ultralytics\bbox\yolo11n.pt"; Sha256 = "0EBBC80D4A7680D14987A577CD21342B65ECFD94632BD9A8DA63AE6417644EE1" },
    @{ Path = "models\rembg\u2net_human_seg.onnx"; Sha256 = "01EB6A29A5C4D8EDB30B56ADAD9BB3A2A0535338E480724A213E0ACFD2D1C73C" }
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

$comfyPython = Join-Path $ComfyRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $comfyPython)) {
    $errors.Add("Missing ComfyUI Python runtime: $comfyPython")
} else {
    & $comfyPython -c "import importlib.metadata as m; assert m.version('ultralytics') == '8.4.76'; assert m.version('rembg') == '2.0.69'"
    if ($LASTEXITCODE -ne 0) {
        $errors.Add("ComfyUI requires ultralytics 8.4.76 and rembg 2.0.69 for v1.0.4 complex routing.")
    }
}

Push-Location (Join-Path $RepoRoot "custom_nodes\ComfyUI-AIToolkit-Training")
try {
    & python -m unittest test_integration.py test_social_photo_core.py test_reference_photo_presets.py test_phone_lens_optics.py test_scene_quality.py test_identity_scope.py test_scene_crop.py test_scene_constraints.py test_scene_objects.py test_camera_finish.py
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
        "Flux2EasySocialPhotoV103",
        "Flux2EasySocialPhotoV104",
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
    $easyInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info/Flux2EasySocialPhotoV104" -TimeoutSec 5
    $livePhotoStyles = @($easyInfo.Flux2EasySocialPhotoV104.input.required.photo_style[0])
    if ("Smartphone — slight lens haze" -notin $livePhotoStyles) {
        $errors.Add("Live FLUX.2 Easy Social Photos is missing the slight phone-lens haze preset.")
    }
} catch {
    $errors.Add("Could not verify the running ComfyUI API: $($_.Exception.Message)")
}

if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Host "Verified workflows, presets, unit tests, synchronized assets, model hashes, live links, and required ComfyUI nodes."
