[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8188",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [switch]$Smoke,
    [int]$TimeoutSeconds = 1800
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WorkflowPath = Join-Path $ProjectRoot "workflows\production\FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1.json"
$NodeName = "Flux2Klein9BPhotoRealismUpgradeV1"
$SourceName = "mitch-canyon-source-edit-05333f6f.png"
$Detail = "Preserve the exact canyon and river layout. Render layered weathered rock, irregular vegetation, believable river banks and water, natural foreground stone, and gradual atmospheric depth with restrained phone-camera detail."

function Get-WorkerSnapshot([int]$Port) {
    try {
        $base = "http://127.0.0.1:$Port"
        $stats = Invoke-RestMethod -Uri "$base/system_stats" -TimeoutSec 5
        $queue = Invoke-RestMethod -Uri "$base/queue" -TimeoutSec 5
        [ordered]@{
            port = $Port
            online = $true
            device = [string]$stats.devices[0].name
            running = @($queue.queue_running).Count
            pending = @($queue.queue_pending).Count
            vram_total = [int64]$stats.devices[0].vram_total
            vram_free = [int64]$stats.devices[0].vram_free
        }
    }
    catch {
        [ordered]@{ port = $Port; online = $false; device = "offline"; running = 0; pending = 0; vram_total = 0; vram_free = 0 }
    }
}

function Assert-Hash([string]$Path, [string]$Expected, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing $Label`: $Path" }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
    if ($actual -ne $Expected) { throw "$Label SHA-256 mismatch. Expected $Expected, found $actual." }
}

if (-not (Test-Path -LiteralPath $WorkflowPath -PathType Leaf)) { throw "Missing production workflow: $WorkflowPath" }
$workflow = Get-Content -Raw -LiteralPath $WorkflowPath | ConvertFrom-Json
if ($workflow.nodes.Count -ne 5) { throw "Production sheet must contain exactly five visible nodes." }
foreach ($required in @("MarkdownNote", "LoadImage", $NodeName, "PreviewImage")) {
    if ($required -notin @($workflow.nodes.type)) { throw "Production sheet is missing $required." }
}
$upgradeNode = @($workflow.nodes | Where-Object type -eq $NodeName)[0]
if (@($upgradeNode.inputs).Count -ne 3) { throw "Upgrade node must expose only source_photo, detail_instructions, and seed." }
if ([UInt64]$upgradeNode.widgets_values[1] -ne 8675416) { throw "Production sheet no longer opens at approved seed 8675416." }

$workers = @(@(8188, 8189, 8190) | ForEach-Object { Get-WorkerSnapshot $_ })
$target = @($workers | Where-Object port -eq 8188)[0]
if (-not $target.online -or $target.device -notmatch "RTX 3090") { throw "Port 8188 is not the RTX 3090 worker." }
if ($target.running -gt 0 -or $target.pending -gt 0) { throw "RTX 3090 queue is active; refusing validation submission." }
if (([Uri]$Server).Port -ne 8188) { throw "This workflow is locked to the RTX 3090 worker on port 8188." }

$nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$NodeName" -TimeoutSec 30
if (-not $nodeInfo.$NodeName) { throw "Live RTX 3090 worker does not expose $NodeName; restart the worker after installing the workflow." }
$requiredInputs = @($nodeInfo.$NodeName.input.required.PSObject.Properties.Name)
if (($requiredInputs -join ",") -ne "source_photo,detail_instructions,seed") {
    throw "Live node input contract drifted: $($requiredInputs -join ', ')"
}

$hashes = [ordered]@{
    workflow = (Get-FileHash -Algorithm SHA256 -LiteralPath $WorkflowPath).Hash.ToUpperInvariant()
    model = "4A54FAD7F5F741B99EEE217198DAAC20B8D8E515E2A1F5B064FD51CF074F95BD"
    text_encoder = "ABAD16806E0CBABC54E0325D6565847443FE396D5F0BE38BB3CD3FE75A1201D6"
    vae = "D64F3A68E1CC4F9F4E29B6E0DA38A0204FE9A49F2D4053F0EC1FA1CA02F9C4B5"
    lora = "D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC"
    identity = "28DF2AE0D717A788370CC825F7BB24CF38DB9C7CDA3F66BAEFAB58BE86D8AF33"
    hair = "3B7C223BFB6390AED6981EB3C3549CC767BDC967B887D170153EFA6BE7DDB201"
    smoke_source = "05333F6FD60DAB6629F34B616A3E1FEA4771B997AA472675FCCCD1F6A2535EEF"
}
Assert-Hash (Join-Path $ComfyRoot "models\diffusion_models\flux-2-klein-base-9b-bf16.safetensors") $hashes.model "Klein Base 9B model"
Assert-Hash (Join-Path $ComfyRoot "models\text_encoders\qwen_3_8b_fp8mixed.safetensors") $hashes.text_encoder "Qwen 3 8B text encoder"
Assert-Hash (Join-Path $ComfyRoot "models\vae\flux2-vae.safetensors") $hashes.vae "FLUX.2 VAE"
Assert-Hash (Join-Path $ComfyRoot "models\loras\m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors") $hashes.lora "protected step-1600 LoRA"
Assert-Hash (Join-Path $ComfyRoot "input\mitch-klein9b-ref-front-neutral-v2.jpg") $hashes.identity "genuine identity reference"
Assert-Hash (Join-Path $ComfyRoot "input\mitch-natural-hair-only-val05-isolated.png") $hashes.hair "isolated hair reference"

$validation = [ordered]@{
    schema_version = 1
    status = "validated"
    workflow = $WorkflowPath
    node = $NodeName
    workers = $workers
    nvidia_smi = @(& nvidia-smi --query-gpu=index,name,uuid,memory.total,memory.used,memory.free,utilization.gpu,pstate --format=csv,noheader,nounits)
    hashes = $hashes
    locked_settings = [ordered]@{ model_dtype = "fp8_e4m3fn"; lora_strength = 0.90; steps = 50; cfg = 4.0; sampler = "euler"; scheduler = "Flux2Scheduler" }
    forbidden_stages = [ordered]@{ source_latent_init = $false; face_swap = $false; output_mask = $false; restoration = $false; sharpening = $false; upscaling = $false; second_pass = $false }
}

if (-not $Smoke) {
    $validation | ConvertTo-Json -Depth 20
    exit 0
}

$sourcePath = Join-Path $ComfyRoot "input\$SourceName"
Assert-Hash $sourcePath $hashes.smoke_source "smoke source"
$workersAtSubmit = @(@(8188, 8189, 8190) | ForEach-Object { Get-WorkerSnapshot $_ })
$targetAtSubmit = @($workersAtSubmit | Where-Object port -eq 8188)[0]
if (-not $targetAtSubmit.online -or $targetAtSubmit.device -notmatch "RTX 3090") {
    throw "Port 8188 changed before smoke submission."
}
if ($targetAtSubmit.running -gt 0 -or $targetAtSubmit.pending -gt 0) {
    throw "RTX 3090 queue became active before smoke submission."
}
$validation.workers_at_submit = $workersAtSubmit
$prompt = [ordered]@{
    "1" = @{ class_type = "LoadImage"; inputs = @{ image = $SourceName } }
    "2" = @{ class_type = $NodeName; inputs = @{ source_photo = @("1", 0); detail_instructions = $Detail; seed = [UInt64]8675412 } }
}
$body = @{ prompt = $prompt; client_id = "verify-upgrade-photo-$([guid]::NewGuid().ToString('N'))" } | ConvertTo-Json -Depth 30
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body -TimeoutSec 60
if (-not $queued.prompt_id) { throw "ComfyUI did not return a smoke prompt ID." }
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 5
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 15
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry -and $entry.status.status_str -eq "error") {
        throw "Smoke generation failed: $($entry.status.messages | ConvertTo-Json -Depth 30)"
    }
    if ($entry -and ($entry.status.completed -or $entry.status.status_str -eq "success")) {
        $images = @($entry.outputs.'2'.images)
        if ($images.Count -eq 0) { throw "Smoke generation completed without a saved photo." }
        $validation.status = "smoke_generated_pending_visual_and_identity_review"
        $validation.smoke_prompt_id = [string]$queued.prompt_id
        $validation.smoke_runtime_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
        $validation.smoke_outputs = @($images | ForEach-Object {
            $relative = if ($_.subfolder) { Join-Path $_.subfolder $_.filename } else { $_.filename }
            Join-Path (Join-Path $ComfyRoot "output") $relative
        })
        $validation | ConvertTo-Json -Depth 20
        exit 0
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for Upgrade Photo Detail & Realism smoke generation."
