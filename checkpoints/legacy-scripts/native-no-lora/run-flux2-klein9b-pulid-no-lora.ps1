[CmdletBinding()]
param(
    [double]$PuLIDStrength = 1.3,
    [switch]$IncludeBodyReference,
    [int]$Steps = 4,
    [double]$Cfg = 1.0,
    [UInt64]$Seed = 9472363,
    [int]$Width = 832,
    [int]$Height = 1248,
    [double]$ReferenceMegapixels = 0.40,
    [switch]$AuthorCenterCrop512,
    [string]$Server = "http://127.0.0.1:8188",
    [string]$FaceReference = "flux2-dev-ref-01-face-front.jpg",
    [string]$BodyReference = "flux2-dev-ref-04-full-body.jpg",
    [string]$OutputPrefix = "flux2-klein9b-pulid-no-lora/state-fair",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ScenePrompt = (
        "Image 1 defines Mitch's face and identity. Create an ordinary candid 1x rear-phone photograph " +
        "of Mitch walking naturally through a genuinely busy Midwestern state fair while holding lemonade. " +
        "Frame him from about mid-thigh upward, slightly off center and integrated among unrelated fairgoers. " +
        "He wears a light-blue casual shirt and dark jeans. Preserve his facial geometry, short light-brown " +
        "hair, apparent age, lean build, and natural skin. Clearly resolve nearby people, varied clothing, " +
        "food stalls, umbrellas, signs, pavement texture, and a Ferris wheel in the middle distance with " +
        "consistent small-sensor depth and late-afternoon daylight. One coherent unedited phone photo; no " +
        "portrait blur, beauty filter, flash, selective subject sharpening, duplicated people, or watermark."
    )
)

$ErrorActionPreference = "Stop"

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
    "UNETLoader", "CLIPLoader", "VAELoader", "LoadImage", "ImageScale", "ImageScaleToTotalPixels",
    "VAEEncode", "ReferenceLatent", "CLIPTextEncode", "EmptyFlux2LatentImage", "KSampler",
    "VAEDecode", "SaveImage", "PuLIDInsightFaceLoader", "PuLIDEVACLIPLoader",
    "PuLIDModelLoader", "ApplyPuLIDFlux2"
)
foreach ($nodeName in $requiredNodes) {
    $nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$nodeName" -TimeoutSec 10
    if (-not $nodeInfo.PSObject.Properties[$nodeName]) {
        throw "Required node is unavailable: $nodeName"
    }
}

$modelName = "flux-2-klein-9b-fp8.safetensors"
$clipName = "qwen_3_8b_fp8mixed.safetensors"
$vaeName = "flux2-vae.safetensors"
$pulidName = "pulid_flux2_klein_v2.safetensors"
$modelPath = Join-Path $ComfyRoot "models\diffusion_models\$modelName"
$pulidPath = Join-Path $ComfyRoot "models\pulid\$pulidName"

$expectedModelBytes = 9433061528
$expectedModelSha256 = "865BA09F5B4C3CBD3468A4BD3ACB9FCB2F8740C54317482F0BCD4ED1D3655CEE"
$expectedPulidBytes = 1364389800
$expectedPulidSha256 = "D5D291CB054EB6ECEB25E3B46EFF8F05F7B58F8F19A89EC76BA730A6BA8935BB"

foreach ($item in @(
    @{ Path = $modelPath; Bytes = $expectedModelBytes; Sha256 = $expectedModelSha256 },
    @{ Path = $pulidPath; Bytes = $expectedPulidBytes; Sha256 = $expectedPulidSha256 }
)) {
    $file = Get-Item -LiteralPath $item.Path
    if ($file.Length -ne [int64]$item.Bytes) {
        throw "Unexpected file size for $($item.Path): $($file.Length)"
    }
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $item.Path).Hash
    if ($hash -ne $item.Sha256) {
        throw "SHA-256 mismatch for $($item.Path): $hash"
    }
}

$allInfo = Invoke-RestMethod -Uri "$Server/object_info" -TimeoutSec 30
if (@($allInfo.UNETLoader.input.required.unet_name[0]) -notcontains $modelName) {
    throw "$modelName is not visible to the live ComfyUI worker."
}
if (@($allInfo.CLIPLoader.input.required.clip_name[0]) -notcontains $clipName) {
    throw "$clipName is not visible to the live ComfyUI worker."
}
if (@($allInfo.VAELoader.input.required.vae_name[0]) -notcontains $vaeName) {
    throw "$vaeName is not visible to the live ComfyUI worker."
}
if (@($allInfo.PuLIDModelLoader.input.required.pulid_file[0]) -notcontains $pulidName) {
    throw "$pulidName is not visible to the live ComfyUI worker."
}

$inputRoot = Join-Path $ComfyRoot "input"
$references = @($FaceReference)
if ($IncludeBodyReference) {
    $references += $BodyReference
}
foreach ($reference in $references) {
    $referencePath = Join-Path $inputRoot $reference
    if (-not (Test-Path -LiteralPath $referencePath -PathType Leaf)) {
        throw "Reference is missing from the local ComfyUI input folder: $referencePath"
    }
}

