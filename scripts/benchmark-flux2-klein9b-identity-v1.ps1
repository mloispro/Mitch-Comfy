[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$LoraName,
    [double]$LoraStrength = 0.9,
    [ValidateSet("Quick", "Full")][string]$Profile = "Quick",
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [int]$Steps = 50,
    [double]$Guidance = 4.0,
    [long]$SeedBase = 8676310,
    [int]$TimeoutSeconds = 1800,
    [string]$ComfyOutputRoot = "C:\projects\AI-Tools\ComfyUI\output",
    [string]$WorkRunName = "flux2-klein9b-identity-v1",
    [string]$StagingManifestName = "checkpoint-staging.json",
    [string]$OutputNamespace = "klein9b-v1",
    [string]$ReferenceDatasetName = "mitch-identity-stills-v3",
    [string]$ReferenceSubdirectory = "validation",
    [switch]$BidirectionalProfiles,
    [string[]]$CalibrationReferenceFiles = @(),
    [string[]]$ReferenceFiles = @(
        "val_01_surf_full_body.jpg",
        "val_02_body_mirror_sleeveless.jpg",
        "val_03_navy_upper_body.jpg",
        "val_04_window_small_smile.jpg",
        "val_05_balcony_opposite_angle.jpg",
        "val_06_car_daylight.jpg"
    )
)

$ErrorActionPreference = "Stop"
$started = Get-Date
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ComfyPython = "C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe"
$BaseModelName = "flux-2-klein-base-9b-bf16.safetensors"
$TextEncoderName = "qwen_3_8b_fp8mixed.safetensors"
$VaeName = "flux2-vae.safetensors"
$Trigger = "m1tch_person"
$SafeName = (($LoraName -replace '[\\/]', '-') -replace '[^A-Za-z0-9._-]', '-')
$StrengthName = $LoraStrength.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
$Prefix = "identity-eval/$OutputNamespace/$SafeName-s$StrengthName-$($Profile.ToLowerInvariant())"
$ComfyRoot = Split-Path -Parent $ComfyOutputRoot
$LoraPath = Join-Path (Join-Path $ComfyRoot "models\loras") $LoraName
$StagingManifestPath = Join-Path $RepoRoot "work\$WorkRunName\$StagingManifestName"

if (-not (Test-Path -LiteralPath $LoraPath -PathType Leaf)) {
    throw "Staged LoRA is missing: $LoraPath"
}
if (-not (Test-Path -LiteralPath $StagingManifestPath -PathType Leaf)) {
    throw "Checkpoint-staging manifest is missing: $StagingManifestPath"
}
$stagingManifest = Get-Content -Raw -LiteralPath $StagingManifestPath | ConvertFrom-Json
$stagingRecords = @($stagingManifest.checkpoints | Where-Object { [string]$_.comfy_lora_name -ceq $LoraName })
if ($stagingRecords.Count -ne 1) {
    throw "Expected exactly one staging record for $LoraName, found $($stagingRecords.Count)."
}
$LoraSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $LoraPath).Hash.ToUpperInvariant()
if ($LoraSha256 -cne [string]$stagingRecords[0].sha256) {
    throw "Staged LoRA hash does not match checkpoint-staging.json for $LoraName."
}

function Test-LocalTcpListener([int]$Port) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync('127.0.0.1', $Port)
        return ($task.Wait(1000) -and $client.Connected)
    }
    catch { return $false }
    finally { $client.Dispose() }
}

$otherComfyUrl = "http://127.0.0.1:8189"
$otherState = Invoke-RestMethod -Uri "$otherComfyUrl/system_stats" -TimeoutSec 10
$otherDevice = [string](@($otherState.devices)[0].name)
if ($otherDevice -notmatch "RTX 4070") { throw "$otherComfyUrl is not the RTX 4070 worker: $otherDevice" }
$otherQueue = Invoke-RestMethod -Uri "$otherComfyUrl/queue" -TimeoutSec 10
$otherRunningAtStart = @($otherQueue.queue_running).Count
$otherPendingAtStart = @($otherQueue.queue_pending).Count
if ($otherRunningAtStart -gt 0 -or $otherPendingAtStart -gt 0) {
    Write-Warning "The RTX 4070 worker is active and will be left untouched."
}

