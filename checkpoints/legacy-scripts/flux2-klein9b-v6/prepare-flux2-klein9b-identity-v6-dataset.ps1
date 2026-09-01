[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$IntakeSpec,
    [string]$DatasetName = "mitch-identity-stills-v6-klein9b",
    [switch]$AuditOnly
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$comfyPython = "C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe"
$auditScript = Join-Path $PSScriptRoot "audit-flux2-klein9b-v6-intake.py"
$baseRoot = Join-Path $repoRoot "datasets\mitch-identity-stills-v3"
$baseManifestPath = Join-Path $baseRoot "manifest.json"
$expectedBaseHash = "D56FE2D752FEBFA63CA0E76689DFD9D4EAAC7443CA086FFA9DFEF51186563003"
$targetRoot = Join-Path $repoRoot ("datasets\{0}" -f $DatasetName)
$workRoot = Join-Path $repoRoot "work\flux2-klein9b-identity-v6-r32-dop\dataset-intake"
$auditPath = Join-Path $workRoot "intake-audit.json"
$contactSheetPath = Join-Path $workRoot "intake-audit-contact-sheet.jpg"
$heldOutBaseIds = @(
    "val_03_navy_upper_body",
    "val_04_window_small_smile",
    "val_05_balcony_opposite_angle",
    "val_06_car_daylight"
)
$removedBaseIds = @("13_full_body_orange_mirror")

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

foreach ($path in @($comfyPython, $auditScript, $baseManifestPath, $IntakeSpec)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required file is missing: $path" }
}
$baseHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $baseManifestPath).Hash.ToUpperInvariant()
if ($baseHash -cne $expectedBaseHash) {
    throw "Locked V3 base manifest changed. Expected $expectedBaseHash, found $baseHash"
}

