[CmdletBinding()]
param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [int[]]$SceneNumbers = @(1, 2, 3, 4, 5, 6, 7, 8, 9),
    [double]$LoraStrength = 1.1,
    [int]$Steps = 28,
    [double]$Guidance = 4.0,
    [UInt64]$BaseSeed = 8675410,
    [int]$TimeoutSeconds = 3600,
    [string]$RunLabel = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$loraName = "flux2-dev-identity-v2-candidates\m1tch-flux2-dev-identity-v2-s1000.safetensors"
$loraPath = Join-Path (Join-Path $ComfyRoot "models\loras") $loraName
$expectedLoraSha256 = "7c0c4f1726189c51e19c8392c12fe3e03a26bd084fffb8d84b907c966a77cc3e"
$inputRoot = Join-Path $ComfyRoot "input"
$outputRoot = Join-Path $ComfyRoot "output"
$runStamp = if ($RunLabel) { $RunLabel } else { Get-Date -Format "yyyyMMdd-HHmmss" }
$runRoot = Join-Path $repoRoot "work\flux2-dev-nine-scenes-3090\$runStamp"
$selectedRoot = Join-Path $runRoot "selected"
$manifestPath = Join-Path $runRoot "manifest.json"

$sceneMode = "SCENE IMAGE — replace the main man with Mitch"
$customPreset = "Custom — write your own scene"
$cameraStyle = "Dating app — natural smartphone"
$promptDecides = "Prompt decides"
$portraitCanvas = "Portrait — 832 × 1248"