$aux3090 = [ordered]@{ port = 8190; online = $false; device = 'offline'; running = 0; pending = 0 }
try {
    $auxStats = Invoke-RestMethod -Uri "http://127.0.0.1:8190/system_stats" -TimeoutSec 5
    $auxQueue = Invoke-RestMethod -Uri "http://127.0.0.1:8190/queue" -TimeoutSec 5
    $aux3090.online = $true
    $aux3090.device = [string](@($auxStats.devices)[0].name)
    $aux3090.running = @($auxQueue.queue_running).Count
    $aux3090.pending = @($auxQueue.queue_pending).Count
    if ($aux3090.device -notmatch 'RTX 3090') { throw "SAFETY: Port 8190 is not the auxiliary RTX 3090 worker: $($aux3090.device)" }
    if ($aux3090.running -gt 0 -or $aux3090.pending -gt 0) { throw "SAFETY: Auxiliary RTX 3090 worker on port 8190 has active work; evaluation will not compete with it." }
}
catch {
    if ($_.Exception.Message -like 'SAFETY:*') { throw }
    if (Test-LocalTcpListener 8190) { throw "SAFETY: Port 8190 is listening but its RTX 3090 queue state could not be verified: $($_.Exception.Message)" }
}
$forge = [ordered]@{ port = 7860; online = $false; active = $false }
try {
    $forgeProgress = Invoke-RestMethod -Uri 'http://127.0.0.1:7860/sdapi/v1/progress?skip_current_image=true' -TimeoutSec 5
    $forge.online = $true
    $forge.active = ([double]$forgeProgress.progress -gt 0 -or -not [string]::IsNullOrWhiteSpace([string]$forgeProgress.state.job))
    if ($forge.active) { throw 'SAFETY: Forge has active RTX 3090 work; evaluation will not compete with it.' }
}
catch {
    if ($_.Exception.Message -like 'SAFETY:*') { throw }
    if (Test-LocalTcpListener 7860) { throw "SAFETY: Forge port 7860 is listening but its RTX 3090 activity state could not be verified: $($_.Exception.Message)" }
}

$state = Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 10
$device = [string](@($state.devices)[0].name)
if ($device -notmatch "RTX 3090") { throw "$ComfyUrl is not the RTX 3090 worker: $device" }
$queue = Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 10
if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) { throw "RTX 3090 ComfyUI is not idle." }

$requiredNodes = @(
    @{ Class = "UNETLoader"; Field = "unet_name"; Value = $BaseModelName },
    @{ Class = "LoraLoaderModelOnly"; Field = "lora_name"; Value = $LoraName },
    @{ Class = "CLIPLoader"; Field = "clip_name"; Value = $TextEncoderName },
    @{ Class = "VAELoader"; Field = "vae_name"; Value = $VaeName },
    @{ Class = "EmptyFlux2LatentImage"; Field = $null; Value = $null },
    @{ Class = "Flux2Scheduler"; Field = $null; Value = $null },
    @{ Class = "CFGGuider"; Field = $null; Value = $null },
    @{ Class = "SamplerCustomAdvanced"; Field = $null; Value = $null }
)
foreach ($required in $requiredNodes) {
    $nodeInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info/$($required.Class)" -TimeoutSec 30
    $node = $nodeInfo.($required.Class)
    if (-not $node) { throw "Required live node is unavailable on the RTX 3090 worker: $($required.Class)" }
    if ($required.Field) {
        $choices = @($node.input.required.($required.Field)[0])
        if ($required.Value -notin $choices) {
            throw "Required live $($required.Field) value is unavailable for $($required.Class): $($required.Value)"
        }
    }
}

