[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8189",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$BaselineReport = "C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-mitch-identity-studio-v1\20260901-203616-108406\report.json",
    [double]$StyleStrength = 0.25,
    [string]$RunLabel = "",
    [string]$ResumeBaselinePromptId = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$inputRoot = Join-Path $ComfyRoot "input"
$outputRoot = Join-Path $ComfyRoot "output\gpu-4070"
$runStamp = if ($RunLabel) { $RunLabel } else { Get-Date -Format "yyyyMMdd-HHmmss" }
$strengthLabel = $StyleStrength.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture).Replace(".", "p")
$projectRunRoot = Join-Path $repoRoot "output\smartphone-snapshot-klein9b-fastest-compatible-4070-ab\$runStamp"

$baseModel = "flux-2-klein-base-9b-bf16.safetensors"
$baseModelSha256 = "4A54FAD7F5F741B99EEE217198DAAC20B8D8E515E2A1F5B064FD51CF074F95BD"
$textEncoder = "qwen_3_8b_fp8mixed.safetensors"
$textEncoderSha256 = "ABAD16806E0CBABC54E0325D6565847443FE396D5F0BE38BB3CD3FE75A1201D6"
$vae = "flux2-vae.safetensors"
$vaeSha256 = "D64F3A68E1CC4F9F4E29B6E0DA38A0204FE9A49F2D4053F0EC1FA1CA02F9C4B5"
$identityLora = "m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors"
$identityLoraSha256 = "D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC"
$identityStrength = 0.90
$styleLora = "smartphone-snapshot\FLUX.2-klein-base-9B_SmartphoneSnapshotPhotoReality_v13.safetensors"
$styleLoraSha256 = "1E0B419B1448F77CF7AEF430625325E46B16D1515CBF6C5C7E8C14D938CF1A90"
$styleTrigger = "casual snapshot"
$identityReference = "mitch-klein9b-ref-front-neutral-v2.jpg"
$identityReferenceSha256 = "28DF2AE0D717A788370CC825F7BB24CF38DB9C7CDA3F66BAEFAB58BE86D8AF33"
$width = 832
$height = 1216
$referenceWidth = 448
$referenceHeight = 592
$steps = 50
$guidance = 4.0

function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing required file: $Path" }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Assert-Sha256([string]$Path, [string]$Expected, [string]$Label) {
    $actual = Get-Sha256 $Path
    if ($actual -cne $Expected) { throw "$Label SHA-256 mismatch. Expected $Expected, got $actual ($Path)" }
    return $actual
}

function Test-LocalTcpListener([int]$Port) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync("127.0.0.1", $Port)
        return ($task.Wait(1000) -and $client.Connected)
    }
    catch { return $false }
    finally { $client.Dispose() }
}

function Get-WorkerSnapshot([int]$Port) {
    if (-not (Test-LocalTcpListener $Port)) {
        return [ordered]@{ port = $Port; online = $false }
    }
    $worker = "http://127.0.0.1:$Port"
    $stats = Invoke-RestMethod -Uri "$worker/system_stats" -TimeoutSec 10
    $queue = Invoke-RestMethod -Uri "$worker/queue" -TimeoutSec 10
    return [ordered]@{
        port = $Port
        online = $true
        device = [string]$stats.devices[0].name
        running = @($queue.queue_running).Count
        pending = @($queue.queue_pending).Count
    }
}

function Assert-TargetIdle {
    $target = Get-WorkerSnapshot 8189
    if (-not $target.online) { throw "RTX 4070 worker on port 8189 is offline." }
    if ([string]$target.device -notmatch "RTX 4070") { throw "Port 8189 is not the RTX 4070: $($target.device)" }
    if ([int]$target.running -gt 0 -or [int]$target.pending -gt 0) { throw "RTX 4070 queue is not idle." }
    $gpuRows = @(nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader,nounits)
    $gpu1 = @($gpuRows | Where-Object { $_ -match '^1,' })
    if ($gpu1.Count -ne 1) { throw "Could not isolate the RTX 4070 nvidia-smi row." }
    $fields = @($gpu1[0].Split(",") | ForEach-Object { $_.Trim() })
    if ([int]$fields[4] -gt 15) { throw "RTX 4070 utilization is $($fields[4])% with an idle queue; refusing to overlap untracked work." }
    return [ordered]@{ worker = $target; nvidia_smi = $gpu1[0] }
}

