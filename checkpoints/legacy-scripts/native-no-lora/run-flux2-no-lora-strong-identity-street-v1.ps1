[CmdletBinding()]
param(
    [UInt64]$SceneSeed = 9472363,
    [UInt64]$IdentitySeed = 9472363,
    [int]$Width = 832,
    [int]$Height = 1248,
    [ValidateRange(1, 100)]
    [int]$IdentitySteps = 30,
    [string]$ReferenceFace = "mitch-inline-author-ref-01-face.jpg",
    [string]$ReferenceAngle = "mitch-inline-author-ref-02-angle.jpg",
    [string]$ReferenceFront = "mitch-inline-author-ref-03-front-outdoor.jpg",
    [string]$Server = "http://127.0.0.1:8188",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$OutputPrefix = "flux2-no-lora-strong-identity-street-v1/final",
    [string]$ScenePrompt = (
        "Images 1 and 2 show Mitch, the same character in every image. Mitch is a lean middle-aged " +
        "white man with short brown hair, blue-gray eyes, an angular oval face, a high forehead, a " +
        "narrow jaw, faint natural stubble, and natural unretouched skin. Create an unplanned vertical " +
        "rear-camera smartphone snapshot of Mitch walking toward the person holding the phone through " +
        "a somewhat busy downtown street corner. Frame him from mid-thigh upward with his face large " +
        "enough to recognize. He wears a navy overshirt over a heather-gray T-shirt and dark jeans. " +
        "Use the ordinary 1x main phone camera at about 26mm equivalent, eye-level handheld perspective, " +
        "automatic exposure and white balance, restrained computational HDR, deep natural phone-camera " +
        "focus, subtle edge sharpening, slight corner softness and lens distortion, faint sensor noise " +
        "in shadows, gently compressed highlights, and a trace of realistic motion blur on a few moving " +
        "pedestrians and hands. Show unrelated pedestrians waiting and crossing, storefronts, traffic " +
        "lights, cars, crosswalk paint, concrete, signs, and resolved street depth. Every background " +
        "person has a distinct face and does not resemble Mitch. It must look like a casual phone photo, " +
        "not a cinematic frame or professional portrait: no studio lighting, no beauty retouching, no " +
        "shallow depth of field, no creamy bokeh, no perfect global sharpness, no dramatic color grade."
    ),
    [string]$IdentityPrompt = (
        "Image 1 is the source street photograph and defines the full composition, camera position, " +
        "subject pose and clothing, pedestrian layout, cars, buildings, traffic lights, signs, " +
        "crosswalk, pavement, lighting, and deep street detail. Images 2, 3, and 4 are genuine " +
        "photographs of Mitch and define the exact identity of the main man in image 1. Recreate image " +
        "1 as a realistic high-resolution smartphone photograph, changing only the main man's face " +
        "and identity so he is unmistakably Mitch from images 2, 3, and 4. Preserve Mitch's apparent " +
        "age, facial geometry, eyes, forehead, nose, jaw, mouth, hairstyle, natural stubble, and " +
        "unretouched skin. Preserve the source street background, crowd diversity, fine building " +
        "texture, traffic, deep focus, full-frame lighting, subject clothing, body, pose, and " +
        "placement. Every pedestrian remains a distinct unrelated person and does not resemble Mitch. " +
        "Do not beautify, add a goatee, smooth skin, create portrait blur, crop, mask, or composite."
    )
)

$ErrorActionPreference = "Stop"

foreach ($port in 8188, 8189) {
    $worker = "http://127.0.0.1:$port"
    try {
        $queue = Invoke-RestMethod -Uri "$worker/queue" -TimeoutSec 5
        if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
            throw "ComfyUI queue is not idle at $worker. Refusing to disturb active GPU work."
        }
    }
    catch {
        if ($worker -eq $Server) { throw }
        Write-Warning "Could not inspect optional worker $worker`: $($_.Exception.Message)"
    }
}

$requiredNodes = @(
    "UNETLoader", "CLIPLoader", "VAELoader", "LoadImage", "ImageScaleToTotalPixels",
    "VAEEncode", "ReferenceLatent", "CLIPTextEncode", "EmptyFlux2LatentImage", "KSampler",
    "CFGGuider", "KSamplerSelect", "Flux2Scheduler", "RandomNoise", "SamplerCustomAdvanced",
    "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $info = Invoke-RestMethod -Uri "$Server/object_info/$nodeName" -TimeoutSec 10
    if (-not $info.PSObject.Properties[$nodeName]) { throw "Required node unavailable: $nodeName" }
}

$models = @{
    Scene = "flux-2-klein-9b-fp8.safetensors"
    SceneClip = "qwen_3_8b_fp8mixed.safetensors"
    Identity = "flux-2-klein-base-4b-fp8.safetensors"
    IdentityClip = "qwen_3_4b_fp8_mixed.safetensors"
    Vae = "flux2-vae.safetensors"
}
$allInfo = Invoke-RestMethod -Uri "$Server/object_info" -TimeoutSec 30
foreach ($model in @($models.Scene, $models.Identity)) {
    if (@($allInfo.UNETLoader.input.required.unet_name[0]) -notcontains $model) {
        throw "Diffusion model is not visible to the live worker: $model"
    }
}
foreach ($clip in @($models.SceneClip, $models.IdentityClip)) {
    if (@($allInfo.CLIPLoader.input.required.clip_name[0]) -notcontains $clip) {
        throw "Text encoder is not visible to the live worker: $clip"
    }
}
if (@($allInfo.VAELoader.input.required.vae_name[0]) -notcontains $models.Vae) {
    throw "VAE is not visible to the live worker: $($models.Vae)"
}

