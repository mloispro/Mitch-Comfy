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
    [string]$OutputNamespace = "klein9b-v5-r32-dop-body",
    [string]$StagingManifestName = "checkpoint-staging.json"
)

$ErrorActionPreference = "Stop"
$benchmark = Join-Path $PSScriptRoot "benchmark-flux2-klein9b-identity-v1.ps1"
$heldOutReferences = @(
    "val_03_navy_upper_body.jpg",
    "val_04_window_small_smile.jpg",
    "val_05_balcony_opposite_angle.jpg",
    "val_06_car_daylight.jpg"
)

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
    -WorkRunName "flux2-klein9b-identity-v5-r32-dop-body" `
    -StagingManifestName $StagingManifestName `
    -OutputNamespace $OutputNamespace `
    -ReferenceDatasetName "mitch-identity-stills-v4-klein9b" `
    -ReferenceSubdirectory "validation" `
    -ReferenceFiles $heldOutReferences

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
