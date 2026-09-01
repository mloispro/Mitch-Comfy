[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8189",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyOutputRoot = "C:\projects\AI-Tools\ComfyUI\output\gpu-4070",
    [string]$Model = "hidream_o1_image_dev_fp8_scaled.safetensors",
    [string]$Reference1 = "hidream-o1-ref-01-sweater-front-neutral.jpg",
    [string]$Reference2 = "hidream-o1-ref-02-opposite-profile.jpg",
    [string]$Reference3 = "hidream-o1-ref-03-laundry-angle.jpg",
    [UInt64[]]$Seeds = @(8675601, 8675602, 8675603, 8675604),
    [int]$Width = 1728,
    [int]$Height = 2304,
    [int]$Steps = 28,
    [string]$OutputPrefixRoot = "hidream-o1-reference-dating-3ref-v1",
    [string]$PublishedRoot = "output\hidream-o1-reference-dating-3ref-v1\candidates",
    [string]$ManifestOutput = "output\hidream-o1-reference-dating-3ref-v1\generation-manifest.json",
    [switch]$PreflightOnly,
    [string]$ScenePrompt = (
        "References 1, 2, and 3 are genuine photographs of Mitch, the same real man, and define the exact " +
        "identity of the only main subject. Create a completely new photorealistic vertical rear-camera " +
        "smartphone photograph of that exact same man at a relaxed neighborhood restaurant patio in early " +
        "evening. Preserve his current apparent age, high forehead and hairline, short light-brown hair, " +
        "blue-gray eye shape and spacing, nose, ears, mouth, narrow jaw, faint natural stubble, lean build, " +
        "and unretouched skin texture. Frame him naturally from the waist upward, slightly off center, with " +
        "a mild three-quarter face, both eyes comfortably open, and a small relaxed smile while he looks a " +
        "few degrees past the camera toward a friend. He wears a simple deep-navy open-collar shirt. Show " +
        "ordinary patio tables, varied unrelated diners, planters, storefront windows, and warm practical " +
        "lights at believable depth. Use an eye-level handheld 1x phone-camera view, normal automatic " +
        "exposure, restrained HDR, natural deep focus, slight shadow noise, and imperfect candid framing. " +
        "Keep every background person distinct from Mitch. The result must look like an ordinary dating-" +
        "profile snapshot, with no beauty filter, studio lighting, face smoothing, portrait-mode blur, " +
        "cinematic grading, text, logo, or watermark."
    )
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$expectedModelSha256 = "7CBF53A475E0A13F92F2EC08BCFFDB9B9DE4305EF3B6F35CDD784D09DCD8D0CC"
$referenceSha256 = [ordered]@{
    $Reference1 = "0E9F30D584646B3455674FA88E03C3C8B5A534D0FCBC2083088032ECB35DA93A"
    $Reference2 = "4B98FEB4D7929BD89F75402B85D1D86BE690D67C48212C1F4740419F9374CA6B"
    $Reference3 = "28D39C19F4FD06CB306E67AE061B40704F53662BEC52201F4D72352E12EE689D"
}
$modelPath = Join-Path (Join-Path $ComfyRoot "models\checkpoints") $Model
$inputRoot = Join-Path $ComfyRoot "input"

if ($Steps -ne 28) { throw "The HiDream-O1 Dev recipe is fixed at 28 steps." }
if (($Width % 32) -ne 0 -or ($Height % 32) -ne 0) {
    throw "HiDream-O1 dimensions must be multiples of 32."
}
if ($Seeds.Count -eq 0) { throw "Supply at least one seed." }

function Assert-SafeWorkerState {
    $gpuState = @(& nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader)
    if ($LASTEXITCODE -ne 0) { throw "nvidia-smi could not inspect both GPUs." }
    Write-Host "GPU state: $($gpuState -join '; ')"
    foreach ($port in 8188, 8189, 8190) {
        $worker = "http://127.0.0.1:$port"
        try {
            $queue = Invoke-RestMethod -Uri "$worker/queue" -TimeoutSec 5
            $running = @($queue.queue_running).Count
            $pending = @($queue.queue_pending).Count
            Write-Host "Queue $port`: running=$running, pending=$pending"
            if ($port -eq 8189 -and ($running -gt 0 -or $pending -gt 0)) {
                throw "RTX 4070 worker queue is not idle. Refusing to disturb active work."
            }
        }
        catch {
            if ($port -eq 8189) { throw }
            Write-Warning "Could not inspect optional ComfyUI worker $port`: $($_.Exception.Message)"
        }
    }
}

Assert-SafeWorkerState
$stats = Invoke-RestMethod -Uri "$Server/system_stats" -TimeoutSec 5
$deviceName = [string](@($stats.devices)[0].name)
if ($deviceName -notlike "*RTX 4070*") { throw "Worker '$deviceName' is not the RTX 4070." }

$requiredNodes = @(
    "CheckpointLoaderSimple", "ModelNoiseScale", "LoadImage", "CLIPTextEncode",
    "HiDreamO1ReferenceImages", "EmptyHiDreamO1LatentImage", "BasicScheduler",
    "SamplerLCM", "SamplerCustom", "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $info = Invoke-RestMethod -Uri "$Server/object_info/$nodeName" -TimeoutSec 10
    if (-not $info.PSObject.Properties[$nodeName]) { throw "Required node unavailable: $nodeName" }
}

if (-not (Test-Path -LiteralPath $modelPath -PathType Leaf)) { throw "Missing model: $modelPath" }
$modelFile = Get-Item -LiteralPath $modelPath
if ($modelFile.Length -lt 7000000000) { throw "Checkpoint appears incomplete: $modelPath" }
$modelHash = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash
if ($modelHash -ne $expectedModelSha256) { throw "Checkpoint SHA256 mismatch: $modelHash" }

$allInfo = Invoke-RestMethod -Uri "$Server/object_info" -TimeoutSec 30
if (@($allInfo.CheckpointLoaderSimple.input.required.ckpt_name[0]) -notcontains $Model) {
    throw "The live RTX 4070 worker cannot see checkpoint: $Model"
}

foreach ($reference in @($Reference1, $Reference2, $Reference3)) {
    $path = Join-Path $inputRoot $reference
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing genuine ComfyUI input photograph: $reference"
    }
    $actualHash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    if ($actualHash -ne $referenceSha256[$reference]) {
        throw "Reference is not the reviewed byte-identical genuine still: $reference ($actualHash)"
    }
}

