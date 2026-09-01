[CmdletBinding()]
param(
    [string]$LoraName = "m1tch-flux2-klein9b-identity-v1-step0900.safetensors",
    [double]$LoraStrength = 1.1,
    [string]$Server = "http://127.0.0.1:8188",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [long]$BaseSeed = 8675410,
    [int]$Steps = 50,
    [double]$Guidance = 4.0,
    [int[]]$SceneNumbers = @(1, 2, 3, 4, 5, 6, 7, 8, 9),
    [switch]$IdentityFirstPrompts,
    [string]$RunLabel = "",
    [string]$WorkRunName = "flux2-klein9b-identity-v1",
    [string]$OutputNamespace = "klein9b-v1",
    [string]$ReferenceDatasetName = "mitch-identity-stills-v3",
    [string]$ReferenceSubdirectory = "validation",
    [string[]]$ReferenceFiles = @(
        "val_01_surf_full_body.jpg",
        "val_02_body_mirror_sleeveless.jpg",
        "val_03_navy_upper_body.jpg",
        "val_04_window_small_smile.jpg",
        "val_05_balcony_opposite_angle.jpg",
        "val_06_car_daylight.jpg"
    )
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$inputRoot = Join-Path $ComfyRoot "input"
$outputRoot = Join-Path $ComfyRoot "output"
$runStamp = if ($RunLabel) { $RunLabel } else { Get-Date -Format "yyyyMMdd-HHmmss" }
$runRoot = Join-Path $repoRoot "work\$WorkRunName\nine-scenes\$runStamp"
$selectedRoot = Join-Path $runRoot "selected"
$manifestPath = Join-Path $runRoot "manifest.json"
$stagingManifestPath = Join-Path $repoRoot "work\$WorkRunName\checkpoint-staging.json"
$sourceSceneLockPath = Join-Path $repoRoot "work\zimage-base-identity-v1\scene-source-lock-test.json"
$expectedSourceSceneLockSha256 = "CCF3F4B04C23C4915ABEE2073618B9953D1F7FCCCFFE84F8276208238B52092F"
$baseModel = "flux-2-klein-base-9b-bf16.safetensors"
$textEncoder = "qwen_3_8b_fp8mixed.safetensors"
$vae = "flux2-vae.safetensors"
$trigger = "m1tch_person"

$referenceRoot = Join-Path $repoRoot "datasets\$ReferenceDatasetName"
if (-not [string]::IsNullOrWhiteSpace($ReferenceSubdirectory)) {
    $referenceRoot = Join-Path $referenceRoot $ReferenceSubdirectory
}
if ($ReferenceFiles.Count -lt 2) {
    throw "At least two held-out genuine reference photographs are required."
}
if (@($ReferenceFiles | Select-Object -Unique).Count -ne $ReferenceFiles.Count) {
    throw "ReferenceFiles contains duplicate filenames."
}
$referenceProvenance = @($ReferenceFiles | ForEach-Object {
    $reference = Join-Path $referenceRoot $_
    if (-not (Test-Path -LiteralPath $reference -PathType Leaf)) {
        throw "Held-out reference photograph is missing: $reference"
    }
    $resolved = (Resolve-Path -LiteralPath $reference).Path
    [ordered]@{
        path = $resolved
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $resolved).Hash.ToUpperInvariant()
    }
})

function Test-LocalTcpListener([int]$Port) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync('127.0.0.1', $Port)
        return ($task.Wait(1000) -and $client.Connected)
    }
    catch { return $false }
    finally { $client.Dispose() }
}

if (Test-Path -LiteralPath $runRoot) {
    throw "Run directory already exists; refusing to overwrite it: $runRoot"
}
if (-not (Test-Path -LiteralPath $sourceSceneLockPath -PathType Leaf)) {
    throw "Original scene metadata lock is missing: $sourceSceneLockPath"
}
$sourceSceneLockSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceSceneLockPath).Hash.ToUpperInvariant()
if ($sourceSceneLockSha256 -cne $expectedSourceSceneLockSha256) {
    throw "Original scene metadata lock changed: $sourceSceneLockPath"
}
$sourceSceneLock = Get-Content -Raw -LiteralPath $sourceSceneLockPath | ConvertFrom-Json
if (@($sourceSceneLock.scenes).Count -ne 9) { throw "Original scene metadata lock does not contain nine scenes." }