$scenes = @(
    [ordered]@{
        Number = 1; Slug = "night-out-a"; Source = "mitch-workbench-dating-01-night-out-a.png"; SeedOffset = 1
        Prompt = "Recreate Picture 1's exact portrait composition and warm amber lounge lighting. Exactly four adults are visible. Replace only the foreground adult man seated diagonally on the caramel curved leather sofa with m1tch_person. He wears the same dark navy suit and open-collar white shirt, keeps his left arm draped along the sofa back, right hand near his pocket, extended crossed legs, and relaxed direct expression. Preserve the three background friends in their exact positions: the woman at far left holding a red drink, the man behind her in black, and the woman at rear right in a sleeveless black dress. Those three are unrelated people with clearly distinct faces; none may resemble m1tch_person. Do not add, remove, merge, or duplicate any person."
    },
    [ordered]@{
        Number = 2; Slug = "night-out-b"; Source = "mitch-workbench-dating-02-night-out-b.png"; SeedOffset = 2
        Prompt = "Recreate Picture 1's exact portrait group composition in the amber lounge. Keep all five visible adult faces, including the partial person at the far left edge. Replace only the central seated adult man with m1tch_person. He remains in the same dark suit and open-collar white shirt, seated forward with hands near his knees and looking naturally toward the camera. Preserve the woman in a black one-shoulder dress on his left, the woman in a brown dress on his right, the man leaning in at the far right, and the partial far-left person. Every friend must remain visibly unrelated with a different face, hairline, skin tone, and facial geometry. Only the central man is m1tch_person; never duplicate his identity."
    },
    [ordered]@{
        Number = 3; Slug = "ragdoll-cat"; Source = "mitch-workbench-dating-03-cat-ragdoll.png"; SeedOffset = 3
        Prompt = "Recreate Picture 1's exact quiet apartment portrait. m1tch_person stands centered in a black zip hoodie and black shirt, cradling the same very large fluffy white-and-gray Ragdoll cat horizontally across both forearms. His head tilts down toward image-right and he smiles affectionately at the cat with no eye contact with the camera. Keep the cat's head and blue eyes at image-right, hind legs and fluffy tail at image-left, both human hands supporting it naturally, the sheer curtains, and the beige leather sofa."
    },
    [ordered]@{
        Number = 4; Slug = "tabby-cat"; Source = "mitch-workbench-dating-04-cat-tabby.png"; SeedOffset = 4
        Prompt = "Recreate Picture 1's exact bright apartment portrait. m1tch_person wears the same plain black pullover hoodie and cradles the same gray-brown tabby-and-white cat close to his chest with both hands. His head is bowed down toward image-right, looking at the cat rather than the camera, while the cat looks up at him. Preserve the cat's horizontal body and tail toward image-left, the hand positions, pale sofa, white wall, beige curtain, soft window light, and the same three-quarter crop."
    },
    [ordered]@{
        Number = 5; Slug = "golfer"; Source = "mitch-workbench-dating-05-golfer-safe.png"; SeedOffset = 5
        Prompt = "Recreate Picture 1's exact full-body walking golf portrait. m1tch_person walks directly toward the camera in the center of a tropical fairway, wearing the same unbranded black long-sleeve golf polo, tailored gray trousers, and black golf shoes. Preserve the white glove on his left hand at image-right, the single golf club held down in his right hand at image-left, his stride and arm positions, the symmetrical palms, distant bunkers, clear morning light, and generous sky. Keep his entire body and both feet inside the frame."
    },
    [ordered]@{
        Number = 6; Slug = "amalfi"; Source = "mitch-workbench-dating-06-amalfi.png"; SeedOffset = 6
        Prompt = "Recreate Picture 1's exact close travel portrait at an Amalfi Coast overlook. m1tch_person stands left-of-center in the same relaxed white short-sleeve linen shirt with an open collar, smiling naturally toward the camera. Preserve his torso angle, the hand resting on the dark railing at image-right, the wristwatch, late-afternoon sunlight, Positano hillside and church dome at image-left, open blue sea at image-right, and the same waist-up smartphone framing."
    },
    [ordered]@{
        Number = 7; Slug = "lake-boat"; Source = "mitch-workbench-dating-07-lake-boat.png"; SeedOffset = 7
        Prompt = "Recreate Picture 1's exact Italian lake boat portrait. m1tch_person sits centered on the cream bow seat of a polished classic wooden motorboat, wearing the same open-collar white linen shirt with rolled sleeves, white shorts, and dark sunglasses. Preserve his seated posture with knees apart, both arms extended and hands resting on the wooden side rails, the glossy wood foreground, rippling lake, villas at image-left, steep green mountains, and the same three-quarter framing."
    },
    [ordered]@{
        Number = 8; Slug = "restaurant"; Source = "mitch-workbench-dating-08-restaurant.png"; SeedOffset = 8
        Prompt = "Recreate Picture 1's exact elegant restaurant portrait. m1tch_person sits centered at the white table in the same light-gray double-breasted blazer over a black shirt. Preserve the pose with his right hand lightly supporting his chin, direct calm eye contact, the small glowing table lamp in the left foreground, warm arched mirror light behind him, dark reflective walls, palm leaves, chair, and the same chest-to-waist crop. Keep one person only."
    },
    [ordered]@{
        Number = 9; Slug = "night-rooftop"; Source = "mitch-workbench-dating-09-night-city.png"; SeedOffset = 9
        Prompt = "Recreate Picture 1's exact night rooftop composition. m1tch_person stands centered at a glass high-rise railing in the same fitted black short-sleeve open-collar button shirt, dark trousers, and watch on his left wrist at image-right. Preserve both extended arms and both hands resting on the railing. His head must tilt downward and turn toward image-left, and his eyes must look down-left away from the camera with absolutely no eye contact. Keep the wide three-quarter-body framing, large dark teal sky, and the dense city lights far below. Do not turn his head toward image-right or toward the viewer."
    }
)

if (-not (Test-Path -LiteralPath $loraPath -PathType Leaf)) {
    throw "Missing FLUX.2 Dev LoRA: $loraPath"
}
$actualLoraSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $loraPath).Hash.ToLowerInvariant()
if ($actualLoraSha256 -ne $expectedLoraSha256) {
    throw "FLUX.2 Dev LoRA hash mismatch. Expected $expectedLoraSha256, found $actualLoraSha256."
}
if ($LoraStrength -lt 0.8 -or $LoraStrength -gt 1.1) {
    throw "LoRA strength must remain within the tested 0.8 to 1.1 range."
}

$queue = Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 10
if (@($queue.queue_running).Count -or @($queue.queue_pending).Count) {
    throw "RTX 3090 ComfyUI queue is not idle."
}
$stats = Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 10
if ([string]$stats.devices[0].name -notmatch "RTX 3090") {
    throw "Port 8188 is not the RTX 3090 worker: $($stats.devices[0].name)"
}
$nodeInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info/Flux2DevMitchSceneStudio" -TimeoutSec 20
if (-not $nodeInfo.Flux2DevMitchSceneStudio) {
    throw "Flux2DevMitchSceneStudio is unavailable on the RTX 3090 worker."
}
$sceneChoices = @($nodeInfo.Flux2DevMitchSceneStudio.input.required.scene_reference[0])