$strengthName = $PuLIDStrength.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
$referenceMpName = $ReferenceMegapixels.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
$modeName = if ($IncludeBodyReference) { "face-plus-body" } else { "author-single-face" }
$preprocessName = if ($AuthorCenterCrop512) { "author-center512" } else { "${referenceMpName}mp" }
$suffix = "$modeName-strength$strengthName-${Steps}step-cfg$Cfg-$preprocessName-seed$Seed"

$faceScaleNode = if ($AuthorCenterCrop512) {
    @{ class_type = "ImageScale"; inputs = @{ image = @("4", 0); upscale_method = "lanczos"; width = 512; height = 512; crop = "center" } }
}
else {
    @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("4", 0); upscale_method = "lanczos"; megapixels = $ReferenceMegapixels; resolution_steps = 1 } }
}

$prompt = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $modelName; weight_dtype = "default" } }
    "2" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $clipName; type = "flux2"; device = "default" } }
    "3" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vaeName } }
    "4" = @{ class_type = "LoadImage"; inputs = @{ image = $FaceReference } }
    "5" = $faceScaleNode
    "6" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("5", 0); vae = @("3", 0) } }
    "7" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $ScenePrompt; clip = @("2", 0) } }
    "8" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("7", 0); latent = @("6", 0) } }
    "9" = @{ class_type = "PuLIDModelLoader"; inputs = @{ pulid_file = $pulidName } }
    "10" = @{ class_type = "PuLIDEVACLIPLoader"; inputs = @{} }
    "11" = @{ class_type = "PuLIDInsightFaceLoader"; inputs = @{ provider = "CPU" } }
    "12" = @{ class_type = "ApplyPuLIDFlux2"; inputs = @{
        model = @("1", 0)
        pulid_model = @("9", 0)
        strength = $PuLIDStrength
        eva_clip = @("10", 0)
        face_analysis = @("11", 0)
        image = @("5", 0)
        face_index = 0
        debug_mode = $false
    } }
    "13" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
}

$conditioningNode = "8"
if ($IncludeBodyReference) {
    $prompt["17"] = @{ class_type = "LoadImage"; inputs = @{ image = $BodyReference } }
    $prompt["18"] = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("17", 0); upscale_method = "lanczos"; megapixels = $ReferenceMegapixels; resolution_steps = 1 } }
    $prompt["19"] = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("18", 0); vae = @("3", 0) } }
    $prompt["20"] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("8", 0); latent = @("19", 0) } }
    $conditioningNode = "20"
}

$prompt["14"] = @{ class_type = "KSampler"; inputs = @{
    model = @("12", 0)
    seed = $Seed
    steps = $Steps
    cfg = $Cfg
    sampler_name = "euler"
    scheduler = "simple"
    positive = @($conditioningNode, 0)
    negative = @($conditioningNode, 0)
    latent_image = @("13", 0)
    denoise = 1.0
} }
$prompt["15"] = @{ class_type = "VAEDecode"; inputs = @{ samples = @("14", 0); vae = @("3", 0) } }
$prompt["16"] = @{ class_type = "SaveImage"; inputs = @{ images = @("15", 0); filename_prefix = "$OutputPrefix-$suffix" } }

$clientId = [guid]::NewGuid().ToString()
$body = @{ prompt = $prompt; client_id = $clientId } | ConvertTo-Json -Depth 100
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt id: $($queued | ConvertTo-Json -Depth 10)"
}

Write-Host "Queued prompt $($queued.prompt_id) on $Server"
$deadline = (Get-Date).AddMinutes(45)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry) {
        if ($entry.status.status_str -eq "error") {
            throw "Generation failed: $($entry.status.messages | ConvertTo-Json -Depth 20)"
        }
        if ($entry.status.completed) {
            $saved = @($entry.outputs.'16'.images)
            if ($saved.Count -eq 0) {
                throw "Generation completed without a saved image."
            }
            foreach ($image in $saved) {
                $relativePath = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                $absolutePath = Join-Path (Join-Path $ComfyRoot "output") $relativePath
                Write-Output ([pscustomobject]@{
                    prompt_id = $queued.prompt_id
                    model = $modelName
                    model_sha256 = $expectedModelSha256
                    text_encoder = $clipName
                    vae = $vaeName
                    identity_adapter = $pulidName
                    identity_adapter_sha256 = $expectedPulidSha256
                    identity_mechanism = "InsightFace + EVA-CLIP identity tokens injected into trained FLUX.2 Klein 9B transformer blocks"
                    references = $references
                    reference_roles = if ($IncludeBodyReference) { @("face_identity_and_native_reference", "body_native_reference") } else { @("face_identity_and_native_reference") }
                    reference_megapixels_each = $ReferenceMegapixels
                    reference_preprocess = if ($AuthorCenterCrop512) { "author example: 512x512 center crop" } else { "scale to total megapixels, preserve aspect ratio" }
                    prompt = $ScenePrompt
                    width = $Width
                    height = $Height
                    steps = $Steps
                    cfg = $Cfg
                    pulid_strength = $PuLIDStrength
                    sampler = "euler"
                    scheduler = "simple"
                    seed = $Seed
                    character_lora = $null
                    output_mask = $null
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

throw "Timed out waiting for prompt $($queued.prompt_id)."
