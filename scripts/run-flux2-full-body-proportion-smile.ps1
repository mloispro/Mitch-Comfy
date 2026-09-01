[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8188",
    [string]$BodyReference = "mitch-genuine-full-body-proportion-20260822.jpg",
    [string]$FaceReference = "20260815_165446.jpg",
    [UInt64]$Seed = 8675312,
    [double]$LoraStrength = 0.5,
    [int]$Steps = 20,
    [double]$Cfg = 4.0,
    [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = "Stop"

$requiredNodes = @(
    "UNETLoader", "LoraLoaderModelOnly", "CLIPLoader", "VAELoader", "LoadImage",
    "ImageScaleToTotalPixels", "VAEEncode", "ReferenceLatent", "CLIPTextEncode",
    "CFGGuider", "KSamplerSelect", "Flux2Scheduler", "RandomNoise",
    "EmptyFlux2LatentImage", "SamplerCustomAdvanced", "VAEDecode", "SaveImage"
)
$objectInfo = Invoke-RestMethod -Uri "$Server/object_info" -TimeoutSec 15
foreach ($node in $requiredNodes) {
    if (-not $objectInfo.PSObject.Properties.Name.Contains($node)) {
        throw "Required ComfyUI node is unavailable: $node"
    }
}

$scenePrompt = @"
Create one coherent, photorealistic vertical iPhone 8 rear-camera photograph of the exact same adult man shown in Pictures 1 and 2. His trained identity token is m1tch_person. Picture 1 is a genuine full-body mirror photo and establishes only his real head-to-shoulder scale, shoulder width, lean adult build, torso length, arm length, leg length, and overall body proportions. Do not copy its room, mirror, phone, clothing, pose, or expression. Picture 2 is a genuine current portrait and establishes his facial identity, current apparent age, hairline, hairstyle, eyes, nose, mouth, jaw, natural skin, and the intended warm approachable expression. Do not copy its balcony, white shirt, framing, or selfie perspective.

New scene: a candid full-body photograph taken by a friend on Washington Avenue in the Minneapolis North Loop in ordinary late-afternoon daylight. The camera is about 3.5 meters away at chest height using the ordinary 1x rear lens, with no close-lens head enlargement. He walks naturally toward the camera wearing a fitted plain navy crew-neck T-shirt, dark charcoal jeans, and dark casual sneakers. His complete body is visible with ground beneath both shoes. Keep his head naturally small relative to the complete body, about one eighth of visible height; keep the shoulders at least two and a half head widths; center the head directly over a normal vertical neck and shoulder line. Preserve his real lean build without narrowing the shoulders or torso.

He looks toward the photographer with a warm, relaxed, confident expression: brow and jaw relaxed, both eyes naturally open and softly engaged, and a small symmetrical closed-mouth smile with the lips resting together. No visible teeth, crooked smirk, grimace, squint, blank stare, exaggerated grin, model pose, or beauty treatment.

Show exactly two unrelated secondary pedestrians, laterally separated in the middle distance and not overlapping him: an older woman in a mustard jacket walking away at far left and a younger Black man in a rust overshirt crossing near the curb at right. Show exactly two parked cars, one small dark-red hatchback and one light-silver sedan, separated by bare asphalt. Include coherent red-brick warehouse storefronts, sidewalk joints, a bicycle near the curb, and a detailed street receding into the distance.

The entire frame is one ordinary unedited phone exposure. Face, ears, neck, arms, shirt, pedestrians, cars, and buildings share the same daylight, white balance, perspective, edge softness, sensor grain, and distance-dependent detail. No portrait mode, fake bokeh, pasted face or head, cutout boundary, halo, selective sharpening, face swap, CGI polish, HDR look, cinematic grade, beauty filter, text, logo, or watermark.
"@

$width = 896
$height = 1344
$prefix = "flux2-full-body-proportion-smile/seed-$Seed/photo"
$prompt = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = "flux-2-klein-base-4b-fp8.safetensors"; weight_dtype = "default" } }
    "2" = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = "aitk\m1tch-flux2-klein-4b-identity-v1-best.safetensors"; strength_model = $LoraStrength } }
    "3" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = "qwen_3_4b_fp8_mixed.safetensors"; type = "flux2"; device = "default" } }
    "4" = @{ class_type = "VAELoader"; inputs = @{ vae_name = "flux2-vae.safetensors" } }
    "5" = @{ class_type = "LoadImage"; inputs = @{ image = $BodyReference } }
    "6" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("5", 0); upscale_method = "lanczos"; megapixels = 0.25; resolution_steps = 1 } }
    "7" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("6", 0); vae = @("4", 0) } }
    "8" = @{ class_type = "LoadImage"; inputs = @{ image = $FaceReference } }
    "9" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("8", 0); upscale_method = "lanczos"; megapixels = 0.25; resolution_steps = 1 } }
    "10" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("9", 0); vae = @("4", 0) } }
    "11" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $scenePrompt; clip = @("3", 0) } }
    "12" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("11", 0); latent = @("7", 0) } }
    "13" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("12", 0); latent = @("10", 0) } }
    "14" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("3", 0) } }
    "15" = @{ class_type = "CFGGuider"; inputs = @{ model = @("2", 0); positive = @("13", 0); negative = @("14", 0); cfg = $Cfg } }
    "16" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    "17" = @{ class_type = "Flux2Scheduler"; inputs = @{ steps = $Steps; width = $width; height = $height } }
    "18" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Seed } }
    "19" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $width; height = $height; batch_size = 1 } }
    "20" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("18", 0); guider = @("15", 0); sampler = @("16", 0); sigmas = @("17", 0); latent_image = @("19", 0) } }
    "21" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("20", 0); vae = @("4", 0) } }
    "22" = @{ class_type = "SaveImage"; inputs = @{ images = @("21", 0); filename_prefix = $prefix } }
}

$body = @{ prompt = $prompt; client_id = "flux2-proportion-smile-$(New-Guid)" } | ConvertTo-Json -Depth 30
$queued = Invoke-RestMethod -Uri "$Server/prompt" -Method Post -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt id."
}
Write-Host "Queued $($queued.prompt_id) on $Server"

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 15
    $entry = $history.($queued.prompt_id)
    if ($entry -and $entry.status.status_str -eq "error") {
        $entry | ConvertTo-Json -Depth 20
        throw "FLUX.2 proportion/expression generation failed."
    }
    if ($entry -and $entry.status.status_str -eq "success") {
        $image = @($entry.outputs."22".images)[0]
        [pscustomobject]@{
            prompt_id = $queued.prompt_id
            filename = $image.filename
            subfolder = $image.subfolder
            output = "C:\projects\AI-Tools\ComfyUI\output\$($image.subfolder)\$($image.filename)"
            body_reference = $BodyReference
            face_reference = $FaceReference
            seed = $Seed
            lora_strength = $LoraStrength
            steps = $Steps
            cfg = $Cfg
        } | ConvertTo-Json -Depth 5
        exit 0
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for $($queued.prompt_id)."
