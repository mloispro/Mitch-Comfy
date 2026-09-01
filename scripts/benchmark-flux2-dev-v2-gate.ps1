param(
    [ValidateSet("Gate200", "Gate300", "Gate1000", "Gate1100", "Gate1200", "FinalScreen")]
    [string]$Mode = "Gate200",
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [int]$TimeoutSeconds = 2700
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$workRoot = Join-Path $repoRoot "work\flux2-dev-identity-v2"
$trainingDirectory = "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit\output\m1tch-flux2-dev-identity-v2"
$archiveDirectory = Join-Path $workRoot "checkpoint-archives"
$candidateSubfolder = "flux2-dev-identity-v2-candidates"
$candidateDirectory = Join-Path $ComfyRoot "models\loras\$candidateSubfolder"
$runLabel = switch ($Mode) {
    "Gate200" { "gate-200" }
    "Gate300" { "gate-300" }
    "Gate1000" { "gate-1000" }
    "Gate1100" { "gate-1100" }
    "Gate1200" { "gate-1200" }
    default { "final-screen" }
}
$reportDirectory = Join-Path $workRoot "comparisons\$runLabel"
$manifestPath = Join-Path $reportDirectory "$runLabel-manifest.json"
$diagnosticPath = Join-Path $reportDirectory "insightface-diagnostic.json"
$sheetPath = Join-Path $reportDirectory "$runLabel-review-thumbnails.jpg"
$validator = Join-Path $repoRoot "scripts\validate-flux2-dev-v2-checkpoint.py"
$toolkitPython = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$comfyPython = Join-Path $ComfyRoot ".venv\Scripts\python.exe"
$optimizer = Join-Path $trainingDirectory "optimizer.pt"
$steps = 28
$guidance = 4.0
$width = 832
$height = 1248
$baseSeed = [UInt64]8675310

foreach ($path in @($validator, $toolkitPython, $comfyPython, $optimizer)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required file is missing: $path" }
}
$queue = Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 10
if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) { throw "ComfyUI queue is not idle." }
$stats = Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 10
if ([string]$stats.devices[0].name -notmatch "RTX 3090") { throw "Gate benchmark must use the RTX 3090 worker at 8188." }

$candidateSteps = switch ($Mode) {
    "Gate200" { @(100, 150, 200) }
    "Gate300" { @(250, 300) }
    "Gate1000" { @(800, 900, 1000) }
    "Gate1100" { @(900, 1000, 1100) }
    "Gate1200" { @(1000, 1100, 1200) }
    default { @(250, 300, 350, 400, 450, 500) }
}
$finalStep = switch ($Mode) {
    "Gate200" { 200 }
    "Gate300" { 300 }
    "Gate1000" { 1000 }
    "Gate1100" { 1100 }
    "Gate1200" { 1200 }
    default { 500 }
}
$sources = [ordered]@{}
foreach ($candidateStep in $candidateSteps) {
    $candidateKey = "s$($candidateStep.ToString('0000'))"
    $filename = if ($Mode -in @("Gate1000", "Gate1100", "Gate1200")) {
        "m1tch-flux2-dev-identity-v2-step-$($candidateStep.ToString('0000')).safetensors"
    } elseif ($candidateStep -eq $finalStep) {
        "m1tch-flux2-dev-identity-v2.safetensors"
    } else {
        "m1tch-flux2-dev-identity-v2_$($candidateStep.ToString('000000000')).safetensors"
    }
    $sources[$candidateKey] = Join-Path $(if ($Mode -in @("Gate1000", "Gate1100", "Gate1200")) { $archiveDirectory } else { $trainingDirectory }) $filename
}
New-Item -ItemType Directory -Path $candidateDirectory, $reportDirectory -Force | Out-Null
$staged = [System.Collections.Generic.List[object]]::new()
foreach ($entry in $sources.GetEnumerator()) {
    if (-not (Test-Path -LiteralPath $entry.Value -PathType Leaf)) { throw "Gate checkpoint is missing: $($entry.Value)" }
    $expectedStep = [int]$entry.Key.Substring(1)
    $validationJson = Join-Path $workRoot "checkpoint-validation\$runLabel-$($entry.Key).json"
    & $toolkitPython $validator $entry.Value --expected-step $expectedStep --expected-modules 128 --json-output $validationJson
    if ($LASTEXITCODE -ne 0) { throw "Candidate validation failed: $($entry.Key)" }
    $destinationName = "m1tch-flux2-dev-identity-v2-$($entry.Key).safetensors"
    $destination = Join-Path $candidateDirectory $destinationName
    Copy-Item -LiteralPath $entry.Value -Destination $destination -Force
    $staged.Add([pscustomobject]@{
        label = $entry.Key
        step = $expectedStep
        source = $entry.Value
        staged_name = "$candidateSubfolder\$destinationName"
        staged_path = $destination
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash.ToLowerInvariant()
    })
}

