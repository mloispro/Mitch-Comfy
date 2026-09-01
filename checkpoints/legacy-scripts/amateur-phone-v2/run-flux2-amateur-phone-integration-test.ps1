[CmdletBinding()]
param(
    [string]$SourceImage = "output\flux2-amateur-phone-v2-4070\stage1-9b.png",
    [double]$SceneReferenceMegapixels = 1.0,
    [string]$ReferenceFace = "mitch-inline-author-ref-01-face.jpg",
    [string]$ReferenceAngle = "mitch-inline-author-ref-02-angle.jpg",
    [string]$ReferenceFront = "mitch-inline-author-ref-03-front-outdoor.jpg",
    [UInt64]$Seed = 9472363,
    [int]$Width = 832,
    [int]$Height = 1248,
    [int]$Steps = 30,
    [string]$Server = "http://127.0.0.1:8189",
    [string]$OutputPrefix = "flux2-amateur-phone-v2-4070/integration-scene-1mp",
    [int]$TimeoutSeconds = 900,
    [switch]$AllowRejectedExperiment
)

$ErrorActionPreference = "Stop"
if (-not $AllowRejectedExperiment) {
    throw "This experiment was rejected by Mitch for obvious visual failure. It is retained only to prevent rediscovery. Use -AllowRejectedExperiment only for deliberate failure analysis."
}
$sourcePath = [System.IO.Path]::GetFullPath($SourceImage)
if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
    throw "Source image does not exist: $sourcePath"
}

# Protect both workers before submitting exclusively to the RTX 4070 worker.
foreach ($port in 8188, 8189) {
    $worker = "http://127.0.0.1:$port"
    $queue = Invoke-RestMethod -Uri "$worker/queue" -TimeoutSec 10
    if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
        throw "ComfyUI queue is not idle at $worker. Nothing was submitted."
    }
}
$stats = Invoke-RestMethod -Uri "$Server/system_stats" -TimeoutSec 10
$deviceName = [string](@($stats.devices)[0].name)
if ($deviceName -notlike "*RTX 4070*") {
    throw "Integration test must run on the RTX 4070, but $Server serves '$deviceName'."
}

$requiredNodes = @(
    "UNETLoader", "CLIPLoader", "VAELoader", "Image Load", "ImageScaleToTotalPixels",
    "LoadImage", "VAEEncode", "ReferenceLatent", "CLIPTextEncode", "CFGGuider",
    "KSamplerSelect", "Flux2Scheduler", "RandomNoise", "EmptyFlux2LatentImage",
    "SamplerCustomAdvanced", "VAEDecode", "SaveImage", "EmptyImage", "Image Blend",
    "Image Film Grain"
)
$objectInfo = Invoke-RestMethod -Uri "$Server/object_info" -TimeoutSec 45
foreach ($nodeName in $requiredNodes) {
    if (-not $objectInfo.PSObject.Properties[$nodeName]) {
        throw "Required node is unavailable: $nodeName"
    }
}

$modelName = "flux-2-klein-base-4b-fp8.safetensors"
$clipName = "qwen_3_4b_fp8_mixed.safetensors"
$vaeName = "flux2-vae.safetensors"
if (@($objectInfo.UNETLoader.input.required.unet_name[0]) -notcontains $modelName) {
    throw "Model is not visible to the live worker: $modelName"
}
if (@($objectInfo.CLIPLoader.input.required.clip_name[0]) -notcontains $clipName) {
    throw "Text encoder is not visible to the live worker: $clipName"
}
if (@($objectInfo.VAELoader.input.required.vae_name[0]) -notcontains $vaeName) {
    throw "VAE is not visible to the live worker: $vaeName"
}

