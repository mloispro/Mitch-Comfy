[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8188",
    [UInt64]$Seed = 8675412,
    [string]$SceneImage = "mitch-klein9b-layout-lounge-center-source.png",
    [string]$IdentityImage = "mitch-klein9b-ref-front-neutral-v2.jpg",
    [string]$ExpressionImage = "",
    [double]$SceneReferenceMegapixels = 0.25,
    [double]$IdentityReferenceMegapixels = 0.50,
    [double]$ExpressionReferenceMegapixels = 0.50,
    [switch]$UseCannyLayout = $true,
    [switch]$SceneImageIsPrecomputedEdgeLayout = $false,
    [double]$PrecomputedHeadScale = 1.00,
    [double]$CannyLowThreshold = 0.20,
    [double]$CannyHighThreshold = 0.60,
    [string]$OutputPrefix = "flux2-klein9b-group-layout-reference/lounge-center-canny-id050-gentle-lips-integrated-scale",
    [string]$ScenePrompt = (
        "Create one photorealistic vertical phone-flash group photograph matching Picture 1. Four adults sit closely " +
        "on the rust-orange booth, with a partial fifth person at the extreme image-right edge. The central seated man " +
        "is m1tch_person from Picture 2, wearing a fitted dark navy suit and crisp white open-collar shirt. Match his real " +
        "balanced head width, moderately broad forehead and upper cheeks, straight jaw sides, rounded chin, facial-feature " +
        "spacing, hairline, apparent age, and natural skin. Give him a calm pleasant expression: his lips rest gently " +
        "together, their corners rise only slightly, his jaw and cheeks remain relaxed, and his eyes engage softly with " +
        "the camera. Match Picture 1's relative head scale: his head is only modestly larger than nearby heads as " +
        "dictated by the shared perspective. Every face shares one camera plane, direct-flash exposure, focus, pore " +
        "detail, sensor texture, color response, and natural edge softness. Both complete forearms extend down and his " +
        "separate hands rest on his thighs. Keep " +
        "every surrounding person distinct and unrelated. Preserve the copper wall, amber perimeter light, booth, low " +
        "table, ordinary smartphone perspective, direct flash, and seamless natural detail."
    )
)

$ErrorActionPreference = "Stop"
$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
$targetPort = ([uri]$Server).Port
$applyCanny = $UseCannyLayout -and -not $SceneImageIsPrecomputedEdgeLayout

foreach ($port in 8188, 8189, 8190) {
    $worker = "http://127.0.0.1:$port"
    try {
        $queue = Invoke-RestMethod -Uri "$worker/queue" -TimeoutSec 5
        if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
            throw "ComfyUI queue is active at $worker."
        }
    }
    catch {
        if ($port -eq $targetPort -or $_.Exception.Message -match "queue is active") { throw }
        Write-Warning "Could not inspect optional worker $worker`: $($_.Exception.Message)"
    }
}

$stats = Invoke-RestMethod -Uri "$Server/system_stats" -TimeoutSec 10
if ([string]@($stats.devices)[0].name -notmatch "RTX 3090") {
    throw "This layout-reference test requires the RTX 3090; $Server reports $(@($stats.devices)[0].name)."
}

$requiredNodes = @(
    "UNETLoader", "LoraLoaderModelOnly", "CLIPLoader", "VAELoader", "LoadImage",
    "ImageScaleToTotalPixels", "VAEEncode", "ReferenceLatent", "CLIPTextEncode", "CFGGuider",
    "KSamplerSelect", "Flux2Scheduler", "RandomNoise", "EmptyFlux2LatentImage",
    "SamplerCustomAdvanced", "VAEDecode", "SaveImage"
)
if ($applyCanny) { $requiredNodes += "Canny" }
foreach ($nodeName in $requiredNodes) {
    $nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$nodeName" -TimeoutSec 15
    if (-not $nodeInfo.PSObject.Properties[$nodeName]) { throw "Required node is unavailable: $nodeName" }
}

$modelName = "flux-2-klein-base-9b-bf16.safetensors"
$clipName = "qwen_3_8b_fp8mixed.safetensors"
$vaeName = "flux2-vae.safetensors"
$loraName = "m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors"
$loraPath = Join-Path $ComfyRoot "models\loras\$loraName"
$expectedLoraHash = "D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC"
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $loraPath).Hash -ne $expectedLoraHash) {
    throw "Protected Klein 9B LoRA hash mismatch."
}

