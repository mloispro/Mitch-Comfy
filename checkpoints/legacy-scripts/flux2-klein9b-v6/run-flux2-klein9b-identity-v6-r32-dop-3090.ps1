[CmdletBinding()]
param(
    [ValidateSet("Validate", "Smoke", "AcceptSmoke", "Train", "Resume")]
    [string]$Phase = "Validate"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runName = "flux2-klein9b-identity-v6-r32-dop"
$jobName = "m1tch-flux2-klein9b-identity-v6-r32-dop"
$datasetName = "mitch-identity-stills-v6-klein9b"
$lockPath = Join-Path $repoRoot "work\$runName\training-lock.json"
$runner = Join-Path $PSScriptRoot "run-flux2-klein9b-identity-v2-r32-3090.ps1"

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}
foreach ($path in @($lockPath, $runner)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "V6 is not training-locked; missing: $path" }
}
$lock = Get-Content -Raw -LiteralPath $lockPath | ConvertFrom-Json
if (-not [bool]$lock.valid -or [int]$lock.schema_version -ne 1 -or
    [string]$lock.dataset.run -cne $runName -or [string]$lock.dataset.job -cne $jobName -or
    [string]$lock.dataset.dataset -cne $datasetName -or [int]$lock.dataset.train -ne 18 -or
    [int]$lock.dataset.validation -ne 6 -or $null -ne $lock.dataset.fallback_gpu) {
    throw "V6 training lock is invalid or targets the wrong dataset/GPU policy."
}
if ((Get-Sha256 ([string]$lock.dataset.manifest)) -cne [string]$lock.dataset.manifest_sha256) {
    throw "V6 dataset manifest changed after training lock."
}
foreach ($name in @("production", "smoke", "resume_step0301", "continue_to2000")) {
    $record = $lock.configs.$name
    if (-not (Test-Path -LiteralPath ([string]$record.path) -PathType Leaf) -or
        (Get-Sha256 ([string]$record.path)) -cne [string]$record.sha256) {
        throw "Locked V6 config is missing or changed: $name"
    }
}

& $runner `
    -Phase $Phase `
    -RunName $runName `
    -JobName $jobName `
    -ProductionConfigName "flux2-klein9b-identity-v6-r32-dop-3090.yaml" `
    -SmokeConfigName "flux2-klein9b-identity-v6-r32-dop-3090-smoke.yaml" `
    -ResumeConfigName "flux2-klein9b-identity-v6-r32-dop-3090-resume-step0301.yaml" `
    -ResumeCheckpointStep 300 `
    -SourceDatasetName $datasetName `
    -ExpectedManifestHash ([string]$lock.dataset.manifest_sha256) `
    -ExpectedTrainCount 18 `
    -ExpectedValidationCount 6 `
    -RequireDiffOutputPreservation

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
