[CmdletBinding()]
param(
    [string]$Reference = "20260815_165446.jpg",
    [string]$Prompt = "An ordinary unedited iPhone rear-camera photograph of the same man from Picture 1 walking naturally toward the camera on a busy downtown sidewalk in soft open-shade afternoon light. Portrait mode is off. Natural 1x phone-camera perspective and depth of field, with nearby pedestrians and storefronts reasonably detailed. Candid imperfect mid-stride framing, restrained phone HDR, natural skin texture, slight sensor noise and compression. He wears a plain navy crew-neck T-shirt and dark pants.",
    [UInt64]$Seed = 17072027,
    [int]$Width = 832,
    [int]$Height = 1248,
    [int]$Port = 8189,
    [int]$TimeoutSeconds = 900,
    [string]$OutputPrefix = "krea2-reid-iphone/mitch-iphone"
)

$ErrorActionPreference = "Stop"

$comfyRoot = "C:\projects\AI-Tools\ComfyUI"
$baseUrl = "http://127.0.0.1:$Port"
$expectedGpu = "NVIDIA GeForce RTX 4070"
$referencePath = Join-Path (Join-Path $comfyRoot "input") $Reference

if (-not (Test-Path -LiteralPath $referencePath -PathType Leaf)) {
    throw "Reference image was not found in the ComfyUI input folder: $referencePath"
}
if (($Width % 16) -ne 0 -or ($Height % 16) -ne 0) {
    throw "Width and height must both be divisible by 16. Received ${Width}x${Height}."
}

$stats = Invoke-RestMethod -Uri "$baseUrl/system_stats" -TimeoutSec 10
$deviceName = [string](@($stats.devices)[0].name)
if ($deviceName -notlike "*$expectedGpu*") {
    throw "Port $Port is serving '$deviceName', not the expected RTX 4070 worker."
}

$objectInfo = Invoke-RestMethod -Uri "$baseUrl/object_info" -TimeoutSec 30
$requiredNodes = @(
    "TextEncodeKrea2OstrisEdit",
    "Krea2OstrisEditModelPatch",
    "FluxKontextMultiReferenceLatentMethod"
)
foreach ($nodeName in $requiredNodes) {
    if ($objectInfo.PSObject.Properties.Name -notcontains $nodeName) {
        throw "Required ReID node is not loaded: $nodeName"
    }
}

$workflow = [ordered]@{
    "1" = @{
        class_type = "VAELoader"
        inputs = @{ vae_name = "qwen_image_vae.safetensors" }
    }
    "2" = @{
        class_type = "UNETLoader"
        inputs = @{
            unet_name = "krea2_turbo_int8_convrot.safetensors"
            weight_dtype = "default"
        }
    }
    "3" = @{
        class_type = "CLIPLoader"
        inputs = @{
            clip_name = "qwen3vl_4b_bf16.safetensors"
            type = "krea2"
            device = "default"
        }
    }
    "4" = @{
        class_type = "LoadImage"
        inputs = @{ image = $Reference }
    }
    "5" = @{
        class_type = "ImageScaleToTotalPixels"
        inputs = @{
            image = @("4", 0)
            upscale_method = "area"
            megapixels = 0.140625
            resolution_steps = 16
        }
    }
    "6" = @{
        class_type = "LoraLoaderModelOnly"
        inputs = @{
            model = @("2", 0)
            lora_name = "krea2_reid_rank32.safetensors"
            strength_model = 1.0
        }
    }
    "7" = @{
        class_type = "Krea2OstrisEditModelPatch"
        inputs = @{
            model = @("6", 0)
            kv_cache = $true
        }
    }
    "8" = @{
        class_type = "TextEncodeKrea2OstrisEdit"
        inputs = @{
            clip = @("3", 0)
            prompt = $Prompt
            vae = @("1", 0)
            image1 = @("5", 0)
        }
    }
    "9" = @{
        class_type = "FluxKontextMultiReferenceLatentMethod"
        inputs = @{
            conditioning = @("8", 0)
            reference_latents_method = "index_timestep_zero"
        }
    }
    "10" = @{
        class_type = "TextEncodeKrea2OstrisEdit"
        inputs = @{
            clip = @("3", 0)
            prompt = ""
            vae = @("1", 0)
            image1 = @("5", 0)
        }
    }
    "11" = @{
        class_type = "FluxKontextMultiReferenceLatentMethod"
        inputs = @{
            conditioning = @("10", 0)
            reference_latents_method = "index_timestep_zero"
        }
    }
    "12" = @{
        class_type = "EmptyLatentImage"
        inputs = @{
            width = $Width
            height = $Height
            batch_size = 1
        }
    }
    "13" = @{
        class_type = "KSampler"
        inputs = @{
            model = @("7", 0)
            seed = $Seed
            steps = 8
            cfg = 1.0
            sampler_name = "euler"
            scheduler = "simple"
            positive = @("9", 0)
            negative = @("11", 0)
            latent_image = @("12", 0)
            denoise = 1.0
        }
    }
    "14" = @{
        class_type = "VAEDecode"
        inputs = @{
            samples = @("13", 0)
            vae = @("1", 0)
        }
    }
    "15" = @{
        class_type = "SaveImage"
        inputs = @{
            images = @("14", 0)
            filename_prefix = "$OutputPrefix-$Seed"
        }
    }
}

$body = @{
    prompt = $workflow
    client_id = "krea2-reid-smoke"
} | ConvertTo-Json -Depth 30

$queued = Invoke-RestMethod -Method Post -Uri "$baseUrl/prompt" -ContentType "application/json" -Body $body
$promptId = [string]$queued.prompt_id
if (-not $promptId) {
    throw "ComfyUI did not return a prompt id: $($queued | ConvertTo-Json -Depth 10 -Compress)"
}

Write-Host "Queued Krea2 ReID seed $Seed on RTX 4070: $promptId"

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
        throw "Krea2 ReID failed: $($messages -join [Environment]::NewLine)"
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

throw "Timed out waiting for Krea2 ReID prompt $promptId."