$requiredNodes = @("UNETLoader", "LoraLoaderModelOnly", "CLIPLoader", "CLIPTextEncode", "FluxGuidance", "BasicGuider", "KSamplerSelect", "Flux2Scheduler", "RandomNoise", "EmptyFlux2LatentImage", "SamplerCustomAdvanced", "VAELoader", "VAEDecode", "SaveImage")
foreach ($node in $requiredNodes) {
    $info = Invoke-RestMethod -Uri "$ComfyUrl/object_info/$node" -TimeoutSec 20
    if (-not $info.PSObject.Properties[$node]) { throw "Required node is unavailable: $node" }
}

$scenes = @(
    [ordered]@{
        label = "portrait"
        seed = $baseSeed
        prompt = "An ordinary unedited smartphone portrait of m1tch_person, an adult man, seated at a neighborhood cafe in soft open shade, head and shoulders, navy crew-neck T-shirt, relaxed natural half-smile, looking at the camera, realistic pores and fine facial detail, believable phone-camera exposure, no beauty filter."
    },
    [ordered]@{
        label = "waist-up-social"
        seed = $baseSeed + 1
        prompt = if ($Mode -eq "Gate200") {
            "A candid waist-up social smartphone photo of m1tch_person, an adult man, standing at a casual backyard gathering in late-afternoon daylight, pale blue open-collar shirt, relaxed expression, looking toward a friend beside the camera, natural skin texture, ordinary phone-camera depth and exposure."
        } else {
            "An ordinary candid waist-up smartphone photo of one clearly featured person: m1tch_person, an adult man, standing alone in the foreground at a casual backyard gathering in late-afternoon daylight. He is the only foreground subject, wearing a pale blue open-collar shirt and looking directly toward the camera with a relaxed neutral expression. Any other guests are distant, small, softly blurred background figures; no foreground friend, no occlusion, no second prominent face. Natural skin texture, ordinary phone-camera depth and exposure."
        }
    }
)

function Invoke-Scene {
    param([string]$Variant, [string]$LoraName, [System.Collections.IDictionary]$Scene)
    $modelRef = @("1", 0)
    $workflow = [ordered]@{
        "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = "flux2_dev_fp8mixed.safetensors"; weight_dtype = "default" } }
    }
    if ($LoraName) {
        $workflow["2"] = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $LoraName; strength_model = 1.0 } }
        $modelRef = @("2", 0)
    }
    $workflow["3"] = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = "mistral_3_small_flux2_fp4_mixed.safetensors"; type = "flux2"; device = "default" } }
    $workflow["4"] = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $Scene.prompt; clip = @("3", 0) } }
    $workflow["5"] = @{ class_type = "FluxGuidance"; inputs = @{ conditioning = @("4", 0); guidance = $guidance } }
    $workflow["6"] = @{ class_type = "BasicGuider"; inputs = @{ model = $modelRef; conditioning = @("5", 0) } }
    $workflow["7"] = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    $workflow["8"] = @{ class_type = "Flux2Scheduler"; inputs = @{ width = $width; height = $height; steps = $steps } }
    $workflow["9"] = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Scene.seed } }
    $workflow["10"] = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $width; height = $height; batch_size = 1 } }
    $workflow["11"] = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("9", 0); guider = @("6", 0); sampler = @("7", 0); sigmas = @("8", 0); latent_image = @("10", 0) } }
    $workflow["12"] = @{ class_type = "VAELoader"; inputs = @{ vae_name = "flux2-vae.safetensors" } }
    $workflow["13"] = @{ class_type = "VAEDecode"; inputs = @{ samples = @("11", 0); vae = @("12", 0) } }
    $workflow["14"] = @{ class_type = "SaveImage"; inputs = @{ images = @("13", 0); filename_prefix = "identity-eval/flux2-dev-v2/$runLabel-$Variant-$($Scene.label)" } }

    $body = @{ prompt = $workflow; client_id = "flux2-dev-v2-gate" } | ConvertTo-Json -Depth 30
    $queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
    if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id." }
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        Start-Sleep -Seconds 2
        $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 15
        $entry = $history.PSObject.Properties[$queued.prompt_id].Value
        if ($entry -and $entry.status.status_str -eq "error") { throw "Generation failed: $($entry.status.messages | ConvertTo-Json -Depth 15)" }
        if ($entry -and $entry.status.completed) {
            $image = @($entry.outputs."14".images)[0]
            $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
            return Join-Path (Join-Path $ComfyRoot "output") $relative
        }
    } while ((Get-Date) -lt $deadline)
    throw "Timed out generating $Variant/$($Scene.label)."
}

