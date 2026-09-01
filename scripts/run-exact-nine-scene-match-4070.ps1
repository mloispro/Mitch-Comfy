param(
    [string]$ComfyUrl = "http://127.0.0.1:8189",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ManifestPath = "C:\projects\AI-Tools\Mitch-Comfy\work\exact-nine-scene-v9\manifest.json"
)

$ErrorActionPreference = "Stop"

$scenes = @(
    @{ Number = 1; Slug = "01-night-out-a"; Input = "mitch-workbench-dating-01-night-out-a.png"; TargetIndex = "2"; ExpectedFaces = 4; Target = "third visible face from image-left; foreground man seated on the tan couch" },
    @{ Number = 2; Slug = "02-night-out-b"; Input = "mitch-workbench-dating-02-night-out-b.png"; TargetIndex = "1"; ExpectedFaces = 4; Target = "second visible face from image-left; central primary man" },
    @{ Number = 3; Slug = "03-cat-ragdoll"; Input = "mitch-workbench-dating-03-cat-ragdoll.png"; TargetIndex = "0"; ExpectedFaces = 1; Target = "only man" },
    @{ Number = 4; Slug = "04-cat-tabby"; Input = "mitch-workbench-dating-04-cat-tabby.png"; TargetIndex = "0"; ExpectedFaces = 1; Target = "only man" },
    @{ Number = 5; Slug = "05-golfer"; Input = "mitch-workbench-dating-05-golfer-safe.png"; TargetIndex = "0"; ExpectedFaces = 1; Target = "only man" },
    @{ Number = 6; Slug = "06-amalfi"; Input = "mitch-workbench-dating-06-amalfi.png"; TargetIndex = "0"; ExpectedFaces = 1; Target = "only man" },
    @{ Number = 7; Slug = "07-lake-boat"; Input = "mitch-workbench-dating-07-lake-boat.png"; TargetIndex = "0"; ExpectedFaces = 1; Target = "only man" },
    @{ Number = 8; Slug = "08-restaurant"; Input = "mitch-workbench-dating-08-restaurant.png"; TargetIndex = "0"; ExpectedFaces = 1; Target = "only man" },
    @{ Number = 9; Slug = "09-night-city"; Input = "mitch-workbench-dating-09-night-city.png"; TargetIndex = "0"; ExpectedFaces = 1; Target = "only man; preserve downward head pitch and gaze toward image-left" }
)

$identityReferences = @(
    "20260815_165446.jpg",
    "20260508_123156.jpg",
    "20260818_173106.jpg"
)

function Assert-WorkerReady {
    $stats = Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 15
    $deviceNames = @($stats.devices | ForEach-Object { $_.name })
    if (-not ($deviceNames -match "RTX 4070")) {
        throw "Refusing to run: $ComfyUrl is not the RTX 4070 worker. Devices: $($deviceNames -join ', ')"
    }

    $queue = Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 15
    if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
        throw "Refusing to disturb active GPU work: the RTX 4070 queue is not empty."
    }

    $objectInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info" -TimeoutSec 30
    $requiredNodes = @(
        "LoadImage",
        "SaveImage",
        "ReActorBuildFaceModel",
        "ReActorMakeFaceModelBatch",
        "ReActorFaceBoost",
        "ReActorOptions",
        "ReActorFaceSwapOpt"
    )
    foreach ($nodeName in $requiredNodes) {
        if (-not ($objectInfo.PSObject.Properties.Name -contains $nodeName)) {
            throw "Required node is unavailable on RTX 4070 worker: $nodeName"
        }
    }

    $boostModels = @($objectInfo.ReActorFaceBoost.input.required.boost_model[0])
    if ($boostModels -notcontains "GPEN-BFR-512.onnx") {
        throw "Required face booster is unavailable: GPEN-BFR-512.onnx"
    }
}

function Assert-InputsPresent {
    $inputRoot = Join-Path $ComfyRoot "input"
    foreach ($name in @($identityReferences) + @($scenes | ForEach-Object { $_.Input })) {
        $path = Join-Path $inputRoot $name
        if (-not (Test-Path -LiteralPath $path)) {
            throw "Required ComfyUI input is missing: $path"
        }
    }
}

Assert-WorkerReady
Assert-InputsPresent

# The queue was verified empty. Free only this worker's cached model memory before
# running the lightweight face-only pass; the RTX 3090 worker is untouched.
Invoke-RestMethod -Uri "$ComfyUrl/free" -Method Post -ContentType "application/json" -Body '{"unload_models":true,"free_memory":true}' -TimeoutSec 30 | Out-Null

