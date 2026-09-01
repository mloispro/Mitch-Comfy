[CmdletBinding()]
param(
    [string]$DatasetName = "mitch-identity-stills-v6-klein9b",
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runName = "flux2-klein9b-identity-v6-r32-dop"
$jobName = "m1tch-flux2-klein9b-identity-v6-r32-dop"
$datasetRoot = Join-Path $repoRoot "datasets\$DatasetName"
$manifestPath = Join-Path $datasetRoot "manifest.json"
$workRoot = Join-Path $repoRoot "work\$runName"
$lockPath = Join-Path $workRoot "training-lock.json"
$oldRun = "flux2-klein9b-identity-v5-r32-dop-body"
$oldJob = "m1tch-flux2-klein9b-identity-v5-r32-dop-body"
$oldDataset = "mitch-identity-stills-v4-klein9b"
$oldManifestHash = "460AECB7D7A13AFAB6C186368A3711A86E415AF72D04D738A6F20BA1D7CEB9D1"
$oldVersion = "5.0-r32-dop-body"
$newVersion = "6.0-r32-dop-measured-views"
$evaluationScriptPaths = @(
    (Join-Path $repoRoot "scripts\benchmark-flux2-klein9b-identity-v1.ps1"),
    (Join-Path $repoRoot "scripts\benchmark-flux2-klein9b-identity-v6.ps1"),
    (Join-Path $repoRoot "scripts\stage-flux2-klein9b-identity-v2-r32-checkpoints.ps1"),
    (Join-Path $repoRoot "scripts\stage-flux2-klein9b-identity-v6-extension2000-checkpoints.ps1"),
    (Join-Path $repoRoot "scripts\screen-flux2-klein9b-identity-v4.ps1"),
    (Join-Path $repoRoot "scripts\screen-flux2-klein9b-identity-v6-extension2000.ps1"),
    (Join-Path $repoRoot "scripts\full-screen-flux2-klein9b-identity-v4.ps1"),
    (Join-Path $repoRoot "scripts\full-screen-flux2-klein9b-identity-v6-extension2000.ps1"),
    (Join-Path $repoRoot "scripts\run-flux2-klein9b-v6-extension2000-comparison.ps1"),
    (Join-Path $repoRoot "scripts\publish-flux2-klein9b-identity-v6-r32-dop.ps1"),
    (Join-Path $repoRoot "scripts\evaluate-face-likeness.py"),
    (Join-Path $repoRoot "scripts\evaluate-flux2-dev-identity.py"),
    (Join-Path $repoRoot "scripts\build-flux2-klein9b-v3-dop-screen-sheet.py"),
    (Join-Path $repoRoot "custom_nodes\ComfyUI-AIToolkit-Training\identity_leakage.py")
)

$templateSpecs = @(
    [ordered]@{
        key = "production"
        template = Join-Path $repoRoot "config\flux2-klein9b-identity-v5-r32-dop-body-3090.yaml"
        template_sha256 = "3A90B48EB6932644A01C710C0FE8026CEA98D0306F3CE7C407403CDCB96A76B6"
        output = Join-Path $repoRoot "config\flux2-klein9b-identity-v6-r32-dop-3090.yaml"
        steps = 1200
    },
    [ordered]@{
        key = "smoke"
        template = Join-Path $repoRoot "config\flux2-klein9b-identity-v5-r32-dop-body-3090-smoke.yaml"
        template_sha256 = "4FA8A8466BD34676619D749724AD2397201E7B7EDD67D7D0A93282DDF43329A7"
        output = Join-Path $repoRoot "config\flux2-klein9b-identity-v6-r32-dop-3090-smoke.yaml"
        steps = 40
    },
    [ordered]@{
        key = "resume_step0301"
        template = Join-Path $repoRoot "config\flux2-klein9b-identity-v5-r32-dop-body-3090-resume-step0301.yaml"
        template_sha256 = "4272C66D3209AB0D267AEE43B6CA5D2463692D50B7EE45BB8ED9EF4EBC853A8A"
        output = Join-Path $repoRoot "config\flux2-klein9b-identity-v6-r32-dop-3090-resume-step0301.yaml"
        steps = 1200
    },
    [ordered]@{
        key = "continue_to2000"
        template = Join-Path $repoRoot "config\flux2-klein9b-identity-v5-r32-dop-body-3090-continue-to2000.yaml"
        template_sha256 = "432B5F31328B84190CDB10055D1654E3010002768060A2DDC3910DA78FF9F554"
        output = Join-Path $repoRoot "config\flux2-klein9b-identity-v6-r32-dop-3090-continue-to2000.yaml"
        steps = 2000
    }
)

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Assert-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required file is missing: $Path" }
}

