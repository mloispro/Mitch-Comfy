[CmdletBinding()]
param(
    [ValidateSet("whole_frame_reference", "contextual_inpaint")]
    [string]$Mode = "whole_frame_reference",
    [ValidateSet("contextual_full_body", "internal_face_geometry_lock")]
    [string]$MaskStrategy = "contextual_full_body",
    [string]$ScenePlatePath = "C:\projects\AI-Tools\Mitch-Comfy\output\scene-first-state-fair-plate-seed-8675401.png",
    [string[]]$References = @(
        "20260815_165446.jpg",
        "20260815_165449.jpg",
        "20260818_173106.jpg",
        "20240923_130835.jpg"
    ),
    [double]$PrimaryStrength = 0.50,
    [double]$SecondaryStrength = 0.60,
    [double]$PrimaryDenoise = 1.0,
    [double]$SecondaryDenoise = 1.0,
    [string]$SceneContext = "",
    [switch]$PreservePlateDimensions,
    [long]$Seed = 8675310,
    [int]$ContextRingPixels = 36,
    [int]$TimeoutSeconds = 1800,
    [ValidateSet("Both", "RTX3090", "RTX4070")]
    [string]$WorkerSet = "Both",
    [string]$ManifestRoot = "C:\projects\AI-Tools\Mitch-Comfy\output\crowd-proof-campaign"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ScenePlatePath -PathType Leaf)) {
    throw "State-fair plate is unavailable: $ScenePlatePath"
}
if ($References.Count -lt 1 -or $References.Count -gt 4) {
    throw "Supply between one and four genuine reference filenames."
}

$workers = @(
    [pscustomobject]@{
        Label = "RTX 3090"
        Url = "http://127.0.0.1:8188"
        ExpectedName = "NVIDIA GeForce RTX 3090"
        Strength = $PrimaryStrength
        Denoise = $PrimaryDenoise
        OutputRoot = "C:\projects\AI-Tools\ComfyUI\output"
    },
    [pscustomobject]@{
        Label = "RTX 4070"
        Url = "http://127.0.0.1:8189"
        ExpectedName = "NVIDIA GeForce RTX 4070"
        Strength = $SecondaryStrength
        Denoise = $SecondaryDenoise
        OutputRoot = "C:\projects\AI-Tools\ComfyUI\output\gpu-4070"
    }
)
if ($WorkerSet -eq "RTX3090") {
    $workers = @($workers | Where-Object { $_.Label -eq "RTX 3090" })
}
elseif ($WorkerSet -eq "RTX4070") {
    $workers = @($workers | Where-Object { $_.Label -eq "RTX 4070" })
}

function Assert-WorkerReady {
    param($Worker)

    $stats = Invoke-RestMethod -Uri "$($Worker.Url)/system_stats" -TimeoutSec 10
    $deviceName = [string](@($stats.devices)[0].name)
    if ($deviceName -notlike "*$($Worker.ExpectedName)*") {
        throw "$($Worker.Url) is serving '$deviceName', not $($Worker.ExpectedName)."
    }
    $queue = Invoke-RestMethod -Uri "$($Worker.Url)/queue" -TimeoutSec 10
    if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
        throw "$($Worker.Label) has unrelated queued work. Nothing was submitted."
    }
    $objectInfo = Invoke-RestMethod -Uri "$($Worker.Url)/object_info/Flux2CrowdProofExperiment" -TimeoutSec 60
    if (-not $objectInfo.PSObject.Properties["Flux2CrowdProofExperiment"]) {
        throw "$($Worker.Label) has not loaded Flux2CrowdProofExperiment. Restart the idle worker."
    }
    return $deviceName
}

function Submit-CrowdProof {
    param($Worker)

    $inputs = @{
        scene_plate_path = $ScenePlatePath
        face_reference = $References[0]
        reference_2 = if ($References.Count -ge 2) { $References[1] } else { "No additional reference" }
        reference_3 = if ($References.Count -ge 3) { $References[2] } else { "No additional reference" }
        reference_4 = if ($References.Count -ge 4) { $References[3] } else { "No additional reference" }
        mode = $Mode
        mask_strategy = $MaskStrategy
        denoise_strength = [double]$Worker.Denoise
        lora_strength = [double]$Worker.Strength
        seed = $Seed
        context_ring_pixels = $ContextRingPixels
        scene_context = $SceneContext
        preserve_plate_dimensions = [bool]$PreservePlateDimensions
    }
    $workflow = @{
        "1" = @{
            class_type = "Flux2CrowdProofExperiment"
            inputs = $inputs
        }
    }
    $clientId = "state-fair-crowd-proof-$($Worker.Label.Replace(' ', '-'))-$(New-Guid)"
    $body = @{
        prompt = $workflow
        client_id = $clientId
    } | ConvertTo-Json -Depth 20
    $queued = Invoke-RestMethod -Method Post -Uri "$($Worker.Url)/prompt" -ContentType "application/json" -Body $body
    if (-not $queued.prompt_id) {
        throw "$($Worker.Label) did not return a prompt id: $($queued | ConvertTo-Json -Depth 10 -Compress)"
    }
    return [pscustomobject]@{
        Worker = $Worker
        PromptId = [string]$queued.prompt_id
        ClientId = $clientId
        Started = Get-Date
        Complete = $false
        Result = $null
    }
}

