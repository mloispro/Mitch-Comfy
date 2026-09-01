[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$LoraName,
    [double]$LoraStrength = 0.9,
    [ValidateSet("Quick", "Full")][string]$Profile = "Quick",
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [int]$Steps = 50,
    [double]$Guidance = 4.0,
    [long]$SeedBase = 8676310,
    [int]$TimeoutSeconds = 1800,
    [string]$ComfyOutputRoot = "C:\projects\AI-Tools\ComfyUI\output",
    [string]$OutputNamespace = "klein9b-v5-r32-dop-body-extension2000"
)

$ErrorActionPreference = "Stop"
$benchmark = Join-Path $PSScriptRoot "benchmark-flux2-klein9b-identity-v5.ps1"
& $benchmark `
    -LoraName $LoraName `
    -LoraStrength $LoraStrength `
    -Profile $Profile `
    -ComfyUrl $ComfyUrl `
    -Steps $Steps `
    -Guidance $Guidance `
    -SeedBase $SeedBase `
    -TimeoutSeconds $TimeoutSeconds `
    -ComfyOutputRoot $ComfyOutputRoot `
    -OutputNamespace $OutputNamespace `
    -StagingManifestName "checkpoint-staging-extension-to2000.json"

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