function Wait-ComfyPrompt([string]$PromptId, [string]$SaveNodeId) {
    $deadline = (Get-Date).AddMinutes(45)
    do {
        Start-Sleep -Seconds 2
        $history = Invoke-RestMethod -Uri "$Server/history/$PromptId" -TimeoutSec 15
        $entry = $history.PSObject.Properties[$PromptId].Value
        if ($entry -and $entry.status.status_str -eq "error") {
            throw "Generation $PromptId failed: $($entry.status.messages | ConvertTo-Json -Depth 30)"
        }
    } while ((-not $entry -or -not $entry.status.completed) -and (Get-Date) -lt $deadline)
    if (-not $entry -or -not $entry.status.completed) { throw "Timed out waiting for generation $PromptId." }
    $image = @($entry.outputs.$SaveNodeId.images)[0]
    if (-not $image) { throw "Generation $PromptId completed without a saved image." }
    $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
    return Join-Path $outputRoot $relative
}

function New-Graph([bool]$UseStyle, [string]$PromptText, [long]$Seed, [string]$RawPrefix) {
    $graph = [ordered]@{
        "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $baseModel; weight_dtype = "fp8_e4m3fn" } }
        "2" = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $identityLora; strength_model = $identityStrength } }
        "4" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $textEncoder; type = "flux2"; device = "default" } }
        "5" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vae } }
        "6" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $PromptText; clip = @("4", 0) } }
        "7" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("4", 0) } }
        "8" = @{ class_type = "LoadImage"; inputs = @{ image = $identityReference } }
        "9" = @{ class_type = "ImageScale"; inputs = @{ image = @("8", 0); upscale_method = "lanczos"; width = $referenceWidth; height = $referenceHeight; crop = "disabled" } }
        "10" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("9", 0); vae = @("5", 0) } }
        "11" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("6", 0); latent = @("10", 0) } }
        "12" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("7", 0); latent = @("10", 0) } }
        "14" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
        "15" = @{ class_type = "Flux2Scheduler"; inputs = @{ width = $width; height = $height; steps = $steps } }
        "16" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Seed } }
        "17" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $width; height = $height; batch_size = 1 } }
        "18" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("16", 0); guider = @("13", 0); sampler = @("14", 0); sigmas = @("15", 0); latent_image = @("17", 0) } }
        "19" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("18", 0); vae = @("5", 0) } }
        "20" = @{ class_type = "SaveImage"; inputs = @{ images = @("19", 0); filename_prefix = $RawPrefix } }
    }
    $modelNode = "2"
    if ($UseStyle) {
        $graph["3"] = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("2", 0); lora_name = $styleLora; strength_model = $StyleStrength } }
        $modelNode = "3"
    }
    $graph["13"] = @{ class_type = "CFGGuider"; inputs = @{ model = @($modelNode, 0); positive = @("11", 0); negative = @("12", 0); cfg = $guidance } }
    return $graph
}

if ((Test-Path -LiteralPath $projectRunRoot) -and -not $ResumeBaselinePromptId) {
    throw "Run directory already exists; refusing to overwrite: $projectRunRoot"
}
if ($StyleStrength -le 0 -or $StyleStrength -gt 1.0) { throw "StyleStrength must be greater than 0 and no more than 1.0." }

$locked = Get-Content -Raw -LiteralPath $BaselineReport | ConvertFrom-Json
if ([string]$locked.model -cne $baseModel -or [int]$locked.steps -ne $steps -or [double]$locked.guidance -ne $guidance) {
    throw "The selected locked report is not the expected Base-9B 50-step CFG-4 workflow."
}
if ([int]$locked.reference_count -ne 1) { throw "The fastest compatible test requires the one-reference profile." }
$seed = [long]$locked.seed
$baselinePrompt = [string]$locked.effective_prompt
$stylePrompt = "$styleTrigger. $baselinePrompt"

$paths = [ordered]@{
    base_model = Join-Path $ComfyRoot "models\diffusion_models\$baseModel"
    text_encoder = Join-Path $ComfyRoot "models\text_encoders\$textEncoder"
    vae = Join-Path $ComfyRoot "models\vae\$vae"
    identity_lora = Join-Path $ComfyRoot "models\loras\$identityLora"
    style_lora = Join-Path $ComfyRoot "models\loras\$styleLora"
    identity_reference = Join-Path $inputRoot $identityReference
}
Assert-Sha256 $paths.base_model $baseModelSha256 "Base model" | Out-Null
Assert-Sha256 $paths.text_encoder $textEncoderSha256 "Text encoder" | Out-Null
Assert-Sha256 $paths.vae $vaeSha256 "VAE" | Out-Null
Assert-Sha256 $paths.identity_lora $identityLoraSha256 "Protected Mitch identity LoRA" | Out-Null
Assert-Sha256 $paths.style_lora $styleLoraSha256 "Smartphone Snapshot v13 LoRA" | Out-Null
Assert-Sha256 $paths.identity_reference $identityReferenceSha256 "Genuine identity reference" | Out-Null

