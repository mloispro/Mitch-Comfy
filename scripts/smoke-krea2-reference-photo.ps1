[CmdletBinding()]
param(
    [string]$Reference = "20260815_165446.jpg",
    [string]$Reference2 = "[none]",
    [string]$Reference3 = "[none]",
    [string]$Prompt = "Using Picture 1 as the identity reference, create a new realistic smartphone photograph of the exact same adult man. Preserve his recognizable facial geometry, eyes, nose, mouth, ears, hairline, current short light-brown hairstyle, apparent age, and natural skin texture. Waist-up on a lively downtown sidewalk in soft open-shade afternoon light, wearing a plain fitted navy crew-neck T-shirt, relaxed candid posture, looking slightly past the camera. Ordinary recent phone camera, natural exposure, subtle sensor texture, realistic skin detail, gentle background detail with unrelated pedestrians. No flash, no studio lighting, no beauty filter, no glamour retouching, no face replacement seam, no copied reference background, no text or watermark.",
    [uint64]$Seed = 8675401,
    [int]$Width = 768,
    [int]$Height = 1152,
    [int]$Port = 8189,
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"
$baseUrl = "http://127.0.0.1:$Port"
$referenceCount = 1 + [int]($Reference2 -ne "[none]") + [int]($Reference3 -ne "[none]")

$stats = Invoke-RestMethod -Uri "$baseUrl/system_stats" -TimeoutSec 10
$deviceName = [string](@($stats.devices)[0].name)
if ($deviceName -notlike "*NVIDIA GeForce RTX 4070*") {
    throw "Port $Port is serving '$deviceName', not the RTX 4070."
}

$objectInfo = Invoke-RestMethod -Uri "$baseUrl/object_info" -TimeoutSec 30
$requiredNodes = @(
    "UNETLoader",
    "LoraLoaderModelOnly",
    "CLIPLoader",
    "VAELoader",
    "LoadImage",
    "TextEncodeQwenImageEditPlus",
    "FluxKontextMultiReferenceLatentMethod",
    "ConditioningZeroOut",
    "ModelSamplingFlux",
    "EmptyLatentImage",
    "KSampler",
    "VAEDecode",
    "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    if (-not $objectInfo.PSObject.Properties[$nodeName]) {
        throw "RTX 4070 ComfyUI is missing required node '$nodeName'."
    }
}

$loraNames = @($objectInfo.LoraLoaderModelOnly.input.required.lora_name[0])
if ($loraNames -notcontains "krea2_style_reference.safetensors") {
    throw "The official Krea2 style-reference LoRA is not visible to ComfyUI."
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
            model = @("1", 0)
            lora_name = "krea2_style_reference.safetensors"
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
        class_type = "TextEncodeQwenImageEditPlus"
        inputs = @{
            clip = @("3", 0)
            vae = @("4", 0)
            image1 = @("5", 0)
            prompt = $Prompt
        }
    }
    "7" = @{
        class_type = "FluxKontextMultiReferenceLatentMethod"
        inputs = @{
            conditioning = @("6", 0)
            reference_latents_method = "index_timestep_zero"
        }
    }
    "8" = @{
        class_type = "ConditioningZeroOut"
        inputs = @{ conditioning = @("7", 0) }
    }
    "9" = @{
        class_type = "ModelSamplingFlux"
        inputs = @{
            model = @("2", 0)
            max_shift = 1.15
            base_shift = 0.5
            width = $Width
            height = $Height
        }
    }
    "10" = @{
        class_type = "EmptyLatentImage"
        inputs = @{
            width = $Width
            height = $Height
            batch_size = 1
        }
    }
    "11" = @{
        class_type = "KSampler"
        inputs = @{
            model = @("9", 0)
            seed = $Seed
            steps = 8
            cfg = 1.0
            sampler_name = "euler"
            scheduler = "simple"
            positive = @("7", 0)
            negative = @("8", 0)
            latent_image = @("10", 0)
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
            images = @("12", 0)
            filename_prefix = "krea2-reference-identity/$referenceCount-references"
        }
    }
}

if ($Reference2 -ne "[none]") {
    $workflow["14"] = @{
        class_type = "LoadImage"
        inputs = @{ image = $Reference2 }
    }
    $workflow["6"].inputs.image2 = @("14", 0)
}
if ($Reference3 -ne "[none]") {
    $workflow["15"] = @{
        class_type = "LoadImage"
        inputs = @{ image = $Reference3 }
    }
    $workflow["6"].inputs.image3 = @("15", 0)
}

$body = @{
    prompt = $workflow
    client_id = "krea2-reference-identity-smoke"
} | ConvertTo-Json -Depth 20

$queued = Invoke-RestMethod -Method Post -Uri "$baseUrl/prompt" -ContentType "application/json" -Body $body
$promptId = [string]$queued.prompt_id
if (-not $promptId) {
    throw "ComfyUI did not return a prompt id."
}
Write-Host "Queued Krea2 $referenceCount-reference identity experiment on RTX 4070: $promptId"

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
        throw "Krea2 reference experiment failed: $($messages -join [Environment]::NewLine)"
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
            Write-Host "Saved: C:\projects\AI-Tools\ComfyUI\output\gpu-4070\$relative"
        }
        exit 0
    }
}

throw "Timed out waiting for Krea2 reference experiment $promptId."
