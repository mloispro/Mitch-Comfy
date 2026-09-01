param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [ValidateSet("HighValue", "AttractiveCandids")]
    [string]$SceneSet = "HighValue",
    [string]$LoraName = "flux2-dev-identity-v2-candidates\m1tch-flux2-dev-identity-v2-s1000.safetensors",
    [double]$LoraStrength = 1.0,
    [int]$Steps = 28,
    [double]$Guidance = 4.0,
    [int]$Width = 832,
    [int]$Height = 1248,
    [UInt64]$BaseSeed = 62419820,
    [int]$TimeoutSeconds = 2700
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$category = if ($SceneSet -eq "AttractiveCandids") { "attractive-candids" } else { "high-value-scenes" }
$runLabel = if ($SceneSet -eq "AttractiveCandids") { "attractive-candid" } else { "high-value" }
$workRoot = Join-Path $repoRoot "work\flux2-dev-identity-v2\$category"
$runId = "$runLabel-$((Get-Date).ToString('yyyyMMdd-HHmmss'))"
$runDirectory = Join-Path $workRoot $runId
$manifestPath = Join-Path $runDirectory "$runId-manifest.json"
$diagnosticPath = Join-Path $runDirectory "$runId-face-diagnostic.json"
$sheetPath = Join-Path $runDirectory "$runId-contact-sheet.jpg"
$loraPath = Join-Path (Join-Path $ComfyRoot "models\loras") $LoraName
$expectedSha256 = "7c0c4f1726189c51e19c8392c12fe3e03a26bd084fffb8d84b907c966a77cc3e"
$outputPrefix = "identity-eval/flux2-dev-v2/$category/$runId"

if (-not (Test-Path -LiteralPath $loraPath -PathType Leaf)) {
    throw "Protected step-1000 LoRA is not staged: $loraPath"
}
$actualSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $loraPath).Hash.ToLowerInvariant()
if ($actualSha256 -ne $expectedSha256) {
    throw "Step-1000 LoRA hash mismatch. Expected $expectedSha256, found $actualSha256."
}
if ($Width * $Height -lt 900000 -or $Width * $Height -gt 1200000) {
    throw "Resolution must remain approximately one megapixel."
}

$queue = Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 10
if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
    throw "ComfyUI queue is not idle at $ComfyUrl."
}
$stats = Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 10
if ([string]$stats.devices[0].name -notmatch "RTX 3090") {
    throw "High-value generation must use the RTX 3090 worker at port 8188."
}

$requiredNodes = @(
    "UNETLoader", "LoraLoaderModelOnly", "CLIPLoader", "CLIPTextEncode",
    "FluxGuidance", "BasicGuider", "KSamplerSelect", "Flux2Scheduler",
    "RandomNoise", "EmptyFlux2LatentImage", "SamplerCustomAdvanced",
    "VAELoader", "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $nodeInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info/$nodeName" -TimeoutSec 20
    if (-not $nodeInfo.PSObject.Properties[$nodeName]) {
        throw "Required node is unavailable: $nodeName"
    }
}
$loraInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info/LoraLoaderModelOnly" -TimeoutSec 20
if (@($loraInfo.LoraLoaderModelOnly.input.required.lora_name[0]) -notcontains $LoraName) {
    throw "ComfyUI has not discovered the protected step-1000 LoRA: $LoraName"
}

