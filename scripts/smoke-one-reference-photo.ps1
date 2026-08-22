param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [string]$FaceReference = "20260815_165446.jpg",
    [string]$ScenePrompt = "A casual waist-up smartphone photo on a shaded city sidewalk in soft afternoon daylight, wearing a fitted navy crew-neck T-shirt, relaxed posture, small natural smile, looking at the camera.",
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"

$workflow = @{
    "1" = @{
        class_type = "Flux2OneReferencePhoto"
        inputs = @{
            face_reference = $FaceReference
            scene_prompt = $ScenePrompt
        }
    }
}

$body = @{ prompt = $workflow; client_id = "flux2-one-reference-photo" } | ConvertTo-Json -Depth 10
$queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt_id."
}
Write-Host "Queued one-reference FLUX.2 photo: $($queued.prompt_id)"

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.($queued.prompt_id)
    if ($entry) {
        if ($entry.status.status_str -eq "success") {
            Write-Host "One-reference FLUX.2 photo succeeded."
            $entry | ConvertTo-Json -Depth 12
            exit 0
        }
        if ($entry.status.status_str -eq "error") {
            $entry | ConvertTo-Json -Depth 12
            throw "One-reference FLUX.2 photo failed."
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for one-reference photo $($queued.prompt_id)."
