[CmdletBinding()]
param(
    [string]$Prompt = @"
An ordinary candid vertical 1x rear smartphone photograph of m1tch_person walking naturally toward the camera through a genuinely busy Midwestern state fair in clear late-afternoon open daylight. He is the unmistakable subject but is not posing, shown approximately full body and slightly off center in a natural mid-stride, wearing a plain fitted navy crew-neck T-shirt, dark casual pants, and ordinary dark sneakers. Preserve m1tch_person's recognizable adult male identity, current short light-brown hair and hairline, apparent age, lean build, and natural skin texture. Numerous unrelated fairgoers overlap naturally at varied depths and move in both directions while performing different actions. They have visibly different ages, builds, hair, posture, and naturally varied clothing across muted red, green, denim blue, tan, yellow, gray, patterns, black, and white; no coordinated crowd wardrobe or dominant shirt color. Include one coherent Ferris wheel in the middle distance, food stalls, colorful umbrellas, ride structures, pavement, railings, and ordinary fair clutter. Use natural deep phone-camera focus with resolved foreground and middle-distance people and structures, gentle far-distance falloff, restrained phone HDR, subtle sensor texture, and slight motion only on moving people. The subject and crowd share one exposure, sharpness progression, noise response, perspective, shadows, and edge quality. No flash, portrait-mode blur, beauty filter, cinematic grading, staged group pose, duplicated people, pasted boundary, selective sharpening, legible text, logo, or watermark. Make it look like one unedited phone photograph captured in a single moment.
"@,
    [uint64]$Seed = 9472103,
    [int]$Width = 896,
    [int]$Height = 1344,
    [int]$Steps = 8,
    [double]$MitchLoraStrength = 0.85,
    [double]$SmartphoneLoraStrength = 0.35,
    [switch]$SkipPhoneFinish,
    [int]$Port = 8188,
    [string]$ExpectedGpuName = "NVIDIA GeForce RTX 3090",
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
$baseUrl = "http://127.0.0.1:$Port"
$mitchLoraName = "aitk\mitch-krea2-identity-v1.safetensors"
$smartphoneLoraName = "krea-smartphone-photo-slider.safetensors"

$stats = Invoke-RestMethod -Uri "$baseUrl/system_stats" -TimeoutSec 10
$deviceName = [string](@($stats.devices)[0].name)
if ($deviceName -notlike "*$ExpectedGpuName*") {
    throw "Port $Port is serving '$deviceName', not the expected $ExpectedGpuName worker."
}

$queue = Invoke-RestMethod -Uri "$baseUrl/queue" -TimeoutSec 10
if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
    throw "Port $Port already has queued work. The character-LoRA test was not submitted."
}

$objectInfo = Invoke-RestMethod -Uri "$baseUrl/object_info" -TimeoutSec 45
$requiredNodes = @(
    "UNETLoader",
    "LoraLoaderModelOnly",
    "CLIPLoader",
    "CLIPTextEncode",
    "VAELoader",
    "EmptySD3LatentImage",
    "KSampler",
    "VAEDecode",
    "SaveImage"
)
if (-not $SkipPhoneFinish) {
    $requiredNodes += "WholeFramePhoneFinish"
}
foreach ($nodeName in $requiredNodes) {
    if (-not $objectInfo.PSObject.Properties[$nodeName]) {
        throw "The selected worker does not expose required node '$nodeName'."
    }
}

$loraNames = @($objectInfo.LoraLoaderModelOnly.input.required.lora_name[0])
foreach ($loraName in @($mitchLoraName, $smartphoneLoraName)) {
    if ($loraNames -notcontains $loraName) {
        throw "Required Krea2 LoRA is not visible to ComfyUI: $loraName"
    }
}