$highValueScenes = @(
    [ordered]@{
        label = "founder-editorial"
        seed = $BaseSeed
        prompt = "A premium but authentic personal-brand portrait of m1tch_person, an adult man, photographed waist-up in a bright modern creative studio beside a large window. He wears a tailored charcoal overshirt over a clean white crew-neck shirt, relaxed confident posture, direct eye contact, subtle natural half-smile. Soft daylight, realistic pores and skin texture, 50mm natural perspective, refined editorial composition, believable color, no beauty retouching. He is the only prominent person; the quiet workspace background is softly out of focus."
    },
    [ordered]@{
        label = "rooftop-travel"
        seed = $BaseSeed + 1
        prompt = "A polished candid travel photograph of m1tch_person, an adult man, framed from mid-torso upward on an elegant rooftop terrace overlooking a coastal city at golden hour. He wears a pale sand linen shirt with an open collar, leaning lightly on the railing, looking directly toward the camera with a calm relaxed expression. Natural warm sunlight, true facial texture, realistic hair, premium travel-magazine atmosphere, subtle depth of field. He is the single clear subject; distant guests are tiny and unrecognizable."
    },
    [ordered]@{
        label = "upscale-dinner"
        seed = $BaseSeed + 2
        prompt = "An upscale yet believable evening lifestyle photo of m1tch_person, an adult man, seated at a modern restaurant table, framed chest-up. He wears a dark navy open-collar shirt and looks toward the camera with a warm restrained smile. Soft amber practical lights and gentle window fill illuminate his face clearly, with natural pores, realistic apparent age, and unretouched skin. Elegant restaurant details fall softly out of focus; no other prominent face and no person beside him."
    },
    [ordered]@{
        label = "city-editorial"
        seed = $BaseSeed + 3
        prompt = "A high-end street-style portrait of m1tch_person, an adult man, photographed from the waist up on a clean downtown sidewalk just after sunrise. He wears a fitted black bomber jacket over a muted gray shirt, standing naturally with relaxed shoulders and looking straight into the camera. Crisp soft daylight, realistic skin and hair, subtle urban depth, premium menswear editorial quality without retouching. He is the only foreground subject; pedestrians are distant and softly blurred."
    },
    [ordered]@{
        label = "weekend-lake"
        seed = $BaseSeed + 4
        prompt = "A natural aspirational weekend portrait of m1tch_person, an adult man, framed from mid-torso upward at the end of a wooden lake dock in clear morning light. He wears a fitted heather-gray crew-neck T-shirt, relaxed stance, direct eye contact, and a small genuine smile. Calm water and green shoreline behind him, realistic phone-camera sharpness, believable skin texture and facial proportions, fresh but unfiltered color. He is alone and clearly featured."
    }
)

$attractiveCandidScenes = @(
    [ordered]@{
        label = "cooking-candid"
        seed = $BaseSeed
        prompt = "A genuinely attractive candid lifestyle photograph of m1tch_person, an adult man, preparing a simple dinner in a tasteful modern home kitchen at early evening, framed from mid-torso upward. He wears a fitted dark navy crew-neck T-shirt with the sleeves naturally hugging his arms. His head is turned about twenty-five degrees and his eyes look down and off-camera toward the food he is plating, with a relaxed subtle smile; he is definitely not looking at the camera. One hand rests naturally near a wooden cutting board with fresh ingredients. Soft window daylight mixed with warm kitchen light, quietly confident and capable mood, realistic skin pores, true apparent age, natural hair, believable candid 50mm photography, no beauty retouching. He is alone and the kitchen is clean but lived-in."
    },
    [ordered]@{
        label = "golden-hour-candid"
        seed = $BaseSeed + 1
        prompt = "An effortlessly attractive candid travel photograph of m1tch_person, an adult man, framed from the waist up on an elegant rooftop terrace during golden hour. He wears a pale blue linen shirt with the top button open and the sleeves casually rolled. His body faces mostly toward the camera, but his head is turned about thirty degrees and his eyes look clearly off-camera toward the sunset, with a warm restrained smile as if listening to someone nearby; he is not looking at the camera. Soft directional sunlight defines his face without harsh shadows, realistic skin and hair, confident relaxed posture, premium but authentic lifestyle photography, subtle city skyline blur. He is the only prominent person; no companion, no foreground stranger, and no second prominent face."
    }
)
$scenes = if ($SceneSet -eq "AttractiveCandids") { $attractiveCandidScenes } else { $highValueScenes }

