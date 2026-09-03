[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8189",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$RunLabel = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runStamp = if ($RunLabel) { $RunLabel } else { Get-Date -Format "yyyyMMdd-HHmmss" }
$runRoot = Join-Path $repoRoot "output\smartphone-snapshot-klein9b-production-rollout-4070\$runStamp"
$rawOutputRoot = Join-Path $ComfyRoot "output\gpu-4070"

$baseModel = "flux-2-klein-base-9b-bf16.safetensors"
$textEncoder = "qwen_3_8b_fp8mixed.safetensors"
$vae = "flux2-vae.safetensors"
$identityLora = "m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors"
$identityStrength = 0.90
$styleLora = "smartphone-snapshot\FLUX.2-klein-base-9B_SmartphoneSnapshotPhotoReality_v13.safetensors"
$styleLoraSha256 = "1E0B419B1448F77CF7AEF430625325E46B16D1515CBF6C5C7E8C14D938CF1A90"
$styleStrength = 0.25
$styleTrigger = "casual snapshot"

function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing required file: $Path" }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Get-WorkerSnapshot([int]$Port) {
    try {
        $base = "http://127.0.0.1:$Port"
        $stats = Invoke-RestMethod -Uri "$base/system_stats" -TimeoutSec 5
        $queue = Invoke-RestMethod -Uri "$base/queue" -TimeoutSec 5
        return [ordered]@{
            port = $Port
            online = $true
            device = [string]$stats.devices[0].name
            running = @($queue.queue_running).Count
            pending = @($queue.queue_pending).Count
        }
    }
    catch {
        return [ordered]@{ port = $Port; online = $false; device = "offline"; running = 0; pending = 0 }
    }
}

function Assert-4070Idle {
    $target = Get-WorkerSnapshot 8189
    if (-not $target.online -or [string]$target.device -notmatch "RTX 4070") {
        throw "Port 8189 is not the live RTX 4070 worker."
    }
    if ([int]$target.running -gt 0 -or [int]$target.pending -gt 0) {
        throw "RTX 4070 queue is active; refusing to overlap work."
    }
    $gpuRow = @(nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | Where-Object { $_ -match '^1,' })
    if ($gpuRow.Count -ne 1) { throw "Could not isolate the RTX 4070 nvidia-smi row." }
    $fields = @($gpuRow[0].Split(',') | ForEach-Object { $_.Trim() })
    if ([int]$fields[4] -gt 15) {
        throw "RTX 4070 utilization is $($fields[4])% despite an idle queue; refusing submission."
    }
    return [ordered]@{ worker = $target; nvidia_smi = $gpuRow[0] }
}

function Wait-ComfyPrompt([string]$PromptId, [string]$SaveNodeId) {
    $deadline = (Get-Date).AddMinutes(45)
    do {
        Start-Sleep -Seconds 3
        $history = Invoke-RestMethod -Uri "$Server/history/$PromptId" -TimeoutSec 15
        $entry = $history.PSObject.Properties[$PromptId].Value
        if ($entry -and $entry.status.status_str -eq "error") {
            throw "Generation $PromptId failed: $($entry.status.messages | ConvertTo-Json -Depth 30)"
        }
    } while ((-not $entry -or -not $entry.status.completed) -and (Get-Date) -lt $deadline)
    if (-not $entry -or -not $entry.status.completed) { throw "Timed out waiting for $PromptId." }
    $image = @($entry.outputs.$SaveNodeId.images)[0]
    if (-not $image) { throw "Generation $PromptId completed without a saved image." }
    $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
    return [ordered]@{ path = (Join-Path $rawOutputRoot $relative); history = $entry }
}

