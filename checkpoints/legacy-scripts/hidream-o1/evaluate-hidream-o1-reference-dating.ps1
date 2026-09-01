[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string[]]$Candidate,
    [Parameter(Mandatory = $true)]
    [string[]]$CandidateLabel,
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$OutputRoot = "output\hidream-o1-reference-dating-v1\evaluation"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $ComfyRoot ".venv\Scripts\python.exe"
$evaluationRoot = Join-Path $repoRoot $OutputRoot
$validationRoot = Join-Path $repoRoot "datasets\mitch-identity-stills-v3\validation"

if ($Candidate.Count -ne $CandidateLabel.Count) {
    throw "Use exactly one CandidateLabel for each Candidate."
}
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Missing ComfyUI Python: $pythonPath"
}

$references = @(
    "val_01_surf_full_body.jpg",
    "val_02_body_mirror_sleeveless.jpg",
    "val_03_navy_upper_body.jpg",
    "val_04_window_small_smile.jpg",
    "val_05_balcony_opposite_angle.jpg"
) | ForEach-Object { Join-Path $validationRoot $_ }
$candidatePaths = @($Candidate | ForEach-Object { (Resolve-Path -LiteralPath $_).Path })
foreach ($path in @($references) + @($candidatePaths)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Evaluation image is missing: $path"
    }
}

New-Item -ItemType Directory -Path $evaluationRoot -Force | Out-Null
$identityPath = Join-Path $evaluationRoot "identity.json"
$faceArgs = @((Join-Path $PSScriptRoot "evaluate-face-likeness.py"))
foreach ($reference in $references) { $faceArgs += @("--reference", $reference) }
foreach ($candidate in $candidatePaths) { $faceArgs += @("--candidate", $candidate) }
foreach ($label in $CandidateLabel) { $faceArgs += @("--candidate-label", $label) }
$faceArgs += @("--json-output", $identityPath)
& $pythonPath @faceArgs
if ($LASTEXITCODE -ne 0) { throw "Identity evaluation failed." }

for ($index = 0; $index -lt $candidatePaths.Count; $index++) {
    $safeLabel = $CandidateLabel[$index] -replace "[^A-Za-z0-9._-]", "-"
    & $pythonPath (Join-Path $PSScriptRoot "build-hidream-o1-audit-views.py") `
        $candidatePaths[$index] (Join-Path $evaluationRoot $safeLabel)
    if ($LASTEXITCODE -ne 0) { throw "Audit-view generation failed for $($CandidateLabel[$index])." }
}

$skinSheet = Join-Path $evaluationRoot "face-texture-contact-sheet.png"
$skinJson = Join-Path $evaluationRoot "face-texture.json"
$skinArgs = @(
    (Join-Path $PSScriptRoot "evaluate-skin-realism.py"),
    "--reference", (Join-Path (Join-Path $ComfyRoot "input") "20260815_165446.jpg"),
    "--reference", (Join-Path (Join-Path $ComfyRoot "input") "20260818_173106.jpg")
)
foreach ($candidate in $candidatePaths) { $skinArgs += @("--candidate", $candidate) }
foreach ($label in $CandidateLabel) { $skinArgs += @("--candidate-label", $label) }
$skinArgs += @("--contact-sheet", $skinSheet, "--json-output", $skinJson)
& $pythonPath @skinArgs
if ($LASTEXITCODE -ne 0) { throw "Skin-realism evaluation failed." }

Write-Host "Identity report: $identityPath"
Write-Host "Face texture sheet: $skinSheet"
