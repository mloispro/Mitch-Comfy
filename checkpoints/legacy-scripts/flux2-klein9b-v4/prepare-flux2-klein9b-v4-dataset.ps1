[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$sourceRoot = Join-Path $repoRoot 'datasets\mitch-identity-stills-v3'
$sourceManifestPath = Join-Path $sourceRoot 'manifest.json'
$targetRoot = Join-Path $repoRoot 'datasets\mitch-identity-stills-v4-klein9b'
$targetDataset = Join-Path $targetRoot 'dataset'
$targetValidation = Join-Path $targetRoot 'validation'
$targetManifestPath = Join-Path $targetRoot 'manifest.json'
$expectedSourceManifestHash = 'D56FE2D752FEBFA63CA0E76689DFD9D4EAAC7443CA086FFA9DFEF51186563003'
$promotedCaptions = [ordered]@{
    val_01_surf_full_body = 'm1tch_person, an adult man, full-body beach cellphone photo standing beside a tall blue surfboard, facing the camera with a natural smile, dark blue long-sleeve rash guard and black wetsuit bottoms, bright overcast beach daylight'
    val_02_body_mirror_sleeveless = 'm1tch_person, an adult man, three-quarter-length hotel mirror cellphone photo, standing at a slight angle with a relaxed neutral expression, sleeveless off-white graphic shirt and light blue shorts, phone visible in one hand, soft indoor daylight'
}
$heldOutIds = @('val_03_navy_upper_body','val_04_window_small_smile','val_05_balcony_opposite_angle','val_06_car_daylight')

if (Test-Path -LiteralPath $targetRoot) { throw "Refusing to overwrite existing dataset: $targetRoot" }
if (-not (Test-Path -LiteralPath $sourceManifestPath -PathType Leaf)) { throw "Missing source manifest: $sourceManifestPath" }
$sourceManifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceManifestPath).Hash.ToUpperInvariant()
if ($sourceManifestHash -cne $expectedSourceManifestHash) {
    throw "Source manifest changed: expected $expectedSourceManifestHash, found $sourceManifestHash"
}
$source = Get-Content -Raw -LiteralPath $sourceManifestPath | ConvertFrom-Json
$sourceTrain = @($source.records | Where-Object split -eq 'train')
$sourceValidation = @($source.records | Where-Object split -eq 'validation')
if ($source.trigger_word -cne 'm1tch_person' -or $sourceTrain.Count -ne 13 -or $sourceValidation.Count -ne 6) {
    throw 'The source dataset must contain the locked 13-train/6-validation split.'
}

New-Item -ItemType Directory -Path $targetDataset,$targetValidation | Out-Null
$records = [System.Collections.Generic.List[object]]::new()
foreach ($record in $sourceTrain) {
    $sourceImage = [string]$record.dataset_file
    $sourceCaption = [IO.Path]::ChangeExtension($sourceImage, '.txt')
    foreach ($path in @($sourceImage,$sourceCaption)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing locked source file: $path" }
    }
    $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceImage).Hash.ToLowerInvariant()
    if ($actualHash -cne ([string]$record.dataset_sha256).ToLowerInvariant()) { throw "Source image hash mismatch: $sourceImage" }
    $caption = (Get-Content -Raw -LiteralPath $sourceCaption).Trim()
    if ($caption -cne ([string]$record.caption).Trim() -or -not $caption.StartsWith('m1tch_person', [StringComparison]::Ordinal)) {
        throw "Source caption mismatch: $sourceCaption"
    }
    $targetImage = Join-Path $targetDataset ([IO.Path]::GetFileName($sourceImage))
    $targetCaption = [IO.Path]::ChangeExtension($targetImage, '.txt')
    Copy-Item -LiteralPath $sourceImage -Destination $targetImage
    Copy-Item -LiteralPath $sourceCaption -Destination $targetCaption
    $records.Add([ordered]@{
        id = [string]$record.id
        split = 'train'
        dataset_file = $targetImage
        dataset_sha256 = $actualHash
        caption = $caption
        source_record_id = [string]$record.id
        promoted_from_validation = $false
    })
}

