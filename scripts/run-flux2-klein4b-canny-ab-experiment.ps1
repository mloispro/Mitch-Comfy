[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Upgrade", "Group")]
    [string]$Mode,
    [string]$Server = "http://127.0.0.1:8188",
    [string]$ExpectedGpuName = "NVIDIA GeForce RTX 3090",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ExperimentRoot = "C:\projects\AI-Tools\Mitch-Comfy\output\klein4b-canny-ab-experiment-20260901",
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"

$modelName = "flux-2-klein-base-4b-fp8.safetensors"
$clipName = "qwen_3_4b_fp8_mixed.safetensors"
$vaeName = "flux2-vae.safetensors"
$loraName = "aitk\m1tch-flux2-klein-4b-identity-v3-portrait-profile.safetensors"
$loraStrength = 1.20

$expectedFiles = @{
    (Join-Path $ComfyRoot "models\diffusion_models\$modelName") = @(
        4089498488, "44BAB3A86FE98B85D21DD2A4729EBDC3AE51FB8A39F76E457E18C724219E6840"
    )
    (Join-Path $ComfyRoot "models\text_encoders\$clipName") = @(
        5631994051, "72450B19758172C5A7273CF7DE729D1C17E7F434A104A00167624CBA94F68F15"
    )
    (Join-Path $ComfyRoot "models\vae\$vaeName") = @(
        336213556, "D64F3A68E1CC4F9F4E29B6E0DA38A0204FE9A49F2D4053F0EC1FA1CA02F9C4B5"
    )
    (Join-Path $ComfyRoot "models\loras\$loraName") = @(
        46224560, "C43D7C1FCA404A8B316A9D0C8756E140033E4763532628F62FACC791F0B8A149"
    )
}

foreach ($port in 8188, 8189, 8190) {
    $worker = "http://127.0.0.1:$port"
    $queue = Invoke-RestMethod -Uri "$worker/queue" -TimeoutSec 10
    if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
        throw "ComfyUI queue is active at $worker. Refusing to disturb or overlap GPU work."
    }
}

$stats = Invoke-RestMethod -Uri "$Server/system_stats" -TimeoutSec 10
$deviceName = [string](@($stats.devices)[0].name)
if ($deviceName -notlike "*$ExpectedGpuName*") {
    throw "Target worker is '$deviceName', not the expected $ExpectedGpuName."
}

$requiredNodes = @(
    "UNETLoader", "LoraLoaderModelOnly", "CLIPLoader", "VAELoader", "LoadImage",
    "ImageScale", "VAEEncode", "ReferenceLatent", "CLIPTextEncode", "CFGGuider",
    "KSamplerSelect", "Flux2Scheduler", "RandomNoise", "EmptyFlux2LatentImage",
    "SamplerCustomAdvanced", "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$nodeName" -TimeoutSec 15
    if (-not $nodeInfo.PSObject.Properties[$nodeName]) {
        throw "Required live ComfyUI node is unavailable: $nodeName"
    }
}

foreach ($path in $expectedFiles.Keys) {
    $file = Get-Item -LiteralPath $path
    if ($file.Length -ne [int64]$expectedFiles[$path][0]) {
        throw "Unexpected file size: $path"
    }
    $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash
    if ($actualHash -ne $expectedFiles[$path][1]) {
        throw "SHA-256 mismatch: $path"
    }
}

$inputRoot = Join-Path $ComfyRoot "input"
if ($Mode -eq "Upgrade") {
    $baselineFolder = Join-Path $ComfyRoot "output\flux2-klein9b-upgrade-photo-detail-realism-v1\20260901-162214-644956"
    $baselineReportPath = Join-Path $baselineFolder "report.json"
    $baselinePhotoPath = Join-Path $baselineFolder "photo_00001_.png"
    $baselineGuidePath = Join-Path $baselineFolder "structure-guide_00001_.png"
    $guideName = "experiment-klein4b-canny-ab-upgrade-guide.png"
    $references = @(
        [ordered]@{ name = "mitch-photo2-source-aef87048.png"; width = 1024; height = 1024; method = "bicubic"; role = "exact source scene, pose, expression, clothing, lighting, and composition" },
        [ordered]@{ name = $guideName; width = 724; height = 724; method = "nearest-exact"; role = "pixel-identical face-interior-free Canny guide from the 9B baseline" },
        [ordered]@{ name = "mitch-klein9b-ref-front-neutral-v2.jpg"; width = 627; height = 836; method = "nearest-exact"; role = "genuine Mitch identity" },
        [ordered]@{ name = "mitch-natural-hair-only-val05-isolated.png"; width = 460; height = 228; method = "bicubic"; role = "genuine Mitch hair material" }
    )
    $outputPrefix = "klein4b-canny-ab-experiment/upgrade/seed-8675412"
}
else {
    $baselineFolder = Join-Path $ComfyRoot "output\flux2-klein9b-mitch-group-scene-studio-v1\20260901-165841-547535"
    $baselineReportPath = Join-Path $baselineFolder "report.json"
    $baselinePhotoPath = Join-Path $baselineFolder "photo_00001_.png"
    $baselineGuidePath = Join-Path $baselineFolder "layout-guide_00001_.png"
    $guideName = "experiment-klein4b-canny-ab-group-guide.png"
    $references = @(
        [ordered]@{ name = $guideName; width = 448; height = 592; method = "lanczos"; role = "pixel-identical face-free group Canny layout from the 9B baseline" },
        [ordered]@{ name = "mitch-klein9b-ref-training04-front-neutral.jpg"; width = 1184; height = 880; method = "lanczos"; role = "genuine Mitch identity" }
    )
    $outputPrefix = "klein4b-canny-ab-experiment/group/seed-8675413"
}