Assert-File $manifestPath
$manifestHash = Get-Sha256 $manifestPath
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
if ([int]$manifest.schema_version -ne 2 -or [string]$manifest.dataset -cne $DatasetName -or
    [string]$manifest.trigger_word -cne "m1tch_person" -or [int]$manifest.training_count -ne 18 -or
    [int]$manifest.validation_count -ne 6 -or [int]$manifest.synthetic_images -ne 0 -or
    [int]$manifest.uploaded_images -ne 0) {
    throw "The V6 dataset manifest does not prove the locked 18-train/6-validation genuine-photo split."
}

$auditPath = [string]$manifest.intake_audit
Assert-File $auditPath
if ((Get-Sha256 $auditPath) -cne [string]$manifest.intake_audit_sha256) {
    throw "The copied V6 intake audit hash no longer matches the dataset manifest."
}
$audit = Get-Content -Raw -LiteralPath $auditPath | ConvertFrom-Json
if (-not [bool]$audit.valid -or @($audit.records).Count -ne 8 -or @($audit.records | Where-Object { -not [bool]$_.valid }).Count -ne 0) {
    throw "The V6 intake audit does not prove eight passing new genuine photographs."
}

$records = @($manifest.records)
$trainingRecords = @($records | Where-Object split -eq "train")
$validationRecords = @($records | Where-Object split -eq "validation")
if ($records.Count -ne 24 -or $trainingRecords.Count -ne 18 -or $validationRecords.Count -ne 6) {
    throw "V6 record counts changed after dataset preparation."
}
$seenHashes = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($record in $records) {
    $image = [string]$record.dataset_file
    Assert-File $image
    $actualHash = Get-Sha256 $image
    if ($actualHash -cne ([string]$record.dataset_sha256).ToUpperInvariant()) { throw "Dataset image hash changed: $image" }
    if (-not $seenHashes.Add($actualHash)) { throw "Duplicate image hash in V6 manifest: $image" }
    if ([string]$record.split -eq "train") {
        $captionPath = [IO.Path]::ChangeExtension($image, ".txt")
        Assert-File $captionPath
        $caption = (Get-Content -Raw -LiteralPath $captionPath).Trim()
        if (-not $caption.StartsWith("m1tch_person", [StringComparison]::Ordinal) -or
            ([regex]::Matches($caption, [regex]::Escape("m1tch_person"))).Count -ne 1 -or
            $caption -cne ([string]$record.caption).Trim()) {
            throw "Training caption changed or has an invalid trigger: $captionPath"
        }
    }
}

$datasetFolder = Join-Path $datasetRoot "dataset"
$validationFolder = Join-Path $datasetRoot "validation"
$trainFiles = @(Get-ChildItem -LiteralPath $datasetFolder -File -Force)
$trainImages = @($trainFiles | Where-Object Extension -In @(".jpg", ".jpeg", ".png", ".webp"))
$trainCaptions = @($trainFiles | Where-Object Extension -eq ".txt")
$validationImages = @(Get-ChildItem -LiteralPath $validationFolder -File -Force | Where-Object Extension -In @(".jpg", ".jpeg", ".png", ".webp"))
if ($trainImages.Count -ne 18 -or $trainCaptions.Count -ne 18 -or $validationImages.Count -ne 6) {
    throw "V6 filesystem counts are no longer exactly 18 image/TXT pairs and six held-outs."
}
if (@(Get-ChildItem -LiteralPath $datasetFolder -Directory -Force).Count -ne 0 -or
    (Test-Path -LiteralPath (Join-Path $datasetFolder ".aitk_size.json"))) {
    throw "The source V6 dataset contains a stale AI-Toolkit cache or size index."
}

foreach ($spec in $templateSpecs) {
    Assert-File ([string]$spec.template)
    if ((Get-Sha256 ([string]$spec.template)) -cne [string]$spec.template_sha256) {
        throw "Proven V5 recipe template changed: $($spec.template)"
    }
    if (Test-Path -LiteralPath ([string]$spec.output)) { throw "Refusing to overwrite a V6 config: $($spec.output)" }
}
foreach ($path in $evaluationScriptPaths) { Assert-File $path }
if (Test-Path -LiteralPath $lockPath) { throw "Refusing to overwrite an existing V6 training lock: $lockPath" }

