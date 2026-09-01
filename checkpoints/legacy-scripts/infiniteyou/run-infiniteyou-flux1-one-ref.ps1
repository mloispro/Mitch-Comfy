[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8190",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ReferenceImage = "mitch-inline-author-ref-01-face.jpg",
    [string]$ModelVariant = "aes_stage2",
    [UInt64]$Seed = 8675367,
    [int]$Width = 864,
    [int]$Height = 1152,
    [int]$Steps = 30,
    [double]$Guidance = 3.5,
    [double]$InfuseStrength = 1.0,
    [double]$InfuseStart = 0.0,
    [double]$InfuseEnd = 1.0,
    [string]$OutputPrefix = "",
    [string]$ScenePrompt = (
        "An unposed waist-up rear-camera smartphone photograph of a man standing naturally on a busy " +
        "downtown sidewalk in late afternoon. He wears a plain charcoal crew-neck T-shirt and dark jeans " +
        "and looks toward the camera with a relaxed neutral expression. Frame him slightly off center beside " +
        "a brick storefront. Clearly resolve unrelated pedestrians at different distances, parked cars, shop " +
        "windows, street signs, sidewalk texture, and ordinary ambient daylight. Natural small-sensor camera " +
        "perspective, realistic skin texture, slight handheld imperfection, and one coherent photograph with " +
        "the person and background captured together. No portrait blur, beauty filter, flash, face cutout, " +
        "selective subject sharpening, watermark, or text."
    )
)

$ErrorActionPreference = "Stop"

if ($ModelVariant -notin @("aes_stage2", "sim_stage1")) {
    throw "ModelVariant must be aes_stage2 or sim_stage1."
}
if (-not $OutputPrefix) {
    $variantLabel = $ModelVariant.Replace("_", "-")
    $OutputPrefix = "InfiniteYou/$variantLabel-one-ref"
}
if ($Width % 8 -ne 0 -or $Height % 8 -ne 0) {
    throw "Width and height must be divisible by 8."
}

foreach ($port in 8188, 8189) {
    $worker = "http://127.0.0.1:$port"
    try {
        $workerQueue = Invoke-RestMethod -Uri "$worker/queue" -TimeoutSec 5
        if (@($workerQueue.queue_running).Count -gt 0 -or @($workerQueue.queue_pending).Count -gt 0) {
            throw "ComfyUI queue is not idle at $worker. Refusing to disturb active GPU work."
        }
    }
    catch {
        if ($worker -eq $Server) {
            throw
        }
        Write-Warning "Could not inspect optional worker $worker`: $($_.Exception.Message)"
    }
}

$requiredNodes = @(
    "CheckpointLoaderSimple", "LoadImage", "IDEmbeddingModelLoader", "ExtractIDEmbedding",
    "CLIPTextEncodeFlux", "CLIPTextEncode", "InfuseNetLoader", "InfuseNetApply",
    "EmptyImage", "EmptyLatentImage", "KSampler", "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$nodeName" -TimeoutSec 15
    if (-not $nodeInfo.PSObject.Properties[$nodeName]) {
        throw "Required node is unavailable: $nodeName"
    }
}

$checkpointName = "flux1-dev-fp8.safetensors"
$projectionName = "$ModelVariant\image_proj_model.bin"
$infuseName = switch ($ModelVariant) {
    "aes_stage2" { "$ModelVariant\infusenet_aes_fp8e4m3fn.safetensors" }
    "sim_stage1" { "$ModelVariant\infusenet_sim_fp8e4m3fn.safetensors" }
}

$files = @(
    [pscustomobject]@{
        Label = "FLUX.1 Dev FP8 checkpoint"
        Path = Join-Path $ComfyRoot "models\checkpoints\$checkpointName"
        Bytes = [int64]17246524772
        Sha256 = "8E91B68084B53A7FC44ED2A3756D821E355AC1A7B6FE29BE760C1DB532F3D88A"
    },
    [pscustomobject]@{
        Label = "InfiniteYou image projector"
        Path = Join-Path $ComfyRoot "models\infinite_you\$projectionName"
        Bytes = [int64]338413026
        Sha256 = if ($ModelVariant -eq "aes_stage2") {
            "F85518431D7367DE30B9558A939C003462A7E331E8C8B929146916DC27E471D6"
        }
        else {
            "B7A8A1B6FECF2731B2AC64BDE33A1885014949C8C08F3EFAEBD0665BB0E8AD8F"
        }
    },
    [pscustomobject]@{
        Label = "InfiniteYou InfuseNet"
        Path = Join-Path $ComfyRoot "models\infinite_you\$infuseName"
        Bytes = [int64]2952691776
        Sha256 = if ($ModelVariant -eq "aes_stage2") {
            "7F6526AE545731182F95E5FF2F1DEDDDFE4ADB3895BA727F332029E7DF8395A7"
        }
        else {
            "DE810F98F99FF103EA2529A141CDBE62C856177851D1660B33C3ADE7FF0DBA56"
        }
    },
    [pscustomobject]@{
        Label = "FaceXlib ArcFace IR-SE50"
        Path = Join-Path $ComfyRoot ".venv\Lib\site-packages\facexlib\weights\recognition_arcface_ir_se50.pth"
        Bytes = [int64]175367323
        Sha256 = "A035C768259B98AB1CE0E646312F48B9E1E218197A0F80AC6765E88F8B6DDF28"
    }
)

foreach ($file in $files) {
    if (-not (Test-Path -LiteralPath $file.Path -PathType Leaf)) {
        throw "$($file.Label) is missing: $($file.Path)"
    }
    $item = Get-Item -LiteralPath $file.Path
    if ($file.Bytes -gt 0 -and $item.Length -ne $file.Bytes) {
        throw "$($file.Label) has unexpected size: $($item.Length) bytes"
    }
    if ($file.Sha256) {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.Path).Hash
        if ($hash -ne $file.Sha256) {
            throw "$($file.Label) SHA-256 mismatch: $hash"
        }
    }
}

