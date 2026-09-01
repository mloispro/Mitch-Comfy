[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Prompt,
    [Parameter(Mandatory = $true)]
    [string]$OutputPrefix,
    [UInt64]$Seed = 8675418,
    [int]$Width = 832,
    [int]$Height = 1248,
    [string]$Server = "http://127.0.0.1:8188",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"
if (-not $Prompt.Trim()) {
    throw "Prompt cannot be empty."
}

$queue3090 = Invoke-RestMethod -Uri "$Server/queue" -TimeoutSec 10
if (@($queue3090.queue_running).Count -gt 0 -or @($queue3090.queue_pending).Count -gt 0) {
    throw "RTX 3090 ComfyUI queue is not idle."
}
$stats = Invoke-RestMethod -Uri "$Server/system_stats" -TimeoutSec 10
if ([string]$stats.devices[0].name -notmatch "RTX 3090") {
    throw "The selected worker is not the RTX 3090: $($stats.devices[0].name)"
}
$queue4070 = Invoke-RestMethod -Uri "http://127.0.0.1:8189/queue" -TimeoutSec 10
$otherWorkerState = [ordered]@{
    port = 8189
    running = @($queue4070.queue_running).Count
    pending = @($queue4070.queue_pending).Count
    action_taken = "none"
}
if ($otherWorkerState.running -gt 0 -or $otherWorkerState.pending -gt 0) {
    Write-Warning "RTX 4070 worker is active and will be left untouched."
}

$requiredNodes = @(
    "UNETLoader", "CLIPLoader", "VAELoader", "CLIPTextEncode",
    "EmptyFlux2LatentImage", "RandomNoise", "BasicGuider", "KSamplerSelect",
    "Flux2Scheduler", "SamplerCustomAdvanced", "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $info = Invoke-RestMethod -Uri "$Server/object_info/$nodeName" -TimeoutSec 10
    if (-not $info.PSObject.Properties[$nodeName]) {
        throw "Required node unavailable: $nodeName"
    }
}

$modelName = "flux-2-klein-9b-fp8.safetensors"
$clipName = "qwen_3_8b_fp8mixed.safetensors"
$vaeName = "flux2-vae.safetensors"
$modelPath = Join-Path $ComfyRoot "models\diffusion_models\$modelName"
$expectedModelBytes = 9433061528
$modelFile = Get-Item -LiteralPath $modelPath
if ($modelFile.Length -ne [int64]$expectedModelBytes) {
    throw "Unexpected Klein 9B model size: $($modelFile.Length)"
}
$allInfo = Invoke-RestMethod -Uri "$Server/object_info" -TimeoutSec 30
if (@($allInfo.UNETLoader.input.required.unet_name[0]) -notcontains $modelName) {
    throw "Klein 9B model is not visible to the live worker: $modelName"
}
if (@($allInfo.CLIPLoader.input.required.clip_name[0]) -notcontains $clipName) {
    throw "Klein 9B text encoder is not visible to the live worker: $clipName"
}
if (@($allInfo.VAELoader.input.required.vae_name[0]) -notcontains $vaeName) {
    throw "Klein 9B VAE is not visible to the live worker: $vaeName"
}

$workflow = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $modelName; weight_dtype = "default" } }
    "2" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $clipName; type = "flux2"; device = "default" } }
    "3" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vaeName } }
    "4" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $Prompt.Trim(); clip = @("2", 0) } }
    "5" = @{ class_type = "BasicGuider"; inputs = @{ model = @("1", 0); conditioning = @("4", 0) } }
    "6" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    "7" = @{ class_type = "Flux2Scheduler"; inputs = @{ steps = 4; width = $Width; height = $Height } }
    "8" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Seed } }
    "9" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
    "10" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("8", 0); guider = @("5", 0); sampler = @("6", 0); sigmas = @("7", 0); latent_image = @("9", 0) } }
    "11" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("10", 0); vae = @("3", 0) } }
    "12" = @{ class_type = "SaveImage"; inputs = @{ images = @("11", 0); filename_prefix = $OutputPrefix } }
}

$clientId = [guid]::NewGuid().ToString()
$body = @{ prompt = $workflow; client_id = $clientId } | ConvertTo-Json -Depth 50
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt id."
}
Write-Host "Queued Klein 9B text-to-image prompt $($queued.prompt_id) on $Server"

$deadline = (Get-Date).AddMinutes(45)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry) {
        if ($entry.status.status_str -eq "error") {
            throw "Generation failed: $($entry.status.messages | ConvertTo-Json -Depth 20)"
        }
        if ($entry.status.completed) {
            $saved = @($entry.outputs.'12'.images)
            if ($saved.Count -eq 0) {
                throw "Text-to-image generation completed without a saved image."
            }
            $image = $saved[0]
            $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
            $absolutePath = Join-Path (Join-Path $ComfyRoot "output") $relative
            Write-Output ([pscustomobject]@{
                workflow_id = "flux2-klein9b-text-to-image-3090"
                prompt_id = $queued.prompt_id
                worker = $Server
                gpu = [string]$stats.devices[0].name
                model = $modelName
                model_sha256 = "865BA09F5B4C3CBD3468A4BD3ACB9FCB2F8740C54317482F0BCD4ED1D3655CEE"
                text_encoder = $clipName
                vae = $vaeName
                prompt = $Prompt.Trim()
                width = $Width
                height = $Height
                steps = 4
                guidance = "basic distilled guider"
                sampler = "euler"
                seed = $Seed
                input_images = @()
                reference_latents = @()
                character_lora = $null
                identity_adapter = $null
                identity_pass = $false
                face_swap = $null
                mask = $null
                post_processing = $null
                other_worker_activity_at_start = $otherWorkerState
                seconds = [Math]::Round(((Get-Date) - $started).TotalSeconds, 3)
                file = $absolutePath
            } | ConvertTo-Json -Depth 10 -Compress)
            return
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for prompt $($queued.prompt_id)."