$prompt = @{
    "1" = @{ class_type = "LoadImage"; inputs = @{ image = $identityReferences[0] } }
    "2" = @{ class_type = "LoadImage"; inputs = @{ image = $identityReferences[1] } }
    "3" = @{ class_type = "LoadImage"; inputs = @{ image = $identityReferences[2] } }
    "4" = @{ class_type = "ReActorBuildFaceModel"; inputs = @{ save_mode = $false; send_only = $false; face_model_name = "mitch_exact_front"; compute_method = "Mean"; images = @("1", 0) } }
    "5" = @{ class_type = "ReActorBuildFaceModel"; inputs = @{ save_mode = $false; send_only = $false; face_model_name = "mitch_exact_angle_1"; compute_method = "Mean"; images = @("2", 0) } }
    "6" = @{ class_type = "ReActorBuildFaceModel"; inputs = @{ save_mode = $false; send_only = $false; face_model_name = "mitch_exact_angle_2"; compute_method = "Mean"; images = @("3", 0) } }
    "7" = @{ class_type = "ReActorMakeFaceModelBatch"; inputs = @{ face_model1 = @("4", 0); face_model2 = @("5", 0); face_model3 = @("6", 0) } }
    "8" = @{ class_type = "ReActorBuildFaceModel"; inputs = @{ save_mode = $false; send_only = $false; face_model_name = "mitch_exact_3ref_mean"; compute_method = "Mean"; face_models = @("7", 0) } }
    "9" = @{ class_type = "ReActorFaceBoost"; inputs = @{ enabled = $true; boost_model = "GPEN-BFR-512.onnx"; interpolation = "Lanczos"; visibility = 0.70; codeformer_weight = 0.50; restore_with_main_after = $false } }
}

$saveNodeBySlug = @{}
$node = 20
foreach ($scene in $scenes) {
    $load = "$node"
    $options = "$($node + 1)"
    $swap = "$($node + 2)"
    $save = "$($node + 3)"

    # Loading the supplied target itself is the key constraint: ReActor changes the
    # selected face while retaining the target pose, people, crop, clothing and scene.
    $prompt[$load] = @{
        class_type = "LoadImage"
        inputs = @{ image = $scene.Input }
    }
    $prompt[$options] = @{
        class_type = "ReActorOptions"
        inputs = @{
            input_faces_order = "left-right"
            input_faces_index = $scene.TargetIndex
            detect_gender_input = "male"
            source_faces_order = "large-small"
            source_faces_index = "0"
            detect_gender_source = "male"
            console_log_level = 2
            restore_swapped_only = $true
        }
    }
    $prompt[$swap] = @{
        class_type = "ReActorFaceSwapOpt"
        inputs = @{
            enabled = $true
            swap_model = "inswapper_128.onnx"
            facedetection = "retinaface_resnet50"
            face_restore_model = "none"
            face_restore_visibility = 1.0
            codeformer_weight = 0.5
            input_image = @($load, 0)
            face_model = @("8", 0)
            options = @($options, 0)
            face_boost = @("9", 0)
        }
    }
    $prompt[$save] = @{
        class_type = "SaveImage"
        inputs = @{
            images = @($swap, 0)
            filename_prefix = "dating-app-exact-scene-v9/$($scene.Slug)/final"
        }
    }
    $saveNodeBySlug[$scene.Slug] = $save
    $node += 4
}

$clientId = "mitch-exact-scene-v9-$([Guid]::NewGuid().ToString('N'))"
$body = @{ prompt = $prompt; client_id = $clientId } | ConvertTo-Json -Depth 30
$submission = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 30
$promptId = $submission.prompt_id
if (-not $promptId) {
    throw "ComfyUI did not return a prompt ID."
}
Write-Output "PROMPT_ID=$promptId"

$entry = $null
while ($true) {
    Start-Sleep -Seconds 3
    $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$promptId" -TimeoutSec 15
    $entry = $history.PSObject.Properties[$promptId].Value
    if ($entry -and $entry.status.completed) {
        Write-Output "STATUS=$($entry.status.status_str)"
        if ($entry.status.status_str -ne "success") {
            $entry.status.messages | ConvertTo-Json -Depth 30
            throw "Exact-scene generation failed."
        }
        break
    }
}

$outputRoot = Join-Path $ComfyRoot "output\gpu-4070"
$resultRows = foreach ($scene in $scenes) {
    $saveNode = $saveNodeBySlug[$scene.Slug]
    $nodeOutput = $entry.outputs.PSObject.Properties[$saveNode].Value
    $image = @($nodeOutput.images)[0]
    if (-not $image) {
        throw "No saved output was reported for $($scene.Slug)."
    }
    $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
    [ordered]@{
        number = $scene.Number
        slug = $scene.Slug
        source = (Join-Path (Join-Path $ComfyRoot "input") $scene.Input)
        output = (Join-Path $outputRoot $relative)
        target_index_left_to_right = [int]$scene.TargetIndex
        expected_face_count = $scene.ExpectedFaces
        target_description = $scene.Target
    }
}

$manifest = [ordered]@{
    created_at = (Get-Date).ToString("o")
    comfy_url = $ComfyUrl
    gpu = "NVIDIA GeForce RTX 4070"
    prompt_id = $promptId
    method = "original scene plate + one indexed ReActor identity replacement"
    identity_references = @($identityReferences | ForEach-Object { Join-Path (Join-Path $ComfyRoot "input") $_ })
    settings = [ordered]@{
        swap_model = "inswapper_128.onnx"
        detector = "retinaface_resnet50"
        blend = "mean of three genuine reference face models"
        booster = "GPEN-BFR-512.onnx"
        booster_visibility = 0.70
        restore_swapped_only = $true
    }
    scenes = @($resultRows)
}

$manifestDirectory = Split-Path -Parent $ManifestPath
New-Item -ItemType Directory -Force -Path $manifestDirectory | Out-Null
$manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $ManifestPath -Encoding utf8
Write-Output "MANIFEST=$ManifestPath"
$resultRows | ForEach-Object { Write-Output "OUTPUT_$($_.number)=$($_.output)" }