$initialQueues = @(
    Get-WorkerSnapshot 8188
    Get-WorkerSnapshot 8189
    Get-WorkerSnapshot 8190
)
$targetState = Assert-TargetIdle

$requirements = @(
    @{ Class = "UNETLoader"; Field = "unet_name"; Value = $baseModel },
    @{ Class = "LoraLoaderModelOnly"; Field = "lora_name"; Value = $identityLora },
    @{ Class = "LoraLoaderModelOnly"; Field = "lora_name"; Value = $styleLora },
    @{ Class = "CLIPLoader"; Field = "clip_name"; Value = $textEncoder },
    @{ Class = "VAELoader"; Field = "vae_name"; Value = $vae },
    @{ Class = "LoadImage"; Field = $null; Value = $null },
    @{ Class = "ImageScale"; Field = $null; Value = $null },
    @{ Class = "VAEEncode"; Field = $null; Value = $null },
    @{ Class = "ReferenceLatent"; Field = $null; Value = $null },
    @{ Class = "CLIPTextEncode"; Field = $null; Value = $null },
    @{ Class = "CFGGuider"; Field = $null; Value = $null },
    @{ Class = "KSamplerSelect"; Field = $null; Value = $null },
    @{ Class = "Flux2Scheduler"; Field = $null; Value = $null },
    @{ Class = "RandomNoise"; Field = $null; Value = $null },
    @{ Class = "EmptyFlux2LatentImage"; Field = $null; Value = $null },
    @{ Class = "SamplerCustomAdvanced"; Field = $null; Value = $null },
    @{ Class = "VAEDecode"; Field = $null; Value = $null },
    @{ Class = "SaveImage"; Field = $null; Value = $null }
)
foreach ($required in $requirements) {
    $nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$($required.Class)" -TimeoutSec 30
    $node = $nodeInfo.($required.Class)
    if (-not $node) { throw "Required live node is unavailable: $($required.Class)" }
    if ($required.Field) {
        $choices = @($node.input.required.($required.Field)[0])
        if ($required.Value -notin $choices) { throw "Required live model is unavailable: $($required.Value)" }
    }
}

New-Item -ItemType Directory -Force -Path $projectRunRoot | Out-Null
$runs = [System.Collections.Generic.List[object]]::new()
if ($ResumeBaselinePromptId) {
    $baselineGraphPath = Join-Path $projectRunRoot "baseline-prompt-api.json"
    if (-not (Test-Path -LiteralPath $baselineGraphPath -PathType Leaf)) {
        throw "Cannot resume because the preserved baseline graph is missing: $baselineGraphPath"
    }
    $baselineRawPath = Wait-ComfyPrompt $ResumeBaselinePromptId "20"
    $baselineProjectPath = Join-Path $projectRunRoot "baseline-seed-$seed.png"
    Copy-Item -LiteralPath $baselineRawPath -Destination $baselineProjectPath -Force
    $baselineHistory = Invoke-RestMethod -Uri "$Server/history/$ResumeBaselinePromptId" -TimeoutSec 15
    $baselineEntry = $baselineHistory.PSObject.Properties[$ResumeBaselinePromptId].Value
    $startMessage = @($baselineEntry.status.messages | Where-Object { $_[0] -eq "execution_start" })[0]
    $successMessage = @($baselineEntry.status.messages | Where-Object { $_[0] -eq "execution_success" })[0]
    $baselineSeconds = if ($startMessage -and $successMessage) {
        [Math]::Round(([double]$successMessage[1].timestamp - [double]$startMessage[1].timestamp) / 1000.0, 3)
    }
    else { $null }
    $runs.Add([ordered]@{
        label = "baseline"
        style_enabled = $false
        prompt = $baselinePrompt
        graph = $baselineGraphPath
        prompt_id = $ResumeBaselinePromptId
        pre_submission_state = [ordered]@{ recovered_from_completed_prompt = $true }
        raw_output = $baselineRawPath
        raw_output_sha256 = Get-Sha256 $baselineRawPath
        project_output = $baselineProjectPath
        project_output_sha256 = Get-Sha256 $baselineProjectPath
        seconds = $baselineSeconds
    })
    $variants = @([ordered]@{ label = "smartphone-v13-strength-$strengthLabel"; use_style = $true; prompt = $stylePrompt })
}
else {
    $variants = @(
        [ordered]@{ label = "baseline"; use_style = $false; prompt = $baselinePrompt },
        [ordered]@{ label = "smartphone-v13-strength-$strengthLabel"; use_style = $true; prompt = $stylePrompt }
    )
}
foreach ($variant in $variants) {
    $preSubmit = Assert-TargetIdle
    $rawPrefix = "smartphone-snapshot-klein9b-fastest-compatible-4070-ab/$runStamp/$($variant.label)-seed-$seed"
    $graph = New-Graph ([bool]$variant.use_style) ([string]$variant.prompt) $seed $rawPrefix
    $graphPath = Join-Path $projectRunRoot "$($variant.label)-prompt-api.json"
    $graph | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $graphPath -Encoding utf8
    $body = @{ prompt = $graph; client_id = "smartphone-snapshot-klein9b-fastest-compatible-4070-ab" } | ConvertTo-Json -Depth 100
    $started = Get-Date
    $queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
    if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id for $($variant.label)." }
    Write-Host "Queued $($variant.label) on RTX 4070: $($queued.prompt_id)"
    $rawPath = Wait-ComfyPrompt ([string]$queued.prompt_id) "20"
    $candidatePath = Join-Path $projectRunRoot "$($variant.label)-seed-$seed.png"
    Copy-Item -LiteralPath $rawPath -Destination $candidatePath
    $runs.Add([ordered]@{
        label = [string]$variant.label
        style_enabled = [bool]$variant.use_style
        prompt = [string]$variant.prompt
        graph = $graphPath
        prompt_id = [string]$queued.prompt_id
        pre_submission_state = $preSubmit
        raw_output = $rawPath
        raw_output_sha256 = Get-Sha256 $rawPath
        project_output = $candidatePath
        project_output_sha256 = Get-Sha256 $candidatePath
        seconds = [Math]::Round(((Get-Date) - $started).TotalSeconds, 3)
    })
}

