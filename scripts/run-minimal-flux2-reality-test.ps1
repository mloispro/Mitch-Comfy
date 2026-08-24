param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
$workflow = @{
    "1" = @{
        class_type = "Flux2MinimalRealityTest"
        inputs = @{
            reference_1 = "20260815_165446.jpg"
            reference_2 = "20260815_165449.jpg"
            reference_3 = "20260818_173106.jpg"
            reference_4 = "20260508_123156.jpg"
        }
    }
}
$body = @{ prompt = $workflow; client_id = "flux2-minimal-reality-test" } | ConvertTo-Json -Depth 10
$queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt_id."
}
Write-Host "Queued minimal FLUX.2 reality test: $($queued.prompt_id)"

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.($queued.prompt_id)
    if ($entry -and $entry.status.status_str -eq "error") {
        $entry | ConvertTo-Json -Depth 12
        throw "Minimal FLUX.2 reality test failed."
    }
    if ($entry -and $entry.status.status_str -eq "success") {
        $entry | ConvertTo-Json -Depth 12
        exit 0
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for minimal FLUX.2 reality test $($queued.prompt_id)."