New-Item -ItemType Directory -Path $workRoot -Force | Out-Null
& $comfyPython $auditScript `
    --spec (Resolve-Path -LiteralPath $IntakeSpec).Path `
    --json-output $auditPath `
    --contact-sheet $contactSheetPath
$auditExit = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $auditPath -PathType Leaf)) {
    throw "The V6 intake audit did not write its report: $auditPath"
}
$audit = Get-Content -Raw -LiteralPath $auditPath | ConvertFrom-Json
if ($auditExit -ne 0 -or -not [bool]$audit.valid) {
    throw "The V6 intake failed its measured genuine-photo gate. Review $auditPath and $contactSheetPath"
}
if ($AuditOnly) {
    [ordered]@{
        valid = $true
        audit = $auditPath
        contact_sheet = $contactSheetPath
    } | ConvertTo-Json -Depth 5
    exit 0
}

if (Test-Path -LiteralPath $targetRoot) {
    throw "Refusing to overwrite an existing V6 dataset: $targetRoot"
}
$targetDataset = Join-Path $targetRoot "dataset"
$targetValidation = Join-Path $targetRoot "validation"
$targetReview = Join-Path $targetRoot "review"
New-Item -ItemType Directory -Path $targetDataset,$targetValidation,$targetReview | Out-Null

$base = Get-Content -Raw -LiteralPath $baseManifestPath | ConvertFrom-Json
$records = [System.Collections.Generic.List[object]]::new()
$baseTrain = @($base.records | Where-Object { $_.split -eq "train" -and $_.id -notin $removedBaseIds })
if ($baseTrain.Count -ne 12) { throw "Expected 12 retained V3 training records after removing the small-face body frame." }
foreach ($record in $baseTrain) {
    $sourceImage = [string]$record.dataset_file
    $sourceCaption = [IO.Path]::ChangeExtension($sourceImage, ".txt")
    foreach ($path in @($sourceImage,$sourceCaption)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing base source file: $path" }
    }
    $targetImage = Join-Path $targetDataset (Split-Path -Leaf $sourceImage)
    $targetCaption = [IO.Path]::ChangeExtension($targetImage, ".txt")
    Copy-Item -LiteralPath $sourceImage -Destination $targetImage
    Copy-Item -LiteralPath $sourceCaption -Destination $targetCaption
    $caption = (Get-Content -Raw -LiteralPath $targetCaption).Trim()
    if (-not $caption.StartsWith("m1tch_person", [StringComparison]::Ordinal)) {
        throw "Base caption trigger is not first: $targetCaption"
    }
    $records.Add([ordered]@{
        id = [string]$record.id
        split = "train"
        role = "retained_v3"
        session = [string]$record.session
        dataset_file = $targetImage
        dataset_sha256 = Get-Sha256 $targetImage
        caption = $caption
        source_record_id = [string]$record.id
        source_manifest = $baseManifestPath
        new_v6_intake = $false
    })
}

$baseValidation = @($base.records | Where-Object { $_.split -eq "validation" -and $_.id -in $heldOutBaseIds })
if ($baseValidation.Count -ne 4) { throw "Expected four locked V3 held-out identity records." }
foreach ($record in $baseValidation) {
    $sourceImage = [string]$record.dataset_file
    $targetImage = Join-Path $targetValidation (Split-Path -Leaf $sourceImage)
    Copy-Item -LiteralPath $sourceImage -Destination $targetImage
    $records.Add([ordered]@{
        id = [string]$record.id
        split = "validation"
        role = "heldout_existing_identity"
        session = [string]$record.session
        dataset_file = $targetImage
        dataset_sha256 = Get-Sha256 $targetImage
        caption = ""
        source_record_id = [string]$record.id
        source_manifest = $baseManifestPath
        new_v6_intake = $false
    })
}

foreach ($item in @($audit.records)) {
    if (-not [bool]$item.valid) { throw "Invalid audit record reached dataset preparation: $($item.id)" }
    $sourceImage = [string]$item.path
    $extension = [IO.Path]::GetExtension($sourceImage).ToLowerInvariant()
    $destinationRoot = if ([string]$item.split -eq "train") { $targetDataset } else { $targetValidation }
    $targetImage = Join-Path $destinationRoot ("{0}{1}" -f ([string]$item.id),$extension)
    Copy-Item -LiteralPath $sourceImage -Destination $targetImage
    if ((Get-Sha256 $sourceImage) -cne (Get-Sha256 $targetImage)) {
        throw "Byte-identical image copy verification failed: $sourceImage"
    }
    $caption = if ([string]$item.split -eq "train") { ([string]$item.caption).Trim() } else { "" }
    if ([string]$item.split -eq "train") {
        if (-not $caption.StartsWith("m1tch_person", [StringComparison]::Ordinal)) {
            throw "Intake caption trigger is not first: $($item.id)"
        }
        Set-Content -LiteralPath ([IO.Path]::ChangeExtension($targetImage, ".txt")) -Value $caption -Encoding utf8
    }
    $records.Add([ordered]@{
        id = [string]$item.id
        split = [string]$item.split
        role = [string]$item.role
        session = [string]$item.session
        dataset_file = $targetImage
        dataset_sha256 = Get-Sha256 $targetImage
        caption = $caption
        source_file = $sourceImage
        source_sha256 = [string]$item.sha256
        new_v6_intake = $true
        measured_yaw_degrees = [double]$item.yaw_degrees
        measured_face_height_pixels = [double]$item.face_height_pixels
        measured_face_sharpness = [double]$item.face_sharpness
        detector_confidence = [double]$item.detector_confidence
        identity_centroid_similarity_diagnostic = [double]$item.identity_centroid_similarity_diagnostic
        attestations = $item.attestations
    })
}

$train = @($records | Where-Object split -eq "train")
$validation = @($records | Where-Object split -eq "validation")
$trainImages = @(Get-ChildItem -LiteralPath $targetDataset -File | Where-Object Extension -In @(".jpg",".jpeg",".png",".webp"))
$trainCaptions = @(Get-ChildItem -LiteralPath $targetDataset -File -Filter "*.txt")
$validationImages = @(Get-ChildItem -LiteralPath $targetValidation -File | Where-Object Extension -In @(".jpg",".jpeg",".png",".webp"))
if ($train.Count -ne 18 -or $validation.Count -ne 6 -or $trainImages.Count -ne 18 -or $trainCaptions.Count -ne 18 -or $validationImages.Count -ne 6) {
    throw "V6 split mismatch: records=$($train.Count)/$($validation.Count), files=$($trainImages.Count)/$($trainCaptions.Count)/$($validationImages.Count)"
}
$trainHashes = [Collections.Generic.HashSet[string]]::new([string[]]@($train | ForEach-Object dataset_sha256))
$validationHashes = [Collections.Generic.HashSet[string]]::new([string[]]@($validation | ForEach-Object dataset_sha256))
if ($trainHashes.Count -ne 18 -or $validationHashes.Count -ne 6 -or $trainHashes.Overlaps($validationHashes)) {
    throw "V6 contains an exact duplicate or training/validation overlap."
}

Copy-Item -LiteralPath $auditPath -Destination (Join-Path $targetReview "intake-audit.json")
Copy-Item -LiteralPath $contactSheetPath -Destination (Join-Path $targetReview "intake-audit-contact-sheet.jpg")
$manifestPath = Join-Path $targetRoot "manifest.json"
$manifest = [ordered]@{
    schema_version = 2
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    dataset = $DatasetName
    purpose = "Genuine-photo Klein Base 9B identity V6: measured true-profile geometry, sharp body coverage, and independent profile holdouts."
    trigger_word = "m1tch_person"
    training_count = 18
    validation_count = 6
    base_source_manifest = $baseManifestPath
    base_source_manifest_sha256 = $baseHash
    removed_base_records = @([ordered]@{
        id = "13_full_body_orange_mirror"
        reason = "Measured face height 120.8px was too small to teach identity in full-body scenes."
    })
    excluded_v5_promotions = @("val_01_surf_full_body","val_02_body_mirror_sleeveless")
    intake_spec = (Resolve-Path -LiteralPath $IntakeSpec).Path
    intake_spec_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $IntakeSpec).Hash.ToUpperInvariant()
    intake_audit = (Join-Path $targetReview "intake-audit.json")
    intake_audit_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetReview "intake-audit.json")).Hash.ToUpperInvariant()
    synthetic_images = 0
    uploaded_images = 0
    pixel_policy = "Every image is a byte-identical genuine still copy; no crop, resize, enhancement, restoration, identity edit, or generated pixels."
    records = @($records)
}
$manifest | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $manifestPath -Encoding utf8

$readme = @"
# Mitch identity stills V6 for FLUX.2 Klein Base 9B

- Training pairs: 18
- Held-out identity/profile photographs: 6
- Trigger: ``m1tch_person``
- Images are byte-identical local genuine stills; no uploads or generated pixels.
- The weak V3 small-face full-body frame and both failed V5 promoted body frames are excluded.
- See ``review/intake-audit.json`` for measured yaw, face size, sharpness, hashes, and attestations.

Do not train until ``lock-flux2-klein9b-identity-v6-training.ps1`` creates configs bound to this exact manifest hash.
"@
Set-Content -LiteralPath (Join-Path $targetRoot "README.md") -Value $readme -Encoding utf8

[ordered]@{
    valid = $true
    dataset_root = $targetRoot
    manifest = $manifestPath
    manifest_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToUpperInvariant()
    train = 18
    validation = 6
    audit = (Join-Path $targetReview "intake-audit.json")
    contact_sheet = (Join-Path $targetReview "intake-audit-contact-sheet.jpg")
} | ConvertTo-Json -Depth 6