function Read-CrowdProofResult {
    param($Job)

    $history = Invoke-RestMethod -Uri "$($Job.Worker.Url)/history/$($Job.PromptId)" -TimeoutSec 30
    $record = $history.PSObject.Properties[$Job.PromptId].Value
    if (-not $record) {
        return $null
    }
    if ($record.status.status_str -eq "error") {
        $messages = @($record.status.messages | ForEach-Object { $_ | ConvertTo-Json -Depth 30 -Compress })
        throw "$($Job.Worker.Label) crowd proof failed: $($messages -join [Environment]::NewLine)"
    }
    if (-not ($record.status.completed -or $record.status.status_str -eq "success")) {
        return $null
    }
    $images = @()
    $texts = @()
    foreach ($output in $record.outputs.PSObject.Properties.Value) {
        foreach ($image in @($output.images)) {
            if (-not $image.filename) {
                continue
            }
            $relative = if ($image.subfolder) {
                Join-Path $image.subfolder $image.filename
            }
            else {
                $image.filename
            }
            $images += [pscustomobject]@{
                relative_path = $relative
                absolute_path = Join-Path $Job.Worker.OutputRoot $relative
            }
        }
        foreach ($item in @($output.text)) {
            if ($item) { $texts += [string]$item }
        }
    }
    return [pscustomobject]@{
        prompt_id = $Job.PromptId
        gpu = $Job.Worker.Label
        url = $Job.Worker.Url
        lora_strength = [double]$Job.Worker.Strength
        denoise_strength = [double]$Job.Worker.Denoise
        elapsed_seconds = [math]::Round(((Get-Date) - $Job.Started).TotalSeconds, 3)
        images = $images
        messages = $texts
    }
}

foreach ($worker in $workers) {
    $deviceName = Assert-WorkerReady -Worker $worker
    Write-Host "$($worker.Label) ready: $deviceName"
}

# Submissions are intentionally back-to-back. Both workers then execute concurrently.
$jobs = @($workers | ForEach-Object { Submit-CrowdProof -Worker $_ })
foreach ($job in $jobs) {
    Write-Host "Queued $Mode at LoRA $($job.Worker.Strength) on $($job.Worker.Label): $($job.PromptId)"
}

$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
while ([DateTime]::UtcNow -lt $deadline) {
    foreach ($job in $jobs | Where-Object { -not $_.Complete }) {
        $result = Read-CrowdProofResult -Job $job
        if ($result) {
            $job.Result = $result
            $job.Complete = $true
            Write-Host "Completed $($job.Worker.Label) in $($result.elapsed_seconds)s"
        }
    }
    if (@($jobs | Where-Object { -not $_.Complete }).Count -eq 0) {
        break
    }
    Start-Sleep -Seconds 3
}

$unfinished = @($jobs | Where-Object { -not $_.Complete })
if ($unfinished.Count -gt 0) {
    throw "Timed out waiting for: $($unfinished.Worker.Label -join ', ')"
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$manifestDirectory = Join-Path $ManifestRoot $stamp
New-Item -ItemType Directory -Path $manifestDirectory -Force | Out-Null
$manifestPath = Join-Path $manifestDirectory "dual-run.json"
$manifest = [ordered]@{
    schema_version = 1
    purpose = "state_fair_crowd_identity_proof"
    mode = $Mode
    mask_strategy = $MaskStrategy
    scene_plate = $ScenePlatePath
    references = $References
    seed = $Seed
    context_ring_pixels = $ContextRingPixels
    primary_denoise = $PrimaryDenoise
    secondary_denoise = $SecondaryDenoise
    started_concurrently = ($workers.Count -gt 1)
    candidates = @($jobs | ForEach-Object { $_.Result })
}
$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding utf8
$manifest["manifest_path"] = $manifestPath
$manifest | ConvertTo-Json -Depth 20
