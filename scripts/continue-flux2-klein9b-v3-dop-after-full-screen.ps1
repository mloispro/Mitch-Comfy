[CmdletBinding()]
param(
    [int]$FullScreenProcessId = 41628,
    [int]$TimeoutHours = 12
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runName = "flux2-klein9b-identity-v3-r32-dop"
$jobName = "m1tch-flux2-klein9b-identity-v3-r32-dop"
$runRoot = Join-Path $repoRoot ("work\{0}" -f $runName)
$fullSummaryPath = Join-Path $runRoot "benchmarks\full-screen-summary.json"
$nineSceneScript = Join-Path $PSScriptRoot "run-flux2-klein9b-lora-nine-scenes-3090.ps1"
$sheetScript = Join-Path $PSScriptRoot "build-flux2-klein9b-lora-nine-scene-sheet.py"
$python = "C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe"
$started = Get-Date

Write-Host "Waiting for full-screen process PID $FullScreenProcessId."
while (Get-Process -Id $FullScreenProcessId -ErrorAction SilentlyContinue) {
    if (((Get-Date) - $started).TotalHours -ge $TimeoutHours) {
        throw "Timed out waiting for full checkpoint screening."
    }
    Start-Sleep -Seconds 30
}
if (-not (Test-Path -LiteralPath $fullSummaryPath -PathType Leaf)) {
    throw "Full-screen process exited without a summary: $fullSummaryPath"
}

$summary = Get-Content -Raw -LiteralPath $fullSummaryPath | ConvertFrom-Json
$leader = @($summary.results | Sort-Object rank | Select-Object -First 1)[0]
if (-not $leader) { throw "Full screen did not produce a leading candidate." }
if (@($leader.crowd_leakage_failures).Count -gt 0) {
    throw "Full-screen leader leaks Mitch identity into a secondary face; nine-scene generation is blocked."
}
if (-not [bool]$leader.automatic_gates_passed) {
    throw "No fully passing full-screen leader is available; nine-scene generation is blocked pending a controlled refinement."
}
$step = [int]$leader.step
$strength = [double]$leader.strength
$strengthLabel = $strength.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
$loraName = "{0}-step{1:D4}.safetensors" -f $jobName, $step
$runLabel = "v3-dop-step{0:D4}-s{1}-nine-scenes" -f $step, $strengthLabel

Write-Host "Generating the nine exact comparison scenes with $loraName at strength $strengthLabel."
$manifestOutput = @(& $nineSceneScript `
    -LoraName $loraName `
    -LoraStrength $strength `
    -SceneNumbers @(1,2,3,4,5,6,7,8,9) `
    -RunLabel $runLabel `
    -WorkRunName $runName `
    -OutputNamespace "klein9b-v3-r32-dop")
$manifestPath = @($manifestOutput | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -Last 1)[0]
if (-not $manifestPath) { throw "The nine-scene runner did not return a manifest path." }

& $python $sheetScript $manifestPath
if ($LASTEXITCODE -ne 0) { throw "Nine-scene comparison/evaluation builder failed." }
$evaluationPath = Join-Path (Split-Path -Parent $manifestPath) "evaluation.json"
if (-not (Test-Path -LiteralPath $evaluationPath -PathType Leaf)) {
    throw "Nine-scene evaluation record is missing: $evaluationPath"
}

$completion = [ordered]@{
    schema_version = 1
    completed_utc = (Get-Date).ToUniversalTime().ToString('o')
    selected_from = $fullSummaryPath
    checkpoint_step = $step
    strength = $strength
    lora = $loraName
    manifest = $manifestPath
    evaluation = $evaluationPath
    source_scene_conditioning = $false
    reference_conditioning = $false
    identity_pass = $false
    face_swap = $false
    published = $false
    manual_visual_approval_required = $true
}
$completionPath = Join-Path $runRoot "nine-scene-completion.json"
$completion | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $completionPath -Encoding utf8
$completion | ConvertTo-Json -Depth 12