$inputPath = Join-Path (Join-Path $ComfyRoot "input") $ReferenceImage
if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
    throw "Genuine identity reference is missing: $inputPath"
}

$allInfo = Invoke-RestMethod -Uri "$Server/object_info" -TimeoutSec 45
if (@($allInfo.CheckpointLoaderSimple.input.required.ckpt_name[0]) -notcontains $checkpointName) {
    throw "$checkpointName is not visible to the live ComfyUI worker."
}
if (@($allInfo.IDEmbeddingModelLoader.input.required.image_proj_model_name[0]) -notcontains $projectionName) {
    throw "$projectionName is not visible to the live InfiniteYou node."
}
if (@($allInfo.InfuseNetLoader.input.required.controlnet_name[0]) -notcontains $infuseName) {
    throw "$infuseName is not visible to the live InfiniteYou node."
}

$prompt = [ordered]@{
    "1" = @{ class_type = "CheckpointLoaderSimple"; inputs = @{ ckpt_name = $checkpointName } }
    "2" = @{ class_type = "LoadImage"; inputs = @{ image = $ReferenceImage } }
    "3" = @{ class_type = "IDEmbeddingModelLoader"; inputs = @{
        image_proj_model_name = $projectionName
        image_proj_num_tokens = 8
        face_analysis_provider = "CPU"
        face_analysis_det_size = "AUTO"
    } }
    "4" = @{ class_type = "ExtractIDEmbedding"; inputs = @{
        face_detector = @("3", 0)
        arcface_model = @("3", 1)
        image_proj_model = @("3", 2)
        image = @("2", 0)
    } }
    "5" = @{ class_type = "CLIPTextEncodeFlux"; inputs = @{
        clip = @("1", 1)
        clip_l = $ScenePrompt
        t5xxl = $ScenePrompt
        guidance = $Guidance
    } }
    "6" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("1", 1) } }
    "7" = @{ class_type = "InfuseNetLoader"; inputs = @{ controlnet_name = $infuseName } }
    "8" = @{ class_type = "EmptyImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1; color = 0 } }
    "9" = @{ class_type = "InfuseNetApply"; inputs = @{
        positive = @("5", 0)
        id_embedding = @("4", 0)
        control_net = @("7", 0)
        image = @("8", 0)
        strength = $InfuseStrength
        start_percent = $InfuseStart
        end_percent = $InfuseEnd
        negative = @("6", 0)
        vae = @("1", 2)
    } }
    "10" = @{ class_type = "EmptyLatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
    "11" = @{ class_type = "KSampler"; inputs = @{
        model = @("1", 0)
        seed = $Seed
        steps = $Steps
        cfg = 1.0
        sampler_name = "euler"
        scheduler = "beta"
        positive = @("9", 0)
        negative = @("9", 1)
        latent_image = @("10", 0)
        denoise = 1.0
    } }
    "12" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("11", 0); vae = @("1", 2) } }
    "13" = @{ class_type = "SaveImage"; inputs = @{
        images = @("12", 0)
        filename_prefix = "$OutputPrefix-seed$Seed"
    } }
}

$clientId = [guid]::NewGuid().ToString()
$body = @{ prompt = $prompt; client_id = $clientId } | ConvertTo-Json -Depth 100
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt id: $($queued | ConvertTo-Json -Depth 10)"
}

Write-Host "Queued InfiniteYou prompt $($queued.prompt_id) on $Server"
$deadline = (Get-Date).AddMinutes(45)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 15
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry) {
        if ($entry.status.status_str -eq "error") {
            throw "Generation failed: $($entry.status.messages | ConvertTo-Json -Depth 30)"
        }
        if ($entry.status.completed) {
            $saved = @($entry.outputs.'13'.images)
            if ($saved.Count -eq 0) {
                throw "Generation completed without a saved image."
            }
            foreach ($image in $saved) {
                $relativePath = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                $absolutePath = Join-Path (Join-Path $ComfyRoot "output") $relativePath
                Write-Output ([pscustomobject]@{
                    prompt_id = $queued.prompt_id
                    base_model = $checkpointName
                    base_model_sha256 = $files[0].Sha256
                    identity_adapter = "InfiniteYou-FLUX v1.0 $ModelVariant"
                    projection = $projectionName
                    projection_sha256 = $files[1].Sha256
                    infusenet = $infuseName
                    infusenet_sha256 = $files[2].Sha256
                    identity_mechanism = "FaceXlib ArcFace IR-SE50 embedding -> 8x4096 projection tokens -> InfuseNet residual injection into FLUX.1 Dev"
                    identity_reference = $ReferenceImage
                    identity_reference_role = "single genuine identity photo; largest detected face only"
                    pose_control = $null
                    prompt = $ScenePrompt
                    width = $Width
                    height = $Height
                    steps = $Steps
                    guidance = $Guidance
                    cfg = 1.0
                    infusenet_strength = $InfuseStrength
                    infusenet_start = $InfuseStart
                    infusenet_end = $InfuseEnd
                    identity_tokens = 8
                    sampler = "euler"
                    scheduler = "beta"
                    seed = $Seed
                    optional_lora = $null
                    face_swap = $null
                    post_processing = $null
                    seconds = [Math]::Round(((Get-Date) - $started).TotalSeconds, 3)
                    file = $absolutePath
                } | ConvertTo-Json -Depth 10 -Compress)
            }
            exit 0
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for InfiniteYou prompt $($queued.prompt_id)."