$inputRoot = Join-Path $ComfyRoot "input"
$scenePath = Join-Path $inputRoot $SceneImage
$identityPath = Join-Path $inputRoot $IdentityImage
$expressionPath = if ($ExpressionImage) { Join-Path $inputRoot $ExpressionImage } else { $null }
if (-not (Test-Path -LiteralPath $scenePath -PathType Leaf)) { throw "Missing scene reference: $scenePath" }
if (-not (Test-Path -LiteralPath $identityPath -PathType Leaf)) { throw "Missing identity reference: $identityPath" }
if ($expressionPath -and -not (Test-Path -LiteralPath $expressionPath -PathType Leaf)) { throw "Missing expression reference: $expressionPath" }
$actualSceneHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $scenePath).Hash
$allowedPrecomputedSceneHashes = @(
    "E6641032A28CC3E8CCD769F2280C134FBE0379AF164A40D58B41E6CB77D70746", # original outer head contour
    "DEC72876E7CB1C6E8B68DF7BD7654FDA82D582B0BD2ED7193FD205657DF15704"  # central head contour at 0.92 scale
)
if ($SceneImageIsPrecomputedEdgeLayout) {
    if ($actualSceneHash -notin $allowedPrecomputedSceneHashes) { throw "Precomputed scene-layout guide hash mismatch." }
}
elseif ($actualSceneHash -ne "1B26AC58A4FAD8D03F69DB7A4085C31B6682C71ACBE22D5AEE51F9E53FA0332B") {
    throw "Scene-layout reference hash mismatch."
}
$allowedIdentityHashes = @(
    "28DF2AE0D717A788370CC825F7BB24CF38DB9C7CDA3F66BAEFAB58BE86D8AF33", # front neutral
    "63F149C16C80C82BC77CD222A612C019920895530FD2C3A0765E78FDBA6E53EB", # front small smile
    "D0A16A410BCE58090ACAC1DCDD001EADF23C26CBCB3A204F545CBCE4F84A2683", # genuine neutral face crop
    "31870369467B7A8FC19199D7877F56257FED2B0F28B08AA183006BCD3112DDAB"  # locked training 04 front neutral
)
$actualIdentityHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $identityPath).Hash
if ($actualIdentityHash -notin $allowedIdentityHashes) { throw "Identity reference hash is not in the locked genuine-photo allowlist." }
if ($expressionPath -and (Get-FileHash -Algorithm SHA256 -LiteralPath $expressionPath).Hash -ne "63F149C16C80C82BC77CD222A612C019920895530FD2C3A0765E78FDBA6E53EB") {
    throw "Expression reference hash mismatch."
}

$referenceContract = if ($SceneImageIsPrecomputedEdgeLayout) {
    "Picture 1 is a Canny edge map derived from the source photograph and supplies its camera framing, person " +
    "positions, seated body poses, outer head sizes, arm positions, booth geometry, table placement, and spatial " +
    "layout. The central source person's internal eye, nose, and mouth edges were intentionally removed so Picture 1 " +
    "does not supply his identity. Picture 2 is a genuine photograph of m1tch_person and exclusively supplies the " +
    "central man's identity and internal facial geometry."
}
elseif ($applyCanny) {
    "Picture 1 is a clean edge map derived from the source photograph and supplies its camera framing, person " +
    "positions, seated body poses, arm positions, booth geometry, table placement, and spatial layout. Picture 2 " +
    "is a genuine photograph of m1tch_person and supplies the central man's identity and head geometry."
}
else {
    "Picture 1 is the source photograph and supplies its camera framing, person positions, seated body poses, booth " +
    "geometry, table placement, and spatial layout. Picture 2 is a genuine photograph of m1tch_person and supplies " +
    "the central man's identity and head geometry."
}
$referenceContract += if ($ExpressionImage) {
    " Picture 3 is another genuine front-facing photograph of the same m1tch_person and supplies his exact small " +
    "natural smile and current head geometry. Pictures 2 and 3 describe one central man."
}
else { "" }
$expressionPicture = if ($ExpressionImage) { "Picture 3" } else { "Picture 2" }
$resolvedScenePrompt = $ScenePrompt.Replace("the dedicated expression reference", $expressionPicture)
$effectivePrompt = "$referenceContract $resolvedScenePrompt"

$prompt = [ordered]@{
    "1"  = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $modelName; weight_dtype = "default" } }
    "2"  = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $loraName; strength_model = 0.90 } }
    "3"  = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $clipName; type = "flux2"; device = "default" } }
    "4"  = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vaeName } }
    "5"  = @{ class_type = "LoadImage"; inputs = @{ image = $SceneImage } }
    "6"  = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("5", 0); upscale_method = "nearest-exact"; megapixels = $SceneReferenceMegapixels; resolution_steps = 1 } }
    "7"  = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("6", 0); vae = @("4", 0) } }
    "8"  = @{ class_type = "LoadImage"; inputs = @{ image = $IdentityImage } }
    "9"  = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("8", 0); upscale_method = "nearest-exact"; megapixels = $IdentityReferenceMegapixels; resolution_steps = 1 } }
    "10" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("9", 0); vae = @("4", 0) } }
    "11" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $effectivePrompt; clip = @("3", 0) } }
    "12" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("3", 0) } }
    "13" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("11", 0); latent = @("7", 0) } }
    "14" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("13", 0); latent = @("10", 0) } }
    "15" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("12", 0); latent = @("7", 0) } }
    "16" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("15", 0); latent = @("10", 0) } }
    "17" = @{ class_type = "CFGGuider"; inputs = @{ model = @("2", 0); positive = @("14", 0); negative = @("16", 0); cfg = 4.0 } }
    "18" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    "19" = @{ class_type = "Flux2Scheduler"; inputs = @{ steps = 50; width = 832; height = 1216 } }
    "20" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Seed } }
    "21" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = 832; height = 1216; batch_size = 1 } }
    "22" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("20", 0); guider = @("17", 0); sampler = @("18", 0); sigmas = @("19", 0); latent_image = @("21", 0) } }
    "23" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("22", 0); vae = @("4", 0) } }
    "24" = @{ class_type = "SaveImage"; inputs = @{ images = @("23", 0); filename_prefix = "$OutputPrefix/seed-$Seed" } }
}

