[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ApprovalRecord,
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runName = "flux2-klein9b-identity-v3-r32-dop"
$jobName = "m1tch-flux2-klein9b-identity-v3-r32-dop"
$runRoot = Join-Path $repoRoot ("work\{0}" -f $runName)
$auditPath = Join-Path $runRoot "completion-audit.json"
$trainingPath = Join-Path $runRoot "train\training-validation.json"
$fullSummaryPath = Join-Path $runRoot "benchmarks\full-screen-summary.json"
$nineCompletionPath = Join-Path $runRoot "nine-scene-completion.json"
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
    throw "A publication record already exists; refusing a duplicate publication."
}
$approvalPath = [IO.Path]::GetFullPath($ApprovalRecord)
$approval = Read-Json $approvalPath
$audit = Read-Json $auditPath
$training = Read-Json $trainingPath
$full = Read-Json $fullSummaryPath
$nine = Read-Json $nineCompletionPath

if (-not [bool]$approval.approved -or [string]$approval.approved_by -ne 'Mitch') {
    throw "Publication requires an explicit approval record from Mitch."
}
if ([string]$approval.run_name -ne $runName) { throw "Approval names another run." }
if (-not [bool]$approval.full_size_review_completed -or -not [bool]$approval.thumbnail_review_completed -or -not [bool]$approval.face_geometry_review_completed) {
    throw "Approval must confirm full-size, thumbnail, and face-geometry review."
}
$requiredVisualApprovals = [ordered]@{
    identity_approved = 'Mitch identity and face shape'
    scene_composition_approved = 'all nine source-matched compositions'
    person_counts_approved = 'the required person count in every scene'
    exactly_one_mitch_per_group_approved = 'exactly one Mitch in each multiperson scene'
    anatomy_approved = 'arms, hands, body proportions, cats, and golf objects'
    rooftop_down_left_approved = 'the rooftop head and eyes pointing down-left with no eye contact'
    scene_detail_approved = 'no material loss of scene detail'
}
foreach ($field in $requiredVisualApprovals.Keys) {
    if (-not [bool]$approval.$field) {
        throw "Approval must explicitly confirm $($requiredVisualApprovals[$field])."
    }
}
if (-not [bool]$audit.valid -or -not [bool]$audit.ai_toolkit_training_complete -or [bool]$audit.published) {
    throw "The independent completion audit is invalid or already published."
}
if (-not [bool]$audit.evaluation.automatic_leader_passed) {
    throw "The selected candidate did not pass the automatic identity and group-leakage gates; publication is forbidden."
}
$leader = @($full.results | Sort-Object rank | Select-Object -First 1)[0]
if (-not [bool]$leader.automatic_gates_passed -or -not [bool]$leader.core_gate_passed -or -not [bool]$leader.crowd_gate_passed) {
    throw "The full-screen leader is not a passing identity/leakage candidate."
}
$step = [int]$leader.step
$strength = [double]$leader.strength
if ([int]$approval.checkpoint_step -ne $step -or [math]::Abs([double]$approval.strength - $strength) -gt 1e-6) {
    throw "Approval does not match the selected checkpoint and strength."
}
if ([int]$nine.checkpoint_step -ne $step -or [math]::Abs([double]$nine.strength - $strength) -gt 1e-6) {
    throw "Nine-scene review does not match the selected checkpoint and strength."
}
$evaluationHash = Get-Sha256 ([string]$nine.evaluation)
if ([string]$approval.nine_scene_evaluation_sha256 -ne $evaluationHash) {
    throw "Approval does not match the reviewed nine-scene evaluation artifact."
}
$checkpoint = @($training.checkpoints | Where-Object { [int]$_.step -eq $step })[0]
if (-not $checkpoint) { throw "Selected checkpoint is absent from the training record." }
$sourcePath = [string]$checkpoint.path
$sourceHash = Get-Sha256 $sourcePath
if ($sourceHash -ne ([string]$checkpoint.sha256).ToUpperInvariant()) { throw "Selected checkpoint hash changed." }
$validationPath = Join-Path $runRoot "publication-lora-validation.json"
& $toolkitPython $validator $sourcePath --expected-modules 112 --expected-rank 32 --require-nonzero --json-output $validationPath | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Selected checkpoint failed final LoRA validation." }

$loraRoot = [IO.Path]::GetFullPath((Join-Path $ComfyRoot "models\loras"))
$destinationDirectory = Join-Path $loraRoot "aitk"
$destination = [IO.Path]::GetFullPath((Join-Path $destinationDirectory "$jobName-best.safetensors"))
$requiredPrefix = $loraRoot.TrimEnd('\') + '\'
if (-not $destination.StartsWith($requiredPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Publication destination escaped the ComfyUI LoRA root."
}
$workers = foreach ($port in 8188, 8189) {
    $stats = Invoke-RestMethod -Uri "http://127.0.0.1:$port/system_stats" -TimeoutSec 10
    [ordered]@{ port = $port; device = [string]$stats.devices[0].name }
}
if (($workers | Where-Object port -eq 8188).device -notmatch 'RTX 3090' -or ($workers | Where-Object port -eq 8189).device -notmatch 'RTX 4070') {
    throw "Both expected local ComfyUI workers were not verified before publication."
}
New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
if (Test-Path -LiteralPath $destination -PathType Leaf) {
    if ((Get-Sha256 $destination) -ne $sourceHash) { throw "A different canonical Klein 9B LoRA already exists; refusing to overwrite it." }
    $action = 'already-present-identical'
} else {
    $temporary = "$destination.partial-$PID"
    if (Test-Path -LiteralPath $temporary) { throw "Publication temporary file already exists: $temporary" }
    try {
        Copy-Item -LiteralPath $sourcePath -Destination $temporary
        if ((Get-Sha256 $temporary) -ne $sourceHash) { throw "Temporary publication copy hash verification failed." }
        Move-Item -LiteralPath $temporary -Destination $destination
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
    if ((Get-Sha256 $destination) -ne $sourceHash) { throw "Published copy hash verification failed." }
    $action = 'copied-and-verified'
}
$record = [ordered]@{
    schema_version = 1
    published_utc = (Get-Date).ToUniversalTime().ToString('o')
    run_name = $runName
    source_checkpoint = $sourcePath
    checkpoint_step = $step
    inference_strength = $strength
    source_sha256 = $sourceHash
    destination = $destination
    action = $action
    approval_record = $approvalPath
    approval_record_sha256 = Get-Sha256 $approvalPath
    completion_audit = $auditPath
    completion_audit_sha256 = Get-Sha256 $auditPath
    full_screen_summary = $fullSummaryPath
    full_screen_summary_sha256 = Get-Sha256 $fullSummaryPath
    training_validation = $trainingPath
    training_validation_sha256 = Get-Sha256 $trainingPath
    nine_scene_evaluation = $nine.evaluation
    nine_scene_evaluation_sha256 = $evaluationHash
    validation = $validationPath
    workers = $workers
}
$record | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $publicationPath -Encoding utf8
$record | ConvertTo-Json -Depth 12
