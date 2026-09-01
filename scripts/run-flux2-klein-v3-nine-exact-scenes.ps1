param(
    [int[]]$SceneNumbers = @(1, 2, 3, 4, 5, 6, 7, 8, 9),
    [string]$ComfyUrl = "http://127.0.0.1:8189",
    [ValidateSet("internal_face_geometry_lock", "full_head_identity_lock")]
    [string]$EditRegion = "internal_face_geometry_lock"
)

$ErrorActionPreference = "Stop"
$inputRoot = "C:\projects\AI-Tools\ComfyUI\input"
$scenes = @(
    @{ Number = 1; Input = "mitch-workbench-dating-01-night-out-a.png"; Index = 2; Context = "the supplied four-person nighttime lounge photograph. Preserve exactly the same four people, couch, clothing, body poses, hands, crop, warm lighting, and background. Only the third visible face from image-left—the foreground man seated on the tan couch—is Mitch. The other three people must remain unrelated and visually unchanged; never copy Mitch into any friend." },
    @{ Number = 2; Input = "mitch-workbench-dating-02-night-out-b.png"; Index = 1; Context = "the supplied four-person nighttime social photograph. Preserve exactly the same four visible people, their positions, clothing, gestures, drinks, crop, lighting, furniture, and background. Only the second visible face from image-left—the central primary man—is Mitch. The other three people must remain unrelated and visually unchanged; never copy Mitch into any friend." },
    @{ Number = 3; Input = "mitch-workbench-dating-03-cat-ragdoll.png"; Index = 0; Context = "the supplied home photograph with the ragdoll cat. Preserve the exact cat, its markings and body position, the man's seated pose, hand and arm contact with the cat, gaze direction, clothes, furniture, crop, lighting, and room." },
    @{ Number = 4; Input = "mitch-workbench-dating-04-cat-tabby.png"; Index = 0; Context = "the supplied home photograph with the tabby cat. Preserve the exact cat, its markings and body position, the man's pose, hand and arm contact with the cat, gaze direction, clothes, furniture, crop, lighting, and room." },
    @{ Number = 5; Input = "mitch-workbench-dating-05-golfer-safe.png"; Index = 0; Context = "the supplied tropical golf-course photograph. Preserve the man's exact walking direction, full-body stride, limbs, hands, golf club, glove, cap, clothing, crop, grass, palms, course depth, sunlight, and shadows." },
    @{ Number = 6; Input = "mitch-workbench-dating-06-amalfi.png"; Index = 0; Context = "the supplied Amalfi Coast balcony photograph. Preserve the exact close three-quarter framing, body angle, railing pose, white shirt, arms and hands, coast, buildings, water, crop, daylight, and depth." },
    @{ Number = 7; Input = "mitch-workbench-dating-07-lake-boat.png"; Index = 0; Context = "the supplied Italian lake boat photograph. Preserve the exact waist-up braced pose, sunglasses, white linen shirt, both hands on the boat sides, crop, lake, shoreline, mountains, daylight, and reflections." },
    @{ Number = 8; Input = "mitch-workbench-dating-08-restaurant.png"; Index = 0; Context = "the supplied elegant restaurant photograph. Preserve the exact seated chin-on-hand pose, elbow and hand geometry, fitted dark blazer, table, glassware, crop, warm lighting, restaurant depth, and background." },
    @{ Number = 9; Input = "mitch-workbench-dating-09-night-city.png"; Index = 0; Context = "the supplied nighttime high-rise balcony photograph. Preserve the man leaning against the glass railing, both arms and hands contacting the rail, black open-collar shirt, dark trousers, wristwatch, flash-lit body, glass panels, and exact skyline. The head is pitched downward and turned toward image-left; the eyes look down and away toward image-left, never at the camera." }
)

$stats = Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 15
if (($stats.devices.name -join " ") -notmatch "RTX 4070") {
    throw "$ComfyUrl is not the RTX 4070 worker."
}
$queue = Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 15
if (@($queue.queue_running).Count -or @($queue.queue_pending).Count) {
    throw "The RTX 4070 queue is not empty."
}
$objectInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info/Flux2ExactSceneIdentityV3" -TimeoutSec 30
if (-not ($objectInfo.PSObject.Properties.Name -contains "Flux2ExactSceneIdentityV3")) {
    throw "The FLUX.2 Klein v3 exact-scene node is not loaded."
}

$selected = @($scenes | Where-Object { $SceneNumbers -contains $_.Number })
if (-not $selected.Count) {
    throw "No valid scene numbers were selected."
}

$rows = foreach ($scene in $selected) {
    $scenePath = Join-Path $inputRoot $scene.Input
    if (-not (Test-Path -LiteralPath $scenePath)) {
        throw "Missing scene input: $scenePath"
    }
    $inputs = @{
        scene_plate_path = $scenePath
        face_reference = "20260815_165446.jpg"
        reference_2 = "20260508_123156.jpg"
        reference_3 = "20260818_173106.jpg"
        reference_4 = "No additional reference"
        target_face_index_left_to_right = $scene.Index
        denoise_strength = 0.65
        lora_strength = 1.20
        seed = 8675310 + $scene.Number
        scene_context = $scene.Context
        edit_region = $EditRegion
    }
    $body = @{
        prompt = @{
            "1" = @{
                class_type = "Flux2ExactSceneIdentityV3"
                inputs = $inputs
            }
        }
        client_id = "mitch-klein-v3-exact-scene-$($scene.Number)"
    } | ConvertTo-Json -Depth 20
    $submission = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 30
    $promptId = $submission.prompt_id
    if (-not $promptId) {
        throw "No prompt ID returned for scene $($scene.Number)."
    }
    Write-Output "SCENE_$($scene.Number)_PROMPT_ID=$promptId"

    while ($true) {
        Start-Sleep -Seconds 3
        $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$promptId" -TimeoutSec 15
        $entry = $history.PSObject.Properties[$promptId].Value
        if ($entry -and $entry.status.completed) {
            if ($entry.status.status_str -ne "success") {
                $entry.status.messages | ConvertTo-Json -Depth 30
                throw "Scene $($scene.Number) failed."
            }
            $nodeOutput = $entry.outputs.PSObject.Properties["1"].Value
            $image = @($nodeOutput.images)[0]
            $message = @($nodeOutput.text)[0]
            Write-Output "SCENE_$($scene.Number)_STATUS=$message"
            [ordered]@{
                scene = $scene.Number
                source = $scenePath
                target_face_index_left_to_right = $scene.Index
                prompt_id = $promptId
                output_subfolder = $image.subfolder
                output_filename = $image.filename
                status_message = $message
            }
            break
        }
    }
}

$manifestPath = "C:\projects\AI-Tools\Mitch-Comfy\work\exact-scene-klein-v3\latest-run.json"
$manifest = [ordered]@{
    created_at = (Get-Date).ToString("o")
    method = "FLUX.2 Klein Base 4B + newly trained v3 identity LoRA + one indexed $EditRegion latent edit"
    lora = "aitk\m1tch-flux2-klein-4b-identity-v3-portrait-profile.safetensors"
    lora_strength = 1.20
    denoise_strength = 0.65
    edit_region = $EditRegion
    gpu = "NVIDIA GeForce RTX 4070"
    results = @($rows)
}
$manifestDirectory = Split-Path -Parent $manifestPath
New-Item -ItemType Directory -Force -Path $manifestDirectory | Out-Null
$manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Output "MANIFEST=$manifestPath"
