[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8188",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$LoraName = "m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors",
    [double]$LoraStrength = 0.90,
    [double]$ReferenceMegapixels = 0.25,
    [int]$Steps = 50,
    [double]$Guidance = 4.0,
    [long]$BaseSeed = 8675410,
    [int[]]$SceneNumbers = @(1, 2, 3, 4, 5, 6, 7, 8, 9),
    [string]$RunLabel = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$inputRoot = Join-Path $ComfyRoot "input"
$outputRoot = Join-Path $ComfyRoot "output"
$runStamp = if ($RunLabel) { $RunLabel } else { Get-Date -Format "yyyyMMdd-HHmmss" }
$runRoot = Join-Path $repoRoot "work\flux2-klein9b-identity-v3-r32-dop\lora-native-reference-nine-scenes\$runStamp"
$selectedRoot = Join-Path $runRoot "selected"
$manifestPath = Join-Path $runRoot "manifest.json"

$baseModel = "flux-2-klein-base-9b-bf16.safetensors"
$textEncoder = "qwen_3_8b_fp8mixed.safetensors"
$vae = "flux2-vae.safetensors"
$trigger = "m1tch_person"
$expectedLoraSha256 = "D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC"
$stagingManifestPath = Join-Path $repoRoot "work\flux2-klein9b-identity-v3-r32-dop\checkpoint-staging-extension-to2000.json"

$referenceCatalog = [ordered]@{
    front = [ordered]@{
        file = "mitch-klein9b-ref-front-neutral-v2.jpg"
        role = "neutral frontal face and upper-body identity"
        source = "C:\projects\AI-Tools\Mitch photos\20260316_200102.jpg"
        expected_sha256 = "28DF2AE0D717A788370CC825F7BB24CF38DB9C7CDA3F66BAEFAB58BE86D8AF33"
    }
    left = [ordered]@{
        file = "mitch-klein9b-ref-left-3q-v2.jpg"
        role = "face turned toward image-left"
        source = "C:\projects\AI-Tools\Mitch photos\20260508_123009.jpg"
        expected_sha256 = "1DBEDEE1F712222F4E183D0B7648AA4739510CD86DB8B097697D2CB2C4ECEB08"
    }
    right = [ordered]@{
        file = "mitch-klein9b-ref-right-3q-v2.jpg"
        role = "face turned toward image-right"
        source = "C:\projects\AI-Tools\Mitch photos\20260508_123133.jpg"
        expected_sha256 = "2F502B5233950BB01808FC3168540D54B8CC3A09894E2895D003C10A69EAA3BA"
    }
    body = [ordered]@{
        file = "flux2-dev-ref-04-full-body.jpg"
        role = "lean full-body proportions only"
        source = "C:\projects\AI-Tools\Mitch photos\20260822_140934.jpg"
        expected_sha256 = "C5F57CC155075071F8F761356E3AD1153AA0BCE55825A52226B2A4E8A19365FC"
    }
}

$scenes = @(
    [ordered]@{
        Number = 1; Slug = "night-out-a"; Label = "night out A"; Source = "mitch-workbench-dating-01-night-out-a.png"; References = @("front")
        Prompt = "A vertical candid phone photograph in a warm amber lounge. Exactly four adults are visible. m1tch_person is the foreground man seated diagonally on a caramel curved leather sofa in a dark navy suit and open-collar white shirt, with his complete left arm draped along the sofa back, his complete right arm and visible right hand near his pocket, and extended crossed legs. Behind him are three unrelated friends: a woman at far left holding a red drink, a dark-haired man behind her in black, and a woman at rear right in a sleeveless black dress. Only the foreground man is m1tch_person. Every friend has a clearly different face, hair, and age; no duplicate person or face. Both of his arms and hands are anatomically coherent; no missing or fused limb."
    },
    [ordered]@{
        Number = 2; Slug = "night-out-b"; Label = "night out B"; Source = "mitch-workbench-dating-02-night-out-b.png"; References = @("front")
        Prompt = "A vertical candid group phone photograph in an amber lounge. Exactly five adult faces are visible, including a partial person at the far left edge. m1tch_person is the central seated man in a dark suit and open-collar white shirt, leaning forward with both complete arms and both visible coherent hands near his knees while looking naturally toward the camera. An unrelated woman in a black one-shoulder dress is on his left, an unrelated woman in a brown dress is on his right, an unrelated dark-haired man leans in at far right, and a partial unrelated person is at far left. Only the central man is m1tch_person; all other faces must be distinct and must not resemble him. No duplicate person or face; no missing or fused limb on m1tch_person."
    },
    [ordered]@{
        Number = 3; Slug = "ragdoll-cat"; Label = "Ragdoll cat"; Source = "mitch-workbench-dating-03-cat-ragdoll.png"; References = @("front", "right")
        Prompt = "A vertical quiet apartment portrait of m1tch_person in a black zip hoodie and black shirt, cradling a very large fluffy white-and-gray Ragdoll cat horizontally across both forearms. His head tilts down toward image-right and he smiles affectionately at the cat with no eye contact. The cat's head and blue eyes are at image-right, its hind legs and fluffy tail at image-left, and both human hands support it naturally. Sheer curtains and a beige leather sofa fill the softly lit background. One person only, two complete arms, coherent hands and cat paws."
    },
    [ordered]@{
        Number = 4; Slug = "tabby-cat"; Label = "tabby cat"; Source = "mitch-workbench-dating-04-cat-tabby.png"; References = @("front", "right")
        Prompt = "A vertical bright apartment portrait of m1tch_person wearing a plain black pullover hoodie and cradling a gray-brown tabby-and-white cat close to his chest with both hands. His head is bowed down toward image-right, looking at the cat rather than the camera, while the cat looks up at him. The cat's horizontal body and tail extend toward image-left. Include a pale sofa, white wall, beige curtain, soft window light, and a close three-quarter crop. One person only, two complete arms, coherent hands and cat paws."
    },
    [ordered]@{
        Number = 5; Slug = "golfer"; Label = "golfer"; Source = "mitch-workbench-dating-05-golfer-safe.png"; References = @("front", "body")
        Prompt = "A vertical full-body walking golf portrait of m1tch_person walking directly toward the camera in the center of a tropical fairway. He wears an unbranded black long-sleeve golf polo, tailored gray trousers, and black golf shoes. He has a white glove on his left hand at image-right and holds one golf club down in his right hand at image-left. Keep his entire lean body, both complete arms, both hands, and both feet in frame, with symmetrical palms, distant bunkers, clear morning light, and generous sky. One person only."
    },
    [ordered]@{
        Number = 6; Slug = "amalfi"; Label = "Amalfi"; Source = "mitch-workbench-dating-06-amalfi.png"; References = @("front", "left")
        Prompt = "A vertical close travel portrait of m1tch_person at an Amalfi Coast overlook. He stands left-of-center in a relaxed white short-sleeve linen shirt with an open collar, smiling naturally toward the camera. His torso is angled and one complete hand rests on a dark railing at image-right, with a wristwatch visible. Use late-afternoon sunlight, Positano hillside and church dome at image-left, open blue sea at image-right, and waist-up smartphone framing. One person only."
    },
    [ordered]@{
        Number = 7; Slug = "lake-boat"; Label = "lake boat"; Source = "mitch-workbench-dating-07-lake-boat.png"; References = @("front", "body")
        Prompt = "A vertical Italian lake boat portrait of m1tch_person seated at the center of the cream bow seat of a polished classic wooden motorboat. He wears an open-collar white linen shirt with rolled sleeves, white shorts, and dark sunglasses. He sits with knees apart and both complete arms extended, with both hands resting on the wooden side rails. Include glossy wood in the foreground, rippling lake, villas at image-left, steep green mountains, and three-quarter framing. One person only."
    },
    [ordered]@{
        Number = 8; Slug = "restaurant"; Label = "restaurant"; Source = "mitch-workbench-dating-08-restaurant.png"; References = @("front", "left")
        Prompt = "A vertical elegant restaurant portrait containing one person only. m1tch_person sits centered at a white table in a light-gray double-breasted blazer over a black shirt. Preserve his learned face, skull shape, hairline, apparent age, and natural skin. His right hand lightly supports his chin and he makes direct calm eye contact. Include a small glowing table lamp in the left foreground, warm arched mirror light behind him, dark reflective walls, palm leaves, a chair, and chest-to-waist framing. Both arms and hands are coherent."
    },
    [ordered]@{
        Number = 9; Slug = "night-rooftop"; Label = "night rooftop"; Source = "mitch-workbench-dating-09-night-city.png"; References = @("front", "left")
        Prompt = "A vertical night rooftop portrait of m1tch_person standing centered at a glass high-rise railing in a fitted black short-sleeve open-collar button shirt, dark trousers, and a watch on his left wrist at image-right. Both complete arms are extended and both hands rest on the railing. His head tilts downward and turns toward image-left, and his eyes look down-left away from the camera with absolutely no eye contact. Use wide three-quarter-body framing, a large dark teal sky, and dense city lights far below. Do not turn his head toward image-right or the viewer. One person only."
    }
)

function Test-LocalTcpListener([int]$Port) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync("127.0.0.1", $Port)
        return ($task.Wait(1000) -and $client.Connected)
    }
    catch { return $false }
    finally { $client.Dispose() }
}

