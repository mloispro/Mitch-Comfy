[CmdletBinding()]
param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [string]$ExpectedGpuName = "NVIDIA GeForce RTX 3090",
    [string]$ApprovedSourcePath = "C:\projects\AI-Tools\Mitch-Comfy\output\crowd_route_v1\state-fair\identity-anchor-recovery\lead-raw.png",
    [string]$SceneReference = "state-fair-composition-scale-lock-v1.png",
    [long]$Seed = 8675511,
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
$width = 832
$height = 1248
$crop = @{ x = 176; y = 152; width = 480; height = 1096 }
$core = @{ x = 229; y = 393; width = 374; height = 855 }
$prompt = @"
Continue the visible central rectangular photographic core into one coherent candid vertical rear-smartphone photograph at a busy Midwestern state fair in late-afternoon daylight. The central core already contains the exact adult man, his complete body, clothing, stride, face, hair, and identity at the required camera distance and scale. Preserve that man exactly and generate only the surrounding scene. He is a normal-height pedestrian about 62 percent of frame height, not the tallest person and not an enlarged hero. Add irregular independent fairgoers at varied depths; adults on comparable or closer ground planes must appear comparable in height or larger in perspective. Use natural overlaps, mixed ages and builds, varied colorful ordinary clothing, food stalls, umbrellas, one coherent Ferris wheel, pavement, and fair clutter. Match the core's perspective, open-shade exposure, deep phone focus, restrained HDR, edge response, sensor texture, and contact lighting so the entire frame looks captured at once. No second copy of the central man, no isolated lane, no contour boundary, no collage, no selectively sharpened subject, no repeated faces or poses, no malformed people, no portrait blur, no flash, no beauty filter, no cinematic grade, no text, logo, or watermark.
"@.Trim()

$stats = Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 10
$deviceName = [string](@($stats.devices)[0].name)
if ($deviceName -notlike "*$ExpectedGpuName*") {
    throw "Worker is serving '$deviceName', not the expected $ExpectedGpuName."
}
$queue = Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 10
if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
    throw "The selected ComfyUI worker already has queued work. Nothing was submitted."
}
$objectInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info" -TimeoutSec 45
$requiredNodes = @(
    "UNETLoader", "FluxKVCache", "CLIPLoader", "VAELoader", "CLIPTextEncode",
    "Image Load", "LoadImage", "ImageCrop", "ImageScale", "ImageCompositeMasked",
    "SolidMask", "MaskComposite", "FeatherMask", "MaskToImage", "VAEEncode",
    "SetLatentNoiseMask", "RandomNoise", "BasicGuider", "KSamplerSelect",
    "Flux2Scheduler", "SamplerCustomAdvanced", "VAEDecode", "WholeFramePhoneFinish",
    "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    if (-not $objectInfo.PSObject.Properties[$nodeName]) {
        throw "The selected worker does not expose required node '$nodeName'."
    }
}

