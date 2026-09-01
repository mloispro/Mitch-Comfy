[CmdletBinding()]
param(
    [int[]]$Steps = @(1200, 1400, 1600, 2000),
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runName = "flux2-klein9b-identity-v6-r32-dop"
$jobName = "m1tch-flux2-klein9b-identity-v6-r32-dop"
$lockPath = Join-Path $repoRoot "work\$runName\training-lock.json"
$stager = Join-Path $PSScriptRoot "stage-flux2-klein9b-identity-v2-r32-checkpoints.ps1"

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}
foreach ($path in @($lockPath, $stager)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "V6 checkpoint staging is not locked; missing: $path" }
}
$lock = Get-Content -Raw -LiteralPath $lockPath | ConvertFrom-Json
if (-not [bool]$lock.valid -or [string]$lock.dataset.run -cne $runName -or
    [string]$lock.dataset.job -cne $jobName -or
    (Get-Sha256 ([string]$lock.dataset.manifest)) -cne [string]$lock.dataset.manifest_sha256) {
    throw "V6 training lock or dataset manifest changed before checkpoint staging."
}

& $stager `
    -Steps $Steps `
    -ComfyRoot $ComfyRoot `
    -RunName $runName `
    -JobName $jobName `
    -ExpectedModules 112 `
    -ExpectedRank 32 `
    -ExpectedArchitecture "flux2_klein_9b" `
    -ExpectedBaseModel "black-forest-labs/FLUX.2-klein-base-9B" `
    -ExpectedTrigger "m1tch_person" `
    -ExpectedToolkitCommit "0f788923aef28e3a87fa68cfa15a761d9d499d6c" `
    -TrainingRecordName "training-extension-to2000-validation.json" `
    -StagingManifestName "checkpoint-staging-extension-to2000.json" `
    -ValidationSubdirectory "staging-validation-extension-to2000" `
    -RequireDiffOutputPreservation

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