$promotedIndex = 14
foreach ($id in $promotedCaptions.Keys) {
    $matches = @($sourceValidation | Where-Object id -eq $id)
    if ($matches.Count -ne 1) { throw "Expected one source validation record for $id" }
    $sourceRecord = $matches[0]
    $sourceImage = [string]$sourceRecord.dataset_file
    $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceImage).Hash.ToLowerInvariant()
    if ($actualHash -cne ([string]$sourceRecord.dataset_sha256).ToLowerInvariant()) { throw "Source image hash mismatch: $sourceImage" }
    $suffix = ([IO.Path]::GetFileNameWithoutExtension($sourceImage) -replace '^val_\d+_','')
    $targetImage = Join-Path $targetDataset ('{0:D2}_{1}{2}' -f $promotedIndex,$suffix,[IO.Path]::GetExtension($sourceImage).ToLowerInvariant())
    $targetCaption = [IO.Path]::ChangeExtension($targetImage, '.txt')
    Copy-Item -LiteralPath $sourceImage -Destination $targetImage
    $caption = [string]$promotedCaptions[$id]
    Set-Content -LiteralPath $targetCaption -Value $caption -Encoding utf8
    $records.Add([ordered]@{
        id = [IO.Path]::GetFileNameWithoutExtension($targetImage)
        split = 'train'
        dataset_file = $targetImage
        dataset_sha256 = $actualHash
        caption = $caption
        source_record_id = $id
        promoted_from_validation = $true
    })
    $promotedIndex++
}

foreach ($id in $heldOutIds) {
    $matches = @($sourceValidation | Where-Object id -eq $id)
    if ($matches.Count -ne 1) { throw "Expected one source validation record for $id" }
    $sourceRecord = $matches[0]
    $sourceImage = [string]$sourceRecord.dataset_file
    $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceImage).Hash.ToLowerInvariant()
    if ($actualHash -cne ([string]$sourceRecord.dataset_sha256).ToLowerInvariant()) { throw "Source image hash mismatch: $sourceImage" }
    $targetImage = Join-Path $targetValidation ([IO.Path]::GetFileName($sourceImage))
    Copy-Item -LiteralPath $sourceImage -Destination $targetImage
    $records.Add([ordered]@{
        id = $id
        split = 'validation'
        dataset_file = $targetImage
        dataset_sha256 = $actualHash
        caption = ''
        source_record_id = $id
        promoted_from_validation = $false
    })
}

$images = @(Get-ChildItem -LiteralPath $targetDataset -File | Where-Object Extension -In @('.jpg','.jpeg','.png','.webp'))
$captions = @(Get-ChildItem -LiteralPath $targetDataset -File -Filter '*.txt')
$heldOut = @(Get-ChildItem -LiteralPath $targetValidation -File | Where-Object Extension -In @('.jpg','.jpeg','.png','.webp'))
if ($images.Count -ne 15 -or $captions.Count -ne 15 -or $heldOut.Count -ne 4) {
    throw "Derived split is incomplete: images=$($images.Count), captions=$($captions.Count), validation=$($heldOut.Count)"
}
$trainHashes = [Collections.Generic.HashSet[string]]::new([string[]]@($records | Where-Object split -eq 'train' | ForEach-Object dataset_sha256))
$validationHashes = [Collections.Generic.HashSet[string]]::new([string[]]@($records | Where-Object split -eq 'validation' | ForEach-Object dataset_sha256))
if ($trainHashes.Overlaps($validationHashes)) { throw 'Derived training and validation hashes overlap.' }

$manifest = [ordered]@{
    schema_version = 1
    created_utc = (Get-Date).ToUniversalTime().ToString('o')
    dataset = 'mitch-identity-stills-v4-klein9b'
    purpose = 'Genuine-photo Klein 9B identity retraining split: add two body-composition views while retaining four untouched held-out faces.'
    trigger_word = 'm1tch_person'
    source_manifest = $sourceManifestPath
    source_manifest_sha256 = $sourceManifestHash
    training_count = 15
    validation_count = 4
    promoted_source_records = @($promotedCaptions.Keys)
    held_out_source_records = $heldOutIds
    synthetic_images = 0
    uploaded_images = 0
    records = @($records)
}
$manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $targetManifestPath -Encoding utf8
[ordered]@{
    dataset_root = $targetRoot
    manifest = $targetManifestPath
    manifest_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $targetManifestPath).Hash.ToUpperInvariant()
    train = $images.Count
    validation = $heldOut.Count
} | ConvertTo-Json -Depth 4
