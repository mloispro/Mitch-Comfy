[CmdletBinding()]
param(
    [int[]]$Steps = @(100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200),
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"
$stager = Join-Path $PSScriptRoot "stage-flux2-klein9b-identity-v2-r32-checkpoints.ps1"

& $stager `
    -Steps $Steps `
    -ComfyRoot $ComfyRoot `
    -RunName "flux2-klein9b-identity-v5-r32-dop-body" `
    -JobName "m1tch-flux2-klein9b-identity-v5-r32-dop-body" `
    -ExpectedModules 112 `
    -ExpectedRank 32 `
    -ExpectedArchitecture "flux2_klein_9b" `
    -ExpectedBaseModel "black-forest-labs/FLUX.2-klein-base-9B" `
    -ExpectedTrigger "m1tch_person" `
    -ExpectedToolkitCommit "0f788923aef28e3a87fa68cfa15a761d9d499d6c" `
    -RequireDiffOutputPreservation

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
