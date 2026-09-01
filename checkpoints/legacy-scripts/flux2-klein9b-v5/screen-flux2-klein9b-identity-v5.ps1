[CmdletBinding()]
param(
    [int[]]$CheckpointSteps = @(600, 700, 800, 900, 1000, 1100, 1200),
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
    -OutputNamespace "klein9b-v5-r32-dop-body" `
    -ReferenceDatasetName "mitch-identity-stills-v4-klein9b" `
    -ExpectedRank 32 `
    -ExpectedTrainingSteps 1200 `
    -StageScript (Join-Path $PSScriptRoot "stage-flux2-klein9b-identity-v5-checkpoints.ps1") `
    -BenchmarkScript (Join-Path $PSScriptRoot "benchmark-flux2-klein9b-identity-v5.ps1") `
    -RequireDiffOutputPreservation

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
