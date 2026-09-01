$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $repoRoot "scripts\run-flux2-dev-identity-v2-gated.ps1"
$benchmark = Join-Path $repoRoot "scripts\benchmark-flux2-dev-v2-gate.ps1"
$record = Join-Path $repoRoot "work\flux2-dev-identity-v2\approvals\step-1100-evaluation.json"
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source

& $pwsh -NoProfile -ExecutionPolicy Bypass -File $runner -Phase To1100
if ($LASTEXITCODE -ne 0) { throw "To1100 gated runner failed with exit code $LASTEXITCODE." }

$releaseDeadline = (Get-Date).AddMinutes(3)
do {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:8188/free" -Method Post -ContentType "application/json" -Body '{"unload_models":true,"free_memory":true}' -TimeoutSec 30 | Out-Null
    } catch {
        Write-Warning "Could not request a 3090 Comfy memory release: $($_.Exception.Message)"
    }
    $usedMemory = [int](((& nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | Select-Object -First 1).Trim()))
    if ($usedMemory -le 4096) { break }
    Start-Sleep -Seconds 5
} while ((Get-Date) -lt $releaseDeadline)
if ($usedMemory -gt 4096) { throw "RTX 3090 memory did not release after To1100." }

[ordered]@{
    status = "running"
    started_utc = (Get-Date).ToUniversalTime().ToString("o")
    comparison = "steps 900, 1000, and 1100"
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $record -Encoding utf8

& $pwsh -NoProfile -ExecutionPolicy Bypass -File $benchmark -Mode Gate1100
if ($LASTEXITCODE -ne 0) { throw "Gate1100 benchmark failed with exit code $LASTEXITCODE." }

$manifest = Join-Path $repoRoot "work\flux2-dev-identity-v2\comparisons\gate-1100\gate-1100-manifest.json"
$sheet = Join-Path $repoRoot "work\flux2-dev-identity-v2\comparisons\gate-1100\gate-1100-review-thumbnails.jpg"
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf) -or -not (Test-Path -LiteralPath $sheet -PathType Leaf)) {
    throw "Gate1100 benchmark did not create its manifest and contact sheet."
}
[ordered]@{
    status = "complete"
    completed_utc = (Get-Date).ToUniversalTime().ToString("o")
    training_paused_at_step = 1100
    resume_requires_mitch_approval = $true
    manifest = $manifest
    contact_sheet = $sheet
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $record -Encoding utf8

Write-Host "To1100 training and Gate1100 evaluation completed; training remains paused."
