[CmdletBinding()]
param(
    [switch]$WaitForTraining,
    [ValidateRange(1, 12)][int]$MaximumWaitHours = 6,
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [int]$GenerationSteps = 50
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runRoot = Join-Path $repoRoot "work\flux2-klein9b-identity-v3-r32-dop"
$completion = Join-Path $runRoot "train\training-extension-to2000-validation.json"
$coarse = Join-Path $PSScriptRoot "screen-flux2-klein9b-identity-v3-extension2000.ps1"
$full = Join-Path $PSScriptRoot "full-screen-flux2-klein9b-identity-v3-extension2000.ps1"

if ($WaitForTraining) {
    $deadline = (Get-Date).AddHours($MaximumWaitHours)
    while (-not (Test-Path -LiteralPath $completion -PathType Leaf) -and (Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 30
    }
}
if (-not (Test-Path -LiteralPath $completion -PathType Leaf)) {
    throw "The validated V3 2,000-step continuation has not completed: $completion"
}
$record = Get-Content -Raw -LiteralPath $completion | ConvertFrom-Json
if (-not [bool]$record.valid -or [int]$record.total_steps -ne 2000 -or -not [bool]$record.exact_continuation_proven -or
    [int]$record.dop_total_proven_updates -ne 2000 -or -not [bool]$record.zero_ooms) {
    throw "The V3 2,000-step continuation record failed its provenance gate."
}

$readyDeadline = (Get-Date).AddMinutes(5)
do {
    try {
        $queue = Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 10
        $stats = Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 10
        $ready = [string]$stats.devices[0].name -match "RTX 3090" -and @($queue.queue_running).Count -eq 0 -and @($queue.queue_pending).Count -eq 0
    } catch { $ready = $false }
    if (-not $ready) { Start-Sleep -Seconds 5 }
} while (-not $ready -and (Get-Date) -lt $readyDeadline)
if (-not $ready) { throw "The restored RTX 3090 ComfyUI worker is not online and idle; V3 comparison was not queued." }

Write-Host "Comparing V3 steps 1200, 1400, 1600, and 2000 at fixed strength 0.9."
& $coarse -ComfyRoot $ComfyRoot -ComfyUrl $ComfyUrl
if ($LASTEXITCODE -ne 0) { throw "The V3 four-checkpoint coarse comparison failed." }
& $full -ComfyRoot $ComfyRoot -ComfyUrl $ComfyUrl -Steps $GenerationSteps -Strengths @(0.9)
if ($LASTEXITCODE -ne 0) { throw "The V3 four-checkpoint full comparison failed." }

$summary = Join-Path $runRoot "benchmarks\extension-to2000\full-screen-summary.json"
$sheet = Join-Path $runRoot "benchmarks\extension-to2000\full-screen-sheet.png"
foreach ($path in @($summary, $sheet)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "V3 comparison artifact is missing: $path" }
}
Write-Output $summary
Write-Output $sheet
