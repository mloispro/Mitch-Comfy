[CmdletBinding()]
param(
    [ValidateSet('Validate','Smoke','AcceptSmoke','Train')]
    [string]$Phase = 'Validate'
)

$ErrorActionPreference = 'Stop'
$runner = Join-Path $PSScriptRoot 'run-flux2-klein9b-identity-v1-3090.ps1'
if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) { throw "Missing shared locked runner: $runner" }

& $runner `
    -Phase $Phase `
    -SourceDatasetName 'mitch-identity-stills-v4-klein9b' `
    -RunName 'flux2-klein9b-identity-v4-r16-diverse' `
    -JobName 'm1tch-flux2-klein9b-identity-v4-r16-diverse' `
    -ExpectedManifestHash '460AECB7D7A13AFAB6C186368A3711A86E415AF72D04D738A6F20BA1D7CEB9D1' `
    -ExpectedTrainCount 15 `
    -ExpectedValidationCount 4 `
    -ProductionSteps 1500 `
    -Rank 16

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
