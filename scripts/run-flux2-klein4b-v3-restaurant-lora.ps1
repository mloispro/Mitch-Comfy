[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8188",
    [string]$ExpectedGpuName = "NVIDIA GeForce RTX 3090",
    [string]$LoraName = "aitk\m1tch-flux2-klein-4b-identity-v3-portrait-profile.safetensors",
    [double]$LoraStrength = 1.20,
    [int]$Steps = 20,
    [double]$Guidance = 4.0,
    [long]$Seed = 8675310,
    [int]$Width = 768,
    [int]$Height = 1024,
    [string]$OutputPrefix = "flux2-klein4b-v3-lora/restaurant-face-shape-arms",
    [int]$TimeoutSeconds = 900,
    [string]$Prompt = @"
A completely new vertical photorealistic restaurant portrait of m1tch_person, the same real adult man learned by the character LoRA, containing exactly one person. Preserve his recognizable outer head silhouette and natural facial proportions: forehead and temple width, cheekbone width, cheek fullness, jaw width and taper, chin width and length, and true face length-to-width ratio. Preserve his eye shape and spacing, nose, mouth, ears, natural hairline, short light-brown hair, apparent age, faint stubble, and unretouched skin. Do not lengthen, narrow, widen, square, idealize, masculinize, beautify, or average his face.

He sits centered at a white restaurant table wearing a tailored light-gray double-breasted blazer over a plain black shirt. His right elbow rests naturally on the table and his right hand lightly supports his chin. His left shoulder, upper arm, elbow, forearm, wrist, and hand form one complete anatomically connected limb; his left forearm rests naturally on the table with the hand clearly visible. Show both complete shoulders, exactly two complete arms, exactly two hands, and natural fingers. Frame from mid-torso upward but wide enough to keep both elbows, forearms, and hands inside the image.

A small glowing table lamp sits in the left foreground. Warm nested arched mirror lights glow behind him against dark reflective walls with palm leaves and a chair. Calm direct gaze, ordinary camera perspective, realistic jacket sleeves and table contact, natural skin texture, believable low-light detail. No other people, missing limb, fused arm, cropped arm, extra limb, duplicate hand, face swap, collage, beauty filter, portrait blur, text, logo, or watermark.
"@
)

$ErrorActionPreference = "Stop"
$comfyRoot = "C:\projects\AI-Tools\ComfyUI"
$outputRoot = Join-Path $comfyRoot "output"

$serverUri = [Uri]$Server
$targetPort = $serverUri.Port
foreach ($port in 8188, 8189) {
    $worker = "http://127.0.0.1:$port"
    $queue = Invoke-RestMethod -Uri "$worker/queue" -TimeoutSec 10
    $running = @($queue.queue_running).Count
    $pending = @($queue.queue_pending).Count
    if ($port -eq $targetPort -and ($running -gt 0 -or $pending -gt 0)) {
        throw "Target ComfyUI worker $worker is active. Refusing to queue over existing work."
    }
    if ($port -ne $targetPort -and ($running -gt 0 -or $pending -gt 0)) {
        Write-Warning "Other ComfyUI worker $worker is active and will remain untouched."
    }
}

$stats = Invoke-RestMethod -Uri "$Server/system_stats" -TimeoutSec 10
$deviceName = [string](@($stats.devices)[0].name)
if ($deviceName -notlike "*$ExpectedGpuName*") {
    throw "Target worker is '$deviceName', not the expected $ExpectedGpuName."
}

$requiredNodes = @(
    "UNETLoader", "LoraLoaderModelOnly", "CLIPLoader", "CLIPTextEncode",
    "CFGGuider", "KSamplerSelect", "Flux2Scheduler", "RandomNoise",
    "EmptyFlux2LatentImage", "SamplerCustomAdvanced", "VAELoader",
    "VAEDecode", "SaveImage"
)
$objectInfo = Invoke-RestMethod -Uri "$Server/object_info" -TimeoutSec 45
foreach ($nodeName in $requiredNodes) {
    if (-not $objectInfo.PSObject.Properties[$nodeName]) {
        throw "Required node is unavailable on the target worker: $nodeName"
    }
}

