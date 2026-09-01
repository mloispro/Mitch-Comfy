[CmdletBinding()]
param(
    [string]$ComfyUrl = "http://127.0.0.1:8189",
    [Parameter(Mandatory = $true)][string]$LoraName,
    [double]$LoraStrength = 0.6,
    [ValidateSet("Quick", "Full")][string]$Profile = "Quick",
    [int]$Steps = 20,
    [double]$Guidance = 4.0,
    [long]$SeedBase = 8675310,
    [int]$TimeoutSeconds = 900,
    [string]$ComfyOutputRoot = "C:\projects\AI-Tools\ComfyUI\output\gpu-4070"
)

$ErrorActionPreference = "Stop"
$started = Get-Date
$repoRoot = Split-Path -Parent $PSScriptRoot
$trigger = "m1tch_person"
$safeName = (($LoraName -replace '[\\/]', '-') -replace '[^A-Za-z0-9._-]', '-')
$strengthName = $LoraStrength.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
$prefix = "identity-eval/v3/$safeName-s$strengthName"

$scenes = @(
    @{
        name = "phone-portrait"
        prompt = "An ordinary unedited smartphone photo of $trigger, an adult man, seated on a neighborhood restaurant patio in soft open shade, waist-up, navy crew-neck T-shirt, relaxed natural half-smile, looking at the camera, realistic pores and fine facial detail, believable phone-camera exposure, no beauty filter."
    },
    @{
        name = "professional"
        prompt = "A realistic professional photograph of $trigger, an adult man, standing beside a large office window, waist-up three-quarter view, charcoal blazer over a pale blue open-collar shirt, calm confident expression looking just past the camera, natural 50mm lens perspective, restrained retouching and true skin texture."
    }
)
if ($Profile -eq "Full") {
    $scenes += @(
        @{
            name = "full-body-action"
            prompt = "A candid full-body smartphone photograph of $trigger, an adult man, crossing a downtown street in casual fitted clothes, natural walking stride, looking away from the camera, photographed by a friend, entire body visible, realistic daylight and slight believable motion."
        },
        @{
            name = "side-profile"
            prompt = "A realistic left side-profile photograph of $trigger, an adult man, browsing books in a quiet independent bookstore, head and shoulders visible from his left side, neutral thoughtful expression, natural indoor window light, true skin and hair detail."
        }
    )
}

$candidates = [System.Collections.Generic.List[string]]::new()
$candidateLabels = [System.Collections.Generic.List[string]]::new()
for ($sceneIndex = 0; $sceneIndex -lt $scenes.Count; $sceneIndex++) {
    $scene = $scenes[$sceneIndex]
    $sceneSeed = $SeedBase + $sceneIndex
    $workflow = @{
        "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = "flux-2-klein-base-4b-fp8.safetensors"; weight_dtype = "default" } }
        "2" = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $LoraName; strength_model = $LoraStrength } }
        "3" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = "qwen_3_4b_fp8_mixed.safetensors"; type = "flux2" } }
        "4" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $scene.prompt; clip = @("3", 0) } }
        "5" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("3", 0) } }
        "6" = @{ class_type = "CFGGuider"; inputs = @{ model = @("2", 0); positive = @("4", 0); negative = @("5", 0); cfg = $Guidance } }
        "7" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
        "8" = @{ class_type = "Flux2Scheduler"; inputs = @{ width = 768; height = 1024; steps = $Steps } }
        "9" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $sceneSeed } }
        "10" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = 768; height = 1024; batch_size = 1 } }
        "11" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("9", 0); guider = @("6", 0); sampler = @("7", 0); sigmas = @("8", 0); latent_image = @("10", 0) } }
        "12" = @{ class_type = "VAELoader"; inputs = @{ vae_name = "flux2-vae.safetensors" } }
        "13" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("11", 0); vae = @("12", 0) } }
        "14" = @{ class_type = "SaveImage"; inputs = @{ images = @("13", 0); filename_prefix = "$prefix-$($scene.name)" } }
    }

    $body = @{ prompt = $workflow; client_id = "flux2-klein-identity-v3-benchmark" } | ConvertTo-Json -Depth 20
    $queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
    if (-not $queued.prompt_id) {
        throw "ComfyUI did not return a prompt_id for $($scene.name)."
    }
    Write-Host "Queued $($scene.name) with seed ${sceneSeed}: $($queued.prompt_id)"

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $entry = $null
    do {
        Start-Sleep -Seconds 2
        $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 10
        $entry = $history.($queued.prompt_id)
        if ($entry -and $entry.status.status_str -eq "error") {
            $entry | ConvertTo-Json -Depth 12
            throw "LoRA-only generation failed for $($scene.name)."
        }
        if ($entry -and $entry.status.status_str -eq "success") {
            $image = @($entry.outputs."14".images)[0]
            $candidates.Add((Join-Path $ComfyOutputRoot (Join-Path $image.subfolder $image.filename)))
            $candidateLabels.Add($scene.name)
            break
        }
    } while ((Get-Date) -lt $deadline)
    if (-not $entry -or $entry.status.status_str -ne "success") {
        throw "Timed out waiting for $($scene.name)."
    }
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportPath = Join-Path $repoRoot ("work\flux2-klein-identity-v3\benchmarks\$safeName-s$strengthName-$Profile-$stamp.json")
$evalArgs = [System.Collections.Generic.List[string]]::new()
$evalArgs.Add((Join-Path $repoRoot "scripts\evaluate-face-likeness.py"))
foreach ($reference in @(
    "val_01_surf_full_body.jpg",
    "val_02_body_mirror_sleeveless.jpg",
    "val_03_navy_upper_body.jpg",
    "val_04_window_small_smile.jpg",
    "val_05_balcony_opposite_angle.jpg",
    "val_06_car_daylight.jpg"
)) {
    $evalArgs.Add("--reference")
    $evalArgs.Add((Join-Path $repoRoot ("datasets\mitch-identity-stills-v3\validation\" + $reference)))
}
for ($index = 0; $index -lt $candidates.Count; $index++) {
    $evalArgs.Add("--candidate")
    $evalArgs.Add($candidates[$index])
    $evalArgs.Add("--candidate-label")
    $evalArgs.Add($candidateLabels[$index])
}
$evalArgs.Add("--json-output")
$evalArgs.Add($reportPath)

& "C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe" @evalArgs
if ($LASTEXITCODE -ne 0) {
    throw "Local identity evaluation failed."
}
$report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
$report | Add-Member -NotePropertyName benchmark -NotePropertyValue ([pscustomobject]@{
    lora_name = $LoraName
    lora_strength = $LoraStrength
    profile = $Profile
    model = "flux-2-klein-base-4b-fp8.safetensors"
    sampler = "euler"
    steps = $Steps
    guidance = $Guidance
    width = 768
    height = 1024
    seed_base = $SeedBase
    trigger = $trigger
    reference_conditioning = $false
    duration_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
    manual_full_size_and_thumbnail_review_required = $true
})
$report | ConvertTo-Json -Depth 24 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Host "Saved LoRA-only benchmark: $reportPath"
Write-Host "Automated identity similarity is diagnostic only; manual review remains required."