$scenes = @(
    [ordered]@{
        Number = 1; Slug = "night-out-a"; Label = "night out A"; Source = "mitch-workbench-dating-01-night-out-a.png"
        Prompt = "A vertical candid phone photograph in a warm amber lounge. Exactly four adults are visible. $trigger is the foreground man seated diagonally on a caramel curved leather sofa in a dark navy suit and open-collar white shirt, with his complete left arm draped along the sofa back, his complete right arm and visible right hand near his pocket, and extended crossed legs. Behind him are three unrelated friends: a woman at far left holding a red drink, a dark-haired man behind her in black, and a woman at rear right in a sleeveless black dress. Only the foreground man is $trigger. Every friend has a clearly different face, hair, and age; no duplicate person or face. Both of $trigger's arms and hands are anatomically coherent; no missing or fused limb."
    },
    [ordered]@{
        Number = 2; Slug = "night-out-b"; Label = "night out B"; Source = "mitch-workbench-dating-02-night-out-b.png"
        Prompt = "A vertical candid group phone photograph in an amber lounge. Exactly five adult faces are visible, including a partial person at the far left edge. $trigger is the central seated man in a dark suit and open-collar white shirt, leaning forward with both complete arms and both visible coherent hands near his knees while looking naturally toward the camera. An unrelated woman in a black one-shoulder dress is on his left, an unrelated woman in a brown dress is on his right, an unrelated dark-haired man leans in at far right, and a partial unrelated person is at far left. Only the central man is $trigger; all other faces must be distinct and must not resemble him. No duplicate person or face; no missing or fused limb on $trigger."
    },
    [ordered]@{
        Number = 3; Slug = "ragdoll-cat"; Label = "Ragdoll cat"; Source = "mitch-workbench-dating-03-cat-ragdoll.png"
        Prompt = "A vertical quiet apartment portrait of $trigger in a black zip hoodie and black shirt, cradling a very large fluffy white-and-gray Ragdoll cat horizontally across both forearms. His head tilts down toward image-right and he smiles affectionately at the cat with no eye contact. The cat's head and blue eyes are at image-right, its hind legs and fluffy tail at image-left, and both human hands support it naturally. Sheer curtains and a beige leather sofa fill the softly lit background. One person only, two complete arms, coherent hands and cat paws."
    },
    [ordered]@{
        Number = 4; Slug = "tabby-cat"; Label = "tabby cat"; Source = "mitch-workbench-dating-04-cat-tabby.png"
        Prompt = "A vertical bright apartment portrait of $trigger wearing a plain black pullover hoodie and cradling a gray-brown tabby-and-white cat close to his chest with both hands. His head is bowed down toward image-right, looking at the cat rather than the camera, while the cat looks up at him. The cat's horizontal body and tail extend toward image-left. Include a pale sofa, white wall, beige curtain, soft window light, and a close three-quarter crop. One person only, two complete arms, coherent hands and cat paws."
    },
    [ordered]@{
        Number = 5; Slug = "golfer"; Label = "golfer"; Source = "mitch-workbench-dating-05-golfer-safe.png"
        Prompt = "A vertical full-body walking golf portrait of $trigger walking directly toward the camera in the center of a tropical fairway. He wears an unbranded black long-sleeve golf polo, tailored gray trousers, and black golf shoes. He has a white glove on his left hand at image-right and holds one golf club down in his right hand at image-left. Keep his entire lean body, both complete arms, both hands, and both feet in frame, with symmetrical palms, distant bunkers, clear morning light, and generous sky. One person only."
    },
    [ordered]@{
        Number = 6; Slug = "amalfi"; Label = "Amalfi"; Source = "mitch-workbench-dating-06-amalfi.png"
        Prompt = "A vertical close travel portrait of $trigger at an Amalfi Coast overlook. He stands left-of-center in a relaxed white short-sleeve linen shirt with an open collar, smiling naturally toward the camera. His torso is angled and one complete hand rests on a dark railing at image-right, with a wristwatch visible. Use late-afternoon sunlight, Positano hillside and church dome at image-left, open blue sea at image-right, and waist-up smartphone framing. One person only."
    },
    [ordered]@{
        Number = 7; Slug = "lake-boat"; Label = "lake boat"; Source = "mitch-workbench-dating-07-lake-boat.png"
        Prompt = "A vertical Italian lake boat portrait of $trigger seated at the center of the cream bow seat of a polished classic wooden motorboat. He wears an open-collar white linen shirt with rolled sleeves, white shorts, and dark sunglasses. He sits with knees apart and both complete arms extended, with both hands resting on the wooden side rails. Include glossy wood in the foreground, rippling lake, villas at image-left, steep green mountains, and three-quarter framing. One person only."
    },
    [ordered]@{
        Number = 8; Slug = "restaurant"; Label = "restaurant"; Source = "mitch-workbench-dating-08-restaurant.png"
        Prompt = "A vertical elegant restaurant portrait containing one person only. $trigger sits centered at a white table in a light-gray double-breasted blazer over a black shirt. His right hand lightly supports his chin and he makes direct calm eye contact. Include a small glowing table lamp in the left foreground, warm arched mirror light behind him, dark reflective walls, palm leaves, a chair, and chest-to-waist framing. Both arms and hands are coherent."
    },
    [ordered]@{
        Number = 9; Slug = "night-rooftop"; Label = "night rooftop"; Source = "mitch-workbench-dating-09-night-city.png"
        Prompt = "A vertical night rooftop portrait of $trigger standing centered at a glass high-rise railing in a fitted black short-sleeve open-collar button shirt, dark trousers, and a watch on his left wrist at image-right. Both complete arms are extended and both hands rest on the railing. His head tilts downward and turns toward image-left, and his eyes look down-left away from the camera with absolutely no eye contact. Use wide three-quarter-body framing, a large dark teal sky, and dense city lights far below. Do not turn his head toward image-right or the viewer. One person only."
    }
)

