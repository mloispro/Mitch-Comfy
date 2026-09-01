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
foreach ($required in "source_scene", "scene_prompt", "target_x", "target_y", "head_scale", "seed") {
    if ($required -notin $requiredInputs) { throw "Live node is missing required input: $required" }
}

if (-not (Test-Path -LiteralPath $WorkflowPath -PathType Leaf)) { throw "Missing production workflow: $WorkflowPath" }
$workflow = Get-Content -Raw -LiteralPath $WorkflowPath | ConvertFrom-Json
if (@($workflow.nodes | Where-Object type -eq $NodeName).Count -ne 1) {
    throw "Production workflow must contain exactly one $NodeName node."
}
if (@($workflow.nodes | Where-Object type -eq "LoadImage").Count -ne 1) {
    throw "Production workflow must contain exactly one source LoadImage node."
}

$loraPath = Join-Path $ComfyRoot "models\loras\$LoraName"
$identityPath = Join-Path $ComfyRoot "input\$IdentityName"
$sourcePath = Join-Path $ComfyRoot "input\$SourceName"
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $loraPath).Hash -ne $LoraHash) { throw "Protected LoRA hash mismatch" }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $identityPath).Hash -ne $IdentityHash) { throw "Protected identity-reference hash mismatch" }
if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw "Missing smoke source image: $sourcePath" }

$validation = [ordered]@{
    status = "passed"
    workflow = $WorkflowPath
    node = $NodeName
    gpu = $device
    lora = $LoraName
    identity_reference = $IdentityName
    queues = $queueState
    smoke_requested = [bool]$Smoke
}
if (-not $Smoke) {
    $validation | ConvertTo-Json -Depth 10
    exit 0
}

$scenePrompt = (
    "A photorealistic vertical phone-flash group photograph matching the source. Four adults sit closely on the " +
    "rust-orange booth, with a partial fifth person at the extreme image-right edge. Mitch is the selected central " +
    "seated man, wearing a fitted dark navy suit and crisp white open-collar shirt. Both complete forearms extend down " +
    "and his separate hands rest on his thighs. Keep every surrounding person distinct and unrelated. Preserve the " +
    "source camera framing, people count, seated body poses, copper wall, amber perimeter light, booth, low table, " +
    "objects, ordinary smartphone perspective, direct flash, and seamless natural detail."
)
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