if (Test-Path -LiteralPath $runRoot) { throw "Run directory already exists; refusing to overwrite it: $runRoot" }
$badSceneNumbers = @($SceneNumbers | Where-Object { $_ -notin 1..9 })
if ($badSceneNumbers.Count -gt 0) { throw "Invalid scene numbers: $($badSceneNumbers -join ', ')" }
$scenes = @($scenes | Where-Object { $SceneNumbers -contains [int]$_.Number })
if ($scenes.Count -eq 0) { throw "At least one scene number is required." }

$loraPath = Join-Path $ComfyRoot (Join-Path "models\loras" $LoraName)
if (-not (Test-Path -LiteralPath $loraPath -PathType Leaf)) { throw "Missing LoRA: $loraPath" }
$loraSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $loraPath).Hash.ToUpperInvariant()
if ($loraSha256 -cne $expectedLoraSha256) { throw "LoRA SHA-256 mismatch: $loraSha256" }
if (-not (Test-Path -LiteralPath $stagingManifestPath -PathType Leaf)) { throw "Missing checkpoint staging manifest: $stagingManifestPath" }
$staging = Get-Content -Raw -LiteralPath $stagingManifestPath | ConvertFrom-Json
$stagingMatch = @($staging.checkpoints | Where-Object { [string]$_.comfy_lora_name -ceq $LoraName })
if ($stagingMatch.Count -ne 1 -or [string]$stagingMatch[0].sha256 -cne $expectedLoraSha256) {
    throw "LoRA does not match the locked step-1600 staging record."
}