$preflight = [pscustomobject]@{
    status = "preflight_passed"
    worker = $Server
    gpu = $deviceName
    model = $Model
    model_sha256 = $modelHash
    mechanism = "native HiDream-O1 three-reference subject-driven personalization"
    character_lora = $null
    references = @($Reference1, $Reference2, $Reference3)
    reference_sha256 = $referenceSha256
    seeds = $Seeds
    width = $Width
    height = $Height
    steps = $Steps
}
if ($PreflightOnly) {
    $preflight | ConvertTo-Json -Depth 10
    return
}

$results = @()
foreach ($Seed in $Seeds) {
    Assert-SafeWorkerState
    $outputPrefix = "$OutputPrefixRoot/seed-$Seed"
    $publishedPath = Join-Path $repoRoot (Join-Path $PublishedRoot "seed-$Seed.png")

    $prompt = [ordered]@{
        "1" = @{ class_type = "CheckpointLoaderSimple"; inputs = @{ ckpt_name = $Model } }
        "2" = @{ class_type = "ModelNoiseScale"; inputs = @{ model = @("1", 0); noise_scale = 7.6 } }
        "3" = @{ class_type = "LoadImage"; inputs = @{ image = $Reference1 } }
        "4" = @{ class_type = "LoadImage"; inputs = @{ image = $Reference2 } }
        "5" = @{ class_type = "LoadImage"; inputs = @{ image = $Reference3 } }
        "6" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $ScenePrompt; clip = @("1", 1) } }
        "7" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("1", 1) } }
        "8" = @{ class_type = "HiDreamO1ReferenceImages"; inputs = @{
            positive = @("6", 0)
            negative = @("7", 0)
            "images.image_1" = @("3", 0)
            "images.image_2" = @("4", 0)
            "images.image_3" = @("5", 0)
        } }
        "9" = @{ class_type = "EmptyHiDreamO1LatentImage"; inputs = @{
            width = $Width; height = $Height; batch_size = 1
        } }
        "10" = @{ class_type = "BasicScheduler"; inputs = @{
            model = @("2", 0); scheduler = "normal"; steps = $Steps; denoise = 1.0
        } }
        "11" = @{ class_type = "SamplerLCM"; inputs = @{
            s_noise = 1.0; s_noise_end = 1.0; noise_clip_std = 2.5
        } }
        "12" = @{ class_type = "SamplerCustom"; inputs = @{
            model = @("2", 0); add_noise = $true; noise_seed = $Seed; cfg = 1.0
            positive = @("8", 0); negative = @("8", 1); sampler = @("11", 0)
            sigmas = @("10", 0); latent_image = @("9", 0)
        } }
        "13" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("12", 0); vae = @("1", 2) } }
        "14" = @{ class_type = "SaveImage"; inputs = @{ images = @("13", 0); filename_prefix = $outputPrefix } }
    }

    $clientId = [guid]::NewGuid().ToString()
    $body = @{ prompt = $prompt; client_id = $clientId } | ConvertTo-Json -Depth 100
    $started = Get-Date
    $queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
    if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id for seed $Seed." }
    Write-Host "Queued seed $Seed as prompt $($queued.prompt_id) on the RTX 4070 only."

    $deadline = (Get-Date).AddMinutes(120)
    $completed = $false
    do {
        Start-Sleep -Seconds 2
        $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 10
        $entry = $history.PSObject.Properties[$queued.prompt_id].Value
        if ($entry) {
            if ($entry.status.status_str -eq "error") {
                throw "Seed $Seed failed: $($entry.status.messages | ConvertTo-Json -Depth 20)"
            }
            if ($entry.status.completed) {
                $saved = @($entry.outputs.'14'.images)
                if ($saved.Count -eq 0) { throw "Seed $Seed completed without saving an image." }
                $relative = if ($saved[0].subfolder) {
                    Join-Path $saved[0].subfolder $saved[0].filename
                } else { $saved[0].filename }
                $sourcePath = Join-Path $ComfyOutputRoot $relative
                if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
                    throw "Reported output does not exist: $sourcePath"
                }
                New-Item -ItemType Directory -Path (Split-Path -Parent $publishedPath) -Force | Out-Null
                Copy-Item -LiteralPath $sourcePath -Destination $publishedPath -Force
                $elapsed = ((Get-Date) - $started).TotalSeconds
                $results += [pscustomobject]@{
                    prompt_id = $queued.prompt_id
                    seed = $Seed
                    runtime_seconds = [Math]::Round($elapsed, 3)
                    comfy_output = $sourcePath
                    published_output = $publishedPath
                    output_sha256 = (Get-FileHash -LiteralPath $publishedPath -Algorithm SHA256).Hash
                }
                $completed = $true
            }
        }
    } while (-not $completed -and (Get-Date) -lt $deadline)
    if (-not $completed) { throw "Timed out waiting for seed $Seed." }
}

$manifest = [ordered]@{
    status = "complete"
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    worker = $Server
    gpu = $deviceName
    model = $Model
    model_sha256 = $modelHash
    mechanism = "native HiDream-O1 three-reference subject-driven personalization"
    character_lora = $null
    references = @($Reference1, $Reference2, $Reference3)
    reference_sha256 = $referenceSha256
    prompt = $ScenePrompt
    width = $Width
    height = $Height
    steps = $Steps
    cfg = 1.0
    noise_scale = 7.6
    scheduler = "normal"
    sampler = "LCM (s_noise 1.0 -> 1.0, clip 2.5)"
    results = $results
}
$manifestPath = Join-Path $repoRoot $ManifestOutput
New-Item -ItemType Directory -Path (Split-Path -Parent $manifestPath) -Force | Out-Null
$manifestJson = $manifest | ConvertTo-Json -Depth 20
$manifestJson | Set-Content -LiteralPath $manifestPath -Encoding utf8
$manifestJson
