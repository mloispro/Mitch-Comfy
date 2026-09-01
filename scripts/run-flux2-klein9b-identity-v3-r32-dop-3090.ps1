[CmdletBinding()]
param(
    [ValidateSet("Validate", "Smoke", "AcceptSmoke", "Train")]
    [string]$Phase = "Validate"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $PSScriptRoot "run-flux2-klein9b-identity-v2-r32-3090.ps1"
& $runner `
    -Phase $Phase `
    -RunName "flux2-klein9b-identity-v3-r32-dop" `
    -JobName "m1tch-flux2-klein9b-identity-v3-r32-dop" `
    -ProductionConfigName "flux2-klein9b-identity-v3-r32-dop-3090.yaml" `
    -SmokeConfigName "flux2-klein9b-identity-v3-r32-dop-3090-smoke.yaml" `
    -RequireDiffOutputPreservation
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