function New-CannyGraph(
    [string]$PromptText,
    [long]$Seed,
    [int]$Width,
    [int]$Height,
    [array]$References,
    [string]$RawPrefix
) {
    $graph = [ordered]@{
        "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $baseModel; weight_dtype = "fp8_e4m3fn" } }
        "2" = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $identityLora; strength_model = $identityStrength } }
        "3" = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("2", 0); lora_name = $styleLora; strength_model = $styleStrength } }
        "4" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $textEncoder; type = "flux2"; device = "default" } }
        "5" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vae } }
        "6" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $PromptText; clip = @("4", 0) } }
        "7" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("4", 0) } }
    }
    $positive = "6"
    $negative = "7"
    $next = 8
    foreach ($reference in $References) {
        $loadId = [string]$next; $scaleId = [string]($next + 1); $encodeId = [string]($next + 2)
        $positiveId = [string]($next + 3); $negativeId = [string]($next + 4)
        $graph[$loadId] = @{ class_type = "LoadImage"; inputs = @{ image = [string]$reference.name } }
        $graph[$scaleId] = @{
            class_type = "ImageScale"
            inputs = @{
                image = @($loadId, 0)
                upscale_method = [string]$reference.method
                width = [int]$reference.width
                height = [int]$reference.height
                crop = "disabled"
            }
        }
        $graph[$encodeId] = @{ class_type = "VAEEncode"; inputs = @{ pixels = @($scaleId, 0); vae = @("5", 0) } }
        $graph[$positiveId] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @($positive, 0); latent = @($encodeId, 0) } }
        $graph[$negativeId] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @($negative, 0); latent = @($encodeId, 0) } }
        $positive = $positiveId
        $negative = $negativeId
        $next += 5
    }
    $guiderId = [string]$next; $samplerId = [string]($next + 1); $schedulerId = [string]($next + 2)
    $noiseId = [string]($next + 3); $latentId = [string]($next + 4); $sampleId = [string]($next + 5)
    $decodeId = [string]($next + 6); $saveId = [string]($next + 7)
    $graph[$guiderId] = @{ class_type = "CFGGuider"; inputs = @{ model = @("3", 0); positive = @($positive, 0); negative = @($negative, 0); cfg = 4.0 } }
    $graph[$samplerId] = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    $graph[$schedulerId] = @{ class_type = "Flux2Scheduler"; inputs = @{ width = $Width; height = $Height; steps = 50 } }
    $graph[$noiseId] = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Seed } }
    $graph[$latentId] = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
    $graph[$sampleId] = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @($noiseId, 0); guider = @($guiderId, 0); sampler = @($samplerId, 0); sigmas = @($schedulerId, 0); latent_image = @($latentId, 0) } }
    $graph[$decodeId] = @{ class_type = "VAEDecode"; inputs = @{ samples = @($sampleId, 0); vae = @("5", 0) } }
    $graph[$saveId] = @{ class_type = "SaveImage"; inputs = @{ images = @($decodeId, 0); filename_prefix = $RawPrefix } }
    return [ordered]@{ graph = $graph; save_node = $saveId }
}

if (Test-Path -LiteralPath $runRoot) { throw "Run folder already exists: $runRoot" }
if (([uri]$Server).Port -ne 8189) { throw "This validation is restricted to the RTX 4070 worker at port 8189." }
$stylePath = Join-Path $ComfyRoot "models\loras\$styleLora"
if ((Get-Sha256 $stylePath) -cne $styleLoraSha256) { throw "Smartphone Snapshot v13 hash mismatch." }

$requirements = @(
    @{ class = "UNETLoader"; field = "unet_name"; value = $baseModel },
    @{ class = "LoraLoaderModelOnly"; field = "lora_name"; value = $identityLora },
    @{ class = "LoraLoaderModelOnly"; field = "lora_name"; value = $styleLora },
    @{ class = "CLIPLoader"; field = "clip_name"; value = $textEncoder },
    @{ class = "VAELoader"; field = "vae_name"; value = $vae }
)
foreach ($required in $requirements) {
    $info = Invoke-RestMethod -Uri "$Server/object_info/$($required.class)" -TimeoutSec 30
    $choices = @($info.($required.class).input.required.($required.field)[0])
    if ($required.value -notin $choices) { throw "Live 4070 worker cannot select $($required.value)." }
}

$initialQueues = @(8188, 8189, 8190 | ForEach-Object { Get-WorkerSnapshot $_ })
$target = Assert-4070Idle
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

