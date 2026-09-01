[CmdletBinding()]
param(
    [double[]]$Strengths = @(0.9),
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [int]$Steps = 50
)

$ErrorActionPreference = "Stop"
$screen = Join-Path $PSScriptRoot "full-screen-flux2-klein9b-identity-v4.ps1"
& $screen `
    -Strengths $Strengths `
    -ComfyRoot $ComfyRoot `
    -ComfyUrl $ComfyUrl `
    -Steps $Steps `
    -RunName "flux2-klein9b-identity-v3-r32-dop" `
    -JobName "m1tch-flux2-klein9b-identity-v3-r32-dop" `
    -OutputNamespace "klein9b-v3-r32-dop-extension2000" `
    -ReferenceDatasetName "mitch-identity-stills-v4-klein9b" `
    -ExpectedRank 32 `
    -LeaderCount 4 `
    -ReportSubdirectory "extension-to2000" `
    -BenchmarkScript (Join-Path $PSScriptRoot "benchmark-flux2-klein9b-identity-v3-extension2000.ps1") `
    -RequireDiffOutputPreservation

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