$referenceRecords = [ordered]@{}
foreach ($key in $referenceCatalog.Keys) {
    $record = $referenceCatalog[$key]
    $path = Join-Path $inputRoot $record.file
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing genuine reference: $path" }
    $sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToUpperInvariant()
    if ($sha256 -cne $record.expected_sha256) { throw "Reference hash mismatch: $path" }
    $referenceRecords[$key] = [ordered]@{ file = $record.file; path = $path; source = $record.source; role = $record.role; sha256 = $sha256 }
}
foreach ($scene in $scenes) {
    $sourcePath = Join-Path $inputRoot $scene.Source
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw "Missing comparison source: $sourcePath" }
}

foreach ($port in 8188, 8189) {
    $worker = "http://127.0.0.1:$port"
    try {
        $queue = Invoke-RestMethod -Uri "$worker/queue" -TimeoutSec 10
        if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
            if ($worker -eq $Server) { throw "Target RTX 3090 queue is not idle." }
            Write-Warning "RTX 4070 has active work and will be left untouched."
        }
    }
    catch {
        if ($worker -eq $Server) { throw }
        Write-Warning "Could not inspect optional worker $worker`: $($_.Exception.Message)"
    }
}
if (Test-LocalTcpListener 8190) {
    $auxStats = Invoke-RestMethod -Uri "http://127.0.0.1:8190/system_stats" -TimeoutSec 5
    $auxQueue = Invoke-RestMethod -Uri "http://127.0.0.1:8190/queue" -TimeoutSec 5
    if ([string]$auxStats.devices[0].name -notmatch "RTX 3090") { throw "Port 8190 is not an RTX 3090 worker." }
    if (@($auxQueue.queue_running).Count -gt 0 -or @($auxQueue.queue_pending).Count -gt 0) { throw "Auxiliary RTX 3090 worker has active work." }
}
if (Test-LocalTcpListener 7860) {
    $forge = Invoke-RestMethod -Uri "http://127.0.0.1:7860/sdapi/v1/progress?skip_current_image=true" -TimeoutSec 5
    if ([double]$forge.progress -gt 0 -or -not [string]::IsNullOrWhiteSpace([string]$forge.state.job)) { throw "Forge has active RTX 3090 work." }
}
$stats = Invoke-RestMethod -Uri "$Server/system_stats" -TimeoutSec 10
$device = [string]$stats.devices[0].name
if ($device -notmatch "RTX 3090") { throw "Selected worker is not the RTX 3090: $device" }