$cases = @(
    [ordered]@{
        name = "group-canny"
        baseline_report = "C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-mitch-group-scene-studio-v1\20260901-193031-268085\report.json"
        baseline_photo = "C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-mitch-group-scene-studio-v1\20260901-193031-268085\photo_00001_.png"
        width = 832; height = 1216
        references = @(
            [ordered]@{ name = "mitch-klein9b-layout-lounge-center-face-interior-free-head92-canny.png"; width = 432; height = 576; method = "lanczos"; role = "face-free Canny layout" },
            [ordered]@{ name = "mitch-klein9b-ref-training04-front-neutral.jpg"; width = 1184; height = 880; method = "lanczos"; role = "genuine Mitch identity" }
        )
    },
    [ordered]@{
        name = "upgrade-canny"
        baseline_report = "C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-upgrade-photo-detail-realism-v1\20260901-193908-216286\report.json"
        baseline_photo = "C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-upgrade-photo-detail-realism-v1\20260901-193908-216286\photo_00001_.png"
        width = 1024; height = 1024
        references = @(
            [ordered]@{ name = "mitch-canyon-source-edit-05333f6f.png"; width = 1024; height = 1024; method = "bicubic"; role = "exact source scene" },
            [ordered]@{ name = "experiment-klein4b-canny-ab-upgrade-guide.png"; width = 724; height = 724; method = "nearest-exact"; role = "face-free Canny structure" },
            [ordered]@{ name = "mitch-klein9b-ref-front-neutral-v2.jpg"; width = 627; height = 836; method = "nearest-exact"; role = "genuine Mitch identity" },
            [ordered]@{ name = "mitch-natural-hair-only-val05-isolated.png"; width = 460; height = 228; method = "bicubic"; role = "genuine isolated hair material" }
        )
    }
)

$runs = [System.Collections.Generic.List[object]]::new()
foreach ($case in $cases) {
    $preSubmit = Assert-4070Idle
    $locked = Get-Content -Raw -LiteralPath $case.baseline_report | ConvertFrom-Json
    $promptText = if ([string]$locked.effective_prompt -match '^casual snapshot\.') {
        [string]$locked.effective_prompt
    } else {
        "$styleTrigger. $([string]$locked.effective_prompt)"
    }
    $rawPrefix = "smartphone-snapshot-klein9b-production-rollout-4070/$runStamp/$($case.name)-v13-0p25-seed-$($locked.seed)"
    $built = New-CannyGraph $promptText ([long]$locked.seed) ([int]$case.width) ([int]$case.height) @($case.references) $rawPrefix
    $graphPath = Join-Path $runRoot "$($case.name)-prompt-api.json"
    $built.graph | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $graphPath -Encoding utf8
    $body = @{ prompt = $built.graph; client_id = "smartphone-snapshot-klein9b-canny-rollout-4070" } | ConvertTo-Json -Depth 100
    $started = Get-Date
    $queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body -TimeoutSec 60
    if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id for $($case.name)." }
    Write-Host "Queued $($case.name) on RTX 4070: $($queued.prompt_id)"
    $completed = Wait-ComfyPrompt ([string]$queued.prompt_id) ([string]$built.save_node)
    $projectPhoto = Join-Path $runRoot "$($case.name)-v13-0p25-seed-$($locked.seed).png"
    Copy-Item -LiteralPath $completed.path -Destination $projectPhoto
    $runs.Add([ordered]@{
        case = $case.name
        prompt_id = [string]$queued.prompt_id
        prompt = $promptText
        graph = $graphPath
        baseline_report = $case.baseline_report
        baseline_photo = $case.baseline_photo
        baseline_photo_sha256 = Get-Sha256 $case.baseline_photo
        references = @($case.references)
        pre_submission_state = $preSubmit
        raw_output = $completed.path
        project_output = $projectPhoto
        project_output_sha256 = Get-Sha256 $projectPhoto
        seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
        width = [int]$case.width
        height = [int]$case.height
        seed = [long]$locked.seed
    })
}

$report = [ordered]@{
    schema_version = 1
    status = "generated_pending_visual_and_metric_review"
    purpose = "post-promotion compatibility smoke for Smartphone Snapshot v13 at 0.25 with both production Canny conditioning mechanisms"
    worker = $Server
    gpu = $target.worker.device
    all_queue_snapshots_at_start = $initialQueues
    production_modified_before_validation = $true
    model = [ordered]@{ name = $baseModel; load_dtype = "fp8_e4m3fn" }
    identity_lora = [ordered]@{ name = $identityLora; strength = $identityStrength; load_order = 1 }
    smartphone_style = [ordered]@{ name = $styleLora; sha256 = $styleLoraSha256; strength = $styleStrength; trigger = $styleTrigger; load_order = 2 }
    settings = [ordered]@{ steps = 50; cfg = 4.0; sampler = "euler"; scheduler = "Flux2Scheduler" }
    runs = @($runs)
    manual_review_required = @(
        "identity and apparent age at full size and thumbnail",
        "Canny-guided composition and pose retention",
        "hairline and forehead continuity without halos",
        "background material realism and depth",
        "natural detail without etched sharpening or repeated generated texture",
        "exactly one Mitch and distinct bystanders in the group case"
    )
}
$reportPath = Join-Path $runRoot "generation-report.json"
$report | ConvertTo-Json -Depth 50 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Output $reportPath
