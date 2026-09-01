[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8188",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyOutputRoot = "C:\projects\AI-Tools\ComfyUI\output",
    [string]$Model = "z_image_bf16.safetensors",
    [string]$TextEncoder = "qwen_3_4b.safetensors",
    [string]$Vae = "ae.safetensors",
    [string]$SourceInput = "hidream-best-identity-proof-seed-8675603.png",
    [string]$ExpectedSourceHash = "D867BE7CCFD5562C1822879E9C1B8AC7CE516A3B7AC71A29729D4FE83D5B6508",
    [UInt64]$Seed = 8675603,
    [int]$Steps = 30,
    [double]$Cfg = 4.0,
    [double]$Shift = 3.0,
    [double]$Denoise = 0.15,
    [double]$Megapixels = 1.0,
    [string]$OutputPrefix = "zimage-texture-pass-hidream-v1/denoise-0p15-seed-8675603",
    [string]$PublishedOutput = "output\zimage-texture-pass-hidream-v1\denoise-0p15-seed-8675603.png",
    [string]$ManifestOutput = "",
    [switch]$PreflightOnly,
    [string]$PositivePrompt = (
        "Preserve this exact existing photograph: the same single adult man, exact face, apparent age, " +
        "hairline, hairstyle, eyes, nose, ears, mouth, jaw, expression, pose, navy shirt, camera angle, " +
        "framing, restaurant patio, background diners, tables, plants, lights, and all scene geometry. " +
        "Change only the surface rendering to believable unretouched smartphone photography: natural " +
        "uneven skin texture, fine pores, subtle peach fuzz and stubble, gentle real skin color variation, " +
        "individual hair strands, slight sensor grain, restrained sharpness, and ordinary optical detail. " +
        "Keep the man fully recognizable as the identical person. Do not add, remove, duplicate, reshape, " +
        "repose, relight, beautify, or restyle anything."
    ),
    [string]$NegativePrompt = (
        "plastic skin, waxy skin, airbrushed skin, beauty filter, face smoothing, porcelain skin, CGI, " +
        "3D render, illustration, oversharpening, crunchy detail, changed identity, changed face, changed " +
        "age, changed expression, changed pose, duplicate person, extra person, altered background, text, " +
        "logo, watermark"
    )
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$modelPath = Join-Path $ComfyRoot "models\diffusion_models\$Model"
$textEncoderPath = Join-Path $ComfyRoot "models\text_encoders\$TextEncoder"
$vaePath = Join-Path $ComfyRoot "models\vae\$Vae"
$sourcePath = Join-Path $ComfyRoot "input\$SourceInput"
$expectedHashes = [ordered]@{
    model = "996A67D3FF666946B1C25CBC16D1B1918B6CC0AC166309E23FE3B3D830263DEE"
    text_encoder = "6C671498573AC2F7A5501502CCCE8D2B08EA6CA2F661C458E708F36B36EDFC5A"
    vae = "AFC8E28272CD15DB3919BACDB6918CE9C1ED22E96CB12C4D5ED0FBA823529E38"
    source = $ExpectedSourceHash
}

if ($Steps -ne 30 -or $Cfg -ne 4.0 -or $Shift -ne 3.0 -or $Denoise -notin @(0.10, 0.15) -or $Megapixels -ne 1.0) {
    throw "This controlled screen is locked to 30 steps, CFG 4, shift 3, denoise 0.10 or 0.15, and 1.0 MP."
}

function Get-Hash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing file: $Path" }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Assert-SafeWorkerState {
    $gpuState = @(& nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader)
    if ($LASTEXITCODE -ne 0) { throw "nvidia-smi could not inspect both GPUs." }
    Write-Host "GPU state: $($gpuState -join '; ')"
    foreach ($port in 8188, 8189, 8190) {
        $worker = "http://127.0.0.1:$port"
        try {
            $queue = Invoke-RestMethod -Uri "$worker/queue" -TimeoutSec 5
            $running = @($queue.queue_running).Count
            $pending = @($queue.queue_pending).Count
            Write-Host "Queue $port`: running=$running, pending=$pending"
            if ($port -eq 8188 -and ($running -gt 0 -or $pending -gt 0)) {
                throw "RTX 3090 worker queue is not idle. Refusing to disturb active work."
            }
        }
        catch {
            if ($port -eq 8188) { throw }
            Write-Warning "Could not inspect optional worker $port`: $($_.Exception.Message)"
        }
    }
}

