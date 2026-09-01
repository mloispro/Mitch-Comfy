[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SceneImage,
    [Parameter(Mandatory = $true)]
    [string]$IdentityPrompt,
    [Parameter(Mandatory = $true)]
    [string]$OutputPrefix,
    [UInt64]$IdentitySeed = 9472363,
    [ValidateRange(1, 100)]
    [int]$IdentitySteps = 30,
    [int]$Width = 832,
    [int]$Height = 1248,
    [string]$ReferenceFace = "mitch-inline-author-ref-01-face.jpg",
    [string]$ReferenceAngle = "mitch-inline-author-ref-02-angle.jpg",
    [string]$ReferenceFront = "mitch-inline-author-ref-03-front-outdoor.jpg",
    [string]$Server = "http://127.0.0.1:8188",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"
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
    "UNETLoader", "CLIPLoader", "VAELoader", "LoadImage", "ImageScaleToTotalPixels",
    "VAEEncode", "ReferenceLatent", "CLIPTextEncode", "EmptyFlux2LatentImage",
    "CFGGuider", "KSamplerSelect", "Flux2Scheduler", "RandomNoise",
    "SamplerCustomAdvanced", "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $info = Invoke-RestMethod -Uri "$Server/object_info/$nodeName" -TimeoutSec 10
    if (-not $info.PSObject.Properties[$nodeName]) {
        throw "Required node unavailable: $nodeName"
    }
}

$modelName = "flux-2-klein-base-4b-fp8.safetensors"
$clipName = "qwen_3_4b_fp8_mixed.safetensors"
$vaeName = "flux2-vae.safetensors"
$allInfo = Invoke-RestMethod -Uri "$Server/object_info" -TimeoutSec 30
if (@($allInfo.UNETLoader.input.required.unet_name[0]) -notcontains $modelName) {
    throw "Identity model is not visible to the live worker: $modelName"
}
if (@($allInfo.CLIPLoader.input.required.clip_name[0]) -notcontains $clipName) {
    throw "Identity text encoder is not visible to the live worker: $clipName"
}
if (@($allInfo.VAELoader.input.required.vae_name[0]) -notcontains $vaeName) {
    throw "VAE is not visible to the live worker: $vaeName"
}

$inputRoot = Join-Path $ComfyRoot "input"
foreach ($inputName in @($SceneImage, $ReferenceFace, $ReferenceAngle, $ReferenceFront)) {
    if (-not (Test-Path -LiteralPath (Join-Path $inputRoot $inputName) -PathType Leaf)) {
        throw "Required local input is missing: $inputName"
    }
}
if (-not $IdentityPrompt.Trim()) {
    throw "IdentityPrompt cannot be empty."
}

$prompt = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $modelName; weight_dtype = "default" } }
    "2" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $clipName; type = "flux2"; device = "default" } }
    "3" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vaeName } }
    "4" = @{ class_type = "LoadImage"; inputs = @{ image = $SceneImage } }
    "5" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("4", 0); upscale_method = "lanczos"; megapixels = 0.5; resolution_steps = 1 } }
    "6" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("5", 0); vae = @("3", 0) } }
    "7" = @{ class_type = "LoadImage"; inputs = @{ image = $ReferenceFace } }
    "8" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("7", 0); upscale_method = "lanczos"; megapixels = 1.0; resolution_steps = 1 } }
    "9" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("8", 0); vae = @("3", 0) } }
    "10" = @{ class_type = "LoadImage"; inputs = @{ image = $ReferenceAngle } }
    "11" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("10", 0); upscale_method = "lanczos"; megapixels = 1.0; resolution_steps = 1 } }
    "12" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("11", 0); vae = @("3", 0) } }
    "13" = @{ class_type = "LoadImage"; inputs = @{ image = $ReferenceFront } }
    "14" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("13", 0); upscale_method = "lanczos"; megapixels = 1.0; resolution_steps = 1 } }
    "15" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("14", 0); vae = @("3", 0) } }
    "16" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $IdentityPrompt; clip = @("2", 0) } }
    "17" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("2", 0) } }
    "18" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("16", 0); latent = @("6", 0) } }
    "19" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("18", 0); latent = @("9", 0) } }
    "20" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("19", 0); latent = @("12", 0) } }
    "21" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("20", 0); latent = @("15", 0) } }
    "22" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("17", 0); latent = @("6", 0) } }
    "23" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("22", 0); latent = @("9", 0) } }
    "24" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("23", 0); latent = @("12", 0) } }
    "25" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("24", 0); latent = @("15", 0) } }
    "26" = @{ class_type = "CFGGuider"; inputs = @{ model = @("1", 0); positive = @("21", 0); negative = @("25", 0); cfg = 4.0 } }
    "27" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    "28" = @{ class_type = "Flux2Scheduler"; inputs = @{ steps = $IdentitySteps; width = $Width; height = $Height } }
    "29" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $IdentitySeed } }
    "30" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
    "31" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("29", 0); guider = @("26", 0); sampler = @("27", 0); sigmas = @("28", 0); latent_image = @("30", 0) } }
    "32" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("31", 0); vae = @("3", 0) } }
    "33" = @{ class_type = "SaveImage"; inputs = @{ images = @("32", 0); filename_prefix = $OutputPrefix } }
}

$clientId = [guid]::NewGuid().ToString()
$body = @{ prompt = $prompt; client_id = $clientId } | ConvertTo-Json -Depth 100
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt id."
}
Write-Host "Queued 9B-plate to Base-4B identity refinement $($queued.prompt_id) on $Server"

$deadline = (Get-Date).AddMinutes(60)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry) {
        if ($entry.status.status_str -eq "error") {
            throw "Generation failed: $($entry.status.messages | ConvertTo-Json -Depth 20)"
        }
        if ($entry.status.completed) {
            $saved = @($entry.outputs.'33'.images)
            if ($saved.Count -eq 0) {
                throw "The identity refinement completed without a saved image."
            }
            $image = $saved[0]
            $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
            $absolutePath = Join-Path (Join-Path $ComfyRoot "output") $relative
            Write-Output ([pscustomobject]@{
                workflow_id = "flux2-klein9b-plate-4b-identity-refinement"
                prompt_id = $queued.prompt_id
                worker = $Server
                gpu = [string]$stats.devices[0].name
                scene_reference = $SceneImage
                scene_reference_megapixels = 0.5
                identity_references = @($ReferenceFace, $ReferenceAngle, $ReferenceFront)
                identity_reference_megapixels_each = 1.0
                model = $modelName
                text_encoder = $clipName
                vae = $vaeName
                steps = $IdentitySteps
                cfg = 4.0
                sampler = "euler"
                seed = $IdentitySeed
                prompt = $IdentityPrompt
                width = $Width
                height = $Height
                character_lora = $null
                identity_adapter = $null
                output_mask = $null
                face_swap = $null
                post_processing = $null
                other_worker_activity_at_start = $otherWorkerState
                seconds = [Math]::Round(((Get-Date) - $started).TotalSeconds, 3)
                file = $absolutePath
            } | ConvertTo-Json -Depth 12 -Compress)
            return
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for prompt $($queued.prompt_id)."