foreach ($requiredPath in @($baselineReportPath, $baselinePhotoPath, $baselineGuidePath)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Missing locked 9B comparison artifact: $requiredPath"
    }
}
$copiedGuidePath = Join-Path $inputRoot $guideName
if (-not (Test-Path -LiteralPath $copiedGuidePath -PathType Leaf)) {
    throw "Missing copied experimental guide in ComfyUI input: $copiedGuidePath"
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $copiedGuidePath).Hash -ne
    (Get-FileHash -Algorithm SHA256 -LiteralPath $baselineGuidePath).Hash) {
    throw "The experimental Canny guide is not byte-identical to the saved 9B guide."
}
foreach ($reference in $references) {
    if (-not (Test-Path -LiteralPath (Join-Path $inputRoot $reference.name) -PathType Leaf)) {
        throw "Missing ComfyUI reference image: $($reference.name)"
    }
}

$baselineReport = Get-Content -Raw -LiteralPath $baselineReportPath | ConvertFrom-Json
$promptText = [string]$baselineReport.effective_prompt
$seed = [UInt64]$baselineReport.seed
$width = [int]$baselineReport.width
$height = [int]$baselineReport.height
$steps = [int]$baselineReport.steps
$cfg = if ($null -ne $baselineReport.cfg) { [double]$baselineReport.cfg } else { [double]$baselineReport.guidance }
if (-not $promptText -or $steps -ne 50 -or $cfg -ne 4.0) {
    throw "The locked 9B baseline report does not contain the expected 50-step CFG-4 prompt contract."
}

$graph = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $modelName; weight_dtype = "default" } }
    "2" = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $loraName; strength_model = $loraStrength } }
    "3" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $clipName; type = "flux2"; device = "default" } }
    "4" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vaeName } }
    "5" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $promptText; clip = @("3", 0) } }
    "6" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("3", 0) } }
}

$nextId = 7
$positiveNode = "5"
$negativeNode = "6"
foreach ($reference in $references) {
    $loadId = [string]$nextId; $nextId++
    $scaleId = [string]$nextId; $nextId++
    $encodeId = [string]$nextId; $nextId++
    $positiveRefId = [string]$nextId; $nextId++
    $negativeRefId = [string]$nextId; $nextId++
    $graph[$loadId] = @{ class_type = "LoadImage"; inputs = @{ image = $reference.name } }
    $graph[$scaleId] = @{ class_type = "ImageScale"; inputs = @{
        image = @($loadId, 0); upscale_method = $reference.method
        width = [int]$reference.width; height = [int]$reference.height; crop = "disabled"
    } }
    $graph[$encodeId] = @{ class_type = "VAEEncode"; inputs = @{ pixels = @($scaleId, 0); vae = @("4", 0) } }
    $graph[$positiveRefId] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @($positiveNode, 0); latent = @($encodeId, 0) } }
    $graph[$negativeRefId] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @($negativeNode, 0); latent = @($encodeId, 0) } }
    $positiveNode = $positiveRefId
    $negativeNode = $negativeRefId
}

