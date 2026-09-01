[CmdletBinding()]
param(
    [ValidateSet("Validate", "Train")]
    [string]$Phase = "Validate"
)

$ErrorActionPreference = "Stop"
$extension = Join-Path $PSScriptRoot "extend-flux2-klein9b-identity-v5-to2000-3090.ps1"
& $extension `
    -Phase $Phase `
    -RunName "flux2-klein9b-identity-v3-r32-dop" `
    -JobName "m1tch-flux2-klein9b-identity-v3-r32-dop" `
    -ProductionConfigName "flux2-klein9b-identity-v3-r32-dop-3090.yaml" `
    -SmokeConfigName "flux2-klein9b-identity-v3-r32-dop-3090-smoke.yaml" `
    -SourceDatasetName "mitch-identity-stills-v3" `
    -ExpectedManifestHash "D56FE2D752FEBFA63CA0E76689DFD9D4EAAC7443CA086FFA9DFEF51186563003" `
    -ExpectedTrainCount 13 `
    -ExpectedValidationCount 6 `
    -ExtensionConfigName "flux2-klein9b-identity-v3-r32-dop-3090-continue-to2000.yaml" `
    -ExpectedMetadataDataset "mitch-identity-stills-v3" `
    -RunLabel "V3"

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