$selectedScenes = @($scenes | Where-Object { $SceneNumbers -contains [int]$_.Number })
if (-not $selectedScenes.Count) {
    throw "No valid scene numbers were selected."
}
foreach ($scene in $selectedScenes) {
    $sourcePath = Join-Path $inputRoot $scene.Source
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Missing scene source: $sourcePath"
    }
    if ($sceneChoices -notcontains $scene.Source) {
        throw "The Dev workflow has not exposed scene source '$($scene.Source)'. Restart the RTX 4070 worker after updating the custom node."
    }
}

New-Item -ItemType Directory -Path $selectedRoot -Force | Out-Null
$results = [System.Collections.Generic.List[object]]::new()

foreach ($scene in $selectedScenes) {
    $seed = [UInt64]($BaseSeed + [UInt64]$scene.SeedOffset)
    $workflow = [ordered]@{
        "1" = @{
            class_type = "Flux2DevMitchSceneStudio"
            inputs = [ordered]@{
                scene_mode = $sceneMode
                scene_reference = $scene.Source
                scene_preset = $customPreset
                custom_scene_prompt = $scene.Prompt
                camera_style = $cameraStyle
                framing = $promptDecides
                moment = $promptDecides
                canvas = $portraitCanvas
                lora_strength = $LoraStrength
                steps = $Steps
                guidance = $Guidance
                seed = $seed
            }
        }
    }
    $body = @{ prompt = $workflow; client_id = "flux2-dev-lora-nine-scenes-3090" } | ConvertTo-Json -Depth 30
    $queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 30
    if (-not $queued.prompt_id) {
        throw "ComfyUI rejected scene $($scene.Number): $($queued | ConvertTo-Json -Depth 20)"
    }
    Write-Host "Queued scene $($scene.Number) $($scene.Slug): $($queued.prompt_id)"

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $entry = $null
    do {
        Start-Sleep -Seconds 3
        $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 20
        $entry = $history.PSObject.Properties[$queued.prompt_id].Value
        if ($entry -and $entry.status.status_str -eq "error") {
            throw "Scene $($scene.Number) failed: $($entry.status.messages | ConvertTo-Json -Depth 30)"
        }
    } while ((-not $entry -or -not $entry.status.completed) -and (Get-Date) -lt $deadline)
    if (-not $entry -or -not $entry.status.completed) {
        throw "Timed out generating scene $($scene.Number)."
    }

    $image = @($entry.outputs."1".images)[0]
    if (-not $image) {
        throw "Scene $($scene.Number) completed without a saved image."
    }
    $relativeOutput = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
    $generatedPath = Join-Path $outputRoot $relativeOutput
    if (-not (Test-Path -LiteralPath $generatedPath -PathType Leaf)) {
        throw "Generated file not found for scene $($scene.Number): $generatedPath"
    }
    $selectedPath = Join-Path $selectedRoot ("{0:d2}-{1}.png" -f [int]$scene.Number, $scene.Slug)
    Copy-Item -LiteralPath $generatedPath -Destination $selectedPath -Force
    $results.Add([pscustomobject][ordered]@{
        scene = [int]$scene.Number
        slug = $scene.Slug
        source = (Join-Path $inputRoot $scene.Source)
        selected_output = $selectedPath
        comfy_output = $generatedPath
        prompt_id = [string]$queued.prompt_id
        seed = $seed
        prompt = $scene.Prompt
    })
    Write-Host "Completed scene $($scene.Number): $selectedPath"
}

$manifest = [ordered]@{
    schema_version = 1
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    purpose = "Nine supplied scene restages on the RTX 3090 using the trained FLUX.2 Dev identity LoRA."
    gpu = [string]$stats.devices[0].name
    base_model = "flux2_dev_fp8mixed.safetensors"
    text_encoder = "mistral_3_small_flux2_fp4_mixed.safetensors"
    vae = "flux2-vae.safetensors"
    lora = $loraName
    lora_path = $loraPath
    lora_sha256 = $actualLoraSha256
    lora_checkpoint_step = 1000
    lora_strength = $LoraStrength
    steps = $Steps
    guidance = $Guidance
    sampler = "euler"
    conditioning = "single scene image as native FLUX.2 Dev reference latent; scene is composition, pose, clothing, props and lighting only; Dev LoRA supplies Mitch identity"
    face_swap = $false
    mask = $false
    restoration = $false
    scenes = @($results)
}
$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Host "Manifest: $manifestPath"
Write-Host "Selected outputs: $selectedRoot"