if ($applyCanny) {
    $prompt["25"] = @{ class_type = "Canny"; inputs = @{ image = @("5", 0); low_threshold = $CannyLowThreshold; high_threshold = $CannyHighThreshold } }
    $prompt["6"].inputs.image = @("25", 0)
}

if ($ExpressionImage) {
    $prompt["26"] = @{ class_type = "LoadImage"; inputs = @{ image = $ExpressionImage } }
    $prompt["27"] = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("26", 0); upscale_method = "nearest-exact"; megapixels = $ExpressionReferenceMegapixels; resolution_steps = 1 } }
    $prompt["28"] = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("27", 0); vae = @("4", 0) } }
    $prompt["29"] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("14", 0); latent = @("28", 0) } }
    $prompt["30"] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("16", 0); latent = @("28", 0) } }
    $prompt["17"].inputs.positive = @("29", 0)
    $prompt["17"].inputs.negative = @("30", 0)
}

$clientId = [guid]::NewGuid().ToString()
$body = @{ prompt = $prompt; client_id = $clientId } | ConvertTo-Json -Depth 100
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id." }

Write-Host "Queued Klein 9B group layout-reference test $($queued.prompt_id) on $Server"
$deadline = (Get-Date).AddMinutes(15)
do {
    Start-Sleep -Seconds 5
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 15
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry) {
        if ($entry.status.status_str -eq "error") {
            throw "Generation failed: $($entry.status.messages | ConvertTo-Json -Depth 30)"
        }
        if ($entry.status.completed) {
            $saved = @($entry.outputs."24".images)
            if ($saved.Count -eq 0) { throw "Generation completed without a saved image." }
            foreach ($image in $saved) {
                $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                $absolute = Join-Path (Join-Path $ComfyRoot "output") $relative
                Write-Output ([ordered]@{
                    prompt_id = $queued.prompt_id
                    file = $absolute
                    gpu = [string]@($stats.devices)[0].name
                    model = $modelName
                    lora = $loraName
                    lora_strength = 0.90
                    reference_order = if ($ExpressionImage) { "Picture 1 scene layout; Picture 2 Mitch neutral identity; Picture 3 Mitch small-smile expression and head geometry" } else { "Picture 1 scene layout; Picture 2 Mitch identity" }
                    scene_reference = $scenePath
                    identity_reference = $identityPath
                    expression_reference = $expressionPath
                    scene_reference_megapixels = $SceneReferenceMegapixels
                    identity_reference_megapixels = $IdentityReferenceMegapixels
                    expression_reference_megapixels = if ($ExpressionImage) { $ExpressionReferenceMegapixels } else { $null }
                    source_scene_conditioning = if ($SceneImageIsPrecomputedEdgeLayout) { "native FLUX.2 ReferenceLatent from face-interior-free Canny structural guide" } elseif ($applyCanny) { "native FLUX.2 ReferenceLatent from Canny structural edges" } else { "native FLUX.2 ReferenceLatent from raw source image" }
                    layout_reference_mode = if ($SceneImageIsPrecomputedEdgeLayout) { "precomputed_canny_face_interior_free" } elseif ($applyCanny) { "canny" } else { "raw" }
                    precomputed_head_scale = if ($SceneImageIsPrecomputedEdgeLayout) { $PrecomputedHeadScale } else { $null }
                    canny_low_threshold = if ($SceneImageIsPrecomputedEdgeLayout -or $applyCanny) { $CannyLowThreshold } else { $null }
                    canny_high_threshold = if ($SceneImageIsPrecomputedEdgeLayout -or $applyCanny) { $CannyHighThreshold } else { $null }
                    identity_mechanism = "step-1600 identity LoRA plus genuine native identity reference"
                    face_swap = $false
                    identity_pass = $false
                    width = 832
                    height = 1216
                    steps = 50
                    cfg = 4.0
                    sampler = "euler"
                    scheduler = "Flux2Scheduler"
                    seed = $Seed
                    seconds = [Math]::Round(((Get-Date) - $started).TotalSeconds, 3)
                    prompt = $effectivePrompt
                } | ConvertTo-Json -Depth 20)
            }
            exit 0
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for prompt $($queued.prompt_id)."