$requirements = @(
    @{ Class = "UNETLoader"; Field = "unet_name"; Value = $baseModel },
    @{ Class = "LoraLoaderModelOnly"; Field = "lora_name"; Value = $LoraName },
    @{ Class = "CLIPLoader"; Field = "clip_name"; Value = $textEncoder },
    @{ Class = "VAELoader"; Field = "vae_name"; Value = $vae },
    @{ Class = "LoadImage"; Field = $null; Value = $null },
    @{ Class = "ImageScaleToTotalPixels"; Field = $null; Value = $null },
    @{ Class = "VAEEncode"; Field = $null; Value = $null },
    @{ Class = "ReferenceLatent"; Field = $null; Value = $null },
    @{ Class = "CLIPTextEncode"; Field = $null; Value = $null },
    @{ Class = "CFGGuider"; Field = $null; Value = $null },
    @{ Class = "KSamplerSelect"; Field = $null; Value = $null },
    @{ Class = "Flux2Scheduler"; Field = $null; Value = $null },
    @{ Class = "RandomNoise"; Field = $null; Value = $null },
    @{ Class = "EmptyFlux2LatentImage"; Field = $null; Value = $null },
    @{ Class = "SamplerCustomAdvanced"; Field = $null; Value = $null },
    @{ Class = "VAEDecode"; Field = $null; Value = $null },
    @{ Class = "SaveImage"; Field = $null; Value = $null }
)
foreach ($required in $requirements) {
    $nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$($required.Class)" -TimeoutSec 30
    $node = $nodeInfo.($required.Class)
    if (-not $node) { throw "Required node unavailable: $($required.Class)" }
    if ($required.Field) {
        $choices = @($node.input.required.($required.Field)[0])
        if ($required.Value -notin $choices) { throw "Required value unavailable for $($required.Class): $($required.Value)" }
    }
}

