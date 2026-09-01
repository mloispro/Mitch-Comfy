[CmdletBinding()]
param(
    [int[]]$CheckpointSteps = @(1200, 1400, 1600, 2000),
    [double[]]$Strengths = @(0.9),
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runName = "flux2-klein9b-identity-v6-r32-dop"
$jobName = "m1tch-flux2-klein9b-identity-v6-r32-dop"
$datasetName = "mitch-identity-stills-v6-klein9b"
$lockPath = Join-Path $repoRoot "work\$runName\training-lock.json"
$screen = Join-Path $PSScriptRoot "screen-flux2-klein9b-identity-v4.ps1"
$manifestPath = Join-Path $repoRoot "datasets\$datasetName\manifest.json"
foreach ($path in @($lockPath, $screen, $manifestPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "V6 checkpoint screen is not locked; missing: $path" }
}
$lock = Get-Content -Raw -LiteralPath $lockPath | ConvertFrom-Json
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToUpperInvariant() -cne
    [string]$lock.dataset.manifest_sha256) {
    throw "V6 dataset manifest changed after the training lock."
}
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
$heldOutFiles = @($manifest.records | Where-Object split -eq "validation" | ForEach-Object {
    Split-Path -Leaf ([string]$_.dataset_file)
} | Sort-Object)
if ($heldOutFiles.Count -ne 6) { throw "V6 checkpoint screen requires six held-out photographs." }

& $screen `
    -CheckpointSteps $CheckpointSteps `
    -Strengths $Strengths `
    -ComfyRoot $ComfyRoot `
    -ComfyUrl $ComfyUrl `
    -RunName $runName `
    -JobName $jobName `
    -OutputNamespace "klein9b-v6-r32-dop-extension2000" `
    -ReferenceDatasetName $datasetName `
    -ExpectedRank 32 `
    -ExpectedTrainingSteps 2000 `
    -TrainingRecordName "training-extension-to2000-validation.json" `
    -ReportSubdirectory "extension-to2000" `
    -StageScript (Join-Path $PSScriptRoot "stage-flux2-klein9b-identity-v6-extension2000-checkpoints.ps1") `
    -BenchmarkScript (Join-Path $PSScriptRoot "benchmark-flux2-klein9b-identity-v6.ps1") `
    -HeldOutReferenceFiles $heldOutFiles `
    -TrainingFilesExcludedFromEvaluation @("13_full_body_orange_mirror.jpg", "14_surf_full_body.jpg", "15_body_mirror_sleeveless.jpg") `
    -ExpectedQuickCandidateCount 3 `
    -ExpectedCalibrationReferenceCount 4 `
    -ExpectedReferencePairwiseMinimum 0.6973 `
    -ExpectedReferencePairwiseMean 0.7491 `
    -RequireDiffOutputPreservation

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
