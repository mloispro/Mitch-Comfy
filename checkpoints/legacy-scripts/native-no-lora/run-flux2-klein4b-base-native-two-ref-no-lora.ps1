[CmdletBinding()]
param(
    [int]$Steps = 50,
    [double]$Cfg = 4.0,
    [UInt64]$Seed = 9472363,
    [int]$Width = 832,
    [int]$Height = 1248,
    [double]$ReferenceMegapixels = 1.0,
    [double]$Reference1Megapixels = 0.0,
    [string]$Server = "http://127.0.0.1:8188",
    [string]$Reference1 = "mitch-inline-author-ref-01-face.jpg",
    [string]$Reference2 = "mitch-inline-author-ref-02-angle.jpg",
    [string]$Reference3 = "",
    [string]$Reference4 = "",
    [string]$OutputPrefix = "flux2-inline-author-method/klein4b-base-two-face-ref",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ScenePrompt = (
        "Images 1 and 2 show Mitch, the same character in every image. " +
        "Create a realistic candid phone photograph of Mitch walking toward the camera through a " +
        "somewhat busy downtown street corner."
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
        if ($worker -eq $Server) { throw }
        Write-Warning "Could not inspect optional worker $worker`: $($_.Exception.Message)"
    }
}

$requiredNodes = @(
    "UNETLoader", "CLIPLoader", "VAELoader", "LoadImage", "ImageScaleToTotalPixels",
    "VAEEncode", "ReferenceLatent", "CLIPTextEncode", "CFGGuider", "KSamplerSelect",
    "Flux2Scheduler", "RandomNoise", "EmptyFlux2LatentImage", "SamplerCustomAdvanced",
    "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$nodeName" -TimeoutSec 10
    if (-not $nodeInfo.PSObject.Properties[$nodeName]) {
        throw "Required node is unavailable: $nodeName"
    }
}

$modelName = "flux-2-klein-base-4b-fp8.safetensors"
$clipName = "qwen_3_4b_fp8_mixed.safetensors"
$vaeName = "flux2-vae.safetensors"
$expected = @{
    (Join-Path $ComfyRoot "models\diffusion_models\$modelName") = @(
        4089498488, "44BAB3A86FE98B85D21DD2A4729EBDC3AE51FB8A39F76E457E18C724219E6840"
    )
    (Join-Path $ComfyRoot "models\text_encoders\$clipName") = @(
        5631994051, "72450B19758172C5A7273CF7DE729D1C17E7F434A104A00167624CBA94F68F15"
    )
    (Join-Path $ComfyRoot "models\vae\$vaeName") = @(
        336213556, "D64F3A68E1CC4F9F4E29B6E0DA38A0204FE9A49F2D4053F0EC1FA1CA02F9C4B5"
    )
}
foreach ($path in $expected.Keys) {
    $file = Get-Item -LiteralPath $path
    if ($file.Length -ne [int64]$expected[$path][0]) { throw "Unexpected file size: $path" }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash -ne $expected[$path][1]) {
        throw "SHA-256 mismatch: $path"
    }
}

$inputRoot = Join-Path $ComfyRoot "input"
$references = @($Reference1, $Reference2) + @(if ($Reference3) { $Reference3 }) + @(if ($Reference4) { $Reference4 })
foreach ($reference in $references) {
    if (-not (Test-Path -LiteralPath (Join-Path $inputRoot $reference) -PathType Leaf)) {
        throw "Reference is missing from ComfyUI input: $reference"
    }
}

