[CmdletBinding()]
param(
    [string]$Reference = "20260815_165446.jpg",
    [string]$SceneReference = "[none]",
    [string]$Prompt = "",
    [uint64]$Seed = 9472103,
    [int]$Width = 832,
    [int]$Height = 1248,
    [int]$Steps = 12,
    [double]$RefBoost = 6.0,
    [double]$SmartphoneLoraStrength = 0.0,
    [double]$GokayRealismLoraStrength = 0.0,
    [double]$SceneRefBoost = 1.0,
    [int]$GroundingPixels = 768,
    [switch]$FaceAttentionMask,
    [switch]$ApplyPhoneFinish,
    [int]$Port = 8189,
    [string]$ExpectedGpuName = "",
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
$baseUrl = "http://127.0.0.1:$Port"
$twoInputMode = $SceneReference -ne "[none]"
$smartphoneLoraName = "krea-smartphone-photo-slider.safetensors"
$gokayRealismLoraName = "krea2_realism_lora_comfy.safetensors"

if ($SmartphoneLoraStrength -ne 0.0 -and $GokayRealismLoraStrength -ne 0.0) {
    throw "Use only one realism LoRA per controlled experiment."
}

if ([string]::IsNullOrWhiteSpace($Prompt)) {
    if ($twoInputMode) {
        $Prompt = @"
Use the first image as the scene and the second image as the identity reference. Restage the exact
same man from the second image as the single clear subject walking naturally toward the camera in
the first image's busy downtown sidewalk. Preserve his exact recognizable facial identity, face
shape, forehead lines, eye shape and spacing, nose, mouth, ears, short light-brown hairstyle,
hairline, apparent age, natural skin texture, and lean build. Integrate his whole body into the
scene's existing perspective, daylight, exposure, sharpness, depth, occlusions, phone-camera noise,
and pedestrian motion. He is not posing and nobody is grouped with him. Plain fitted navy crew-neck
T-shirt and dark casual pants. No flash, no studio lighting, no beauty filter, no portrait-mode blur,
no face swap, no pasted head boundary, no collage, no selectively sharpened face, no text, and no
watermark. Make the result look like one real smartphone photograph captured in a single moment.
"@
    }
    else {
        $Prompt = @"
Restage this exact same man in a completely new candid vertical smartphone photograph, walking
naturally toward the camera on a genuinely busy downtown sidewalk. Preserve his exact recognizable
facial identity, face shape, forehead lines, eye shape and spacing, nose, mouth, ears, short
light-brown hairstyle, hairline, apparent age, natural skin texture, and lean build. Show him about
knees-up, slightly off center, mid-stride, wearing a plain fitted navy crew-neck T-shirt and dark
casual pants. He is clearly the subject but is not posing. Unrelated pedestrians move in both
directions at varied depths with overlapping bodies and different actions; nobody is grouped with
him. Use ordinary soft open-shade afternoon daylight, natural recent-smartphone exposure,
restrained phone HDR, realistic skin pores, subtle sensor texture, normal deep phone-camera focus,
and mild motion blur only on moving background pedestrians. No flash, no studio lighting, no beauty
filter, no cinematic grade, no portrait-mode blur, no copied source background, no collage, no face
swap, no pasted head boundary, no selectively sharpened face, no text, and no watermark. Make the
result look like one real photograph captured in a single moment.
"@
    }
}

$expectedGpu = $ExpectedGpuName
if ([string]::IsNullOrWhiteSpace($expectedGpu)) {
    $expectedGpu = switch ($Port) {
        8188 { "NVIDIA GeForce RTX 3090" }
        8189 { "NVIDIA GeForce RTX 4070" }
        default { throw "Pass -ExpectedGpuName when using ComfyUI port $Port." }
    }
}

$stats = Invoke-RestMethod -Uri "$baseUrl/system_stats" -TimeoutSec 10
$deviceName = [string](@($stats.devices)[0].name)
if ($deviceName -notlike "*$expectedGpu*") {
    throw "Port $Port is serving '$deviceName', not the expected $expectedGpu worker."
}

$queue = Invoke-RestMethod -Uri "$baseUrl/queue" -TimeoutSec 10
if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
    throw "Port $Port already has queued work. The smoke test was not submitted."
}

