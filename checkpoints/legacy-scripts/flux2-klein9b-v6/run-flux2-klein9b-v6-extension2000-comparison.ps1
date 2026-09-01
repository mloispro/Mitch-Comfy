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
$runName = "flux2-klein9b-identity-v6-r32-dop"
$runRoot = Join-Path $repoRoot "work\$runName"
$lockPath = Join-Path $runRoot "training-lock.json"
$completion = Join-Path $runRoot "train\training-extension-to2000-validation.json"
$coarse = Join-Path $PSScriptRoot "screen-flux2-klein9b-identity-v6-extension2000.ps1"
$full = Join-Path $PSScriptRoot "full-screen-flux2-klein9b-identity-v6-extension2000.ps1"

foreach ($path in @($lockPath, $coarse, $full)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "V6 comparison is not locked; missing: $path" }
}
$lock = Get-Content -Raw -LiteralPath $lockPath | ConvertFrom-Json
if (-not [bool]$lock.valid -or @($lock.evaluation.scripts).Count -lt 10) {
    throw "V6 training/evaluation lock is invalid."
}
foreach ($script in @($lock.evaluation.scripts)) {
    if (-not (Test-Path -LiteralPath ([string]$script.path) -PathType Leaf) -or
        (Get-FileHash -Algorithm SHA256 -LiteralPath ([string]$script.path)).Hash.ToUpperInvariant() -cne [string]$script.sha256) {
        throw "A V6 evaluation script changed after the lock: $($script.path)"
    }
}
if ($WaitForTraining) {
    $deadline = (Get-Date).AddHours($MaximumWaitHours)
    while (-not (Test-Path -LiteralPath $completion -PathType Leaf) -and (Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 30
    }
}
if (-not (Test-Path -LiteralPath $completion -PathType Leaf)) {
    throw "The validated V6 2,000-step continuation has not completed: $completion"
}
$record = Get-Content -Raw -LiteralPath $completion | ConvertFrom-Json
if (-not [bool]$record.valid -or [int]$record.total_steps -ne 2000 -or
    -not [bool]$record.exact_continuation_proven -or [int]$record.dop_total_proven_updates -ne 2000 -or
    -not [bool]$record.zero_ooms -or [string]$record.gpu -notmatch "RTX 3090" -or $null -ne $record.fallback_gpu) {
    throw "The V6 continuation record failed its 2,000-update RTX 3090 provenance gate."
}

$readyDeadline = (Get-Date).AddMinutes(5)
do {
    try {
        $queue = Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 10
        $stats = Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 10
        $ready = [string]$stats.devices[0].name -match "RTX 3090" -and
            @($queue.queue_running).Count -eq 0 -and @($queue.queue_pending).Count -eq 0
    } catch { $ready = $false }
    if (-not $ready) { Start-Sleep -Seconds 5 }
} while (-not $ready -and (Get-Date) -lt $readyDeadline)
if (-not $ready) { throw "The restored RTX 3090 worker is not online and idle; comparison was not queued." }

& $coarse -ComfyRoot $ComfyRoot -ComfyUrl $ComfyUrl
if ($LASTEXITCODE -ne 0) { throw "The V6 four-checkpoint coarse comparison failed." }
& $full -ComfyRoot $ComfyRoot -ComfyUrl $ComfyUrl -Steps $GenerationSteps -Strengths @(0.9)
if ($LASTEXITCODE -ne 0) { throw "The V6 four-checkpoint full comparison failed." }

$summaryPath = Join-Path $runRoot "benchmarks\extension-to2000\full-screen-summary.json"
$sheetPath = Join-Path $runRoot "benchmarks\extension-to2000\full-screen-sheet.png"
foreach ($path in @($summaryPath, $sheetPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "V6 comparison artifact is missing: $path" }
}
$summary = Get-Content -Raw -LiteralPath $summaryPath | ConvertFrom-Json
$results = @($summary.results)
$actualSteps = @($results | ForEach-Object { [int]$_.step } | Sort-Object -Unique)
if ($results.Count -ne 4 -or (Compare-Object @(1200, 1400, 1600, 2000) $actualSteps).Count -ne 0 -or
    @($results | Where-Object { [double]$_.strength -ne 0.9 }).Count -ne 0) {
    throw "V6 full comparison does not contain exactly steps 1200/1400/1600/2000 at strength 0.9."
}
foreach ($result in $results) {
    $outputNames = @($result.outputs.PSObject.Properties.Name)
    foreach ($required in @("portrait", "waist-up-social", "profile-image-left", "profile-image-right", "full-body-walking", "crowd")) {
        if ($required -notin $outputNames) { throw "V6 candidate $($result.candidate_key) is missing $required." }
    }
}
$comparisonValidationPath = Join-Path $runRoot "benchmarks\extension-to2000\comparison-validation.json"
[ordered]@{
    valid = $true
    completed_utc = (Get-Date).ToUniversalTime().ToString("o")
    training_record = $completion
    checkpoint_steps = @(1200, 1400, 1600, 2000)
    strength = 0.9
    scoring_heldouts = 6
    stable_calibration_heldouts = 4
    bidirectional_profile_tests = $true
    no_reference_conditioning = $true
    no_identity_pass = $true
    no_face_swap = $true
    summary = $summaryPath
    sheet = $sheetPath
    automatic_pass_count = @($results | Where-Object automatic_gates_passed).Count
    manual_full_size_identity_profile_body_anatomy_and_leakage_review_required = $true
    published = $false
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $comparisonValidationPath -Encoding utf8
Write-Output $summaryPath
Write-Output $sheetPath
Write-Output $comparisonValidationPath