$mp = $ReferenceMegapixels.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
$reference1Mp = if ($Reference1Megapixels -gt 0) { $Reference1Megapixels } else { $ReferenceMegapixels }
$cfgName = $Cfg.ToString("0.0", [Globalization.CultureInfo]::InvariantCulture)
$suffix = "${Steps}step-cfg${cfgName}-$($references.Count)ref-${mp}mp-seed${Seed}"
$prompt = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $modelName; weight_dtype = "default" } }
    "2" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $clipName; type = "flux2"; device = "default" } }
    "3" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vaeName } }
    "4" = @{ class_type = "LoadImage"; inputs = @{ image = $Reference1 } }
    "5" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("4", 0); upscale_method = "lanczos"; megapixels = $reference1Mp; resolution_steps = 1 } }
    "6" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("5", 0); vae = @("3", 0) } }
    "7" = @{ class_type = "LoadImage"; inputs = @{ image = $Reference2 } }
    "8" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("7", 0); upscale_method = "lanczos"; megapixels = $ReferenceMegapixels; resolution_steps = 1 } }
    "9" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("8", 0); vae = @("3", 0) } }
    "10" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $ScenePrompt; clip = @("2", 0) } }
    "11" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("2", 0) } }
    "12" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("10", 0); latent = @("6", 0) } }
    "13" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("12", 0); latent = @("9", 0) } }
    "14" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("11", 0); latent = @("6", 0) } }
    "15" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("14", 0); latent = @("9", 0) } }
    "16" = @{ class_type = "CFGGuider"; inputs = @{ model = @("1", 0); positive = @("13", 0); negative = @("15", 0); cfg = $Cfg } }
    "17" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    "18" = @{ class_type = "Flux2Scheduler"; inputs = @{ steps = $Steps; width = $Width; height = $Height } }
    "19" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Seed } }
    "20" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
    "21" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("19", 0); guider = @("16", 0); sampler = @("17", 0); sigmas = @("18", 0); latent_image = @("20", 0) } }
    "22" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("21", 0); vae = @("3", 0) } }
    "23" = @{ class_type = "SaveImage"; inputs = @{ images = @("22", 0); filename_prefix = "$OutputPrefix-$suffix" } }
}

$positiveNode = "13"
$negativeNode = "15"
if ($Reference3) {
    $prompt["24"] = @{ class_type = "LoadImage"; inputs = @{ image = $Reference3 } }
    $prompt["25"] = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("24", 0); upscale_method = "lanczos"; megapixels = $ReferenceMegapixels; resolution_steps = 1 } }
    $prompt["26"] = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("25", 0); vae = @("3", 0) } }
    $prompt["27"] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("13", 0); latent = @("26", 0) } }
    $prompt["28"] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("15", 0); latent = @("26", 0) } }
    $positiveNode = "27"
    $negativeNode = "28"
}
if ($Reference4) {
    $prompt["29"] = @{ class_type = "LoadImage"; inputs = @{ image = $Reference4 } }
    $prompt["30"] = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("29", 0); upscale_method = "lanczos"; megapixels = $ReferenceMegapixels; resolution_steps = 1 } }
    $prompt["31"] = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("30", 0); vae = @("3", 0) } }
    $prompt["32"] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @($positiveNode, 0); latent = @("31", 0) } }
    $prompt["33"] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @($negativeNode, 0); latent = @("31", 0) } }
    $positiveNode = "32"
    $negativeNode = "33"
}
$prompt["16"].inputs.positive = @($positiveNode, 0)
$prompt["16"].inputs.negative = @($negativeNode, 0)

$clientId = [guid]::NewGuid().ToString()
$body = @{ prompt = $prompt; client_id = $clientId } | ConvertTo-Json -Depth 100
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id." }

Write-Host "Queued prompt $($queued.prompt_id) on $Server"
$deadline = (Get-Date).AddMinutes(60)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry) {
        if ($entry.status.status_str -eq "error") {
            throw "Generation failed: $($entry.status.messages | ConvertTo-Json -Depth 20)"
        }
        if ($entry.status.completed) {
            $saved = @($entry.outputs.'23'.images)
            if ($saved.Count -eq 0) { throw "Generation completed without a saved image." }
            foreach ($image in $saved) {
                $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                $absolute = Join-Path (Join-Path $ComfyRoot "output") $relative
                Write-Output ([pscustomobject]@{
                    prompt_id = $queued.prompt_id; model = $modelName; text_encoder = $clipName
                    vae = $vaeName; references = $references
                    reference_1_megapixels = $reference1Mp
                    reference_megapixels_each = $ReferenceMegapixels
                    identity_mechanism = "native FLUX.2 multi-reference conditioning"
                    prompt = $ScenePrompt; width = $Width; height = $Height; steps = $Steps
                    cfg = $Cfg; sampler = "euler"; scheduler = "Flux2Scheduler"; seed = $Seed
                    character_lora = $null; identity_adapter = $null; output_mask = $null
                    face_swap = $null; post_processing = $null
                    seconds = [Math]::Round(((Get-Date) - $started).TotalSeconds, 3); file = $absolute
                } | ConvertTo-Json -Depth 10 -Compress)
            }
            exit 0
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for prompt $($queued.prompt_id)."
