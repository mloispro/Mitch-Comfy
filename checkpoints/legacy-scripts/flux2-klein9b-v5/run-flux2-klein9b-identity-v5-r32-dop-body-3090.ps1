[CmdletBinding()]
param(
    [ValidateSet("Validate", "Smoke", "AcceptSmoke", "Train", "Resume")]
    [string]$Phase = "Validate"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $PSScriptRoot "run-flux2-klein9b-identity-v2-r32-3090.ps1"
if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) { throw "Missing shared locked DOP runner: $runner" }

& $runner `
    -Phase $Phase `
    -RunName "flux2-klein9b-identity-v5-r32-dop-body" `
    -JobName "m1tch-flux2-klein9b-identity-v5-r32-dop-body" `
    -ProductionConfigName "flux2-klein9b-identity-v5-r32-dop-body-3090.yaml" `
    -SmokeConfigName "flux2-klein9b-identity-v5-r32-dop-body-3090-smoke.yaml" `
    -ResumeConfigName "flux2-klein9b-identity-v5-r32-dop-body-3090-resume-step0301.yaml" `
    -ResumeCheckpointStep 300 `
    -SourceDatasetName "mitch-identity-stills-v4-klein9b" `
    -ExpectedManifestHash "460AECB7D7A13AFAB6C186368A3711A86E415AF72D04D738A6F20BA1D7CEB9D1" `
    -ExpectedTrainCount 15 `
    -ExpectedValidationCount 4 `
    -RequireDiffOutputPreservation

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