if ($IdentityFirstPrompts) {
    foreach ($scene in $scenes) {
        switch ([int]$scene.Number) {
            7 {
                $scene.Prompt = "$trigger, one adult light-skinned man with short light-brown hair and a natural side part, sits centered on the cream bow seat of a polished classic wooden motorboat. He wears an open-collar white linen shirt with rolled sleeves, white shorts, and dark sunglasses. His knees are apart and both complete arms extend outward, with both hands resting on the wooden side rails. A rippling Italian lake, villas at image-left, steep green mountains, and glossy wood fill the vertical three-quarter portrait. Preserve $trigger's learned head shape and identity. One person only."
            }
            8 {
                $scene.Prompt = "$trigger, one adult light-skinned man with short light-brown hair and a natural side part, sits centered at a white restaurant table in a light-gray double-breasted blazer over a black shirt. Preserve $trigger's learned face, skull shape, hairline, apparent age, and natural skin. His right hand lightly supports his chin and he makes calm direct eye contact. A small glowing table lamp is in the left foreground, with warm arched mirror light behind him, dark reflective walls, palm leaves, and chest-to-waist vertical framing. One person only; both arms and hands are coherent."
            }
            9 {
                $scene.Prompt = "$trigger, one adult light-skinned man with short light-brown hair and a natural side part, stands centered at a glass high-rise railing at night. Preserve $trigger's learned face, skull shape, hairline, apparent age, and natural skin. He wears a fitted black short-sleeve open-collar button shirt, dark trousers, and a watch on his left wrist at image-right. Both complete arms extend outward and both hands rest on the railing. His head tilts downward and turns toward image-left, and his eyes look down-left away from the camera with absolutely no eye contact. Use wide three-quarter-body vertical framing, a large dark teal sky, and dense city lights far below. Never turn his head toward image-right or the viewer. One person only."
            }
        }
    }
}

$unknownSceneNumbers = @($SceneNumbers | Where-Object { $_ -notin 1..9 })
if ($unknownSceneNumbers.Count -gt 0) {
    throw "SceneNumbers contains invalid values: $($unknownSceneNumbers -join ', ')"
}
$scenes = @($scenes | Where-Object { $SceneNumbers -contains [int]$_.Number })
if ($scenes.Count -eq 0) { throw "At least one scene number is required." }

