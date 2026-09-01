[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetOutputImage,
    [int]$Port = 8188,
    [string]$ExpectedGpuName = "NVIDIA GeForce RTX 3090",
    [string]$FilenamePrefix = "crowd-proof/reactor-krea-statefair/identity-finished",
    [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = "Stop"
$baseUrl = "http://127.0.0.1:$Port"
$annotatedTarget = if ($TargetOutputImage.EndsWith("[output]")) {
    $TargetOutputImage
}
else {
    "$TargetOutputImage [output]"
}

$stats = Invoke-RestMethod -Uri "$baseUrl/system_stats" -TimeoutSec 10
$deviceName = [string](@($stats.devices)[0].name)
if ($deviceName -notlike "*$ExpectedGpuName*") {
    throw "Port $Port is serving '$deviceName', not '$ExpectedGpuName'."
}
$queue = Invoke-RestMethod -Uri "$baseUrl/queue" -TimeoutSec 10
if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
    throw "Port $Port has unrelated queued work. Nothing was submitted."
}
$objectInfo = Invoke-RestMethod -Uri "$baseUrl/object_info" -TimeoutSec 60
foreach ($node in @("LoadImageOutput", "ReActorLoadFaceModel", "ReActorOptions", "ReActorFaceSwapOpt", "WholeFramePhoneFinish", "SaveImage")) {
    if (-not $objectInfo.PSObject.Properties[$node]) {
        throw "Required node is unavailable: $node"
    }
}
if (@($objectInfo.ReActorLoadFaceModel.input.required.face_model[0]) -notcontains "mitch_3ref_mean.safetensors") {
    throw "The locked three-reference Mitch face model is unavailable."
}

$workflow = @{
    "1" = @{
        class_type = "LoadImageOutput"
        inputs = @{ image = $annotatedTarget }
    }
    "2" = @{
        class_type = "ReActorLoadFaceModel"
        inputs = @{ face_model = "mitch_3ref_mean.safetensors" }
    }
    "3" = @{
        class_type = "ReActorOptions"
        inputs = @{
            input_faces_order = "large-small"
            input_faces_index = "0"
            detect_gender_input = "male"
            source_faces_order = "large-small"
            source_faces_index = "0"
            detect_gender_source = "male"
            console_log_level = 2
            restore_swapped_only = $true
        }
    }
    "4" = @{
        class_type = "ReActorFaceSwapOpt"
        inputs = @{
            enabled = $true
            input_image = @("1", 0)
            swap_model = "inswapper_128.onnx"
            facedetection = "retinaface_resnet50"
            face_restore_model = "none"
            face_restore_visibility = 1.0
            codeformer_weight = 0.5
            face_model = @("2", 0)
            options = @("3", 0)
        }
    }
    "5" = @{
        class_type = "WholeFramePhoneFinish"
        inputs = @{ image = @("4", 0) }
    }
    "6" = @{
        class_type = "SaveImage"
        inputs = @{
            images = @("5", 0)
            filename_prefix = $FilenamePrefix
        }
    }
}
$clientId = "reactor-crowd-finish-$(New-Guid)"
$body = @{
    prompt = $workflow
    client_id = $clientId
} | ConvertTo-Json -Depth 20
$queued = Invoke-RestMethod -Method Post -Uri "$baseUrl/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt id."
}

$started = Get-Date
$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
while ([DateTime]::UtcNow -lt $deadline) {
    $history = Invoke-RestMethod -Uri "$baseUrl/history/$($queued.prompt_id)" -TimeoutSec 30
    $record = $history.PSObject.Properties[[string]$queued.prompt_id].Value
    if ($record -and $record.status.status_str -eq "error") {
        throw "ReActor crowd finish failed: $($record.status.messages | ConvertTo-Json -Depth 30 -Compress)"
    }
    if ($record -and ($record.status.completed -or $record.status.status_str -eq "success")) {
        $images = @()
        foreach ($output in $record.outputs.PSObject.Properties.Value) {
            foreach ($image in @($output.images)) {
                if ($image.filename) {
                    $images += if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                }
            }
        }
        [ordered]@{
            prompt_id = [string]$queued.prompt_id
            gpu = $ExpectedGpuName
            target_output_image = $TargetOutputImage
            identity_model = "mitch_3ref_mean.safetensors"
            swap_model = "inswapper_128.onnx"
            face_detector = "retinaface_resnet50"
            face_restore_model = "none"
            whole_frame_phone_finish_after_identity = $true
            target_selection = "largest detected male face only"
            elapsed_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
            images = $images
        } | ConvertTo-Json -Depth 10
        exit 0
    }
    Start-Sleep -Seconds 2
}

throw "Timed out waiting for ReActor crowd finish."