$objectInfo = Invoke-RestMethod -Uri "$baseUrl/object_info" -TimeoutSec 45
$requiredNodes = @(
    "UNETLoader",
    "LoraLoaderModelOnly",
    "CLIPLoader",
    "VAELoader",
    "LoadImage",
    "VAEEncode",
    "EmptySD3LatentImage",
    "Krea2EditModelPatch",
    "Krea2EditGroundedEncode",
    "KSampler",
    "VAEDecode",
    "SaveImage"
)
if ($FaceAttentionMask) {
    $requiredNodes += "Krea2ReferenceFaceAttentionMask"
}
if ($ApplyPhoneFinish) {
    $requiredNodes += "WholeFramePhoneFinish"
}
foreach ($nodeName in $requiredNodes) {
    if (-not $objectInfo.PSObject.Properties[$nodeName]) {
        throw "RTX 4070 ComfyUI is missing required node '$nodeName'."
    }
}

$loraNames = @($objectInfo.LoraLoaderModelOnly.input.required.lora_name[0])
if ($loraNames -notcontains "krea2_identity_edit_v1_2.safetensors") {
    throw "Krea2 Identity Edit v1.2 is not visible to ComfyUI."
}
if ($SmartphoneLoraStrength -ne 0.0 -and $loraNames -notcontains $smartphoneLoraName) {
    throw "Krea2 smartphone photography LoRA is not visible to ComfyUI."
}
if ($GokayRealismLoraStrength -ne 0.0 -and $loraNames -notcontains $gokayRealismLoraName) {
    throw "Gokay Krea2 realism LoRA is not visible to ComfyUI."
}

$identityModelInput = @("1", 0)
$outputVariant = "baseline"
$activeRealismLoraName = $null
$activeRealismLoraStrength = 0.0
if ($SmartphoneLoraStrength -ne 0.0) {
    $identityModelInput = @("16", 0)
    $outputVariant = "smartphone-$($SmartphoneLoraStrength.ToString('0.00', [Globalization.CultureInfo]::InvariantCulture).Replace('.', 'p'))"
    $activeRealismLoraName = $smartphoneLoraName
    $activeRealismLoraStrength = $SmartphoneLoraStrength
}
elseif ($GokayRealismLoraStrength -ne 0.0) {
    $identityModelInput = @("16", 0)
    $outputVariant = "gokay-realism-converted-$($GokayRealismLoraStrength.ToString('0.00', [Globalization.CultureInfo]::InvariantCulture).Replace('.', 'p'))"
    $activeRealismLoraName = $gokayRealismLoraName
    $activeRealismLoraStrength = $GokayRealismLoraStrength
}
if ($FaceAttentionMask) {
    $outputVariant = "$outputVariant-face-attention"
}
if ($ApplyPhoneFinish) {
    $outputVariant = "$outputVariant-phone-finish"
}

$workflow = @{
    "1" = @{
        class_type = "UNETLoader"
        inputs = @{
            unet_name = "krea2_turbo_fp8_scaled.safetensors"
            weight_dtype = "default"
        }
    }
    "2" = @{
        class_type = "LoraLoaderModelOnly"
        inputs = @{
            model = $identityModelInput
            lora_name = "krea2_identity_edit_v1_2.safetensors"
            strength_model = 1.0
        }
    }
    "3" = @{
        class_type = "CLIPLoader"
        inputs = @{
            clip_name = "qwen3vl_4b_fp8_scaled.safetensors"
            type = "krea2"
            device = "default"
        }
    }
    "4" = @{
        class_type = "VAELoader"
        inputs = @{ vae_name = "qwen_image_vae.safetensors" }
    }
    "5" = @{
        class_type = "LoadImage"
        inputs = @{ image = $Reference }
    }
    "6" = @{
        class_type = "VAEEncode"
        inputs = @{
            pixels = @("5", 0)
            vae = @("4", 0)
        }
    }
    "7" = @{
        class_type = "EmptySD3LatentImage"
        inputs = @{
            width = $Width
            height = $Height
            batch_size = 1
        }
    }
    "11" = @{
        class_type = "KSampler"
        inputs = @{
            model = @("8", 0)
            seed = $Seed
            steps = $Steps
            cfg = 1.0
            sampler_name = "euler"
            scheduler = "simple"
            positive = @("9", 0)
            negative = @("10", 0)
            latent_image = @("7", 0)
            denoise = 1.0
        }
    }
    "12" = @{
        class_type = "VAEDecode"
        inputs = @{
            samples = @("11", 0)
            vae = @("4", 0)
        }
    }
    "13" = @{
        class_type = "SaveImage"
        inputs = @{
            images = if ($ApplyPhoneFinish) { @("18", 0) } else { @("12", 0) }
            filename_prefix = if ($twoInputMode) {
                "krea2-identity-edit/mitch-sidewalk-scene-plus-identity-$outputVariant"
            }
            else {
                "krea2-identity-edit/mitch-sidewalk-single-ref-$outputVariant"
            }
        }
    }
}

