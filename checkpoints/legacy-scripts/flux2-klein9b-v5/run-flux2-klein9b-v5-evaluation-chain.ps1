[CmdletBinding()]
param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [int]$GenerationSteps = 50
)

$ErrorActionPreference = "Stop"
$coarseScript = Join-Path $PSScriptRoot "screen-flux2-klein9b-identity-v5.ps1"
$fullScript = Join-Path $PSScriptRoot "full-screen-flux2-klein9b-identity-v5.ps1"
$nineScript = Join-Path $PSScriptRoot "run-flux2-klein9b-v5-nine-scenes-after-screen.ps1"

Write-Host "Beginning v5 coarse checkpoint screen on the RTX 3090."
& $coarseScript -ComfyRoot $ComfyRoot -ComfyUrl $ComfyUrl

Write-Host "Coarse screen completed. Beginning full identity/body/group screen."
& $fullScript -ComfyRoot $ComfyRoot -ComfyUrl $ComfyUrl -Steps $GenerationSteps

Write-Host "A fully passing leader was found. Beginning the exact nine-scene comparison."
& $nineScript -ComfyRoot $ComfyRoot -ComfyUrl $ComfyUrl -Steps $GenerationSteps

Write-Host "The automated v5 evaluation chain completed. Manual full-size visual approval is still required before publication."
