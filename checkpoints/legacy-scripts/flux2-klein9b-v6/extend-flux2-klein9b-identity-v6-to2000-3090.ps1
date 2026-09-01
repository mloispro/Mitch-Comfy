[CmdletBinding()]
param(
    [ValidateSet("Validate", "Train")]
    [string]$Phase = "Validate"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runName = "flux2-klein9b-identity-v6-r32-dop"
$jobName = "m1tch-flux2-klein9b-identity-v6-r32-dop"
$datasetName = "mitch-identity-stills-v6-klein9b"
$lockPath = Join-Path $repoRoot "work\$runName\training-lock.json"
$extensionRunner = Join-Path $PSScriptRoot "extend-flux2-klein9b-identity-v5-to2000-3090.ps1"

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}
foreach ($path in @($lockPath, $extensionRunner)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "V6 extension is not training-locked; missing: $path" }
}
$lock = Get-Content -Raw -LiteralPath $lockPath | ConvertFrom-Json
if (-not [bool]$lock.valid -or [string]$lock.dataset.run -cne $runName -or
    [string]$lock.dataset.job -cne $jobName -or [string]$lock.dataset.dataset -cne $datasetName -or
    $null -ne $lock.dataset.fallback_gpu) {
    throw "V6 training lock is invalid or permits a fallback GPU."
}
if ((Get-Sha256 ([string]$lock.dataset.manifest)) -cne [string]$lock.dataset.manifest_sha256) {
    throw "V6 dataset manifest changed after training lock."
}
foreach ($name in @("production", "smoke", "continue_to2000")) {
    $record = $lock.configs.$name
    if (-not (Test-Path -LiteralPath ([string]$record.path) -PathType Leaf) -or
        (Get-Sha256 ([string]$record.path)) -cne [string]$record.sha256) {
        throw "Locked V6 config is missing or changed: $name"
    }
}

& $extensionRunner `
    -Phase $Phase `
    -RunName $runName `
    -JobName $jobName `
    -ProductionConfigName "flux2-klein9b-identity-v6-r32-dop-3090.yaml" `
    -SmokeConfigName "flux2-klein9b-identity-v6-r32-dop-3090-smoke.yaml" `
    -SourceDatasetName $datasetName `
    -ExpectedManifestHash ([string]$lock.dataset.manifest_sha256) `
    -ExpectedTrainCount 18 `
    -ExpectedValidationCount 6 `
    -ExtensionConfigName "flux2-klein9b-identity-v6-r32-dop-3090-continue-to2000.yaml" `
    -ExpectedMetadataDataset $datasetName `
    -RunLabel "V6"

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