$portraitScene = [ordered]@{
    label = "portrait"
    prompt = "A realistic close smartphone portrait of $Trigger, an adult man, outdoors in soft natural daylight, facing the camera with a relaxed neutral expression, navy crew-neck shirt, natural skin pores and fine facial detail, ordinary unedited phone-camera exposure."
}
$leftProfileScene = [ordered]@{
    label = if ($BidirectionalProfiles) { "profile-image-left" } else { "near-profile-candid" }
    prompt = "A realistic candid chest-up photograph of $Trigger, an adult man, on a city rooftop at night, head and eyes turned down toward image-left in a strong left three-quarter to near-profile view, no eye contact, calm expression, natural available light, true skin and hair detail."
}
$rightProfileScene = [ordered]@{
    label = "profile-image-right"
    prompt = "A realistic candid chest-up photograph of $Trigger, an adult man, beside a large window in ordinary daylight, head and eyes turned toward image-right in a strong right three-quarter to near-profile view, no eye contact, calm expression, true skin and hair detail."
}
$scenes = if ($BidirectionalProfiles) {
    @($portraitScene, $leftProfileScene, $rightProfileScene)
} else {
    @($portraitScene, $leftProfileScene)
}
if ($Profile -eq "Full") {
    $waistScene = [ordered]@{
        label = "waist-up-social"
        prompt = "An ordinary unedited smartphone photograph of $Trigger, an adult man, seated on a neighborhood restaurant patio in soft open shade, waist-up, relaxed natural half-smile looking at the camera, believable phone-camera exposure, no beauty filter."
    }
    $bodyScene = [ordered]@{
        label = "full-body-walking"
        prompt = "A candid full-body smartphone photograph of $Trigger, an adult man, crossing a downtown sidewalk in casual fitted clothes, natural walking stride, looking away from the camera, entire body visible from head to shoes, realistic daylight, coherent arms and hands."
    }
    $crowdScene = [ordered]@{
        label = "crowd"
        prompt = "A realistic group smartphone photograph in a stylish hotel lounge with exactly five distinct adults. $Trigger is the only Mitch and sits centered nearest the camera in a navy blazer and white shirt. Four visually distinct friends sit around him, with different faces, hair, ages, and skin tones. Exactly five people, no duplicate person, coherent arms and hands, ordinary warm available light."
    }
    $scenes = if ($BidirectionalProfiles) {
        @($portraitScene, $waistScene, $leftProfileScene, $rightProfileScene, $bodyScene, $crowdScene)
    } else {
        @($portraitScene, $waistScene, $leftProfileScene, $bodyScene, $crowdScene)
    }
}

