param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [int]$TimeoutSeconds = 3600
)

$ErrorActionPreference = "Stop"
$workflow = @{
    "1" = @{
        class_type = "Flux2ModelBenchmark"
        inputs = @{
            reference_1 = "20260815_165446.jpg"
            reference_2 = "20260815_165449.jpg"
            reference_3 = "20260818_173106.jpg"
            reference_4 = "20260508_123156.jpg"
        }
    }
}
$body = @{ prompt = $workflow; client_id = "flux2-model-benchmark" } | ConvertTo-Json -Depth 10
$queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt_id."
}
Write-Host "Queued FLUX.2 9B-versus-Dev benchmark: $($queued.prompt_id)"

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 3
    $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.($queued.prompt_id)
    if ($entry -and $entry.status.status_str -eq "error") {
        $entry | ConvertTo-Json -Depth 12
        throw "FLUX.2 model benchmark failed."
    }
    if ($entry -and $entry.status.status_str -eq "success") {
        $entry | ConvertTo-Json -Depth 12
        exit 0
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for FLUX.2 model benchmark $($queued.prompt_id)."
