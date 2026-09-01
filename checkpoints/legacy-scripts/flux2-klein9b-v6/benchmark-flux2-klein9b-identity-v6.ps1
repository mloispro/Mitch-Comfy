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
    [string]$OutputNamespace = "klein9b-v6-r32-dop-extension2000",
    [string]$StagingManifestName = "checkpoint-staging-extension-to2000.json"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runName = "flux2-klein9b-identity-v6-r32-dop"
$datasetName = "mitch-identity-stills-v6-klein9b"
$lockPath = Join-Path $repoRoot "work\$runName\training-lock.json"
$benchmark = Join-Path $PSScriptRoot "benchmark-flux2-klein9b-identity-v1.ps1"

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}
foreach ($path in @($lockPath, $benchmark)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "V6 evaluation is not locked; missing: $path" }
}
$lock = Get-Content -Raw -LiteralPath $lockPath | ConvertFrom-Json
if (-not [bool]$lock.valid -or [string]$lock.dataset.dataset -cne $datasetName -or
    (Get-Sha256 ([string]$lock.dataset.manifest)) -cne [string]$lock.dataset.manifest_sha256) {
    throw "V6 training lock or dataset manifest changed before evaluation."
}
$manifest = Get-Content -Raw -LiteralPath ([string]$lock.dataset.manifest) | ConvertFrom-Json
$validationRecords = @($manifest.records | Where-Object split -eq "validation")
$referenceFiles = @($validationRecords | ForEach-Object { Split-Path -Leaf ([string]$_.dataset_file) } | Sort-Object)
$calibrationIds = @(
    "val_03_navy_upper_body",
    "val_04_window_small_smile",
    "val_05_balcony_opposite_angle",
    "val_06_car_daylight"
)
$calibrationFiles = @($validationRecords | Where-Object id -In $calibrationIds | ForEach-Object {
    Split-Path -Leaf ([string]$_.dataset_file)
} | Sort-Object)
if ($referenceFiles.Count -ne 6 -or @($referenceFiles | Select-Object -Unique).Count -ne 6 -or
    $calibrationFiles.Count -ne 4) {
    throw "V6 evaluation requires exactly six unique held-outs and the four locked calibration portraits."
}

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
    -WorkRunName $runName `
    -StagingManifestName $StagingManifestName `
    -OutputNamespace $OutputNamespace `
    -ReferenceDatasetName $datasetName `
    -ReferenceSubdirectory "validation" `
    -ReferenceFiles $referenceFiles `
    -CalibrationReferenceFiles $calibrationFiles `
    -BidirectionalProfiles

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
