[CmdletBinding()]
param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [string]$ExpectedGpuName = "NVIDIA GeForce RTX 3090",
    [string]$Prompt = @"
An ordinary candid vertical 1x rear smartphone photograph at a genuinely busy Midwestern state fair in clear late-afternoon open daylight. The camera is held by a friend at chest height with believable imperfect framing. Leave a natural foreground walking lane where one adult man could later walk toward the camera, without creating a centered hero, an isolated cutout-shaped gap, or an empty-looking scene. Numerous unrelated fairgoers overlap naturally at varied depths, move in both directions, and perform different actions. They are independent people with visibly different ages, builds, hair, posture, and clothing. Clothing colors are naturally varied across muted red, green, denim blue, tan, yellow, gray, patterns, black, and white; no coordinated wardrobe or dominant shirt color. Include coherent food stalls, ride structures, a Ferris wheel in the middle distance, umbrellas, pavement, railings, and ordinary fair clutter. Preserve natural deep phone-camera focus with resolved foreground and middle-distance people and structures, gentle far-distance falloff, restrained phone HDR, subtle sensor texture, and slight motion only on moving people. No flash, portrait-mode blur, beauty filter, cinematic grading, staged group pose, duplicated people, legible text, logo, or watermark. Make it look like one unedited phone photograph captured in a single moment.
"@,
    [int]$Width = 896,
    [int]$Height = 1344,
    [long[]]$Seeds = @(8675401, 8675402, 8675403, 8675404),
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
if ($Seeds.Count -lt 1) {
    throw "Pass at least one seed."
}

$stats = Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 10
$deviceName = [string](@($stats.devices)[0].name)
if ($deviceName -notlike "*$ExpectedGpuName*") {
    throw "Worker is serving '$deviceName', not the expected $ExpectedGpuName."
}

$queue = Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 10
if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
    throw "The selected ComfyUI worker already has queued work. No plates were submitted."
}

$objectInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info" -TimeoutSec 45
$requiredNodes = @(
    "UNETLoader",
    "FluxKVCache",
    "CLIPLoader",
    "VAELoader",
    "CLIPTextEncode",
    "EmptyFlux2LatentImage",
    "RandomNoise",
    "BasicGuider",
    "KSamplerSelect",
    "Flux2Scheduler",
    "SamplerCustomAdvanced",
    "VAEDecode",
    "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    if (-not $objectInfo.PSObject.Properties[$nodeName]) {
        throw "The selected worker does not expose required node '$nodeName'."
    }
}

$unetNames = @($objectInfo.UNETLoader.input.required.unet_name[0])
$clipNames = @($objectInfo.CLIPLoader.input.required.clip_name[0])
$vaeNames = @($objectInfo.VAELoader.input.required.vae_name[0])
foreach ($requirement in @(
    @($unetNames, "flux-2-klein-9b-kv-fp8.safetensors", "diffusion model"),
    @($clipNames, "qwen_3_8b_fp8mixed.safetensors", "text encoder"),
    @($vaeNames, "flux2-vae.safetensors", "VAE")
)) {
    if ($requirement[0] -notcontains $requirement[1]) {
        throw "Missing $($requirement[2]): $($requirement[1])"
    }
}

$workflow = @{
    "1" = @{
        class_type = "UNETLoader"
        inputs = @{
            unet_name = "flux-2-klein-9b-kv-fp8.safetensors"
            weight_dtype = "default"
        }
    }
    "2" = @{
        class_type = "FluxKVCache"
        inputs = @{ model = @("1", 0) }
    }
    "3" = @{
        class_type = "CLIPLoader"
        inputs = @{
            clip_name = "qwen_3_8b_fp8mixed.safetensors"
            type = "flux2"
            device = "default"
        }
    }
    "4" = @{
        class_type = "VAELoader"
        inputs = @{ vae_name = "flux2-vae.safetensors" }
    }
    "5" = @{
        class_type = "CLIPTextEncode"
        inputs = @{
            text = $Prompt.Trim()
            clip = @("3", 0)
        }
    }
    "6" = @{
        class_type = "BasicGuider"
        inputs = @{
            model = @("2", 0)
            conditioning = @("5", 0)
        }
    }
    "7" = @{
        class_type = "KSamplerSelect"
        inputs = @{ sampler_name = "euler" }
    }
    "8" = @{
        class_type = "Flux2Scheduler"
        inputs = @{
            steps = 4
            width = $Width
            height = $Height
        }
    }
}

for ($index = 0; $index -lt $Seeds.Count; $index++) {
    $seed = [long]$Seeds[$index]
    $base = 20 + ($index * 10)
    $noiseId = [string]$base
    $latentId = [string]($base + 1)
    $sampleId = [string]($base + 2)
    $decodeId = [string]($base + 3)
    $saveId = [string]($base + 4)

    $workflow[$noiseId] = @{
        class_type = "RandomNoise"
        inputs = @{ noise_seed = $seed }
    }
    $workflow[$latentId] = @{
        class_type = "EmptyFlux2LatentImage"
        inputs = @{
            width = $Width
            height = $Height
            batch_size = 1
        }
    }
    $workflow[$sampleId] = @{
        class_type = "SamplerCustomAdvanced"
        inputs = @{
            noise = @($noiseId, 0)
            guider = @("6", 0)
            sampler = @("7", 0)
            sigmas = @("8", 0)
            latent_image = @($latentId, 0)
        }
    }
    $workflow[$decodeId] = @{
        class_type = "VAEDecode"
        inputs = @{
            samples = @($sampleId, 0)
            vae = @("4", 0)
        }
    }
    $workflow[$saveId] = @{
        class_type = "SaveImage"
        inputs = @{
            images = @($decodeId, 0)
            filename_prefix = "scene-first/state-fair/plate-seed-$seed"
        }
    }
}

$body = @{
    prompt = $workflow
    client_id = "klein9b-scene-plates"
} | ConvertTo-Json -Depth 24

$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$ComfyUrl/prompt" -ContentType "application/json" -Body $body
$promptId = [string]$queued.prompt_id
if (-not $promptId) {
    throw "ComfyUI did not return a prompt id: $($queued | ConvertTo-Json -Depth 12 -Compress)"
}
Write-Host "Queued $($Seeds.Count) Klein 9B scene plates on $ExpectedGpuName`: $promptId"

$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
while ([DateTime]::UtcNow -lt $deadline) {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$promptId" -TimeoutSec 20
    $record = $history.PSObject.Properties[$promptId].Value
    if (-not $record) {
        continue
    }
    if ($record.status.status_str -eq "error") {
        $messages = @($record.status.messages | ForEach-Object { $_ | ConvertTo-Json -Depth 20 -Compress })
        throw "Klein 9B scene plates failed: $($messages -join [Environment]::NewLine)"
    }
    if ($record.status.completed -or $record.status.status_str -eq "success") {
        $saved = @()
        foreach ($output in $record.outputs.PSObject.Properties.Value) {
            foreach ($image in @($output.images)) {
                if (-not $image.filename) {
                    continue
                }
                $relative = if ($image.subfolder) {
                    Join-Path $image.subfolder $image.filename
                }
                else {
                    $image.filename
                }
                $saved += $relative
                Write-Host "Saved: C:\projects\AI-Tools\ComfyUI\output\$relative"
            }
        }
        [pscustomobject]@{
            prompt_id = $promptId
            gpu = $ExpectedGpuName
            elapsed_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
            prompt = $Prompt.Trim()
            seeds = $Seeds
            images = $saved
        } | ConvertTo-Json -Depth 8
        exit 0
    }
}

throw "Timed out waiting for Klein 9B scene plates prompt $promptId."