New-Item -ItemType Directory -Path $selectedRoot -Force | Out-Null
$sceneRecords = [System.Collections.Generic.List[object]]::new()
foreach ($scene in $scenes) {
    $seed = [long]($BaseSeed + [int]$scene.Number)
    $activeKeys = @($scene.References)
    $referenceIntro = if ($activeKeys.Count -eq 1) {
        "Picture 1 is a genuine photograph of m1tch_person and defines only the exact identity of the named foreground or central man. Never create a separate person from Picture 1 and never apply his identity to any bystander. Ignore Picture 1's clothing, room, pose, and lighting. "
    }
    else {
        $roles = for ($i = 0; $i -lt $activeKeys.Count; $i++) { "Picture $($i + 1) $($referenceCatalog[$activeKeys[$i]].role)" }
        "All reference pictures show the same real man, m1tch_person. $($roles -join '; '). They define only his identity and proportions, not clothing, background, camera, pose, or lighting. The references must produce one person, never duplicate him. "
    }
    $fullPrompt = $referenceIntro + $scene.Prompt
    $workflow = [ordered]@{
        "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $baseModel; weight_dtype = "default" } }
        "2" = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $LoraName; strength_model = $LoraStrength } }
        "3" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $textEncoder; type = "flux2"; device = "default" } }
        "4" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vae } }
        "5" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $fullPrompt; clip = @("3", 0) } }
        "6" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("3", 0) } }
    }
    $positiveNode = "5"
    $negativeNode = "6"
    $nextNodeId = 20
    foreach ($key in $activeKeys) {
        $loadId = [string]$nextNodeId; $nextNodeId++
        $scaleId = [string]$nextNodeId; $nextNodeId++
        $encodeId = [string]$nextNodeId; $nextNodeId++
        $positiveReferenceId = [string]$nextNodeId; $nextNodeId++
        $negativeReferenceId = [string]$nextNodeId; $nextNodeId++
        $workflow[$loadId] = @{ class_type = "LoadImage"; inputs = @{ image = $referenceCatalog[$key].file } }
        $workflow[$scaleId] = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @($loadId, 0); upscale_method = "lanczos"; megapixels = $ReferenceMegapixels; resolution_steps = 1 } }
        $workflow[$encodeId] = @{ class_type = "VAEEncode"; inputs = @{ pixels = @($scaleId, 0); vae = @("4", 0) } }
        $workflow[$positiveReferenceId] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @($positiveNode, 0); latent = @($encodeId, 0) } }
        $workflow[$negativeReferenceId] = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @($negativeNode, 0); latent = @($encodeId, 0) } }
        $positiveNode = $positiveReferenceId
        $negativeNode = $negativeReferenceId
    }
    $workflow["90"] = @{ class_type = "CFGGuider"; inputs = @{ model = @("2", 0); positive = @($positiveNode, 0); negative = @($negativeNode, 0); cfg = $Guidance } }
    $workflow["91"] = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    $workflow["92"] = @{ class_type = "Flux2Scheduler"; inputs = @{ width = 832; height = 1216; steps = $Steps } }
    $workflow["93"] = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $seed } }
    $workflow["94"] = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = 832; height = 1216; batch_size = 1 } }
    $workflow["95"] = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("93", 0); guider = @("90", 0); sampler = @("91", 0); sigmas = @("92", 0); latent_image = @("94", 0) } }
    $workflow["96"] = @{ class_type = "VAEDecode"; inputs = @{ samples = @("95", 0); vae = @("4", 0) } }
    $prefix = "identity-eval/klein9b-v3-step1600-lora-native-ref/nine-scenes/$runStamp/$($scene.Number.ToString('00'))-$($scene.Slug)"
    $workflow["97"] = @{ class_type = "SaveImage"; inputs = @{ images = @("96", 0); filename_prefix = $prefix } }

    $body = @{ prompt = $workflow; client_id = "klein9b-v3-step1600-lora-native-reference" } | ConvertTo-Json -Depth 100
    $started = Get-Date
    $queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
    if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id for scene $($scene.Number)." }
    Write-Host "Queued scene $($scene.Number) $($scene.Label): $($queued.prompt_id)"
    $deadline = (Get-Date).AddMinutes(45)
    $entry = $null
    do {
        Start-Sleep -Seconds 2
        $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 15
        $entry = $history.PSObject.Properties[$queued.prompt_id].Value
        if ($entry -and $entry.status.status_str -eq "error") {
            throw "Generation failed for scene $($scene.Number): $($entry.status.messages | ConvertTo-Json -Depth 30)"
        }
    } while ((-not $entry -or -not $entry.status.completed) -and (Get-Date) -lt $deadline)
    if (-not $entry -or -not $entry.status.completed) { throw "Timed out waiting for scene $($scene.Number)." }
    $image = @($entry.outputs."97".images)[0]
    if (-not $image) { throw "Scene $($scene.Number) completed without an image." }
    $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
    $rawPath = Join-Path $outputRoot $relative
    $selectedPath = Join-Path $selectedRoot "$($scene.Number.ToString('00'))-$($scene.Slug).png"
    Copy-Item -LiteralPath $rawPath -Destination $selectedPath
    $activeReferenceRecords = @($activeKeys | ForEach-Object { $referenceRecords[$_] })
    $sourcePath = Join-Path $inputRoot $scene.Source
    $sceneRecords.Add([ordered]@{
        scene = [int]$scene.Number
        label = [string]$scene.Label
        source_comparison = $sourcePath
        source_comparison_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToUpperInvariant()
        source_used_as_conditioning = $false
        references = $activeReferenceRecords
        selected_output = $selectedPath
        selected_output_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $selectedPath).Hash.ToUpperInvariant()
        raw_output = $rawPath
        seed = $seed
        seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
        prompt = $fullPrompt
    })
}

$manifest = [ordered]@{
    schema_version = 1
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    method = "FLUX.2 Klein Base 9B V3 step-1600 LoRA plus native ReferenceLatent conditioning"
    research_basis = @(
        "BFL FLUX.2 Klein Base 9B model card: undistilled Base supports multi-reference editing and LoRA workflows",
        "BFL multi-reference guidance: explicitly number reference roles and use fewer references when roles may be ambiguous",
        "Official ComfyUI FLUX.2 templates: VAEEncode into ReferenceLatent conditioning"
    )
    gpu = $device
    model = $baseModel
    text_encoder = $textEncoder
    vae = $vae
    lora = $LoraName
    lora_path = $loraPath
    lora_sha256 = $loraSha256
    lora_strength = $LoraStrength
    trigger = $trigger
    identity_mechanism = "learned Base-9B identity LoRA reinforced by genuine-photo native reference latents"
    reference_policy = "one face reference for multiperson scenes; two semantically assigned references for solo/pose/body scenes"
    reference_catalog = $referenceRecords
    source_scene_conditioning = $false
    reference_conditioning = $true
    identity_pass = $false
    face_swap = $false
    restoration = $false
    sharpening = $false
    settings = [ordered]@{ width = 832; height = 1216; steps = $Steps; guidance = $Guidance; sampler = "euler"; scheduler = "Flux2Scheduler"; reference_megapixels_each = $ReferenceMegapixels }
    scenes = @($sceneRecords)
}
$manifest | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Host "Manifest: $manifestPath"
Write-Host "Selected outputs: $selectedRoot"
Write-Output $manifestPath