$outputs = [ordered]@{}
for ($index = 0; $index -lt $scenes.Count; $index++) {
    $scene = $scenes[$index]
    $seed = $SeedBase + $index
    $workflow = @{
        "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $BaseModelName; weight_dtype = "default" } }
        "2" = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $LoraName; strength_model = $LoraStrength } }
        "3" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $TextEncoderName; type = "flux2" } }
        "4" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $scene.prompt; clip = @("3", 0) } }
        "5" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("3", 0) } }
        "6" = @{ class_type = "CFGGuider"; inputs = @{ model = @("2", 0); positive = @("4", 0); negative = @("5", 0); cfg = $Guidance } }
        "7" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
        "8" = @{ class_type = "Flux2Scheduler"; inputs = @{ width = 832; height = 1216; steps = $Steps } }
        "9" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $seed } }
        "10" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = 832; height = 1216; batch_size = 1 } }
        "11" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("9", 0); guider = @("6", 0); sampler = @("7", 0); sigmas = @("8", 0); latent_image = @("10", 0) } }
        "12" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $VaeName } }
        "13" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("11", 0); vae = @("12", 0) } }
        "14" = @{ class_type = "SaveImage"; inputs = @{ images = @("13", 0); filename_prefix = "$Prefix-$($scene.label)" } }
    }
    $body = @{ prompt = $workflow; client_id = "flux2-klein9b-identity-benchmark-$OutputNamespace" } | ConvertTo-Json -Depth 20
    $queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
    if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt_id for $($scene.label)." }
    Write-Host "Queued $($scene.label), seed $seed`: $($queued.prompt_id)"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $entry = $null
    do {
        Start-Sleep -Seconds 2
        $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 10
        $entry = $history.($queued.prompt_id)
        if ($entry -and $entry.status.status_str -eq "error") {
            $entry | ConvertTo-Json -Depth 15
            throw "Klein Base 9B generation failed for $($scene.label)."
        }
        if ($entry -and $entry.status.status_str -eq "success") {
            $image = @($entry.outputs."14".images)[0]
            $outputs[$scene.label] = Join-Path $ComfyOutputRoot (Join-Path $image.subfolder $image.filename)
            break
        }
    } while ((Get-Date) -lt $deadline)
    if (-not $entry -or $entry.status.status_str -ne "success") { throw "Timed out waiting for $($scene.label)." }
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportRoot = Join-Path $RepoRoot "work\$WorkRunName\benchmarks"
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null
$reportPath = Join-Path $reportRoot "$SafeName-s$StrengthName-$Profile-$stamp.json"
$referenceRoot = Join-Path $RepoRoot "datasets\$ReferenceDatasetName"
if (-not [string]::IsNullOrWhiteSpace($ReferenceSubdirectory)) {
    $referenceRoot = Join-Path $referenceRoot $ReferenceSubdirectory
}
if ($ReferenceFiles.Count -lt 2) {
    throw "At least two held-out genuine reference photographs are required."
}
if (@($ReferenceFiles | Select-Object -Unique).Count -ne $ReferenceFiles.Count) {
    throw "ReferenceFiles contains duplicate filenames."
}
$references = @($ReferenceFiles | ForEach-Object {
    $reference = Join-Path $referenceRoot $_
    if (-not (Test-Path -LiteralPath $reference -PathType Leaf)) {
        throw "Held-out reference photograph is missing: $reference"
    }
    (Resolve-Path -LiteralPath $reference).Path
})
$calibrationReferences = if ($CalibrationReferenceFiles.Count -gt 0) {
    if ($CalibrationReferenceFiles.Count -lt 2 -or
        @($CalibrationReferenceFiles | Select-Object -Unique).Count -ne $CalibrationReferenceFiles.Count) {
        throw "CalibrationReferenceFiles must contain at least two unique filenames."
    }
    @($CalibrationReferenceFiles | ForEach-Object {
        $reference = Join-Path $referenceRoot $_
        if (-not (Test-Path -LiteralPath $reference -PathType Leaf)) {
            throw "Calibration reference photograph is missing: $reference"
        }
        (Resolve-Path -LiteralPath $reference).Path
    })
} else {
    @($references)
}
$referenceProvenance = @($references | ForEach-Object {
    [ordered]@{
        path = $_
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_).Hash.ToUpperInvariant()
    }
})
$calibrationReferenceProvenance = @($calibrationReferences | ForEach-Object {
    [ordered]@{
        path = $_
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_).Hash.ToUpperInvariant()
    }
})