function Invoke-Scene {
    param([System.Collections.IDictionary]$Scene)

    $workflow = [ordered]@{
        "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = "flux2_dev_fp8mixed.safetensors"; weight_dtype = "default" } }
        "2" = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $LoraName; strength_model = $LoraStrength } }
        "3" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = "mistral_3_small_flux2_fp4_mixed.safetensors"; type = "flux2"; device = "default" } }
        "4" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $Scene.prompt; clip = @("3", 0) } }
        "5" = @{ class_type = "FluxGuidance"; inputs = @{ conditioning = @("4", 0); guidance = $Guidance } }
        "6" = @{ class_type = "BasicGuider"; inputs = @{ model = @("2", 0); conditioning = @("5", 0) } }
        "7" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
        "8" = @{ class_type = "Flux2Scheduler"; inputs = @{ width = $Width; height = $Height; steps = $Steps } }
        "9" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Scene.seed } }
        "10" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = $Width; height = $Height; batch_size = 1 } }
        "11" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("9", 0); guider = @("6", 0); sampler = @("7", 0); sigmas = @("8", 0); latent_image = @("10", 0) } }
        "12" = @{ class_type = "VAELoader"; inputs = @{ vae_name = "flux2-vae.safetensors" } }
        "13" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("11", 0); vae = @("12", 0) } }
        "14" = @{ class_type = "SaveImage"; inputs = @{ images = @("13", 0); filename_prefix = "$outputPrefix-$($Scene.label)" } }
    }

    $body = @{ prompt = $workflow; client_id = "flux2-dev-v2-high-value" } | ConvertTo-Json -Depth 30
    $queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
    if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id for $($Scene.label)." }
    Write-Host "Queued $($Scene.label): $($queued.prompt_id)"

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        Start-Sleep -Seconds 2
        $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 15
        $entry = $history.PSObject.Properties[$queued.prompt_id].Value
        if ($entry -and $entry.status.status_str -eq "error") {
            throw "Generation failed for $($Scene.label): $($entry.status.messages | ConvertTo-Json -Depth 20)"
        }
        if ($entry -and $entry.status.completed) {
            $image = @($entry.outputs."14".images)[0]
            if (-not $image) { throw "Generation completed without an image for $($Scene.label)." }
            $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
            return Join-Path (Join-Path $ComfyRoot "output") $relative
        }
    } while ((Get-Date) -lt $deadline)
    throw "Timed out generating $($Scene.label)."
}

New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null
$outputs = [ordered]@{}
foreach ($scene in $scenes) {
    $outputs[$scene.label] = Invoke-Scene -Scene $scene
}

$references = @(Get-ChildItem -LiteralPath (Join-Path $repoRoot "datasets\mitch-identity-stills-v3\validation") -Filter "*.jpg" -File | Sort-Object Name)
if ($references.Count -ne 6) { throw "Expected six genuine held-out photos; found $($references.Count)." }

$manifest = [ordered]@{
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    purpose = if ($SceneSet -eq "AttractiveCandids") {
        "Attractive off-camera candid trial using the manually selected step-1000 FLUX.2 Dev identity LoRA candidate."
    } else {
        "Polished high-value scene trial using the manually selected step-1000 FLUX.2 Dev identity LoRA candidate."
    }
    publication_status = "not published; manual review required"
    lora = [ordered]@{
        name = $LoraName
        path = $loraPath
        sha256 = $actualSha256
        checkpoint_step = 1000
        strength = $LoraStrength
    }
    generation = [ordered]@{
        base_model = "flux2_dev_fp8mixed.safetensors"
        text_encoder = "mistral_3_small_flux2_fp4_mixed.safetensors"
        vae = "flux2-vae.safetensors"
        sampler = "euler"
        steps = $Steps
        guidance = $Guidance
        width = $Width
        height = $Height
        reference_conditioning = $false
        face_swap = $false
        masks = $false
        restoration = $false
        post_processing = $false
    }
    scenes = $scenes
    outputs = $outputs
    held_outs = @($references | ForEach-Object { $_.FullName })
    manual_review = [ordered]@{
        status = "pending"
        checks = @("full-size identity", "thumbnail identity", "apparent age", "hairline", "facial geometry", "skin texture", "scene integration")
    }
}
$manifest | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $manifestPath -Encoding utf8

$evalArgs = [System.Collections.Generic.List[string]]::new()
$evalArgs.Add((Join-Path $repoRoot "scripts\evaluate-face-likeness.py"))
foreach ($reference in $references) { $evalArgs.Add("--reference"); $evalArgs.Add($reference.FullName) }
foreach ($scene in $scenes) {
    $evalArgs.Add("--candidate")
    $evalArgs.Add($outputs[$scene.label])
    $evalArgs.Add("--candidate-label")
    $evalArgs.Add($scene.label)
}
$evalArgs.Add("--json-output")
$evalArgs.Add($diagnosticPath)
& (Join-Path $ComfyRoot ".venv\Scripts\python.exe") @evalArgs
if ($LASTEXITCODE -ne 0) { Write-Warning "Face diagnostic returned exit code $LASTEXITCODE; manual review remains authoritative." }

& (Join-Path $ComfyRoot ".venv\Scripts\python.exe") (Join-Path $repoRoot "scripts\build-flux2-dev-v2-high-value-sheet.py") $manifestPath $sheetPath
if ($LASTEXITCODE -ne 0) { throw "Contact-sheet generation failed." }

Write-Host "Manifest: $manifestPath"
Write-Host "Diagnostic: $diagnosticPath"
Write-Host "Contact sheet: $sheetPath"