$inputRoot = Join-Path $ComfyRoot "input"
foreach ($reference in @($ReferenceFace, $ReferenceAngle, $ReferenceFront)) {
    if (-not (Test-Path -LiteralPath (Join-Path $inputRoot $reference) -PathType Leaf)) {
        throw "Reference is missing from ComfyUI input: $reference"
    }
}

$prompt = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $models.Scene; weight_dtype = "default" } }
    "2" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $models.SceneClip; type = "flux2"; device = "default" } }
    "3" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $models.Vae } }
    "4" = @{ class_type = "LoadImage"; inputs = @{ image = $ReferenceFace } }
    "5" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("4", 0); upscale_method = "lanczos"; megapixels = 1.0; resolution_steps = 1 } }
    "6" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("5", 0); vae = @("3", 0) } }
    "7" = @{ class_type = "LoadImage"; inputs = @{ image = $ReferenceAngle } }
    "8" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("7", 0); upscale_method = "lanczos"; megapixels = 1.0; resolution_steps = 1 } }
    "9" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("8", 0); vae = @("3", 0) } }
    "10" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $ScenePrompt; clip = @("2", 0) } }
    "11" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("10", 0); latent = @("6", 0) } }
    "12" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("11", 0); latent = @("9", 0) } }
    "13" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
    "14" = @{ class_type = "KSampler"; inputs = @{
        model = @("1", 0); seed = $SceneSeed; steps = 4; cfg = 1.0; sampler_name = "euler"
        scheduler = "simple"; positive = @("12", 0); negative = @("12", 0)
        latent_image = @("13", 0); denoise = 1.0
    } }
    "15" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("14", 0); vae = @("3", 0) } }
    "16" = @{ class_type = "SaveImage"; inputs = @{ images = @("15", 0); filename_prefix = "flux2-no-lora-strong-identity-street-v1/stage1-9b" } }
    "17" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $models.Identity; weight_dtype = "default" } }
    "18" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $models.IdentityClip; type = "flux2"; device = "default" } }
    "19" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("15", 0); upscale_method = "lanczos"; megapixels = 0.5; resolution_steps = 1 } }
    "20" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("19", 0); vae = @("3", 0) } }
    "21" = @{ class_type = "LoadImage"; inputs = @{ image = $ReferenceFront } }
    "22" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("21", 0); upscale_method = "lanczos"; megapixels = 1.0; resolution_steps = 1 } }
    "23" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("22", 0); vae = @("3", 0) } }
    "24" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $IdentityPrompt; clip = @("18", 0) } }
    "25" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("18", 0) } }
    "26" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("24", 0); latent = @("20", 0) } }
    "27" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("26", 0); latent = @("6", 0) } }
    "28" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("27", 0); latent = @("9", 0) } }
    "29" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("28", 0); latent = @("23", 0) } }
    "30" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("25", 0); latent = @("20", 0) } }
    "31" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("30", 0); latent = @("6", 0) } }
    "32" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("31", 0); latent = @("9", 0) } }
    "33" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("32", 0); latent = @("23", 0) } }
    "34" = @{ class_type = "CFGGuider"; inputs = @{ model = @("17", 0); positive = @("29", 0); negative = @("33", 0); cfg = 4.0 } }
    "35" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    "36" = @{ class_type = "Flux2Scheduler"; inputs = @{ steps = $IdentitySteps; width = $Width; height = $Height } }
    "37" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $IdentitySeed } }
    "38" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
    "39" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("37", 0); guider = @("34", 0); sampler = @("35", 0); sigmas = @("36", 0); latent_image = @("38", 0) } }
    "40" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("39", 0); vae = @("3", 0) } }
    "41" = @{ class_type = "SaveImage"; inputs = @{ images = @("40", 0); filename_prefix = $OutputPrefix } }
}

$clientId = [guid]::NewGuid().ToString()
$body = @{ prompt = $prompt; client_id = $clientId } | ConvertTo-Json -Depth 100
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id." }
Write-Host "Queued production prompt $($queued.prompt_id) on $Server"

$deadline = (Get-Date).AddMinutes(75)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry) {
        if ($entry.status.status_str -eq "error") {
            throw "Generation failed: $($entry.status.messages | ConvertTo-Json -Depth 20)"
        }
        if ($entry.status.completed) {
            $stage1 = @($entry.outputs.'16'.images)
            $final = @($entry.outputs.'41'.images)
            if ($stage1.Count -eq 0 -or $final.Count -eq 0) { throw "A production stage saved no image." }
            $resolve = {
                param($image)
                $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                Join-Path (Join-Path $ComfyRoot "output") $relative
            }
            Write-Output ([pscustomobject]@{
                workflow_id = "flux2-no-lora-strong-identity-street-v1"
                prompt_id = $queued.prompt_id; worker = $Server; gpu = "RTX 3090"
                stage_1 = @{ model = $models.Scene; steps = 4; cfg = 1.0; references = @($ReferenceFace, $ReferenceAngle); file = (& $resolve $stage1[0]) }
                stage_2 = @{ model = $models.Identity; steps = $IdentitySteps; cfg = 4.0; references = @("stage_1", $ReferenceFace, $ReferenceAngle, $ReferenceFront); file = (& $resolve $final[0]) }
                width = $Width; height = $Height; scene_seed = $SceneSeed; identity_seed = $IdentitySeed
                character_lora = $null; identity_adapter = $null; output_mask = $null
                face_swap = $null; post_processing = $null
                seconds = [Math]::Round(((Get-Date) - $started).TotalSeconds, 3)
            } | ConvertTo-Json -Depth 10 -Compress)
            exit 0
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for prompt $($queued.prompt_id)."
