[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8188",
    [switch]$Smoke
)

$ErrorActionPreference = "Stop"
$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WorkflowPath = Join-Path $ProjectRoot "workflows\production\FLUX.2 Klein 9B Mitch Group Scene Studio v1.json"
$NodeName = "Flux2Klein9BMitchGroupSceneStudioV1"
$LoraName = "m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors"
$LoraHash = "D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC"
$StyleLoraName = "smartphone-snapshot\FLUX.2-klein-base-9B_SmartphoneSnapshotPhotoReality_v13.safetensors"
$StyleLoraHash = "1E0B419B1448F77CF7AEF430625325E46B16D1515CBF6C5C7E8C14D938CF1A90"
$TurboLoraName = "flux2-klein9b-turbo\Flux_Klein_9b_Turbo_lora_rank_256_bf16_standard.safetensors"
$TurboLoraHash = "A3BFA40E936AF059C2D0814DE8E9E5531FA0EB135087ADD22C27510685585600"
$IdentityName = "mitch-klein9b-ref-training04-front-neutral.jpg"
$IdentityHash = "31870369467B7A8FC19199D7877F56257FED2B0F28B08AA183006BCD3112DDAB"
$SourceName = "mitch-klein9b-layout-lounge-center-source.png"

$queueState = [ordered]@{}
foreach ($port in 8188, 8189, 8190) {
    try {
        $queue = Invoke-RestMethod -Uri "http://127.0.0.1:$port/queue" -TimeoutSec 5
        $running = @($queue.queue_running).Count
        $pending = @($queue.queue_pending).Count
        $queueState[[string]$port] = [ordered]@{ running = $running; pending = $pending }
        if ($Smoke -and ($running -gt 0 -or $pending -gt 0)) {
            throw "ComfyUI queue is active at port $port."
        }
        if (-not $Smoke -and ($running -gt 0 -or $pending -gt 0)) {
            Write-Warning "Port $port is active; read-only validation will continue without modifying it."
        }
    }
    catch {
        if ($port -eq ([uri]$Server).Port -or $_.Exception.Message -match "queue is active") { throw }
        Write-Warning "Optional worker port $port could not be inspected: $($_.Exception.Message)"
    }
}

$stats = Invoke-RestMethod -Uri "$Server/system_stats" -TimeoutSec 10
$device = [string]@($stats.devices)[0].name
if ($device -notmatch "RTX 3090") { throw "Group Scene Studio requires RTX 3090; worker reports $device" }

$nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$NodeName" -TimeoutSec 20
if (-not $nodeInfo.PSObject.Properties[$NodeName]) { throw "Live ComfyUI worker is missing $NodeName" }
$requiredInputs = @($nodeInfo.$NodeName.input_order.required)
foreach ($required in "source_scene", "scene_prompt", "target_x", "target_y", "head_scale", "appearance_polish", "fast_turbo", "seed") {
    if ($required -notin $requiredInputs) { throw "Live node is missing required input: $required" }
}

if (-not (Test-Path -LiteralPath $WorkflowPath -PathType Leaf)) { throw "Missing production workflow: $WorkflowPath" }
$workflow = Get-Content -Raw -LiteralPath $WorkflowPath | ConvertFrom-Json
if (@($workflow.nodes | Where-Object type -eq $NodeName).Count -ne 1) {
    throw "Production workflow must contain exactly one $NodeName node."
}
$studioNode = @($workflow.nodes | Where-Object type -eq $NodeName)[0]
if (@($studioNode.inputs).Count -ne 8) { throw "Production Group Studio node input contract drifted." }
if ([bool]$studioNode.widgets_values[4] -ne $false) { throw "Production Group Studio must open in the validated identity-first natural-appearance mode." }
if ([bool]$studioNode.widgets_values[5] -ne $false) { throw "Production Group Studio quality baseline must open with Fast Turbo disabled." }
if (@($workflow.nodes | Where-Object type -eq "LoadImage").Count -ne 1) {
    throw "Production workflow must contain exactly one source LoadImage node."
}