$workflow = @{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = "flux-2-klein-9b-kv-fp8.safetensors"; weight_dtype = "default" } }
    "2" = @{ class_type = "FluxKVCache"; inputs = @{ model = @("1", 0) } }
    "3" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = "qwen_3_8b_fp8mixed.safetensors"; type = "flux2"; device = "default" } }
    "4" = @{ class_type = "VAELoader"; inputs = @{ vae_name = "flux2-vae.safetensors" } }
    "5" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $prompt; clip = @("3", 0) } }
    "6" = @{ class_type = "BasicGuider"; inputs = @{ model = @("2", 0); conditioning = @("5", 0) } }
    "7" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    "8" = @{ class_type = "Flux2Scheduler"; inputs = @{ steps = 4; width = $width; height = $height } }
    "9" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Seed } }

    "10" = @{ class_type = "Image Load"; inputs = @{ image_path = $ApprovedSourcePath; RGBA = "false" } }
    "11" = @{ class_type = "ImageCrop"; inputs = @{ image = @("10", 0); width = $crop.width; height = $crop.height; x = $crop.x; y = $crop.y } }
    "12" = @{ class_type = "ImageScale"; inputs = @{ image = @("11", 0); upscale_method = "lanczos"; width = $core.width; height = $core.height; crop = "disabled" } }

    "13" = @{ class_type = "LoadImage"; inputs = @{ image = $SceneReference } }
    "14" = @{ class_type = "ImageScale"; inputs = @{ image = @("13", 0); upscale_method = "lanczos"; width = $width; height = $height; crop = "disabled" } }
    "15" = @{ class_type = "ImageCompositeMasked"; inputs = @{ destination = @("14", 0); source = @("12", 0); x = $core.x; y = $core.y; resize_source = $false } }

    "16" = @{ class_type = "SolidMask"; inputs = @{ value = 1.0; width = $width; height = $height } }
    "17" = @{ class_type = "SolidMask"; inputs = @{ value = 0.0; width = $core.width; height = $core.height } }
    "18" = @{ class_type = "MaskComposite"; inputs = @{ destination = @("16", 0); source = @("17", 0); x = $core.x; y = $core.y; operation = "multiply" } }
    "19" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("15", 0); vae = @("4", 0) } }
    "20" = @{ class_type = "SetLatentNoiseMask"; inputs = @{ samples = @("19", 0); mask = @("18", 0) } }
    "21" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("9", 0); guider = @("6", 0); sampler = @("7", 0); sigmas = @("8", 0); latent_image = @("20", 0) } }
    "22" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("21", 0); vae = @("4", 0) } }

    "23" = @{ class_type = "SolidMask"; inputs = @{ value = 1.0; width = $core.width; height = $core.height } }
    "24" = @{ class_type = "FeatherMask"; inputs = @{ mask = @("23", 0); left = 40; top = 40; right = 40; bottom = 0 } }
    "25" = @{ class_type = "ImageCompositeMasked"; inputs = @{ destination = @("22", 0); source = @("12", 0); x = $core.x; y = $core.y; resize_source = $false; mask = @("24", 0) } }
    "26" = @{ class_type = "WholeFramePhoneFinish"; inputs = @{ image = @("25", 0) } }
    "27" = @{ class_type = "MaskToImage"; inputs = @{ mask = @("18", 0) } }

    # A second pass touches only narrow rectangular seam bands.  The complete
    # person remains outside this mask, so identity/body pixels stay owned by
    # the uniformly scaled approved core rather than a subject contour.
    "40" = @{ class_type = "SolidMask"; inputs = @{ value = 0.0; width = $width; height = $height } }
    "41" = @{ class_type = "SolidMask"; inputs = @{ value = 1.0; width = 104; height = $height } }
    "42" = @{ class_type = "FeatherMask"; inputs = @{ mask = @("41", 0); left = 44; top = 0; right = 44; bottom = 0 } }
    "43" = @{ class_type = "MaskComposite"; inputs = @{ destination = @("40", 0); source = @("42", 0); x = 177; y = 0; operation = "add" } }
    "44" = @{ class_type = "MaskComposite"; inputs = @{ destination = @("43", 0); source = @("42", 0); x = 551; y = 0; operation = "add" } }
    "45" = @{ class_type = "SolidMask"; inputs = @{ value = 1.0; width = $width; height = 112 } }
    "46" = @{ class_type = "FeatherMask"; inputs = @{ mask = @("45", 0); left = 0; top = 48; right = 0; bottom = 48 } }
    "47" = @{ class_type = "MaskComposite"; inputs = @{ destination = @("44", 0); source = @("46", 0); x = 0; y = 337; operation = "add" } }
    "48" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("25", 0); vae = @("4", 0) } }
    "49" = @{ class_type = "SetLatentNoiseMask"; inputs = @{ samples = @("48", 0); mask = @("47", 0) } }
    "50" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = ($Seed + 1) } }
    "51" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("50", 0); guider = @("6", 0); sampler = @("7", 0); sigmas = @("8", 0); latent_image = @("49", 0) } }
    "52" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("51", 0); vae = @("4", 0) } }
    "53" = @{ class_type = "WholeFramePhoneFinish"; inputs = @{ image = @("52", 0) } }
    "54" = @{ class_type = "MaskToImage"; inputs = @{ mask = @("47", 0) } }

    "30" = @{ class_type = "SaveImage"; inputs = @{ images = @("12", 0); filename_prefix = "crowd-route-v1/state-fair-scaled-core/core-seed-$Seed" } }
    "31" = @{ class_type = "SaveImage"; inputs = @{ images = @("15", 0); filename_prefix = "crowd-route-v1/state-fair-scaled-core/provisional-seed-$Seed" } }
    "32" = @{ class_type = "SaveImage"; inputs = @{ images = @("27", 0); filename_prefix = "crowd-route-v1/state-fair-scaled-core/outside-mask-seed-$Seed" } }
    "33" = @{ class_type = "SaveImage"; inputs = @{ images = @("25", 0); filename_prefix = "crowd-route-v1/state-fair-scaled-core/final-raw-seed-$Seed" } }
    "34" = @{ class_type = "SaveImage"; inputs = @{ images = @("26", 0); filename_prefix = "crowd-route-v1/state-fair-scaled-core/final-phone-seed-$Seed" } }
    "35" = @{ class_type = "SaveImage"; inputs = @{ images = @("54", 0); filename_prefix = "crowd-route-v1/state-fair-scaled-core/seam-mask-seed-$Seed" } }
    "36" = @{ class_type = "SaveImage"; inputs = @{ images = @("52", 0); filename_prefix = "crowd-route-v1/state-fair-scaled-core/seam-blended-raw-seed-$Seed" } }
    "37" = @{ class_type = "SaveImage"; inputs = @{ images = @("53", 0); filename_prefix = "crowd-route-v1/state-fair-scaled-core/seam-blended-phone-seed-$Seed" } }
}

$body = @{ prompt = $workflow; client_id = "klein9b-scaled-identity-core" } | ConvertTo-Json -Depth 30
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$ComfyUrl/prompt" -ContentType "application/json" -Body $body
$promptId = [string]$queued.prompt_id
if (-not $promptId) {
    throw "ComfyUI did not return a prompt id: $($queued | ConvertTo-Json -Depth 12 -Compress)"
}
Write-Host "Queued identity-safe scaled rectangular core on $ExpectedGpuName`: $promptId"

$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
while ([DateTime]::UtcNow -lt $deadline) {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$promptId" -TimeoutSec 20
    $record = $history.PSObject.Properties[$promptId].Value
    if (-not $record) { continue }
    if ($record.status.status_str -eq "error") {
        $messages = @($record.status.messages | ForEach-Object { $_ | ConvertTo-Json -Depth 20 -Compress })
        throw "Scaled identity-core run failed: $($messages -join [Environment]::NewLine)"
    }
    if ($record.status.completed -or $record.status.status_str -eq "success") {
        foreach ($output in $record.outputs.PSObject.Properties.Value) {
            foreach ($image in @($output.images)) {
                if ($image.filename) {
                    $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                    Write-Host "Saved: C:\projects\AI-Tools\ComfyUI\output\$relative"
                }
            }
        }
        [pscustomobject]@{
            prompt_id = $promptId
            elapsed_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
            seed = $Seed
            source_crop = $crop
            scaled_core = $core
            prompt = $prompt
        } | ConvertTo-Json -Depth 8
        exit 0
    }
}
throw "Timed out waiting for scaled identity-core prompt $promptId."
