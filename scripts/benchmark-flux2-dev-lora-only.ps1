param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [Parameter(Mandatory = $true)][string]$LoraName,
    [double]$LoraStrength = 1.0,
    [int]$Steps = 20,
    [double]$Guidance = 4.0,
    [UInt64]$BaseSeed = 8675310,
    [int]$Width = 832,
    [int]$Height = 1248,
    [int]$TimeoutSeconds = 2700,
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$Campaign = "flux2-dev-identity-v1",
    [string]$OutputPrefix = "identity-eval/flux2-dev-v1"
)

$ErrorActionPreference = "Stop"
$started = Get-Date
$repoRoot = Split-Path -Parent $PSScriptRoot
$trigger = "m1tch_person"
$safeName = ($LoraName -replace '[^A-Za-z0-9._-]', '-')
$strengthName = $LoraStrength.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
$runName = "$safeName-s$strengthName-$($started.ToString('yyyyMMdd-HHmmss'))"
$prefix = "$OutputPrefix/$runName"
$loraPath = Join-Path (Join-Path $ComfyRoot "models\loras") $LoraName

if (-not (Test-Path -LiteralPath $loraPath -PathType Leaf)) {
    throw "LoRA is not staged in the local ComfyUI model folder: $loraPath"
}
if ($Width * $Height -lt 900000 -or $Width * $Height -gt 1200000) {
    throw "Benchmark resolution must remain approximately one megapixel."
}

$queue = Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 10
if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
    throw "ComfyUI queue is not idle at $ComfyUrl."
}

$requiredNodes = @(
    "UNETLoader", "LoraLoaderModelOnly", "CLIPLoader", "CLIPTextEncode",
    "FluxGuidance", "BasicGuider", "KSamplerSelect", "Flux2Scheduler",
    "RandomNoise", "EmptyFlux2LatentImage", "SamplerCustomAdvanced",
    "VAELoader", "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $nodeInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info/$nodeName" -TimeoutSec 15
    if (-not $nodeInfo.PSObject.Properties[$nodeName]) {
        throw "Required node is unavailable: $nodeName"
    }
}

$modelInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info/UNETLoader" -TimeoutSec 15
if (@($modelInfo.UNETLoader.input.required.unet_name[0]) -notcontains "flux2_dev_fp8mixed.safetensors") {
    throw "FLUX.2 Dev is unavailable on $ComfyUrl."
}
$clipInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info/CLIPLoader" -TimeoutSec 15
if (@($clipInfo.CLIPLoader.input.required.clip_name[0]) -notcontains "mistral_3_small_flux2_fp4_mixed.safetensors") {
    throw "The required FLUX.2 Mistral encoder is unavailable on $ComfyUrl."
}
$vaeInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info/VAELoader" -TimeoutSec 15
if (@($vaeInfo.VAELoader.input.required.vae_name[0]) -notcontains "flux2-vae.safetensors") {
    throw "The required FLUX.2 VAE is unavailable on $ComfyUrl."
}
$loraInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info/LoraLoaderModelOnly" -TimeoutSec 15
if (@($loraInfo.LoraLoaderModelOnly.input.required.lora_name[0]) -notcontains $LoraName) {
    throw "ComfyUI has not discovered the staged LoRA: $LoraName"
}

$scenes = @(
    [ordered]@{
        label = "portrait"
        seed = $BaseSeed
        prompt = "An ordinary unedited smartphone portrait of $trigger, an adult man, seated at a neighborhood cafe in soft open shade, head and shoulders, navy crew-neck T-shirt, relaxed natural half-smile, looking at the camera, realistic pores and fine facial detail, believable phone-camera exposure, no beauty filter."
    },
    [ordered]@{
        label = "waist-up-social"
        seed = $BaseSeed + 1
        prompt = "A candid waist-up social smartphone photo of $trigger, an adult man, standing at a casual backyard gathering in late-afternoon daylight, pale blue open-collar shirt, relaxed expression, looking toward a friend beside the camera, natural skin texture, ordinary phone-camera depth and exposure."
    },
    [ordered]@{
        label = "near-profile-candid"
        seed = $BaseSeed + 2
        prompt = "A realistic near-profile candid smartphone photograph of $trigger, an adult man, browsing books in a quiet independent bookstore, head and upper torso visible from his left side, neutral thoughtful expression, natural indoor window light, true skin and hair detail."
    },
    [ordered]@{
        label = "full-body-walking"
        seed = $BaseSeed + 3
        prompt = "A candid solo full-body smartphone photograph of $trigger, an adult man, walking naturally along a city sidewalk in casual fitted clothing, photographed by a friend, entire body and both feet visible, realistic daylight, believable proportions and slight natural motion."
    },
    [ordered]@{
        label = "friends-crowd-stress"
        seed = $BaseSeed + 4
        prompt = "An ordinary wide smartphone group photo of $trigger, an adult man, at an outdoor neighborhood festival with five unrelated adult friends of varied ages, genders, hair, and facial features, everyone clearly visible and naturally spaced, $trigger near the center in a navy shirt, realistic daylight and deep phone-camera focus."
    }
)