$identityPrompt = (
    "Image 1 is the source phone snapshot and defines the exact off-center composition, slight camera " +
    "roll, imperfect crop, camera perspective, subject pose and clothing, partial edge pedestrian, " +
    "crowd layout, cars, buildings, traffic lights, signs, crosswalk, pavement, exposure, clipped sky, " +
    "shadow detail, motion, and depth. Images 2, 3, and 4 are genuine photographs of Mitch and define " +
    "the exact identity of the main man in image 1. Recreate image 1 while changing only the main man " +
    "so he is unmistakably Mitch from images 2, 3, and 4. Preserve his apparent age, facial geometry, " +
    "eyes, forehead, nose, jaw, mouth, ears, hairline, hairstyle, natural stubble, unretouched skin, lean " +
    "build, clothing, pose, scale, and placement. Preserve all of image 1 camera imperfections and do not " +
    "recenter, beautify, smooth, enlarge the head, sharpen only the face, alter the crowd, create portrait " +
    "blur, crop, mask, composite, add text, or add a watermark. Every pedestrian remains distinct and unrelated."
)

$prompt = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $modelName; weight_dtype = "default" } }
    "2" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $clipName; type = "flux2"; device = "default" } }
    "3" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vaeName } }
    "4" = @{ class_type = "Image Load"; inputs = @{ image_path = $sourcePath; RGBA = "false" } }
    "5" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("4", 0); upscale_method = "lanczos"; megapixels = $SceneReferenceMegapixels; resolution_steps = 1 } }
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
    "16" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $identityPrompt; clip = @("2", 0) } }
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
    "28" = @{ class_type = "Flux2Scheduler"; inputs = @{ steps = $Steps; width = $Width; height = $Height } }
    "29" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Seed } }
    "30" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
    "31" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("29", 0); guider = @("26", 0); sampler = @("27", 0); sigmas = @("28", 0); latent_image = @("30", 0) } }
    "32" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("31", 0); vae = @("3", 0) } }
    "33" = @{ class_type = "SaveImage"; inputs = @{ images = @("32", 0); filename_prefix = "$OutputPrefix-raw" } }
    "34" = @{ class_type = "EmptyImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1; color = 16777215 } }
    "35" = @{ class_type = "Image Blend"; inputs = @{ image_a = @("32", 0); image_b = @("34", 0); blend_percentage = 0.05 } }
    "36" = @{ class_type = "Image Film Grain"; inputs = @{ image = @("35", 0); density = 0.10; intensity = 0.02; highlights = 1.0; supersample_factor = 2 } }
    "37" = @{ class_type = "SaveImage"; inputs = @{ images = @("36", 0); filename_prefix = "$OutputPrefix-light" } }
}

$body = @{ prompt = $prompt; client_id = "flux2-integration-$(New-Guid)" } | ConvertTo-Json -Depth 100
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id." }
Write-Host "Queued integration test $($queued.prompt_id) on $Server"

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.PSObject.Properties[[string]$queued.prompt_id].Value
    if (-not $entry) { continue }
    if ($entry.status.status_str -eq "error") {
        throw "Integration generation failed: $($entry.status.messages | ConvertTo-Json -Depth 20)"
    }
    if ($entry.status.completed -or $entry.status.status_str -eq "success") {
        $outputRoot = "C:\projects\AI-Tools\ComfyUI\output\gpu-4070"
        $resolve = {
            param($image)
            $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
            Join-Path $outputRoot $relative
        }
        $rawImage = @($entry.outputs.'33'.images)[0]
        $lightImage = @($entry.outputs.'37'.images)[0]
        if (-not $rawImage -or -not $lightImage) { throw "Integration test did not save both outputs." }
        [ordered]@{
            prompt_id = [string]$queued.prompt_id
            worker = $Server
            gpu = $deviceName
            elapsed_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
            controlled_change = "scene reference megapixels: 0.5 to $SceneReferenceMegapixels"
            source = $sourcePath
            model = $modelName
            seed = $Seed
            steps = $Steps
            cfg = 4.0
            raw = (& $resolve $rawImage)
            light_finish = (& $resolve $lightImage)
        } | ConvertTo-Json -Depth 10
        exit 0
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for integration test $($queued.prompt_id)."
