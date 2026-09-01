[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8188",
    [UInt64]$Seed = 9472401,
    [int]$Steps = 20,
    [double]$Cfg = 5.0,
    [double]$LoraStrength = 0.60,
    [double]$ReferenceMegapixels = 1.0,
    [double]$IdentityReferenceMegapixels = 1.0,
    [string]$SceneImage = "flux2-official-minneapolis-source.png",
    [string]$IdentityImage = "mitch-flux2-id-right-three-quarter.jpg",
    [string]$IdentityFaceImage = "",
    [string]$OutputPrefix = "flux2-official-edit/minneapolis-identity",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ScenePrompt = (
        "Picture 1 is the exact existing candid Minneapolis street photograph and supplies the camera position, " +
        "vertical framing, North Loop brick buildings, sidewalk, bicycles, cars, background pedestrians, daylight, " +
        "shadows, navy T-shirt, dark jeans, body pose, hand positions, head angle, subject scale, and background layout. " +
        "Picture 2 is a genuine photograph of the exact man, m1tch_person, whose identity must replace only the identity " +
        "of the foreground man in Picture 1. Recreate a single coherent unedited iPhone 8 rear-camera photograph. " +
        "The foreground man must have the age, hairline, short medium-brown hair, facial proportions, eyes, nose, mouth, " +
        "jaw, skin texture, and lean build of Picture 2 while keeping the pose, head angle, expression intensity, location, " +
        "clothing, and scale from Picture 1. Use a relaxed neutral closed-mouth expression with naturally open eyes. " +
        "The man and street must share one exposure, white balance, focus behavior, sensor noise, edge softness, depth of " +
        "field, and shadow direction. Preserve the complete street and all background people. This must look like one " +
        "ordinary phone capture, not a portrait composite. No squint, grin, caricature, face distortion, enlarged head, " +
        "pasted head, halo, selective face sharpness, beauty filter, artificial portrait blur, text, or watermark."
    )
)

$ErrorActionPreference = "Stop"

$targetPort = ([uri]$Server).Port
foreach ($port in 8188, 8189, 8190) {
    $worker = "http://127.0.0.1:$port"
    try {
        $workerQueue = Invoke-RestMethod -Uri "$worker/queue" -TimeoutSec 5
        if (@($workerQueue.queue_running).Count -gt 0 -or @($workerQueue.queue_pending).Count -gt 0) {
            throw "ComfyUI queue is not idle at $worker. Refusing to disturb active GPU work."
        }
    }
    catch {
        if ($port -eq $targetPort) { throw }
        Write-Warning "Could not inspect optional worker $worker`: $($_.Exception.Message)"
    }
}

if ($targetPort -eq 8188 -or $targetPort -eq 8190) {
    try {
        $neo = Invoke-RestMethod -Uri "http://127.0.0.1:7860/sdapi/v1/progress?skip_current_image=true" -TimeoutSec 5
        if ([double]$neo.progress -gt 0 -or [string]$neo.state.job) {
            throw "Neo is actively using the RTX 3090. Refusing to queue another GPU job."
        }
    }
    catch {
        if ($_.Exception.Message -match "actively using") { throw }
        Write-Warning "Could not verify Neo progress: $($_.Exception.Message)"
    }
}

$requiredNodes = @(
    "UNETLoader", "LoraLoaderModelOnly", "CLIPLoader", "VAELoader", "LoadImage",
    "ImageScaleToTotalPixels", "GetImageSize", "VAEEncode", "ReferenceLatent",
    "CLIPTextEncode", "CFGGuider", "KSamplerSelect", "Flux2Scheduler", "RandomNoise",
    "EmptyFlux2LatentImage", "SamplerCustomAdvanced", "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$nodeName" -TimeoutSec 15
    if (-not $nodeInfo.PSObject.Properties[$nodeName]) {
        throw "Required node is unavailable: $nodeName"
    }
}