function Invoke-BenchmarkScene {
    param([System.Collections.IDictionary]$Scene)

    $workflow = [ordered]@{
        "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = "flux2_dev_fp8mixed.safetensors"; weight_dtype = "default" } }
        "2" = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $LoraName; strength_model = $LoraStrength } }
        "3" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = "mistral_3_small_flux2_fp4_mixed.safetensors"; type = "flux2"; device = "default" } }
        "4" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $Scene.prompt; clip = @("3", 0) } }
        "5" = @{ class_type = "FluxGuidance"; inputs = @{ conditioning = @("4", 0); guidance = $Guidance } }
        "6" = @{ class_type = "BasicGuider"; inputs = @{ model = @("2", 0); conditioning = @("5", 0) } }
        "7" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
        "8" = @{ class_type = "Flux2Scheduler"; inputs = @{ width = $Width; height = $Height; steps = $Steps } }
        "9" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Scene.seed } }
        "10" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
        "11" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("9", 0); guider = @("6", 0); sampler = @("7", 0); sigmas = @("8", 0); latent_image = @("10", 0) } }
        "12" = @{ class_type = "VAELoader"; inputs = @{ vae_name = "flux2-vae.safetensors" } }
        "13" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("11", 0); vae = @("12", 0) } }
        "14" = @{ class_type = "SaveImage"; inputs = @{ images = @("13", 0); filename_prefix = "$prefix-$($Scene.label)" } }
    }

    $body = @{ prompt = $workflow; client_id = "flux2-dev-lora-only-benchmark" } | ConvertTo-Json -Depth 30
    $queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
    if (-not $queued.prompt_id) {
        throw "ComfyUI did not return a prompt_id for $($Scene.label)."
    }
    Write-Host "Queued $($Scene.label): $($queued.prompt_id)"

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        Start-Sleep -Seconds 2
        $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 15
        $entry = $history.PSObject.Properties[$queued.prompt_id].Value
        if ($entry -and $entry.status.status_str -eq "error") {
            throw "Generation failed for $($Scene.label): $($entry.status.messages | ConvertTo-Json -Depth 20)"
        }
        if ($entry -and $entry.status.completed) {
            $image = @($entry.outputs."14".images)[0]
            if (-not $image) {
                throw "Generation completed without an image for $($Scene.label)."
            }
            $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
            return Join-Path (Join-Path $ComfyRoot "output") $relative
        }
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for $($Scene.label)."
}

$outputs = [ordered]@{}
foreach ($scene in $scenes) {
    $outputs[$scene.label] = Invoke-BenchmarkScene -Scene $scene
}

$reportPath = Join-Path $repoRoot "work\$Campaign\benchmarks\$runName.json"
$references = @(
    Get-ChildItem -LiteralPath (Join-Path $repoRoot "datasets\mitch-identity-stills-v3\validation") -Filter "*.jpg" -File |
        Sort-Object Name
)
if ($references.Count -ne 6) {
    throw "Expected six held-out validation photos, found $($references.Count)."
}

$evalArgs = [System.Collections.Generic.List[string]]::new()
$evalArgs.Add((Join-Path $repoRoot "scripts\evaluate-flux2-dev-identity.py"))
foreach ($reference in $references) {
    $evalArgs.Add("--reference")
    $evalArgs.Add($reference.FullName)
}
foreach ($label in @("portrait", "waist-up-social", "near-profile-candid", "full-body-walking")) {
    $evalArgs.Add("--scene")
    $evalArgs.Add("$label=$($outputs[$label])")
}
$evalArgs.Add("--crowd")
$evalArgs.Add($outputs["friends-crowd-stress"])
$evalArgs.Add("--json-output")
$evalArgs.Add($reportPath)

& "C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe" @evalArgs
$evaluationExitCode = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $reportPath -PathType Leaf)) {
    throw "Local identity evaluator did not produce its report."
}

$report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
$report | Add-Member -NotePropertyName benchmark -NotePropertyValue ([pscustomobject]@{
    lora_name = $LoraName
    lora_path = $loraPath
    lora_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $loraPath).Hash.ToLowerInvariant()
    lora_strength = $LoraStrength
    base_model = "flux2_dev_fp8mixed.safetensors"
    text_encoder = "mistral_3_small_flux2_fp4_mixed.safetensors"
    vae = "flux2-vae.safetensors"
    trigger = $trigger
    reference_conditioning = $false
    face_swap = $false
    masks = $false
    restoration = $false
    post_processing = $false
    sampler = "euler"
    steps = $Steps
    guidance = $Guidance
    width = $Width
    height = $Height
    base_seed = $BaseSeed
    scene_seeds = [ordered]@{
        portrait = $BaseSeed
        waist_up_social = $BaseSeed + 1
        near_profile_candid = $BaseSeed + 2
        full_body_walking = $BaseSeed + 3
        friends_crowd_stress = $BaseSeed + 4
    }
    prompts = @($scenes)
    raw_outputs = $outputs
    comfy_url = $ComfyUrl
    duration_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
})
$report.acceptance.promotion_eligible = $false
$report | Add-Member -NotePropertyName manual_review -NotePropertyValue ([pscustomobject]@{
    status = "pending"
    required_checks = @(
        "full-size and thumbnail identity",
        "apparent age",
        "hair",
        "facial geometry",
        "skin texture",
        "expression",
        "whole-frame scene integration",
        "full-body proportions and face scale",
        "secondary-person identity leakage"
    )
})
$report | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $reportPath -Encoding utf8

Write-Host "Saved FLUX.2 Dev LoRA-only benchmark: $reportPath"
if ($evaluationExitCode -ne 0) {
    Write-Error "The automatic identity or crowd gate failed. The checkpoint must not be promoted." -ErrorAction Continue
    exit 2
}
Write-Host "Automatic gates passed. Manual full-size and thumbnail review is still required before promotion."