$mitchStrengthLabel = $MitchLoraStrength.ToString('0.00', [Globalization.CultureInfo]::InvariantCulture).Replace('.', 'p')
$smartphoneStrengthLabel = $SmartphoneLoraStrength.ToString('0.00', [Globalization.CultureInfo]::InvariantCulture).Replace('.', 'p')
$finishLabel = if ($SkipPhoneFinish) { "raw" } else { "phone-finish" }

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
            model = @("1", 0)
            lora_name = $smartphoneLoraName
            strength_model = $SmartphoneLoraStrength
        }
    }
    "3" = @{
        class_type = "LoraLoaderModelOnly"
        inputs = @{
            model = @("2", 0)
            lora_name = $mitchLoraName
            strength_model = $MitchLoraStrength
        }
    }
    "4" = @{
        class_type = "CLIPLoader"
        inputs = @{
            clip_name = "qwen3vl_4b_fp8_scaled.safetensors"
            type = "krea2"
            device = "default"
        }
    }
    "5" = @{
        class_type = "CLIPTextEncode"
        inputs = @{
            text = $Prompt.Trim()
            clip = @("4", 0)
        }
    }
    "6" = @{
        class_type = "VAELoader"
        inputs = @{ vae_name = "qwen_image_vae.safetensors" }
    }
    "7" = @{
        class_type = "EmptySD3LatentImage"
        inputs = @{
            width = $Width
            height = $Height
            batch_size = 1
        }
    }
    "8" = @{
        class_type = "KSampler"
        inputs = @{
            model = @("3", 0)
            seed = $Seed
            steps = $Steps
            cfg = 1.0
            sampler_name = "euler"
            scheduler = "simple"
            positive = @("5", 0)
            negative = @("5", 0)
            latent_image = @("7", 0)
            denoise = 1.0
        }
    }
    "9" = @{
        class_type = "VAEDecode"
        inputs = @{
            samples = @("8", 0)
            vae = @("6", 0)
        }
    }
    "11" = @{
        class_type = "SaveImage"
        inputs = @{
            images = if ($SkipPhoneFinish) { @("9", 0) } else { @("10", 0) }
            filename_prefix = "krea2-character-lora/state-fair-mitch-$mitchStrengthLabel-smartphone-$smartphoneStrengthLabel-$finishLabel"
        }
    }
}

if (-not $SkipPhoneFinish) {
    $workflow["10"] = @{
        class_type = "WholeFramePhoneFinish"
        inputs = @{ image = @("9", 0) }
    }
}

$body = @{
    prompt = $workflow
    client_id = "krea2-character-lora-smoke"
} | ConvertTo-Json -Depth 20

$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$baseUrl/prompt" -ContentType "application/json" -Body $body
$promptId = [string]$queued.prompt_id
if (-not $promptId) {
    throw "ComfyUI did not return a prompt id: $($queued | ConvertTo-Json -Depth 12 -Compress)"
}
Write-Host "Queued clean Krea2 Mitch-LoRA state-fair test on $ExpectedGpuName`: $promptId"

$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
while ([DateTime]::UtcNow -lt $deadline) {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$baseUrl/history/$promptId" -TimeoutSec 20
    $record = $history.PSObject.Properties[$promptId].Value
    if (-not $record) {
        continue
    }
    if ($record.status.status_str -eq "error") {
        $messages = @($record.status.messages | ForEach-Object { $_ | ConvertTo-Json -Depth 20 -Compress })
        throw "Clean Krea2 character-LoRA test failed: $($messages -join [Environment]::NewLine)"
    }
    if ($record.status.completed -or $record.status.status_str -eq "success") {
        foreach ($output in $record.outputs.PSObject.Properties.Value) {
            foreach ($image in @($output.images)) {
                if (-not $image.filename) {
                    continue
                }
                $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                $outputRoot = if ($Port -eq 8189) { "C:\projects\AI-Tools\ComfyUI\output\gpu-4070" } else { "C:\projects\AI-Tools\ComfyUI\output" }
                Write-Host "Saved: $outputRoot\$relative"
            }
        }
        Write-Host "Elapsed seconds: $([math]::Round(((Get-Date) - $started).TotalSeconds, 3))"
        exit 0
    }
}

throw "Timed out waiting for clean Krea2 character-LoRA prompt $promptId."
