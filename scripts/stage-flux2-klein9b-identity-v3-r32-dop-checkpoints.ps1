[CmdletBinding()]
param(
    [int[]]$Steps = @(600, 700, 800, 900, 1000, 1100, 1200),
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"
$stageScript = Join-Path $PSScriptRoot "stage-flux2-klein9b-identity-v2-r32-checkpoints.ps1"
& $stageScript `
    -Steps $Steps `
    -ComfyRoot $ComfyRoot `
    -RunName "flux2-klein9b-identity-v3-r32-dop" `
    -JobName "m1tch-flux2-klein9b-identity-v3-r32-dop" `
    -RequireDiffOutputPreservation
