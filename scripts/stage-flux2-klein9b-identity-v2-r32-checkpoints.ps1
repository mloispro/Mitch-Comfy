[CmdletBinding()]
param(
    [int[]]$Steps = @(600, 800, 900, 1000, 1100, 1200),
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$RunName = "flux2-klein9b-identity-v2-r32",
    [string]$JobName = "m1tch-flux2-klein9b-identity-v2-r32",
    [int]$ExpectedModules = 112,
    [int]$ExpectedRank = 32,
    [string]$ExpectedArchitecture = "flux2_klein_9b",
    [string]$ExpectedBaseModel = "black-forest-labs/FLUX.2-klein-base-9B",
    [string]$ExpectedTrigger = "m1tch_person",
    [string]$ExpectedToolkitCommit = "0f788923aef28e3a87fa68cfa15a761d9d499d6c",
    [string]$TrainingRecordName = "training-validation.json",
    [string]$StagingManifestName = "checkpoint-staging.json",
    [string]$ValidationSubdirectory = "staging-validation",
    [switch]$RequireDiffOutputPreservation
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runRoot = Join-Path $repoRoot ("work\{0}" -f $RunName)
$trainingRecordPath = Join-Path $runRoot ("train\{0}" -f $TrainingRecordName)
$sourceRoot = Join-Path $runRoot ("train\ai-toolkit-output\{0}" -f $JobName)
$destinationRoot = Join-Path $ComfyRoot "models\loras"
$validationRoot = Join-Path $runRoot $ValidationSubdirectory
$toolkitPython = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$loraValidator = Join-Path $PSScriptRoot "validate-zimage-lora.py"

foreach ($requiredFile in @($toolkitPython, $loraValidator)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Missing checkpoint-validation dependency: $requiredFile"
    }
}

if (-not (Test-Path -LiteralPath $trainingRecordPath -PathType Leaf)) {
    throw "Validated production training record is missing: $trainingRecordPath"
}
$trainingRecord = Get-Content -Raw -LiteralPath $trainingRecordPath | ConvertFrom-Json
if (-not $trainingRecord.valid -or -not $trainingRecord.zero_ooms -or $trainingRecord.gpu -notmatch "RTX 3090") {
    throw "Production training has not passed the locked RTX 3090 validation gate."
}
$maxSteps = if ($trainingRecord.PSObject.Properties.Name -contains "total_steps") {
    [int]$trainingRecord.total_steps
} else {
    [int]$trainingRecord.steps
}
if ($RequireDiffOutputPreservation) {
    $legacyDopEvidence = (
        [bool]$trainingRecord.diff_output_preservation -and
        [double]$trainingRecord.diff_output_preservation_multiplier -eq 1.0 -and
        [string]$trainingRecord.diff_output_preservation_class -eq "man" -and
        [bool]$trainingRecord.dop_execution_proven -and
        [int]$trainingRecord.dop_prior_prediction_proven_updates -ge $maxSteps -and
        [bool]$trainingRecord.dop_timer_accounting.valid
    )
    $continuationDopEvidence = (
        [bool]$trainingRecord.diff_output_preservation -and
        [bool]$trainingRecord.exact_continuation_proven -and
        [int]$trainingRecord.dop_total_proven_updates -ge $maxSteps -and
        [bool]$trainingRecord.dop_extension_timer_accounting.valid
    )
    if (-not ($legacyDopEvidence -or $continuationDopEvidence)) {
        throw "The training record does not prove differential output preservation executed for every update."
    }
}

$unknownSteps = @($Steps | Where-Object { $_ -lt 100 -or $_ -gt $maxSteps -or $_ % 100 -ne 0 })
if ($unknownSteps.Count -gt 0) {
    throw "Every staged step must be a saved 100-step checkpoint from 100 through $maxSteps`: $($unknownSteps -join ', ')"
}

New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null
New-Item -ItemType Directory -Path $validationRoot -Force | Out-Null
$records = [System.Collections.Generic.List[object]]::new()
foreach ($step in @($Steps | Sort-Object -Unique)) {
    $sourceName = "{0}_{1:D9}.safetensors" -f $JobName, $step
    $sourcePath = Join-Path $sourceRoot $sourceName
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw "Missing checkpoint: $sourcePath" }
    $validationPath = Join-Path $validationRoot ("step-{0:D4}.json" -f $step)
    & $toolkitPython $loraValidator $sourcePath `
        --expected-modules $ExpectedModules `
        --expected-rank $ExpectedRank `
        --require-nonzero `
        --json-output $validationPath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Checkpoint $step failed safetensors validation." }
    $validation = Get-Content -Raw -LiteralPath $validationPath | ConvertFrom-Json
    if (-not [bool]$validation.valid) { throw "Checkpoint $step is not a valid finite LoRA adapter." }
    if ([string]$validation.metadata.architecture -ne $ExpectedArchitecture -or
        [string]$validation.metadata.base_model -ne $ExpectedBaseModel -or
        [string]$validation.metadata.trigger -ne $ExpectedTrigger -or
        [string]$validation.metadata.name -ne $JobName -or
        [string]$validation.metadata.ai_toolkit_commit -ne $ExpectedToolkitCommit) {
        throw "Checkpoint $step metadata does not match the locked Klein 9B training run."
    }
    $trainingInfo = [string]$validation.metadata.training_info | ConvertFrom-Json
    if ([int]$trainingInfo.step -ne $step) {
        throw "Checkpoint filename step $step does not match metadata step $($trainingInfo.step)."
    }
    $destinationName = "{0}-step{1:D4}.safetensors" -f $JobName, $step
    $destinationPath = Join-Path $destinationRoot $destinationName
    $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToUpperInvariant()
    if (Test-Path -LiteralPath $destinationPath) {
        $destinationHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destinationPath).Hash.ToUpperInvariant()
        if ($destinationHash -ne $sourceHash) { throw "Refusing to overwrite a different staged LoRA: $destinationPath" }
        $action = "already-present-identical"
    } else {
        New-Item -ItemType HardLink -Path $destinationPath -Target $sourcePath | Out-Null
        $action = "hardlink-created"
    }
    $records.Add([ordered]@{
        step = $step
        source = $sourcePath
        destination = $destinationPath
        comfy_lora_name = $destinationName
        sha256 = $sourceHash
        validation = $validationPath
        module_count = [int]$validation.module_count
        rank = $ExpectedRank
        action = $action
    })
}

$manifest = [ordered]@{
    schema_version = 2
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    purpose = "Temporary AI-Toolkit checkpoint staging for local FLUX.2 Klein Base 9B evaluation"
    published = $false
    run_name = $RunName
    job_name = $JobName
    differential_output_preservation_required = [bool]$RequireDiffOutputPreservation
    source_training_record = $trainingRecordPath
    checkpoints = @($records)
}
$manifestPath = Join-Path $runRoot $StagingManifestName
$manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding utf8
$manifest | ConvertTo-Json -Depth 10
