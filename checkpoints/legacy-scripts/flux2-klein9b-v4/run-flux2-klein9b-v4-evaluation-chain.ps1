[CmdletBinding()]
param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [int]$GenerationSteps = 50
)

$ErrorActionPreference = "Stop"
$coarseScript = Join-Path $PSScriptRoot "screen-flux2-klein9b-identity-v4.ps1"
$fullScript = Join-Path $PSScriptRoot "full-screen-flux2-klein9b-identity-v4.ps1"
$nineScript = Join-Path $PSScriptRoot "run-flux2-klein9b-v4-nine-scenes-after-screen.ps1"

Write-Host "Beginning v4 coarse checkpoint screen on the RTX 3090."
& $coarseScript `
    -ComfyRoot $ComfyRoot `
    -ComfyUrl $ComfyUrl

Write-Host "Coarse screen passed. Beginning full identity/body/group screen."
& $fullScript `
    -ComfyRoot $ComfyRoot `
    -ComfyUrl $ComfyUrl `
    -Steps $GenerationSteps

Write-Host "Full screen passed. Beginning the exact nine-scene comparison."
& $nineScript `
    -ComfyRoot $ComfyRoot `
    -ComfyUrl $ComfyUrl `
    -Steps $GenerationSteps

Write-Host "The automated v4 evaluation chain completed. Manual full-size visual approval is still required before publication."
