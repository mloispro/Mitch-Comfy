[CmdletBinding()]
param(
    [int]$Steps = 20,
    [double]$Guidance = 4.0,
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
    [string]$OutputPrefix = "flux2-dev-multiref-no-lora/state-fair-v1",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ScenePrompt = (
        "Images 1-2 define Mitch's face from front and three-quarter views; image 3 defines his torso; " +
        "image 4 defines his lean full-body build. Create a candid phone photo of Mitch, framed mid-thigh " +
        "up, walking through a busy Midwestern state fair holding lemonade. He " +
        "wears a light-blue shirt and dark jeans. Preserve his facial geometry, short light-brown hair, " +
        "apparent age, build, and natural skin. Show a varied crowd, food stalls, umbrellas, pavement, " +
        "and Ferris wheel in deep smartphone focus under late-afternoon daylight."
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
    "UNETLoader", "CLIPLoader", "VAELoader", "LoadImage", "ImageScaleToTotalPixels",
    "VAEEncode", "ReferenceLatent", "CLIPTextEncode", "FluxGuidance", "BasicGuider",
    "KSamplerSelect", "Flux2Scheduler", "RandomNoise", "EmptyFlux2LatentImage",
    "SamplerCustomAdvanced", "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$nodeName" -TimeoutSec 10
    if (-not $nodeInfo.PSObject.Properties[$nodeName]) {
        throw "Required node is unavailable: $nodeName"
    }
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

$modelInfo = Invoke-RestMethod -Uri "$Server/object_info/UNETLoader" -TimeoutSec 10
$availableModels = @($modelInfo.UNETLoader.input.required.unet_name[0])
if ($availableModels -notcontains "flux2_dev_fp8mixed.safetensors") {
    throw "FLUX.2 Dev is unavailable on $Server."
}
$clipInfo = Invoke-RestMethod -Uri "$Server/object_info/CLIPLoader" -TimeoutSec 10
$availableClips = @($clipInfo.CLIPLoader.input.required.clip_name[0])
if ($availableClips -notcontains "mistral_3_small_flux2_fp4_mixed.safetensors") {
    throw "The required FLUX.2 Mistral encoder is unavailable on $Server."
}

$guidanceName = $Guidance.ToString("0.0", [Globalization.CultureInfo]::InvariantCulture)
$referenceMpName = $ReferenceMegapixels.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
$suffix = "${Steps}step-guidance${guidanceName}-${ReferenceCount}ref-${referenceMpName}mp-seed${Seed}"
$conditioningNode = switch ($ReferenceCount) {
    1 { "18" }
    2 { "19" }
    3 { "20" }
    4 { "21" }
}
$prompt = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = "flux2_dev_fp8mixed.safetensors"; weight_dtype = "default" } }
    "2" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = "mistral_3_small_flux2_fp4_mixed.safetensors"; type = "flux2"; device = "default" } }
    "3" = @{ class_type = "VAELoader"; inputs = @{ vae_name = "flux2-vae.safetensors" } }
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
    "17" = @{ class_type = "FluxGuidance"; inputs = @{ conditioning = @("16", 0); guidance = $Guidance } }
    "18" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("17", 0); latent = @("6", 0) } }
    "19" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("18", 0); latent = @("9", 0) } }
    "20" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("19", 0); latent = @("12", 0) } }
    "21" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("20", 0); latent = @("15", 0) } }
    "22" = @{ class_type = "BasicGuider"; inputs = @{ model = @("1", 0); conditioning = @($conditioningNode, 0) } }
    "23" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    "24" = @{ class_type = "Flux2Scheduler"; inputs = @{ steps = $Steps; width = $Width; height = $Height } }
    "25" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Seed } }
    "26" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
    "27" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("25", 0); guider = @("22", 0); sampler = @("23", 0); sigmas = @("24", 0); latent_image = @("26", 0) } }
    "28" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("27", 0); vae = @("3", 0) } }
    "29" = @{ class_type = "SaveImage"; inputs = @{ images = @("28", 0); filename_prefix = "$OutputPrefix-$suffix" } }
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
            $saved = @($entry.outputs.'29'.images)
            if ($saved.Count -eq 0) {
                throw "Generation completed without a saved image."
            }
            foreach ($image in $saved) {
                $relativePath = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                $absolutePath = Join-Path (Join-Path $ComfyRoot "output") $relativePath
                Write-Output ([pscustomobject]@{
                    prompt_id = $queued.prompt_id
                    model = "flux2_dev_fp8mixed.safetensors"
                    text_encoder = "mistral_3_small_flux2_fp4_mixed.safetensors"
                    vae = "flux2-vae.safetensors"
                    references = $activeReferences
                    reference_roles = @(@("face_front", "face_three_quarter_right", "face_three_quarter_left", "body_build") | Select-Object -First $ReferenceCount)
                    reference_megapixels_each = $ReferenceMegapixels
                    prompt = $ScenePrompt
                    width = $Width
                    height = $Height
                    steps = $Steps
                    guidance = $Guidance
                    sampler = "euler"
                    scheduler = "Flux2Scheduler"
                    seed = $Seed
                    lora = $null
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