$modelName = "flux-2-klein-base-4b-fp8.safetensors"
$clipName = "qwen_3_4b.safetensors"
$vaeName = "full_encoder_small_decoder.safetensors"
$loraName = "aitk\m1tch-flux2-klein-4b-identity-v1-best.safetensors"
$expected = @{
    (Join-Path $ComfyRoot "models\diffusion_models\$modelName") = @(4089498488, "44BAB3A86FE98B85D21DD2A4729EBDC3AE51FB8A39F76E457E18C724219E6840")
    (Join-Path $ComfyRoot "models\text_encoders\$clipName") = @(8044982048, "6C671498573AC2F7A5501502CCCE8D2B08EA6CA2F661C458E708F36B36EDFC5A")
    (Join-Path $ComfyRoot "models\vae\$vaeName") = @(249519092, "EA4273F02D1FAFBF8E1D1C2CF6018ED8748652EB0BF34F2DD91171F16F15AB62")
    (Join-Path $ComfyRoot "models\loras\$loraName") = @(46223904, $null)
}
foreach ($path in $expected.Keys) {
    $file = Get-Item -LiteralPath $path
    if ($file.Length -ne [int64]$expected[$path][0]) { throw "Unexpected file size: $path" }
    if ($expected[$path][1] -and (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash -ne $expected[$path][1]) {
        throw "SHA-256 mismatch: $path"
    }
}

$inputRoot = Join-Path $ComfyRoot "input"
$inputNames = @($SceneImage, $IdentityImage)
if ($IdentityFaceImage) { $inputNames += $IdentityFaceImage }
foreach ($inputName in $inputNames) {
    if (-not (Test-Path -LiteralPath (Join-Path $inputRoot $inputName) -PathType Leaf)) {
        throw "Input is missing from ComfyUI: $inputName"
    }
}

$prompt = [ordered]@{
    "1"  = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $modelName; weight_dtype = "default" } }
    "2"  = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $loraName; strength_model = $LoraStrength } }
    "3"  = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $clipName; type = "flux2"; device = "default" } }
    "4"  = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vaeName } }
    "5"  = @{ class_type = "LoadImage"; inputs = @{ image = $SceneImage } }
    "6"  = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("5", 0); upscale_method = "nearest-exact"; megapixels = $ReferenceMegapixels; resolution_steps = 1 } }
    "7"  = @{ class_type = "GetImageSize"; inputs = @{ image = @("6", 0) } }
    "8"  = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("6", 0); vae = @("4", 0) } }
    "9"  = @{ class_type = "LoadImage"; inputs = @{ image = $IdentityImage } }
    "10" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("9", 0); upscale_method = "nearest-exact"; megapixels = $IdentityReferenceMegapixels; resolution_steps = 1 } }
    "11" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("10", 0); vae = @("4", 0) } }
    "12" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $ScenePrompt; clip = @("3", 0) } }
    "13" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("3", 0) } }
    "14" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("12", 0); latent = @("8", 0) } }
    "15" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("14", 0); latent = @("11", 0) } }
    "16" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("13", 0); latent = @("8", 0) } }
    "17" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("16", 0); latent = @("11", 0) } }
    "18" = @{ class_type = "CFGGuider"; inputs = @{ model = @("2", 0); positive = @("15", 0); negative = @("17", 0); cfg = $Cfg } }
    "19" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    "20" = @{ class_type = "Flux2Scheduler"; inputs = @{ steps = $Steps; width = @("7", 0); height = @("7", 1) } }
    "21" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Seed } }
    "22" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = @("7", 0); height = @("7", 1); batch_size = 1 } }
    "23" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("21", 0); guider = @("18", 0); sampler = @("19", 0); sigmas = @("20", 0); latent_image = @("22", 0) } }
    "24" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("23", 0); vae = @("4", 0) } }
    "25" = @{ class_type = "SaveImage"; inputs = @{ images = @("24", 0); filename_prefix = "$OutputPrefix/seed-$Seed" } }
}

if ($IdentityFaceImage) {
    $prompt["12"].inputs.text = (
        $ScenePrompt + " Picture 3 is a closer crop from the same genuine photograph as Picture 2; " +
        "Pictures 2 and 3 are the same man and must not create a second person."
    )
    $prompt["26"] = @{ class_type = "LoadImage"; inputs = @{ image = $IdentityFaceImage } }
    $prompt["27"] = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("26", 0); upscale_method = "nearest-exact"; megapixels = $IdentityReferenceMegapixels; resolution_steps = 1 } }
    $prompt["28"] = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("27", 0); vae = @("4", 0) } }
    $prompt["29"] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("15", 0); latent = @("28", 0) } }
    $prompt["30"] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("17", 0); latent = @("28", 0) } }
    $prompt["18"].inputs.positive = @("29", 0)
    $prompt["18"].inputs.negative = @("30", 0)
}

$clientId = [guid]::NewGuid().ToString()
$body = @{ prompt = $prompt; client_id = $clientId } | ConvertTo-Json -Depth 100
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id." }

Write-Host "Queued official FLUX.2 identity edit $($queued.prompt_id) on $Server"
$deadline = (Get-Date).AddMinutes(60)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 15
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry) {
        if ($entry.status.status_str -eq "error") {
            throw "Generation failed: $($entry.status.messages | ConvertTo-Json -Depth 30)"
        }
        if ($entry.status.completed) {
            $saved = @($entry.outputs."25".images)
            if ($saved.Count -eq 0) { throw "Generation completed without a saved image." }
            $outputRoot = if ($targetPort -eq 8189) { Join-Path $ComfyRoot "output\gpu-4070" } else { Join-Path $ComfyRoot "output" }
            foreach ($image in $saved) {
                $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                $absolute = Join-Path $outputRoot $relative
                Write-Output ([ordered]@{
                    prompt_id = $queued.prompt_id
                    file = $absolute
                    server = $Server
                    gpu_route = if ($targetPort -eq 8189) { "RTX 4070" } else { "RTX 3090" }
                    model = $modelName
                    lora = $loraName
                    lora_strength = $LoraStrength
                    text_encoder = $clipName
                    vae = $vaeName
                    scene_reference = $SceneImage
                    identity_reference = $IdentityImage
                    identity_face_reference = if ($IdentityFaceImage) { $IdentityFaceImage } else { $null }
                    reference_order = if ($IdentityFaceImage) { "Picture 1 scene; Picture 2 identity full view; Picture 3 derived face view" } else { "Picture 1 scene; Picture 2 identity" }
                    identity_mechanism = "FLUX.2 ReferenceLatent on positive and negative conditioning plus compatible identity LoRA"
                    latent_source = "EmptyFlux2LatentImage"
                    prompt = $ScenePrompt
                    source_megapixels = $ReferenceMegapixels
                    identity_reference_megapixels = $IdentityReferenceMegapixels
                    steps = $Steps
                    cfg = $Cfg
                    sampler = "euler"
                    scheduler = "Flux2Scheduler"
                    seed = $Seed
                    seconds = [Math]::Round(((Get-Date) - $started).TotalSeconds, 3)
                    mask = $null
                    img2img_denoise = $null
                    face_swap = $null
                    post_processing = $null
                } | ConvertTo-Json -Depth 20 -Compress)
            }
            exit 0
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for prompt $($queued.prompt_id)."