$evalArgs = [System.Collections.Generic.List[string]]::new()
if ($Profile -eq "Full") {
    $evalArgs.Add((Join-Path $RepoRoot "scripts\evaluate-flux2-dev-identity.py"))
    foreach ($reference in $references) { $evalArgs.Add("--reference"); $evalArgs.Add($reference) }
    foreach ($reference in $calibrationReferences) { $evalArgs.Add("--calibration-reference"); $evalArgs.Add($reference) }
    $evalArgs.Add("--expected-reference-count"); $evalArgs.Add([string]$references.Count)
    $coreSceneLabels = if ($BidirectionalProfiles) {
        @("portrait", "waist-up-social", "profile-image-left", "profile-image-right")
    } else {
        @("portrait", "waist-up-social", "near-profile-candid")
    }
    foreach ($label in $coreSceneLabels) { $evalArgs.Add("--core-scene-label"); $evalArgs.Add($label) }
    foreach ($scene in @($scenes | Where-Object { [string]$_.label -cne "crowd" })) {
        $label = [string]$scene.label
        $evalArgs.Add("--scene"); $evalArgs.Add("$label=$($outputs[$label])")
    }
    $evalArgs.Add("--crowd"); $evalArgs.Add($outputs.crowd)
    $evalArgs.Add("--json-output"); $evalArgs.Add($reportPath)
} else {
    $evalArgs.Add((Join-Path $RepoRoot "scripts\evaluate-face-likeness.py"))
    foreach ($reference in $references) { $evalArgs.Add("--reference"); $evalArgs.Add($reference) }
    foreach ($reference in $calibrationReferences) { $evalArgs.Add("--calibration-reference"); $evalArgs.Add($reference) }
    foreach ($label in $outputs.Keys) {
        $evalArgs.Add("--candidate"); $evalArgs.Add($outputs[$label])
        $evalArgs.Add("--candidate-label"); $evalArgs.Add($label)
    }
    $evalArgs.Add("--json-output"); $evalArgs.Add($reportPath)
}
& $ComfyPython @evalArgs
$evalExit = $LASTEXITCODE
if ($Profile -eq "Quick" -and $evalExit -ne 0) { throw "Local identity evaluation failed." }
if ($Profile -eq "Full" -and $evalExit -notin @(0, 2)) { throw "Local identity/leakage evaluation failed unexpectedly." }

$report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
$outputHashes = [ordered]@{}
foreach ($outputEntry in $outputs.GetEnumerator()) {
    if (-not (Test-Path -LiteralPath $outputEntry.Value -PathType Leaf)) {
        throw "Generated benchmark output is missing: $($outputEntry.Value)"
    }
    $outputHashes[$outputEntry.Key] = (Get-FileHash -Algorithm SHA256 -LiteralPath $outputEntry.Value).Hash.ToUpperInvariant()
}
$sceneProvenance = @(
    for ($index = 0; $index -lt $scenes.Count; $index++) {
        [ordered]@{
            label = [string]$scenes[$index].label
            prompt = [string]$scenes[$index].prompt
            seed = [long]($SeedBase + $index)
        }
    }
)
$report | Add-Member -NotePropertyName benchmark -NotePropertyValue ([pscustomobject]@{
    lora_name = $LoraName
    lora_path = $LoraPath
    lora_sha256 = $LoraSha256
    staging_manifest = $StagingManifestPath
    lora_strength = $LoraStrength
    work_run_name = $WorkRunName
    output_namespace = $OutputNamespace
    profile = $Profile
    base_model = $BaseModelName
    base_variant = "undistilled FLUX.2 Klein Base 9B"
    text_encoder = $TextEncoderName
    sampler = "euler"
    steps = $Steps
    guidance = $Guidance
    width = 832
    height = 1216
    seed_base = $SeedBase
    scenes = $sceneProvenance
    trigger = $Trigger
    reference_dataset_name = $ReferenceDatasetName
    reference_subdirectory = $ReferenceSubdirectory
    bidirectional_profiles = [bool]$BidirectionalProfiles
    held_out_references = $referenceProvenance
    calibration_references = $calibrationReferenceProvenance
    reference_conditioning = $false
    identity_pass = $false
    face_swap = $false
    duration_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
    outputs = $outputs
    output_sha256 = $outputHashes
    manual_full_size_and_thumbnail_review_required = $true
    rtx_4070_worker = $otherDevice
    rtx_4070_queue_running_at_start = $otherRunningAtStart
    rtx_4070_queue_pending_at_start = $otherPendingAtStart
    rtx_4070_work_left_untouched = $true
    auxiliary_rtx_3090 = $aux3090
    forge_rtx_3090 = $forge
    other_rtx_3090_work_checked = $true
    live_node_and_model_validation_passed = $true
})
$report | ConvertTo-Json -Depth 24 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Host "Saved Klein Base 9B LoRA-only benchmark: $reportPath"
Write-Host "Automated identity similarity is diagnostic only; manual review remains required."
Write-Output $reportPath
