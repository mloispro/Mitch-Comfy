param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [string]$Reference1 = "20260815_165446.jpg",
    [string]$Reference2 = "No additional reference",
    [string]$Reference3 = "No additional reference",
    [string]$Reference4 = "No additional reference",
    [string]$ScenePrompt = "Walking along a lively city sidewalk in soft late-afternoon light, wearing a fitted navy crew-neck T-shirt and dark jeans, relaxed and comfortable.",
    [ValidateSet("Smartphone — natural", "Smartphone — slight lens haze", "Professional — natural", "Prompt decides")]
    [string]$PhotoStyle = "Smartphone — natural",
    [ValidateSet("Prompt decides", "Head and shoulders", "Waist-up", "Full body")]
    [string]$Framing = "Waist-up",
    [ValidateSet("Prompt decides", "Looking at camera", "Candid / looking away", "Action")]
    [string]$Moment = "Looking at camera",
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
$workflow = @{
    "1" = @{
        class_type = "Flux2EasySocialPhotoV103"
        inputs = @{
            face_reference = $Reference1
            reference_2 = $Reference2
            reference_3 = $Reference3
            reference_4 = $Reference4
            scene_prompt = $ScenePrompt
            photo_style = $PhotoStyle
            framing = $Framing
            moment = $Moment
        }
    }
}
$body = @{ prompt = $workflow; client_id = "flux2-easy-social-photo-smoke" } | ConvertTo-Json -Depth 10
$queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt_id."
}
Write-Host "Queued easy social photo: $($queued.prompt_id)"

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.($queued.prompt_id)
    if ($entry -and $entry.status.status_str -eq "error") {
        $entry | ConvertTo-Json -Depth 12
        throw "Easy social photo smoke test failed."
    }
    if ($entry -and $entry.status.status_str -eq "success") {
        $entry | ConvertTo-Json -Depth 12
        exit 0
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for easy social photo $($queued.prompt_id)."