foreach ($scene in $scenes) {
    $sourcePath = Join-Path $inputRoot $scene.Source
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Missing comparison source: $sourcePath"
    }
}
$loraPath = Join-Path $ComfyRoot (Join-Path "models\loras" $LoraName)
if (-not (Test-Path -LiteralPath $loraPath -PathType Leaf)) { throw "Missing LoRA: $loraPath" }
$loraSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $loraPath).Hash.ToUpperInvariant()
if (-not (Test-Path -LiteralPath $stagingManifestPath -PathType Leaf)) {
    throw "Checkpoint-staging manifest is missing: $stagingManifestPath"
}
$stagingManifest = Get-Content -Raw -LiteralPath $stagingManifestPath | ConvertFrom-Json
$stagingRecords = @($stagingManifest.checkpoints | Where-Object { [string]$_.comfy_lora_name -ceq $LoraName })
if ($stagingRecords.Count -ne 1) {
    throw "Expected exactly one staging record for $LoraName, found $($stagingRecords.Count)."
}
if ($loraSha256 -cne [string]$stagingRecords[0].sha256) {
    throw "Nine-scene LoRA hash does not match checkpoint-staging.json for $LoraName."
}

$queue3090 = Invoke-RestMethod -Uri "$Server/queue" -TimeoutSec 10
if (@($queue3090.queue_running).Count -gt 0 -or @($queue3090.queue_pending).Count -gt 0) {
    throw "RTX 3090 ComfyUI queue is not idle."
}
$otherServer = "http://127.0.0.1:8189"
$otherStats = Invoke-RestMethod -Uri "$otherServer/system_stats" -TimeoutSec 10
$otherDevice = [string]$otherStats.devices[0].name
if ($otherDevice -notmatch "RTX 4070") { throw "$otherServer is not the RTX 4070 worker: $otherDevice" }
$queue4070 = Invoke-RestMethod -Uri "$otherServer/queue" -TimeoutSec 10
$otherWorkerRunningAtStart = @($queue4070.queue_running).Count
$otherWorkerPendingAtStart = @($queue4070.queue_pending).Count
if ($otherWorkerRunningAtStart -gt 0 -or $otherWorkerPendingAtStart -gt 0) {
    Write-Warning "RTX 4070 worker is active and will be left untouched."
}
$aux3090 = [ordered]@{ port = 8190; online = $false; device = 'offline'; running = 0; pending = 0 }
try {
    $auxStats = Invoke-RestMethod -Uri 'http://127.0.0.1:8190/system_stats' -TimeoutSec 5
    $auxQueue = Invoke-RestMethod -Uri 'http://127.0.0.1:8190/queue' -TimeoutSec 5
    $aux3090.online = $true
    $aux3090.device = [string](@($auxStats.devices)[0].name)
    $aux3090.running = @($auxQueue.queue_running).Count
    $aux3090.pending = @($auxQueue.queue_pending).Count
    if ($aux3090.device -notmatch 'RTX 3090') { throw "SAFETY: Port 8190 is not the auxiliary RTX 3090 worker: $($aux3090.device)" }
    if ($aux3090.running -gt 0 -or $aux3090.pending -gt 0) { throw 'SAFETY: Auxiliary RTX 3090 worker on port 8190 has active work; nine-scene generation will not compete with it.' }
}
catch {
    if ($_.Exception.Message -like 'SAFETY:*') { throw }
    if (Test-LocalTcpListener 8190) { throw "SAFETY: Port 8190 is listening but its RTX 3090 queue state could not be verified: $($_.Exception.Message)" }
}
$forge = [ordered]@{ port = 7860; online = $false; active = $false }
try {
    $forgeProgress = Invoke-RestMethod -Uri 'http://127.0.0.1:7860/sdapi/v1/progress?skip_current_image=true' -TimeoutSec 5
    $forge.online = $true
    $forge.active = ([double]$forgeProgress.progress -gt 0 -or -not [string]::IsNullOrWhiteSpace([string]$forgeProgress.state.job))
    if ($forge.active) { throw 'SAFETY: Forge has active RTX 3090 work; nine-scene generation will not compete with it.' }
}
catch {
    if ($_.Exception.Message -like 'SAFETY:*') { throw }
    if (Test-LocalTcpListener 7860) { throw "SAFETY: Forge port 7860 is listening but its RTX 3090 activity state could not be verified: $($_.Exception.Message)" }
}
$stats = Invoke-RestMethod -Uri "$Server/system_stats" -TimeoutSec 10
$device = [string]$stats.devices[0].name
if ($device -notmatch "RTX 3090") { throw "Selected worker is not the RTX 3090: $device" }