Assert-SafeWorkerState
$stats = Invoke-RestMethod -Uri "$Server/system_stats" -TimeoutSec 5
$deviceName = [string](@($stats.devices)[0].name)
if ($deviceName -notlike "*RTX 3090*") { throw "Worker '$deviceName' is not the RTX 3090." }

$requiredNodes = @(
    "UNETLoader", "ModelSamplingAuraFlow", "CLIPLoader", "VAELoader", "LoadImage",
    "ImageScaleToTotalPixels", "VAEEncode", "CLIPTextEncode", "KSampler", "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $info = Invoke-RestMethod -Uri "$Server/object_info/$nodeName" -TimeoutSec 10
    if (-not $info.PSObject.Properties[$nodeName]) { throw "Required node unavailable: $nodeName" }
}

$actualHashes = [ordered]@{
    model = Get-Hash $modelPath
    text_encoder = Get-Hash $textEncoderPath
    vae = Get-Hash $vaePath
    source = Get-Hash $sourcePath
}
foreach ($key in $expectedHashes.Keys) {
    if ($actualHashes[$key] -ne $expectedHashes[$key]) {
        throw "SHA256 mismatch for $key`: expected $($expectedHashes[$key]), got $($actualHashes[$key])"
    }
}

$allInfo = Invoke-RestMethod -Uri "$Server/object_info" -TimeoutSec 30
if (@($allInfo.UNETLoader.input.required.unet_name[0]) -notcontains $Model) {
    throw "The live RTX 3090 worker cannot see Z-Image model: $Model"
}
if (@($allInfo.CLIPLoader.input.required.clip_name[0]) -notcontains $TextEncoder) {
    throw "The live RTX 3090 worker cannot see text encoder: $TextEncoder"
}
if (@($allInfo.VAELoader.input.required.vae_name[0]) -notcontains $Vae) {
    throw "The live RTX 3090 worker cannot see VAE: $Vae"
}
if (@($allInfo.LoadImage.input.required.image[0]) -notcontains $SourceInput) {
    throw "The live RTX 3090 worker cannot see edit source: $SourceInput"
}

$preflight = [ordered]@{
    status = "preflight_passed"
    worker = $Server
    gpu = $deviceName
    mechanism = "Z-Image Base low-denoise latent img2img texture refinement"
    source_role = "edit-source latent conditioning; not identity-reference conditioning"
    identity_lora = $null
    face_swap = $false
    model = $Model
    text_encoder = $TextEncoder
    vae = $Vae
    hashes = $actualHashes
    seed = $Seed
    steps = $Steps
    cfg = $Cfg
    shift = $Shift
    denoise = $Denoise
    megapixels = $Megapixels
    sampler = "res_multistep"
    scheduler = "simple"
}
if ($PreflightOnly) {
    $preflight | ConvertTo-Json -Depth 10
    return
}