if ($activeRealismLoraName) {
    $workflow["16"] = @{
        class_type = "LoraLoaderModelOnly"
        inputs = @{
            model = @("1", 0)
            lora_name = $activeRealismLoraName
            strength_model = $activeRealismLoraStrength
        }
    }
}

if ($FaceAttentionMask) {
    $workflow["17"] = @{
        class_type = "Krea2ReferenceFaceAttentionMask"
        inputs = @{
            image = @("5", 0)
            width_scale = 0.82
            height_scale = 0.86
            vertical_offset = 0.02
        }
    }
}

if ($ApplyPhoneFinish) {
    $workflow["18"] = @{
        class_type = "WholeFramePhoneFinish"
        inputs = @{
            image = @("12", 0)
        }
    }
}

if ($twoInputMode) {
    $workflow["14"] = @{
        class_type = "LoadImage"
        inputs = @{ image = $SceneReference }
    }
    $workflow["15"] = @{
        class_type = "VAEEncode"
        inputs = @{
            pixels = @("14", 0)
            vae = @("4", 0)
        }
    }
    $patchInputs = @{
        model = @("2", 0)
        source_latent = @("15", 0)
        source_latent_b = @("6", 0)
        ref_boost = $RefBoost
        ref_boost_a = $SceneRefBoost
        fit_mode = "fit"
        vae = @("4", 0)
        source_image = @("14", 0)
        source_image_b = @("5", 0)
        target_latent = @("7", 0)
    }
    $groundedInputs = @{
        clip = @("3", 0)
        image = @("14", 0)
        image_b = @("5", 0)
        grounding_px = $GroundingPixels
        system_prompt = ""
    }
}
else {
    $patchInputs = @{
        model = @("2", 0)
        source_latent = @("6", 0)
        ref_boost = $RefBoost
        ref_boost_a = 1.0
        fit_mode = "fit"
        vae = @("4", 0)
        source_image = @("5", 0)
        target_latent = @("7", 0)
    }
    $groundedInputs = @{
        clip = @("3", 0)
        image = @("5", 0)
        grounding_px = $GroundingPixels
        system_prompt = ""
    }
}

if ($FaceAttentionMask) {
    $patchInputs.ref_boost_mask = @("17", 0)
}

$workflow["8"] = @{
    class_type = "Krea2EditModelPatch"
    inputs = $patchInputs
}
$workflow["9"] = @{
    class_type = "Krea2EditGroundedEncode"
    inputs = $groundedInputs.Clone()
}
$workflow["9"].inputs.prompt = $Prompt
$workflow["10"] = @{
    class_type = "Krea2EditGroundedEncode"
    inputs = $groundedInputs.Clone()
}
$workflow["10"].inputs.prompt = ""

$body = @{
    prompt = $workflow
    client_id = "krea2-identity-edit-smoke"
} | ConvertTo-Json -Depth 24

$queued = Invoke-RestMethod -Method Post -Uri "$baseUrl/prompt" -ContentType "application/json" -Body $body
$promptId = [string]$queued.prompt_id
if (-not $promptId) {
    $details = $queued | ConvertTo-Json -Depth 20 -Compress
    throw "ComfyUI did not return a prompt id: $details"
}

$modeLabel = if ($twoInputMode) { "scene + identity" } else { "single identity reference" }
Write-Host "Queued Krea2 Identity Edit ($modeLabel) on $expectedGpu`: $promptId"

$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
while ([DateTime]::UtcNow -lt $deadline) {
    Start-Sleep -Seconds 3
    $history = Invoke-RestMethod -Uri "$baseUrl/history/$promptId" -TimeoutSec 20
    $record = $history.PSObject.Properties[$promptId].Value
    if (-not $record) {
        continue
    }
    if ($record.status.status_str -eq "error") {
        $messages = @($record.status.messages | ForEach-Object { $_ | ConvertTo-Json -Depth 20 -Compress })
        throw "Krea2 Identity Edit failed: $($messages -join [Environment]::NewLine)"
    }
    if ($record.status.completed) {
        $images = @($record.outputs.PSObject.Properties.Value.images | ForEach-Object { $_ })
        foreach ($image in $images) {
            $relative = if ($image.subfolder) {
                Join-Path $image.subfolder $image.filename
            }
            else {
                $image.filename
            }
            $outputRoot = if ($Port -eq 8189) {
                "C:\projects\AI-Tools\ComfyUI\output\gpu-4070"
            }
            else {
                "C:\projects\AI-Tools\ComfyUI\output"
            }
            Write-Host "Saved: $outputRoot\$relative"
        }
        exit 0
    }
}

throw "Timed out waiting for Krea2 Identity Edit prompt $promptId."