$requiredNodes = @(
    @{ Class = "UNETLoader"; Field = "unet_name"; Value = $baseModel },
    @{ Class = "LoraLoaderModelOnly"; Field = "lora_name"; Value = $LoraName },
    @{ Class = "CLIPLoader"; Field = "clip_name"; Value = $textEncoder },
    @{ Class = "VAELoader"; Field = "vae_name"; Value = $vae },
    @{ Class = "EmptyFlux2LatentImage"; Field = $null; Value = $null },
    @{ Class = "Flux2Scheduler"; Field = $null; Value = $null },
    @{ Class = "CFGGuider"; Field = $null; Value = $null },
    @{ Class = "SamplerCustomAdvanced"; Field = $null; Value = $null }
)
foreach ($required in $requiredNodes) {
    $nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$($required.Class)" -TimeoutSec 30
    $node = $nodeInfo.($required.Class)
    if (-not $node) { throw "Required live node is unavailable on the RTX 3090 worker: $($required.Class)" }
    if ($required.Field) {
        $choices = @($node.input.required.($required.Field)[0])
        if ($required.Value -notin $choices) {
            throw "Required live $($required.Field) value is unavailable for $($required.Class): $($required.Value)"
        }
    }
}

New-Item -ItemType Directory -Path $selectedRoot -Force | Out-Null
$records = [System.Collections.Generic.List[object]]::new()
foreach ($scene in $scenes) {
    $seed = [long]($BaseSeed + $scene.Number)
    $outputPrefix = "identity-eval/$OutputNamespace/nine-scenes/$runStamp/$($scene.Number.ToString('00'))-$($scene.Slug)"
    $workflow = @{
        "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = $baseModel; weight_dtype = "default" } }
        "2" = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $LoraName; strength_model = $LoraStrength } }
        "3" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = $textEncoder; type = "flux2" } }
        "4" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $scene.Prompt; clip = @("3", 0) } }
        "5" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("3", 0) } }
        "6" = @{ class_type = "CFGGuider"; inputs = @{ model = @("2", 0); positive = @("4", 0); negative = @("5", 0); cfg = $Guidance } }
        "7" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
        "8" = @{ class_type = "Flux2Scheduler"; inputs = @{ width = 832; height = 1216; steps = $Steps } }
        "9" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $seed } }
        "10" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = 832; height = 1216; batch_size = 1 } }
        "11" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("9", 0); guider = @("6", 0); sampler = @("7", 0); sigmas = @("8", 0); latent_image = @("10", 0) } }
        "12" = @{ class_type = "VAELoader"; inputs = @{ vae_name = $vae } }
        "13" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("11", 0); vae = @("12", 0) } }
        "14" = @{ class_type = "SaveImage"; inputs = @{ images = @("13", 0); filename_prefix = $outputPrefix } }
    }
    $body = @{ prompt = $workflow; client_id = "flux2-klein9b-lora-nine-scenes-3090-$OutputNamespace" } | ConvertTo-Json -Depth 20
    $sceneStarted = Get-Date
    $queued = Invoke-RestMethod -Uri "$Server/prompt" -Method Post -ContentType "application/json" -Body $body
    if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt_id for scene $($scene.Number)." }
    Write-Host "Queued $($scene.Number.ToString('00')) $($scene.Label), seed $seed`: $($queued.prompt_id)"
    $deadline = (Get-Date).AddMinutes(20)
    $entry = $null
    do {
        Start-Sleep -Seconds 2
        $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 10
        $entry = $history.($queued.prompt_id)
        if ($entry -and $entry.status.status_str -eq "error") {
            $entry | ConvertTo-Json -Depth 15
            throw "Klein Base 9B generation failed for scene $($scene.Number)."
        }
    } while ((-not $entry -or $entry.status.status_str -ne "success") -and (Get-Date) -lt $deadline)
    if (-not $entry -or $entry.status.status_str -ne "success") { throw "Timed out waiting for scene $($scene.Number)." }
    $image = @($entry.outputs."14".images)[0]
    $rawPath = Join-Path $outputRoot (Join-Path $image.subfolder $image.filename)
    $selectedPath = Join-Path $selectedRoot "$($scene.Number.ToString('00'))-$($scene.Slug).png"
    Copy-Item -LiteralPath $rawPath -Destination $selectedPath
    $sourceMetadata = @($sourceSceneLock.scenes | Where-Object { [int]$_.number -eq [int]$scene.Number })
    if ($sourceMetadata.Count -ne 1) { throw "Original scene metadata is not unique for scene $($scene.Number)." }
    if ((Split-Path -Leaf ([string]$sourceMetadata[0].final_target)) -cne [string]$scene.Source) {
        throw "Original scene metadata target does not match scene $($scene.Number)."
    }
    $records.Add([ordered]@{
        scene = [int]$scene.Number
        label = [string]$scene.Label
        source = (Join-Path $inputRoot $scene.Source)
        source_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $inputRoot $scene.Source)).Hash.ToUpperInvariant()
        source_used_as_conditioning = $false
        selected_output = $selectedPath
        selected_output_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $selectedPath).Hash.ToUpperInvariant()
        raw_output = $rawPath
        raw_output_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $rawPath).Hash.ToUpperInvariant()
        seed = $seed
        generation_seed = $seed
        original_source_seed = [long]$sourceMetadata[0].seed
        seconds = [math]::Round(((Get-Date) - $sceneStarted).TotalSeconds, 3)
        prompt = [string]$scene.Prompt
        generation_prompt = [string]$scene.Prompt
        original_source_prompt = [string]$sourceMetadata[0].prompt
        original_source_reference_preset = [string]$sourceMetadata[0].reference_preset
        original_source_control_strength = [double]$sourceMetadata[0].control_strength
        cross_architecture_seed_reuse = $false
    })
}