$guiderId = [string]$nextId; $nextId++
$samplerId = [string]$nextId; $nextId++
$schedulerId = [string]$nextId; $nextId++
$noiseId = [string]$nextId; $nextId++
$latentId = [string]$nextId; $nextId++
$sampleId = [string]$nextId; $nextId++
$decodeId = [string]$nextId; $nextId++
$saveId = [string]$nextId
$graph[$guiderId] = @{ class_type = "CFGGuider"; inputs = @{ model = @("2", 0); positive = @($positiveNode, 0); negative = @($negativeNode, 0); cfg = $cfg } }
$graph[$samplerId] = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
$graph[$schedulerId] = @{ class_type = "Flux2Scheduler"; inputs = @{ steps = $steps; width = $width; height = $height } }
$graph[$noiseId] = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $seed } }
$graph[$latentId] = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $width; height = $height; batch_size = 1 } }
$graph[$sampleId] = @{ class_type = "SamplerCustomAdvanced"; inputs = @{
    noise = @($noiseId, 0); guider = @($guiderId, 0); sampler = @($samplerId, 0)
    sigmas = @($schedulerId, 0); latent_image = @($latentId, 0)
} }
$graph[$decodeId] = @{ class_type = "VAEDecode"; inputs = @{ samples = @($sampleId, 0); vae = @("4", 0) } }
$graph[$saveId] = @{ class_type = "SaveImage"; inputs = @{ images = @($decodeId, 0); filename_prefix = $outputPrefix } }

$modeFolder = Join-Path $ExperimentRoot $Mode.ToLowerInvariant()
New-Item -ItemType Directory -Force -Path $modeFolder | Out-Null
$promptPath = Join-Path $modeFolder "prompt-api.json"
$graph | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $promptPath -Encoding utf8

$body = @{ prompt = $graph; client_id = "klein4b-canny-ab-$($Mode.ToLowerInvariant())" } | ConvertTo-Json -Depth 100
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body -TimeoutSec 60
$promptId = [string]$queued.prompt_id
if (-not $promptId) { throw "ComfyUI did not return a prompt id." }
Write-Host "Queued isolated Klein 4B Canny A/B $Mode experiment on $ExpectedGpuName`: $promptId"

$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
while ([DateTime]::UtcNow -lt $deadline) {
    Start-Sleep -Seconds 3
    $history = Invoke-RestMethod -Uri "$Server/history/$promptId" -TimeoutSec 20
    $entry = $history.PSObject.Properties[$promptId].Value
    if (-not $entry) { continue }
    if ($entry.status.status_str -eq "error") {
        throw "Generation failed: $($entry.status.messages | ConvertTo-Json -Depth 30)"
    }
    if ($entry.status.completed -or $entry.status.status_str -eq "success") {
        $saved = @($entry.outputs.$saveId.images)
        if ($saved.Count -eq 0) { throw "Generation completed without a saved image." }
        $image = $saved[0]
        $relativePath = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
        $outputPath = Join-Path (Join-Path $ComfyRoot "output") $relativePath
        $report = [ordered]@{
            schema_version = 1
            status = "generated_pending_evaluation"
            experiment = "flux2_klein4b_canny_ab_against_locked_klein9b"
            mode = $Mode
            production_workflows_modified = $false
            prompt_id = $promptId
            worker = $deviceName
            model = $modelName
            model_sha256 = $expectedFiles[(Join-Path $ComfyRoot "models\diffusion_models\$modelName")][1]
            text_encoder = $clipName
            text_encoder_sha256 = $expectedFiles[(Join-Path $ComfyRoot "models\text_encoders\$clipName")][1]
            vae = $vaeName
            vae_sha256 = $expectedFiles[(Join-Path $ComfyRoot "models\vae\$vaeName")][1]
            lora = $loraName
            lora_sha256 = $expectedFiles[(Join-Path $ComfyRoot "models\loras\$loraName")][1]
            lora_strength = $loraStrength
            lora_approved_scope = "portrait/profile; whole-frame Canny use is experimental"
            identity_mechanism = "matching Klein Base 4B LoRA plus genuine-photo native ReferenceLatent"
            references = @($references)
            canny_guide_source = $baselineGuidePath
            canny_guide_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $baselineGuidePath).Hash
            canny_guide_byte_identical_to_9b = $true
            prompt = $promptText
            baseline_9b_report = $baselineReportPath
            baseline_9b_photo = $baselinePhotoPath
            baseline_9b_photo_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $baselinePhotoPath).Hash
            width = $width
            height = $height
            steps = $steps
            cfg = $cfg
            sampler = "euler"
            scheduler = "Flux2Scheduler"
            seed = $seed
            face_swap = $false
            output_mask = $false
            restoration = $false
            sharpening = $false
            second_model_pass = $false
            seconds = [Math]::Round(((Get-Date) - $started).TotalSeconds, 3)
            output = $outputPath
            output_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $outputPath).Hash
            prompt_graph = $promptPath
        }
        $reportPath = Join-Path $modeFolder "generation-report.json"
        $report | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $reportPath -Encoding utf8
        $report | ConvertTo-Json -Depth 30 -Compress
        exit 0
    }
}

throw "Timed out waiting for prompt $promptId."