$variants = [System.Collections.Generic.List[object]]::new()
if ($Mode -eq "Gate200") {
    $baseOutputs = [ordered]@{}
    foreach ($scene in $scenes) { $baseOutputs[$scene.label] = Invoke-Scene -Variant "base" -LoraName "" -Scene $scene }
    $variants.Add([pscustomobject]@{ label = "base-only"; lora = $null; outputs = $baseOutputs })
}
foreach ($candidate in $staged) {
    $outputs = [ordered]@{}
    foreach ($scene in $scenes) { $outputs[$scene.label] = Invoke-Scene -Variant $candidate.label -LoraName $candidate.staged_name -Scene $scene }
    $variants.Add([pscustomobject]@{ label = $candidate.label; lora = $candidate.staged_name; outputs = $outputs })
}

if ($Mode -eq "Gate200") {
    $v1ReportPath = Join-Path $repoRoot "work\flux2-dev-identity-v1\benchmarks\flux2-dev-identity-v1-candidates-m1tch-flux2-dev-identity-v1-s0900.safetensors-s1.00-20260825-225243.json"
    $v1Report = Get-Content -Raw -LiteralPath $v1ReportPath | ConvertFrom-Json
    $variants.Insert(1, [pscustomobject]@{
        label = "v1-rejected-s0900"
        lora = "rejected-v1"
        outputs = [ordered]@{
            portrait = $v1Report.benchmark.raw_outputs.portrait
            "waist-up-social" = $v1Report.benchmark.raw_outputs."waist-up-social"
        }
    })
}

$heldOuts = @(Get-ChildItem -LiteralPath (Join-Path $repoRoot "datasets\mitch-identity-stills-v3\validation") -Filter "*.jpg" -File | Sort-Object Name | ForEach-Object { [pscustomobject]@{ label = $_.BaseName; path = $_.FullName; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant() } })
if ($heldOuts.Count -ne 6) { throw "Expected six held-out photographs." }
$manifest = [ordered]@{
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    purpose = switch ($Mode) {
        "Gate200" { "Step-200 manual identity-direction gate; no checkpoint is promotion eligible." }
        "Gate300" { "Bounded step-300 identity-direction gate comparing steps 250 and 300; no checkpoint is promotion eligible." }
        "Gate1000" { "Step-1000 pause review comparing steps 800, 900, and 1000 to determine whether identity is improving, plateauing, or overtraining; no checkpoint is promotion eligible without Mitch's approval." }
        "Gate1100" { "Step-1100 pause review comparing steps 900, 1000, and 1100 to determine whether identity has plateaued or begun overtraining; no checkpoint is promotion eligible without Mitch's approval." }
        "Gate1200" { "Final step-1200 review comparing steps 1000, 1100, and 1200 to select the strongest checkpoint; publication still requires Mitch's approval." }
        default { "Final portrait and waist-up screening; manual review chooses the best three for full evaluation." }
    }
    settings = [ordered]@{ strength = 1.0; sampler = "euler"; steps = $steps; guidance = $guidance; width = $width; height = $height; seeds = @($baseSeed, $baseSeed + 1); reference_conditioning = $false; face_swap = $false; masks = $false; restoration = $false; post_processing = $false }
    candidates = $staged
    held_outs = $heldOuts
    review_variants = $variants
    manual_review = [ordered]@{ decision = "pending"; required = @("unmistakable identity at full size", "unmistakable identity at thumbnail", "hairline", "brow and eye spacing", "nose", "mouth", "jaw and chin", "apparent age", "skin texture", "absence of v1 wrong-face archetype") }
    insightface_role = "diagnostic ranking only; it cannot approve or promote a checkpoint"
}
$manifest | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $manifestPath -Encoding utf8

$evalArgs = [System.Collections.Generic.List[string]]::new()
$evalArgs.Add((Join-Path $repoRoot "scripts\evaluate-face-likeness.py"))
foreach ($reference in $heldOuts) { $evalArgs.Add("--reference"); $evalArgs.Add($reference.path) }
foreach ($variant in $variants) {
    foreach ($scene in $scenes) {
        $evalArgs.Add("--candidate"); $evalArgs.Add($variant.outputs[$scene.label])
        $evalArgs.Add("--candidate-label"); $evalArgs.Add("$($variant.label)-$($scene.label)")
    }
}
$evalArgs.Add("--json-output"); $evalArgs.Add($diagnosticPath)
& $comfyPython @evalArgs
if ($LASTEXITCODE -ne 0) { throw "Local diagnostic failed." }
& $comfyPython (Join-Path $repoRoot "scripts\build-flux2-dev-v2-gate-sheet.py") $manifestPath $sheetPath
if ($LASTEXITCODE -ne 0) { throw "Thumbnail sheet build failed." }

Write-Host "$Mode package: $manifestPath"
Write-Host "Thumbnail sheet: $sheetPath"
Write-Host "All full-size paths are recorded in the manifest. Manual review is required."