$newControlledChange = "Keep the proven rank-32, 8e-5, DOP recipe unchanged; replace only the failed view coverage with measured true profiles, independent profile holdouts, and sharp body photographs from the locked V6 dataset."
$newAcceptance = "Train through 2000 and compare checkpoints 1200, 1400, 1600, and 2000 with identical LoRA-only prompts and seeds; reject profile drift, body/anatomy failure, or any multiperson identity leakage before visual approval."
$rendered = [ordered]@{}
foreach ($spec in $templateSpecs) {
    $text = Get-Content -Raw -LiteralPath ([string]$spec.template)
    $text = $text.Replace($oldRun, $runName).Replace($oldJob, $jobName).Replace($oldDataset, $DatasetName)
    $text = $text.Replace($oldManifestHash, $manifestHash).Replace($oldVersion, $newVersion)
    $text = [regex]::Replace($text, '(?m)^  controlled_change: .+$', "  controlled_change: $newControlledChange")
    $text = [regex]::Replace($text, '(?m)^  acceptance: .+$', "  acceptance: $newAcceptance")
    $text = [regex]::Replace(
        $text,
        '(?m)^  purpose: Isolated 40-update rank-32 DOP acceptance smoke.+$',
        '  purpose: Isolated 40-update rank-32 DOP acceptance smoke with the 18 locked V6 genuine training photographs; never publish this adapter.'
    )
    if ($text.Contains($oldRun) -or $text.Contains($oldJob) -or $text.Contains($oldDataset) -or
        $text.Contains($oldManifestHash) -or -not $text.Contains($runName) -or
        -not $text.Contains($jobName) -or -not $text.Contains($DatasetName) -or
        -not $text.Contains($manifestHash) -or
        $text -notmatch ("(?m)^        steps: {0}$" -f [int]$spec.steps)) {
        throw "Rendered V6 $($spec.key) config failed its binding checks."
    }
    foreach ($required in @(
        "        linear: 32", "        linear_alpha: 32", "        lr: 0.00008",
        "        diff_output_preservation: true", "        diff_output_preservation_class: man",
        "        resolution: [768, 1024]", "        qtype: qfloat8", "      device: cuda:0",
        "  target_gpu: NVIDIA GeForce RTX 3090", "  fallback_gpu: none"
    )) {
        if (-not $text.Contains($required)) { throw "Rendered V6 $($spec.key) config lost locked setting: $required" }
    }
    $rendered[[string]$spec.key] = $text
}

$validation = [ordered]@{
    valid = $true
    dataset = $DatasetName
    manifest = $manifestPath
    manifest_sha256 = $manifestHash
    train = 18
    validation = 6
    intake_audit = $auditPath
    intake_audit_sha256 = Get-Sha256 $auditPath
    run = $runName
    job = $jobName
    target_gpu = "physical GPU 0 / NVIDIA GeForce RTX 3090"
    fallback_gpu = $null
    production_steps = 1200
    final_target_steps = 2000
    comparison_steps = @(1200, 1400, 1600, 2000)
}
if ($ValidateOnly) {
    $validation | ConvertTo-Json -Depth 6
    exit 0
}

New-Item -ItemType Directory -Path $workRoot -Force | Out-Null
foreach ($spec in $templateSpecs) {
    Set-Content -LiteralPath ([string]$spec.output) -Value ([string]$rendered[[string]$spec.key]) -Encoding utf8
}
$configRecords = [ordered]@{}
foreach ($spec in $templateSpecs) {
    $configRecords[[string]$spec.key] = [ordered]@{
        path = [string]$spec.output
        sha256 = Get-Sha256 ([string]$spec.output)
        source_template = [string]$spec.template
        source_template_sha256 = [string]$spec.template_sha256
    }
}
$evaluationScriptRecords = @($evaluationScriptPaths | ForEach-Object {
    [ordered]@{ path = $_; sha256 = Get-Sha256 $_ }
})
$lock = [ordered]@{
    schema_version = 1
    valid = $true
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    purpose = "Immutable dataset/config binding for the V6 FLUX.2 Klein Base 9B identity LoRA."
    dataset = $validation
    configs = $configRecords
    evaluation = [ordered]@{
        scripts = $evaluationScriptRecords
        checkpoint_steps = @(1200, 1400, 1600, 2000)
        scoring_heldouts = 6
        stable_calibration_heldouts = 4
        bidirectional_profile_tests = $true
        full_body_and_crowd_tests = $true
        reference_conditioning = $false
        identity_pass = $false
        face_swap = $false
    }
    recipe = [ordered]@{
        architecture = "flux2_klein_9b"
        base_model = "black-forest-labs/FLUX.2-klein-base-9B"
        network = "linear LoRA rank 32 / alpha 32, transformer only"
        optimizer = "AdamW 8-bit"
        learning_rate = 0.00008
        scheduler = "constant"
        resolutions = @(768, 1024)
        diff_output_preservation = $true
        checkpoint_every = 100
        smoke_updates = 40
        production_updates = 1200
        final_updates = 2000
    }
}
$lock | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $lockPath -Encoding utf8
[ordered]@{
    valid = $true
    lock = $lockPath
    lock_sha256 = Get-Sha256 $lockPath
    configs = $configRecords
    next = "Run Validate, then Smoke, AcceptSmoke, Train, and the controlled extension to 2000 on physical GPU 0."
} | ConvertTo-Json -Depth 10
