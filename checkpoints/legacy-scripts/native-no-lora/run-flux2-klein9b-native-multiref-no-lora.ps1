[CmdletBinding()]
param(
    [int]$Steps = 4,
    [double]$Cfg = 1.0,
    [UInt64]$Seed = 9472363,
    [int]$Width = 832,
    [int]$Height = 1248,
    [double]$ReferenceMegapixels = 0.40,
    [ValidateRange(1, 4)]
    [int]$ReferenceCount = 4,
    [string]$Server = "http://127.0.0.1:8188",
    [string]$Reference1 = "flux2-dev-ref-01-face-front.jpg",
    [string]$Reference2 = "flux2-dev-ref-02-face-angle.jpg",
    [string]$Reference3 = "flux2-dev-ref-03-upper-body.jpg",
    [string]$Reference4 = "flux2-dev-ref-04-full-body.jpg",
    [string]$OutputPrefix = "flux2-klein9b-native-multiref-no-lora/state-fair",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [switch]$SkipModelHashValidation,
    [switch]$AllowOtherWorkerBusy,
    [string]$ScenePrompt = (
        "Images 1-2 define Mitch's face from front and three-quarter views; image 3 defines his torso; " +
        "image 4 defines his lean build. Create an ordinary candid phone photo of Mitch, framed waist-up " +
        "while walking through a busy Midwestern state fair holding lemonade. He wears a light-blue shirt " +
        "and dark jeans. Preserve his facial geometry, short light-brown hair, apparent age, build, and " +
        "natural skin. Use a 1x rear phone camera in standard photo mode, clearly resolving Mitch, nearby " +
        "people, stalls, signs, umbrellas, pavement texture, and the distant Ferris wheel with consistent " +
        "small-sensor depth under late-afternoon daylight."
    )
)

$ErrorActionPreference = "Stop"

foreach ($port in 8188, 8189) {
    $worker = "http://127.0.0.1:$port"
    try {
        $workerQueue = Invoke-RestMethod -Uri "$worker/queue" -TimeoutSec 5
        if (@($workerQueue.queue_running).Count -gt 0 -or @($workerQueue.queue_pending).Count -gt 0) {
            if ($worker -ne $Server -and $AllowOtherWorkerBusy) {
                Write-Warning "Optional worker $worker is active and will be left untouched."
            }
            else {
                throw "ComfyUI queue is not idle at $worker. Refusing to disturb active GPU work."
            }
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
    "UNETLoader", "CLIPLoader", "VAELoader", "LoadImage", "ImageScaleToTotalPixels",
    "VAEEncode", "ReferenceLatent", "CLIPTextEncode", "EmptyFlux2LatentImage", "KSampler",
    "VAEDecode", "SaveImage"
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
$modelPath = Join-Path $ComfyRoot "models\diffusion_models\$modelName"
$expectedModelBytes = 9433061528
$expectedModelSha256 = "865BA09F5B4C3CBD3468A4BD3ACB9FCB2F8740C54317482F0BCD4ED1D3655CEE"
$modelFile = Get-Item -LiteralPath $modelPath
if ($modelFile.Length -ne [int64]$expectedModelBytes) {
    throw "Unexpected file size for $modelPath`: $($modelFile.Length)"
}
if (-not $SkipModelHashValidation -and (Get-FileHash -Algorithm SHA256 -LiteralPath $modelPath).Hash -ne $expectedModelSha256) {
    throw "SHA-256 mismatch for $modelPath"
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

$inputRoot = Join-Path $ComfyRoot "input"
$references = @($Reference1, $Reference2, $Reference3, $Reference4)
$activeReferences = @($references | Select-Object -First $ReferenceCount)
foreach ($reference in $activeReferences) {
    $referencePath = Join-Path $inputRoot $reference
    if (-not (Test-Path -LiteralPath $referencePath -PathType Leaf)) {
        throw "Reference is missing from the local ComfyUI input folder: $referencePath"
    }
}

$referenceMpName = $ReferenceMegapixels.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
$suffix = "${Steps}step-cfg${Cfg}-${ReferenceCount}ref-${referenceMpName}mp-seed${Seed}"
$conditioningNode = switch ($ReferenceCount) {
    1 { "17" }
    2 { "18" }
    3 { "19" }
    4 { "20" }
}
$prompt = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $modelName; weight_dtype = "default" } }
    "2" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $clipName; type = "flux2"; device = "default" } }
    "3" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vaeName } }
    "4" = @{ class_type = "LoadImage"; inputs = @{ image = $Reference1 } }
    "5" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("4", 0); upscale_method = "lanczos"; megapixels = $ReferenceMegapixels; resolution_steps = 1 } }
    "6" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("5", 0); vae = @("3", 0) } }
    "7" = @{ class_type = "LoadImage"; inputs = @{ image = $Reference2 } }
    "8" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("7", 0); upscale_method = "lanczos"; megapixels = $ReferenceMegapixels; resolution_steps = 1 } }
    "9" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("8", 0); vae = @("3", 0) } }
    "10" = @{ class_type = "LoadImage"; inputs = @{ image = $Reference3 } }
    "11" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("10", 0); upscale_method = "lanczos"; megapixels = $ReferenceMegapixels; resolution_steps = 1 } }
    "12" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("11", 0); vae = @("3", 0) } }
    "13" = @{ class_type = "LoadImage"; inputs = @{ image = $Reference4 } }
    "14" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("13", 0); upscale_method = "lanczos"; megapixels = $ReferenceMegapixels; resolution_steps = 1 } }
    "15" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("14", 0); vae = @("3", 0) } }
    "16" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $ScenePrompt; clip = @("2", 0) } }
    "17" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("16", 0); latent = @("6", 0) } }
    "18" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("17", 0); latent = @("9", 0) } }
    "19" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("18", 0); latent = @("12", 0) } }
    "20" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("19", 0); latent = @("15", 0) } }
    "21" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
    "22" = @{ class_type = "KSampler"; inputs = @{
        model = @("1", 0)
        seed = $Seed
        steps = $Steps
        cfg = $Cfg
        sampler_name = "euler"
        scheduler = "simple"
        positive = @($conditioningNode, 0)
        negative = @($conditioningNode, 0)
        latent_image = @("21", 0)
        denoise = 1.0
    } }
    "23" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("22", 0); vae = @("3", 0) } }
    "24" = @{ class_type = "SaveImage"; inputs = @{ images = @("23", 0); filename_prefix = "$OutputPrefix-$suffix" } }
}

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
            $saved = @($entry.outputs.'24'.images)
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
                    references = $activeReferences
                    reference_roles = @(@("face_front", "face_three_quarter_right", "face_three_quarter_left", "body_build") | Select-Object -First $ReferenceCount)
                    reference_megapixels_each = $ReferenceMegapixels
                    identity_mechanism = "native FLUX.2 multi-reference conditioning"
                    prompt = $ScenePrompt
                    width = $Width
                    height = $Height
                    steps = $Steps
                    cfg = $Cfg
                    sampler = "euler"
                    scheduler = "simple"
                    seed = $Seed
                    character_lora = $null
                    identity_adapter = $null
                    output_mask = $null
                    face_swap = $null
                    post_processing = $null
                    seconds = [Math]::Round(((Get-Date) - $started).TotalSeconds, 3)
                    file = $absolutePath
                } | ConvertTo-Json -Depth 10 -Compress)
            }
            return
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for prompt $($queued.prompt_id)."
