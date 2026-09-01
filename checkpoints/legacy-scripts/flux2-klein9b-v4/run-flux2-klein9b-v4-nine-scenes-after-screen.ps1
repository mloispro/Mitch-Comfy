[CmdletBinding()]
param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [int]$Steps = 50,
    [string]$RunName = "flux2-klein9b-identity-v4-r16-diverse",
    [string]$JobName = "m1tch-flux2-klein9b-identity-v4-r16-diverse",
    [string]$OutputNamespace = "klein9b-v4-r16-diverse",
    [string]$ReferenceDatasetName = "mitch-identity-stills-v4-klein9b",
    [int]$ExpectedRank = 16,
    [string]$RunLabelPrefix = "v4-r16-diverse",
    [switch]$RequireSummaryRank,
    [switch]$RequireDiffOutputPreservation
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runRoot = Join-Path $repoRoot ("work\{0}" -f $RunName)
$fullSummaryPath = Join-Path $runRoot "benchmarks\full-screen-summary.json"
$nineSceneScript = Join-Path $PSScriptRoot "run-flux2-klein9b-lora-nine-scenes-3090.ps1"
$sheetScript = Join-Path $PSScriptRoot "build-flux2-klein9b-lora-nine-scene-sheet.py"
$python = "C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe"
$heldOutReferences = @(
    "val_03_navy_upper_body.jpg",
    "val_04_window_small_smile.jpg",
    "val_05_balcony_opposite_angle.jpg",
    "val_06_car_daylight.jpg"
)

if (-not (Test-Path -LiteralPath $fullSummaryPath -PathType Leaf)) {
    throw "The v4 full screen has not completed: $fullSummaryPath"
}
$summary = Get-Content -Raw -LiteralPath $fullSummaryPath | ConvertFrom-Json
if ([string]$summary.dataset -cne $ReferenceDatasetName -or
    ($RequireSummaryRank -and [int]$summary.rank -ne $ExpectedRank) -or
    ($RequireDiffOutputPreservation -and -not [bool]$summary.differential_output_preservation_required) -or
    @($summary.held_out_reference_files).Count -ne 4 -or
    [bool]$summary.reference_conditioning -or
    [bool]$summary.identity_pass -or
    [bool]$summary.face_swap) {
    throw "The full-screen summary provenance does not match the locked v4 evaluation."
}
$leader = @($summary.results | Sort-Object rank | Select-Object -First 1)[0]
if (-not $leader) {
    throw "The v4 full screen did not produce a leading candidate."
}
if (@($leader.crowd_leakage_failures).Count -gt 0 -or -not [bool]$leader.crowd_identity_leakage_passed) {
    throw "The full-screen leader leaks Mitch identity into a secondary face; nine-scene generation is blocked."
}
if (-not [bool]$leader.automatic_gates_passed -or
    -not [bool]$leader.core_gate_passed -or
    -not [bool]$leader.crowd_gate_passed) {
    throw "No fully passing v4 full-screen leader is available; nine-scene generation is blocked pending a controlled refinement."
}

$step = [int]$leader.step
$strength = [double]$leader.strength
$strengthLabel = $strength.ToString("0.00", [Globalization.CultureInfo]::InvariantCulture)
$loraName = "{0}-step{1:D4}.safetensors" -f $JobName, $step
$runLabel = "{0}-step{1:D4}-s{2}-nine-scenes" -f $RunLabelPrefix, $step, $strengthLabel

Write-Host "Generating the nine exact comparison scenes with $loraName at strength $strengthLabel."
$manifestOutput = @(& $nineSceneScript `
    -LoraName $loraName `
    -LoraStrength $strength `
    -Server $ComfyUrl `
    -ComfyRoot $ComfyRoot `
    -Steps $Steps `
    -SceneNumbers @(1, 2, 3, 4, 5, 6, 7, 8, 9) `
    -RunLabel $runLabel `
    -WorkRunName $RunName `
    -OutputNamespace $OutputNamespace `
    -ReferenceDatasetName $ReferenceDatasetName `
    -ReferenceSubdirectory "validation" `
    -ReferenceFiles $heldOutReferences)
$manifestPath = @($manifestOutput | Where-Object {
    $_ -is [string] -and (Test-Path -LiteralPath $_ -PathType Leaf)
} | Select-Object -Last 1)[0]
if (-not $manifestPath) {
    throw "The nine-scene runner did not return a manifest path."
}

& $python $sheetScript $manifestPath
if ($LASTEXITCODE -ne 0) {
    throw "Nine-scene comparison/evaluation builder failed."
}
$evaluationPath = Join-Path (Split-Path -Parent $manifestPath) "evaluation.json"
if (-not (Test-Path -LiteralPath $evaluationPath -PathType Leaf)) {
    throw "Nine-scene evaluation record is missing: $evaluationPath"
}
$evaluation = Get-Content -Raw -LiteralPath $evaluationPath | ConvertFrom-Json
if (@($evaluation.held_out_genuine_identity_references).Count -ne 4 -or
    [math]::Abs([double]$evaluation.calibration.reference_pairwise_floor - 0.6973) -gt 0.0001 -or
    [math]::Abs([double]$evaluation.calibration.reference_pairwise_mean - 0.7491) -gt 0.0001 -or
    [bool]$evaluation.reference_conditioning -or
    [string]$evaluation.evaluation_scope -cne "complete_nine_scene_review") {
    throw "Nine-scene evaluation did not use the locked four-reference complete-review scope."
}

$completion = [ordered]@{
    schema_version = 1
    completed_utc = (Get-Date).ToUniversalTime().ToString("o")
    selected_from = $fullSummaryPath
    checkpoint_step = $step
    strength = $strength
    lora = $loraName
    manifest = $manifestPath
    evaluation = $evaluationPath
    held_out_reference_count = 4
    source_scene_conditioning = $false
    reference_conditioning = $false
    identity_pass = $false
    face_swap = $false
    published = $false
    manual_visual_approval_required = $true
    rooftop_down_left_manual_gate_required = $true
    group_exactly_one_mitch_manual_gate_required = $true
    full_body_anatomy_manual_gate_required = $true
}
$completionPath = Join-Path $runRoot "nine-scene-completion.json"
$completion | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $completionPath -Encoding utf8
$completion | ConvertTo-Json -Depth 12