$groupSourcePath = Join-Path $ProjectRoot "custom_nodes\ComfyUI-AIToolkit-Training\flux2_klein9b_group_scene_studio.py"
$groupSource = Get-Content -Raw -LiteralPath $groupSourcePath
foreach ($requiredText in @(
    "Canny edge map derived from the source photograph",
    "does not supply his identity",
    "exclusively ",
    "supplies the selected man's identity and internal facial geometry",
    "GROUP_IDENTITY_SAFE_POLISH",
    '"default": False'
)) {
    if ($groupSource -notmatch [regex]::Escape($requiredText)) {
        throw "Production Group Studio is missing the concise identity-first contract: $requiredText"
    }
}
foreach ($rejectedText in @("preserve_bone_structure=True", "Present him about three to five years younger")) {
    if ($groupSource -match [regex]::Escape($rejectedText)) {
        throw "Production Group Studio still contains rejected identity-drifting prompt text: $rejectedText"
    }
}

$loraPath = Join-Path $ComfyRoot "models\loras\$LoraName"
$styleLoraPath = Join-Path $ComfyRoot "models\loras\$StyleLoraName"
$turboLoraPath = Join-Path $ComfyRoot "models\loras\$TurboLoraName"
$identityPath = Join-Path $ComfyRoot "input\$IdentityName"
$sourcePath = Join-Path $ComfyRoot "input\$SourceName"
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $loraPath).Hash -ne $LoraHash) { throw "Protected LoRA hash mismatch" }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $styleLoraPath).Hash -ne $StyleLoraHash) { throw "Smartphone Snapshot v13 LoRA hash mismatch" }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $turboLoraPath).Hash -ne $TurboLoraHash) { throw "Rank-256 BF16 Turbo LoRA hash mismatch" }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $identityPath).Hash -ne $IdentityHash) { throw "Protected identity-reference hash mismatch" }
if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw "Missing smoke source image: $sourcePath" }

$validation = [ordered]@{
    status = "passed"
    workflow = $WorkflowPath
    node = $NodeName
    gpu = $device
    lora = $LoraName
    smartphone_style = [ordered]@{ lora = $StyleLoraName; sha256 = $StyleLoraHash; strength = 0.25; trigger = "casual snapshot" }
    turbo = [ordered]@{ lora = $TurboLoraName; sha256 = $TurboLoraHash; strength = 1.0; enabled_by_default = $false; enabled_settings = "8 Euler steps / CFG 1"; quality_fallback = "50 Euler steps / CFG 4" }
    identity_reference = $IdentityName
    queues = $queueState
    smoke_requested = [bool]$Smoke
}
if (-not $Smoke) {
    $validation | ConvertTo-Json -Depth 10
    exit 0
}

$scenePrompt = [string]$studioNode.widgets_values[0]
$prompt = [ordered]@{
    "1" = @{ class_type = "LoadImage"; inputs = @{ image = $SourceName } }
    "2" = @{
        class_type = $NodeName
        inputs = @{
            source_scene = @("1", 0)
            scene_prompt = $scenePrompt
            target_x = 0.50
            target_y = 0.44
            head_scale = 0.92
            appearance_polish = $false
            fast_turbo = $false
            seed = 8675412
        }
    }
}
$body = @{ prompt = $prompt; client_id = [guid]::NewGuid().ToString() } | ConvertTo-Json -Depth 100
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id" }

$deadline = (Get-Date).AddMinutes(15)
do {
    Start-Sleep -Seconds 5
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 15
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry) {
        if ($entry.status.status_str -eq "error") {
            throw "Smoke generation failed: $($entry.status.messages | ConvertTo-Json -Depth 30)"
        }
        if ($entry.status.completed) {
            $images = @($entry.outputs."2".images)
            if ($images.Count -eq 0) { throw "Smoke generation completed without a saved photo" }
            $saved = foreach ($image in $images) {
                $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                Join-Path (Join-Path $ComfyRoot "output") $relative
            }
            $validation.smoke_prompt_id = $queued.prompt_id
            $validation.smoke_outputs = @($saved)
            $validation | ConvertTo-Json -Depth 20
            exit 0
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for Group Scene Studio smoke generation"