$report = [ordered]@{
    schema_version = 1
    status = "pending_evaluation"
    purpose = "one-variable Smartphone Snapshot Photo Reality v13 A/B on fastest compatible local Klein Base 9B identity graph"
    excluded_faster_graph = [ordered]@{
        workflow = "4-step distilled FLUX.2 Klein 9B"
        reason = "incompatible model variant and inference regime; style LoRA is explicitly trained for undistilled Klein Base 9B at 50 Euler steps and CFG 4"
    }
    production_modified = $false
    worker = $Server
    gpu = [string]$targetState.worker.device
    all_queue_snapshots_at_start = $initialQueues
    model = [ordered]@{ name = $baseModel; path = $paths.base_model; sha256 = $baseModelSha256; load_dtype = "fp8_e4m3fn" }
    text_encoder = [ordered]@{ name = $textEncoder; path = $paths.text_encoder; sha256 = $textEncoderSha256 }
    vae = [ordered]@{ name = $vae; path = $paths.vae; sha256 = $vaeSha256 }
    identity_lora = [ordered]@{ name = $identityLora; path = $paths.identity_lora; sha256 = $identityLoraSha256; strength = $identityStrength }
    style_lora = [ordered]@{
        name = $styleLora
        path = $paths.style_lora
        sha256 = $styleLoraSha256
        strength = $StyleStrength
        trigger = $styleTrigger
        civitai_model_id = 2381927
        civitai_model_version_id = 2916530
        civitai_file_id = 2794778
        embedded_base_model = "flux2_klein_9b"
        embedded_training_step = 2520
        embedded_training_epoch = 84
        embedded_rank = 8
        embedded_ai_toolkit_version = "0.9.0"
    }
    lora_order_for_style_variant = @("identity LoRA at 0.90", "Smartphone Snapshot v13 style LoRA at $StyleStrength")
    identity_reference = [ordered]@{ name = $identityReference; path = $paths.identity_reference; sha256 = $identityReferenceSha256; encoded_size = @($referenceWidth, $referenceHeight); role = "identity and adult-age anchor" }
    conditioning_mechanism = "one genuine-photo ReferenceLatent appended to positive and empty-negative conditioning"
    baseline_prompt_source = $BaselineReport
    prompt_difference = "style variant prepends required trigger 'casual snapshot.'; scene and identity prompt otherwise unchanged"
    settings = [ordered]@{ width = $width; height = $height; steps = $steps; cfg = $guidance; sampler = "euler"; scheduler = "Flux2Scheduler"; seed = $seed }
    source_scene_conditioning = $false
    identity_pass = $false
    face_swap = $false
    output_mask = $false
    restoration = $false
    sharpening = $false
    upscaling = $false
    second_model_pass = $false
    runs = @($runs)
    manual_review_required = @(
        "identity and apparent age at full size and thumbnail",
        "hairline, skin texture, and facial geometry",
        "smartphone realism without plastic skin or etched sharpening",
        "background material coherence and depth",
        "pose, gaze, expression, clothing, and scene drift",
        "whether the style benefit justifies implementing it in slower production workflows"
    )
}
$reportPath = Join-Path $projectRunRoot "generation-report.json"
$report | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Host "A/B report: $reportPath"
Write-Output $reportPath
