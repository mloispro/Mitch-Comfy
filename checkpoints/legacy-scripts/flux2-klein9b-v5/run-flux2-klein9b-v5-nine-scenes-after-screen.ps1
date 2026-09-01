[CmdletBinding()]
param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [int]$Steps = 50
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $PSScriptRoot "run-flux2-klein9b-v4-nine-scenes-after-screen.ps1"
& $runner `
    -ComfyRoot $ComfyRoot `
    -ComfyUrl $ComfyUrl `
    -Steps $Steps `
    -RunName "flux2-klein9b-identity-v5-r32-dop-body" `
    -JobName "m1tch-flux2-klein9b-identity-v5-r32-dop-body" `
    -OutputNamespace "klein9b-v5-r32-dop-body" `
    -ReferenceDatasetName "mitch-identity-stills-v4-klein9b" `
    -ExpectedRank 32 `
    -RunLabelPrefix "v5-r32-dop-body" `
    -RequireSummaryRank `
    -RequireDiffOutputPreservation

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
