[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$missingProcessId = [int]::MaxValue

& (Join-Path $PSScriptRoot 'continue-flux2-klein9b-v3-dop-after-training.ps1') `
    -TrainingProcessId $missingProcessId
& (Join-Path $PSScriptRoot 'continue-flux2-klein9b-v3-dop-after-coarse-screen.ps1') `
    -CoarseScreenProcessId $missingProcessId
& (Join-Path $PSScriptRoot 'continue-flux2-klein9b-v3-dop-after-full-screen.ps1') `
    -FullScreenProcessId $missingProcessId
& (Join-Path $PSScriptRoot 'continue-flux2-klein9b-v3-dop-completion-audit.ps1') `
    -NineSceneProcessId $missingProcessId