Assert-SafeWorkerState
$prompt = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $Model; weight_dtype = "default" } }
    "2" = @{ class_type = "ModelSamplingAuraFlow"; inputs = @{ model = @("1", 0); shift = $Shift } }
    "3" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $TextEncoder; type = "lumina2"; device = "default" } }
    "4" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $Vae } }
    "5" = @{ class_type = "LoadImage"; inputs = @{ image = $SourceInput } }
    "6" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{
        image = @("5", 0); upscale_method = "lanczos"; megapixels = $Megapixels; resolution_steps = 32
    } }
    "7" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("6", 0); vae = @("4", 0) } }
    "8" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $PositivePrompt; clip = @("3", 0) } }
    "9" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $NegativePrompt; clip = @("3", 0) } }
    "10" = @{ class_type = "KSampler"; inputs = @{
        model = @("2", 0)
        seed = $Seed
        steps = $Steps
        cfg = $Cfg
        sampler_name = "res_multistep"
        scheduler = "simple"
        positive = @("8", 0)
        negative = @("9", 0)
        latent_image = @("7", 0)
        denoise = $Denoise
    } }
    "11" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("10", 0); vae = @("4", 0) } }
    "12" = @{ class_type = "SaveImage"; inputs = @{ images = @("11", 0); filename_prefix = $OutputPrefix } }
}

$clientId = [guid]::NewGuid().ToString()
$body = @{ prompt = $prompt; client_id = $clientId } | ConvertTo-Json -Depth 100
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id." }
Write-Host "Queued Z-Image texture pass $($queued.prompt_id) on the RTX 3090 only."

$deadline = (Get-Date).AddMinutes(120)
do {
    Start-Sleep -Seconds 3
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry) {
        if ($entry.status.status_str -eq "error") {
            throw "Z-Image texture pass failed: $($entry.status.messages | ConvertTo-Json -Depth 20)"
        }
        if ($entry.status.completed) {
            $saved = @($entry.outputs.'12'.images)
            if ($saved.Count -eq 0) { throw "Z-Image completed without saving an image." }
            $relative = if ($saved[0].subfolder) {
                Join-Path $saved[0].subfolder $saved[0].filename
            } else { $saved[0].filename }
            $generatedPath = Join-Path $ComfyOutputRoot $relative
            if (-not (Test-Path -LiteralPath $generatedPath -PathType Leaf)) {
                throw "ComfyUI reported a missing output: $generatedPath"
            }
            $publishedPath = Join-Path $repoRoot $PublishedOutput
            New-Item -ItemType Directory -Path (Split-Path -Parent $publishedPath) -Force | Out-Null
            Copy-Item -LiteralPath $generatedPath -Destination $publishedPath -Force
            $elapsed = ((Get-Date) - $started).TotalSeconds
            $result = [ordered]@{
                status = "complete_pending_identity_and_visual_review"
                created_utc = (Get-Date).ToUniversalTime().ToString("o")
                prompt_id = $queued.prompt_id
                worker = $Server
                gpu = $deviceName
                mechanism = "Z-Image Base low-denoise latent img2img texture refinement"
                source_role = "edit-source latent conditioning; not identity-reference conditioning"
                identity_lora = $null
                face_swap = $false
                model = $Model
                text_encoder = $TextEncoder
                vae = $Vae
                hashes = $actualHashes
                source_input = $sourcePath
                positive_prompt = $PositivePrompt
                negative_prompt = $NegativePrompt
                seed = $Seed
                steps = $Steps
                cfg = $Cfg
                shift = $Shift
                denoise = $Denoise
                megapixels = $Megapixels
                sampler = "res_multistep"
                scheduler = "simple"
                runtime_seconds = [math]::Round($elapsed, 3)
                comfy_output = $generatedPath
                published_output = $publishedPath
                output_sha256 = Get-Hash $publishedPath
            }
            if ($ManifestOutput) {
                $manifestPath = Join-Path $repoRoot $ManifestOutput
            } else {
                $manifestName = if ($Denoise -eq 0.15) {
                    "generation-manifest.json"
                } else {
                    "generation-manifest-denoise-0p10.json"
                }
                $manifestPath = Join-Path $repoRoot "output\zimage-texture-pass-hidream-v1\$manifestName"
            }
            New-Item -ItemType Directory -Path (Split-Path -Parent $manifestPath) -Force | Out-Null
            $resultJson = $result | ConvertTo-Json -Depth 15
            $resultJson | Set-Content -LiteralPath $manifestPath -Encoding utf8
            $resultJson
            exit 0
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for Z-Image prompt $($queued.prompt_id)."
