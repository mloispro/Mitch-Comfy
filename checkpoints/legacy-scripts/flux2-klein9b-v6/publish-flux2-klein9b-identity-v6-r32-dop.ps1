[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ApprovalRecord,
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runName = "flux2-klein9b-identity-v6-r32-dop"
$jobName = "m1tch-flux2-klein9b-identity-v6-r32-dop"
$runRoot = Join-Path $repoRoot "work\$runName"
$lockPath = Join-Path $runRoot "training-lock.json"
$trainingPath = Join-Path $runRoot "train\training-extension-to2000-validation.json"
$comparisonPath = Join-Path $runRoot "benchmarks\extension-to2000\comparison-validation.json"
$summaryPath = Join-Path $runRoot "benchmarks\extension-to2000\full-screen-summary.json"
$sheetPath = Join-Path $runRoot "benchmarks\extension-to2000\full-screen-sheet.png"
$publicationPath = Join-Path $runRoot "publication-record.json"
$validator = Join-Path $PSScriptRoot "validate-zimage-lora.py"
$toolkitPython = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"

function Read-Json([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required JSON is missing: $Path" }
    return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}
function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required file is missing: $Path" }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

if (Test-Path -LiteralPath $publicationPath -PathType Leaf) {
    throw "A V6 publication record already exists; refusing duplicate publication."
}
foreach ($path in @($lockPath, $trainingPath, $comparisonPath, $summaryPath, $sheetPath, $validator, $toolkitPython)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Publication prerequisite is missing: $path" }
}
$approvalPath = [IO.Path]::GetFullPath($ApprovalRecord)
$approval = Read-Json $approvalPath
$lock = Read-Json $lockPath
$training = Read-Json $trainingPath
$comparison = Read-Json $comparisonPath
$summary = Read-Json $summaryPath
if (-not [bool]$lock.valid -or -not [bool]$training.valid -or -not [bool]$comparison.valid -or
    [int]$training.total_steps -ne 2000 -or -not [bool]$training.zero_ooms -or
    [string]$training.gpu -notmatch "RTX 3090" -or $null -ne $training.fallback_gpu -or
    [bool]$comparison.published -or [bool]$summary.published) {
    throw "V6 training or comparison provenance is invalid or already published."
}
if (-not [bool]$approval.approved -or [string]$approval.approved_by -cne "Mitch" -or
    [string]$approval.run_name -cne $runName) {
    throw "Publication requires an explicit approval record from Mitch for this V6 run."
}
$requiredApprovals = [ordered]@{
    full_size_review_completed = "full-size review"
    thumbnail_review_completed = "thumbnail review"
    identity_and_face_shape_approved = "identity and face shape"
    profile_image_left_approved = "image-left profile identity"
    profile_image_right_approved = "image-right profile identity"
    rooftop_down_left_approved = "the rooftop head and eyes pointing down-left without eye contact"
    full_body_identity_and_anatomy_approved = "full-body identity, proportions, arms, and anatomy"
    exactly_one_mitch_in_group_approved = "exactly one Mitch in the group"
    bystander_diversity_approved = "distinct bystander identities"
    hands_objects_and_person_count_approved = "hands, objects, and intended person count"
    scene_detail_and_whole_frame_integration_approved = "scene detail and whole-frame integration"
}
foreach ($field in $requiredApprovals.Keys) {
    if (-not [bool]$approval.$field) { throw "Approval must explicitly confirm $($requiredApprovals[$field])." }
}
if ([string]$approval.full_screen_summary_sha256 -cne (Get-Sha256 $summaryPath) -or
    [string]$approval.comparison_sheet_sha256 -cne (Get-Sha256 $sheetPath)) {
    throw "Approval hashes do not match the reviewed V6 summary and sheet."
}
$leader = @($summary.results | Sort-Object rank | Select-Object -First 1)[0]
if (-not $leader -or -not [bool]$leader.automatic_gates_passed -or
    -not [bool]$leader.core_gate_passed -or -not [bool]$leader.crowd_gate_passed -or
    @($leader.crowd_leakage_failures).Count -ne 0) {
    throw "The selected V6 leader did not pass every automatic identity/leakage gate."
}
$step = [int]$leader.step
$strength = [double]$leader.strength
if ($step -notin @(1200, 1400, 1600, 2000) -or [int]$approval.checkpoint_step -ne $step -or
    [math]::Abs([double]$approval.strength - $strength) -gt 1e-6) {
    throw "Approval does not match the selected V6 checkpoint and strength."
}
$sourcePath = Join-Path $runRoot ("train\ai-toolkit-output\{0}\{0}_{1:D9}.safetensors" -f $jobName, $step)
$sourceHash = Get-Sha256 $sourcePath
$validationPath = Join-Path $runRoot "publication-lora-validation.json"
& $toolkitPython $validator $sourcePath --expected-modules 112 --expected-rank 32 --require-nonzero --json-output $validationPath | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Selected V6 checkpoint failed final finite rank-32 validation." }
$validation = Read-Json $validationPath
$trainingInfo = [string]$validation.metadata.training_info | ConvertFrom-Json
if (-not [bool]$validation.valid -or [int]$trainingInfo.step -ne $step -or
    [string]$validation.metadata.name -cne $jobName -or
    [string]$validation.metadata.dataset -cne [string]$lock.dataset.dataset -or
    [string]$validation.metadata.source_manifest_sha256 -cne [string]$lock.dataset.manifest_sha256) {
    throw "Selected V6 checkpoint metadata does not match the locked run."
}

$loraRoot = [IO.Path]::GetFullPath((Join-Path $ComfyRoot "models\loras"))
$destinationDirectory = Join-Path $loraRoot "aitk"
$destination = [IO.Path]::GetFullPath((Join-Path $destinationDirectory "$jobName-best.safetensors"))
if (-not $destination.StartsWith($loraRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw "Publication destination escaped the ComfyUI LoRA root."
}
if (Test-Path -LiteralPath $destination -PathType Leaf) {
    if ((Get-Sha256 $destination) -cne $sourceHash) { throw "A different canonical V6 LoRA exists; refusing to overwrite it." }
    $action = "already-present-identical"
} else {
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    $temporary = "$destination.partial-$PID"
    if (Test-Path -LiteralPath $temporary) { throw "Publication temporary file already exists: $temporary" }
    try {
        Copy-Item -LiteralPath $sourcePath -Destination $temporary
        if ((Get-Sha256 $temporary) -cne $sourceHash) { throw "Temporary publication copy hash verification failed." }
        Move-Item -LiteralPath $temporary -Destination $destination
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
    if ((Get-Sha256 $destination) -cne $sourceHash) { throw "Published V6 copy hash verification failed." }
    $action = "copied-and-verified"
}
[ordered]@{
    schema_version = 1
    published_utc = (Get-Date).ToUniversalTime().ToString("o")
    run_name = $runName
    source_checkpoint = $sourcePath
    checkpoint_step = $step
    inference_strength = $strength
    source_sha256 = $sourceHash
    destination = $destination
    action = $action
    approval_record = $approvalPath
    approval_record_sha256 = Get-Sha256 $approvalPath
    training_validation = $trainingPath
    training_validation_sha256 = Get-Sha256 $trainingPath
    comparison_validation = $comparisonPath
    comparison_validation_sha256 = Get-Sha256 $comparisonPath
    full_screen_summary = $summaryPath
    full_screen_summary_sha256 = Get-Sha256 $summaryPath
    comparison_sheet = $sheetPath
    comparison_sheet_sha256 = Get-Sha256 $sheetPath
    adapter_validation = $validationPath
  } | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $publicationPath -Encoding utf8
Get-Content -Raw -LiteralPath $publicationPath