$modelName = "flux-2-klein-base-4b-fp8.safetensors"
$clipName = "qwen_3_4b_fp8_mixed.safetensors"
$vaeName = "flux2-vae.safetensors"
if (@($objectInfo.UNETLoader.input.required.unet_name[0]) -notcontains $modelName) {
    throw "The target worker cannot see $modelName."
}
if (@($objectInfo.CLIPLoader.input.required.clip_name[0]) -notcontains $clipName) {
    throw "The target worker cannot see $clipName."
}
if (@($objectInfo.VAELoader.input.required.vae_name[0]) -notcontains $vaeName) {
    throw "The target worker cannot see $vaeName."
}
if (@($objectInfo.LoraLoaderModelOnly.input.required.lora_name[0]) -notcontains $LoraName) {
    throw "The target worker cannot see $LoraName."
}

$loraPath = Join-Path (Join-Path $comfyRoot "models\loras") $LoraName
$loraSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $loraPath).Hash
$expectedLoraSha256 = "C43D7C1FCA404A8B316A9D0C8756E140033E4763532628F62FACC791F0B8A149"
if ($loraSha256 -ne $expectedLoraSha256) {
    throw "Unexpected LoRA hash for $loraPath`: $loraSha256"
}

$workflow = @{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $modelName; weight_dtype = "default" } }
    "2" = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $LoraName; strength_model = $LoraStrength } }
    "3" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $clipName; type = "flux2" } }
    "4" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $Prompt.Trim(); clip = @("3", 0) } }
    "5" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("3", 0) } }
    "6" = @{ class_type = "CFGGuider"; inputs = @{ model = @("2", 0); positive = @("4", 0); negative = @("5", 0); cfg = $Guidance } }
    "7" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    "8" = @{ class_type = "Flux2Scheduler"; inputs = @{ width = $Width; height = $Height; steps = $Steps } }
    "9" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Seed } }
    "10" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
    "11" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("9", 0); guider = @("6", 0); sampler = @("7", 0); sigmas = @("8", 0); latent_image = @("10", 0) } }
    "12" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vaeName } }
    "13" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("11", 0); vae = @("12", 0) } }
    "14" = @{ class_type = "SaveImage"; inputs = @{ images = @("13", 0); filename_prefix = $OutputPrefix } }
}

$body = @{ prompt = $workflow; client_id = "flux2-klein4b-v3-restaurant-lora" } | ConvertTo-Json -Depth 24
$started = Get-Date
$queued = Invoke-RestMethod -Uri "$Server/prompt" -Method Post -ContentType "application/json" -Body $body
$promptId = [string]$queued.prompt_id
if (-not $promptId) {
    throw "ComfyUI did not return a prompt id."
}
Write-Host "Queued Klein Base 4B + Mitch v3 LoRA on $ExpectedGpuName`: $promptId"

$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
while ([DateTime]::UtcNow -lt $deadline) {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$Server/history/$promptId" -TimeoutSec 20
    $record = $history.PSObject.Properties[$promptId].Value
    if (-not $record) {
        continue
    }
    if ($record.status.status_str -eq "error") {
        throw "Generation failed: $($record.status.messages | ConvertTo-Json -Depth 20)"
    }
    if ($record.status.completed -or $record.status.status_str -eq "success") {
        $image = @($record.outputs."14".images)[0]
        if (-not $image.filename) {
            throw "Generation completed without a saved image."
        }
        $relativePath = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
        [ordered]@{
            prompt_id = $promptId
            worker = $deviceName
            model = $modelName
            lora = $LoraName
            lora_sha256 = $loraSha256
            lora_strength = $LoraStrength
            trigger = "m1tch_person"
            reference_image = $null
            starts_from_empty_latent = $true
            prompt = $Prompt.Trim()
            width = $Width
            height = $Height
            steps = $Steps
            guidance = $Guidance
            sampler = "euler"
            seed = $Seed
            seconds = [Math]::Round(((Get-Date) - $started).TotalSeconds, 3)
            file = Join-Path $outputRoot $relativePath
        } | ConvertTo-Json -Depth 12 -Compress
        return
    }
}

throw "Timed out waiting for prompt $promptId."
