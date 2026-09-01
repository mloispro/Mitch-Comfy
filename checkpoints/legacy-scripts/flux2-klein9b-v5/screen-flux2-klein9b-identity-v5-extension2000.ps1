[CmdletBinding()]
param(
    [int[]]$CheckpointSteps = @(1200, 1400, 1600, 2000),
    [double[]]$Strengths = @(0.9),
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188"
)

$ErrorActionPreference = "Stop"
$screen = Join-Path $PSScriptRoot "screen-flux2-klein9b-identity-v4.ps1"
& $screen `
    -CheckpointSteps $CheckpointSteps `
    -Strengths $Strengths `
    -ComfyRoot $ComfyRoot `
    -ComfyUrl $ComfyUrl `
    -RunName "flux2-klein9b-identity-v5-r32-dop-body" `
    -JobName "m1tch-flux2-klein9b-identity-v5-r32-dop-body" `
    -OutputNamespace "klein9b-v5-r32-dop-body-extension2000" `
    -ReferenceDatasetName "mitch-identity-stills-v4-klein9b" `
    -ExpectedRank 32 `
    -ExpectedTrainingSteps 2000 `
    -TrainingRecordName "training-extension-to2000-validation.json" `
    -ReportSubdirectory "extension-to2000" `
    -StageScript (Join-Path $PSScriptRoot "stage-flux2-klein9b-identity-v5-extension2000-checkpoints.ps1") `
    -BenchmarkScript (Join-Path $PSScriptRoot "benchmark-flux2-klein9b-identity-v5-extension2000.ps1") `
    -RequireDiffOutputPreservation

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