$manifest = [ordered]@{
    schema_version = 1
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    method = "FLUX.2 Klein Base 9B LoRA-only text-to-image; source scenes shown only for comparison"
    source_scene_metadata_lock = $sourceSceneLockPath
    source_scene_metadata_lock_sha256 = $sourceSceneLockSha256
    source_scene_model_family = "Z-Image source generation"
    prompt_adaptation = "Original source prompts and seeds are preserved as provenance. Klein uses fixed model-specific seeds and visually explicit prompts because random-noise seeds are not composition controls across different model architectures."
    cross_architecture_seed_reuse = $false
    gpu = $device
    model = $baseModel
    text_encoder = $textEncoder
    vae = $vae
    lora = $LoraName
    lora_sha256 = $loraSha256
    lora_path = $loraPath
    staging_manifest = $stagingManifestPath
    staging_checkpoint_step = [int]$stagingRecords[0].step
    staging_checkpoint_sha256 = [string]$stagingRecords[0].sha256
    lora_strength = $LoraStrength
    work_run_name = $WorkRunName
    output_namespace = $OutputNamespace
    trigger = $trigger
    reference_dataset_name = $ReferenceDatasetName
    reference_subdirectory = $ReferenceSubdirectory
    held_out_genuine_identity_references = $referenceProvenance
    prompt_variant = if ($IdentityFirstPrompts) { "identity-first" } else { "baseline" }
    source_scene_conditioning = $false
    reference_conditioning = $false
    identity_pass = $false
    face_swap = $false
    restoration = $false
    other_worker_activity_at_start = [ordered]@{
        port = 8189
        device = $otherDevice
        running = $otherWorkerRunningAtStart
        pending = $otherWorkerPendingAtStart
        action_taken = "none"
    }
    auxiliary_rtx_3090 = $aux3090
    forge_rtx_3090 = $forge
    other_rtx_3090_work_checked = $true
    live_node_and_model_validation_passed = $true
    settings = [ordered]@{
        width = 832
        height = 1216
        steps = $Steps
        guidance = $Guidance
        sampler = "euler"
        scheduler = "Flux2Scheduler"
    }
    scenes = @($records)
}
$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Host "Manifest: $manifestPath"
Write-Output $manifestPath
