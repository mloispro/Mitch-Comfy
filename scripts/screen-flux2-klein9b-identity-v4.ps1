[CmdletBinding()]
param(
    [int[]]$CheckpointSteps = @(600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500),
    [double[]]$Strengths = @(0.9),
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [string]$RunName = "flux2-klein9b-identity-v4-r16-diverse",
    [string]$JobName = "m1tch-flux2-klein9b-identity-v4-r16-diverse",
    [string]$OutputNamespace = "klein9b-v4-r16-diverse",
    [string]$ReferenceDatasetName = "mitch-identity-stills-v4-klein9b",
    [int]$ExpectedRank = 16,
    [int]$ExpectedTrainingSteps = 1500,
    [string]$TrainingRecordName = "training-validation.json",
    [string]$ReportSubdirectory = "",
    [string]$StageScript = "",
    [string]$BenchmarkScript = "",
    [string[]]$HeldOutReferenceFiles = @(
        "val_03_navy_upper_body.jpg",
        "val_04_window_small_smile.jpg",
        "val_05_balcony_opposite_angle.jpg",
        "val_06_car_daylight.jpg"
    ),
    [string[]]$TrainingFilesExcludedFromEvaluation = @(
        "val_01_surf_full_body.jpg",
        "val_02_body_mirror_sleeveless.jpg"
    ),
    [ValidateRange(2, 20)][int]$ExpectedQuickCandidateCount = 2,
    [ValidateRange(0, 20)][int]$ExpectedCalibrationReferenceCount = 0,
    [double]$ExpectedReferencePairwiseMinimum = 0.6973,
    [double]$ExpectedReferencePairwiseMean = 0.7491,
    [switch]$AllowDynamicReferenceCalibration,
    [switch]$RequireDiffOutputPreservation
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runRoot = Join-Path $repoRoot ("work\{0}" -f $RunName)
$trainingRecordPath = Join-Path $runRoot ("train\{0}" -f $TrainingRecordName)
$reportRoot = if ($ReportSubdirectory) { Join-Path $runRoot ("benchmarks\{0}" -f $ReportSubdirectory) } else { Join-Path $runRoot "benchmarks" }
$summaryPath = Join-Path $reportRoot "coarse-screen-summary.json"
if (-not $StageScript) { $StageScript = Join-Path $PSScriptRoot "stage-flux2-klein9b-identity-v4-checkpoints.ps1" }
if (-not $BenchmarkScript) { $BenchmarkScript = Join-Path $PSScriptRoot "benchmark-flux2-klein9b-identity-v4.ps1" }
$sheetScript = Join-Path $PSScriptRoot "build-flux2-klein9b-v3-dop-screen-sheet.py"
$comfyPython = "C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $trainingRecordPath -PathType Leaf)) {
    throw "Validated production training is incomplete: $trainingRecordPath"
}
$trainingRecord = Get-Content -Raw -LiteralPath $trainingRecordPath | ConvertFrom-Json
$provenTrainingSteps = if ($trainingRecord.PSObject.Properties.Name -contains "total_steps") {
    [int]$trainingRecord.total_steps
} else {
    [int]$trainingRecord.steps
}
if (-not [bool]$trainingRecord.valid -or
    -not [bool]$trainingRecord.zero_ooms -or
    [string]$trainingRecord.gpu -notmatch "RTX 3090" -or
    $provenTrainingSteps -ne $ExpectedTrainingSteps) {
    throw "The production record does not prove a valid $ExpectedTrainingSteps-step RTX 3090 run."
}
$legacyDopEvidence = (
    [bool]$trainingRecord.diff_output_preservation -and
    [double]$trainingRecord.diff_output_preservation_multiplier -eq 1.0 -and
    [string]$trainingRecord.diff_output_preservation_class -ceq "man" -and
    [bool]$trainingRecord.dop_execution_proven -and
    [int]$trainingRecord.dop_prior_prediction_proven_updates -ge $ExpectedTrainingSteps -and
    [bool]$trainingRecord.dop_timer_accounting.valid
)
$continuationDopEvidence = (
    [bool]$trainingRecord.diff_output_preservation -and
    [bool]$trainingRecord.exact_continuation_proven -and
    [int]$trainingRecord.dop_total_proven_updates -ge $ExpectedTrainingSteps -and
    [bool]$trainingRecord.dop_extension_timer_accounting.valid
)
if ($RequireDiffOutputPreservation -and -not ($legacyDopEvidence -or $continuationDopEvidence)) {
    throw "The production record does not prove differential output preservation executed for every update."
}

$invalidSteps = @($CheckpointSteps | Where-Object { $_ -lt 100 -or $_ -gt $ExpectedTrainingSteps -or $_ % 100 -ne 0 })
if ($invalidSteps.Count -gt 0) {
    throw "CheckpointSteps contains an unsaved v4 step: $($invalidSteps -join ', ')"
}
if ($Strengths.Count -lt 1 -or @($Strengths | Where-Object { $_ -le 0 -or $_ -gt 1.5 }).Count -gt 0) {
    throw "Strengths must contain values greater than 0 and no greater than 1.5."
}
if ($HeldOutReferenceFiles.Count -lt 2 -or @($HeldOutReferenceFiles | Select-Object -Unique).Count -ne $HeldOutReferenceFiles.Count) {
    throw "HeldOutReferenceFiles must contain at least two unique filenames."
}
$calibrationReferenceCount = if ($ExpectedCalibrationReferenceCount -gt 0) {
    $ExpectedCalibrationReferenceCount
} else {
    $HeldOutReferenceFiles.Count
}

# Stage every retained checkpoint once. This preserves one complete hash manifest for
# coarse screening and any later adjacent-checkpoint follow-up.
& $StageScript -ComfyRoot $ComfyRoot | Out-Null

$records = [System.Collections.Generic.List[object]]::new()
$observedReferencePairwiseMinimum = $null
$observedReferencePairwiseMean = $null
foreach ($step in @($CheckpointSteps | Sort-Object -Unique)) {
    $loraName = "{0}-step{1:D4}.safetensors" -f $JobName, $step
    foreach ($strength in @($Strengths | Sort-Object -Unique)) {
        $benchmarkOutput = @(& $BenchmarkScript `
            -LoraName $loraName `
            -LoraStrength $strength `
            -Profile Quick `
            -ComfyUrl $ComfyUrl `
            -ComfyOutputRoot (Join-Path $ComfyRoot "output") `
            -OutputNamespace $OutputNamespace)

        $reportPath = @($benchmarkOutput | Where-Object {
            $_ -is [string] -and (Test-Path -LiteralPath $_ -PathType Leaf)
        } | Select-Object -Last 1)[0]
        if (-not $reportPath) {
            throw "Benchmark did not return its report path for step $step at strength $strength."
        }
        $result = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
        $reportReferenceMinimum = [double]$result.reference_calibration.pairwise_minimum
        $reportReferenceMean = [double]$result.reference_calibration.pairwise_mean
        if ($null -eq $observedReferencePairwiseMinimum) {
            $observedReferencePairwiseMinimum = $reportReferenceMinimum
            $observedReferencePairwiseMean = $reportReferenceMean
        }
        $referenceCalibrationInvalid = if ($AllowDynamicReferenceCalibration) {
            [math]::Abs($reportReferenceMinimum - [double]$observedReferencePairwiseMinimum) -gt 0.0001 -or
            [math]::Abs($reportReferenceMean - [double]$observedReferencePairwiseMean) -gt 0.0001
        } else {
            [math]::Abs($reportReferenceMinimum - $ExpectedReferencePairwiseMinimum) -gt 0.0001 -or
            [math]::Abs($reportReferenceMean - $ExpectedReferencePairwiseMean) -gt 0.0001
        }
        if ([string]$result.benchmark.lora_name -cne $loraName -or
            [double]$result.benchmark.lora_strength -ne [double]$strength -or
            [string]$result.benchmark.profile -cne "Quick" -or
            [string]$result.benchmark.reference_dataset_name -cne $ReferenceDatasetName -or
            @($result.benchmark.held_out_references).Count -ne $HeldOutReferenceFiles.Count -or
            @($result.benchmark.calibration_references).Count -ne $calibrationReferenceCount -or
            $referenceCalibrationInvalid) {
            throw "Benchmark report provenance does not match the locked checkpoint screen for step $step at strength $strength."
        }
        $candidates = @($result.candidates)
        if ($candidates.Count -ne $ExpectedQuickCandidateCount) {
            throw "Expected $ExpectedQuickCandidateCount Quick candidates in $reportPath."
        }
        $centroids = @($candidates | ForEach-Object { [double]$_.centroid_similarity })
        $means = @($candidates | ForEach-Object { [double]$_.mean_reference_similarity })
        $records.Add([ordered]@{
            step = [int]$step
            strength = [double]$strength
            average_centroid_similarity = [math]::Round(($centroids | Measure-Object -Average).Average, 4)
            minimum_centroid_similarity = [math]::Round(($centroids | Measure-Object -Minimum).Minimum, 4)
            average_mean_reference_similarity = [math]::Round(($means | Measure-Object -Average).Average, 4)
            minimum_mean_reference_similarity = [math]::Round(($means | Measure-Object -Minimum).Minimum, 4)
            strong_count = @($candidates | Where-Object { $_.calibrated_status -eq "strong_match" }).Count
            near_count = @($candidates | Where-Object { $_.calibrated_status -eq "near_match" }).Count
            report = $reportPath
            outputs = $result.benchmark.outputs
        })
    }
}

$ranked = @($records | Sort-Object `
    @{ Expression = { $_.strong_count }; Descending = $true },
    @{ Expression = { $_.near_count }; Descending = $true },
    @{ Expression = { $_.minimum_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.minimum_mean_reference_similarity }; Descending = $true },
    @{ Expression = { $_.average_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.average_mean_reference_similarity }; Descending = $true },
    @{ Expression = { $_.step }; Descending = $false })
for ($index = 0; $index -lt $ranked.Count; $index++) {
    $ranked[$index].rank = $index + 1
}

$summary = [ordered]@{
    schema_version = 1
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    purpose = "Coarse held-out identity screening for a validated AI-Toolkit FLUX.2 Klein Base 9B LoRA"
    training_record = $trainingRecordPath
    model = "FLUX.2 Klein Base 9B"
    dataset = $ReferenceDatasetName
    held_out_reference_files = @($HeldOutReferenceFiles)
    held_out_reference_calibration = (Join-Path $runRoot "heldout-reference-calibration.json")
    reference_pairwise_floor = [double]$observedReferencePairwiseMinimum
    reference_pairwise_mean = [double]$observedReferencePairwiseMean
    dynamic_reference_calibration = [bool]$AllowDynamicReferenceCalibration
    calibration_reference_count = $calibrationReferenceCount
    promoted_training_files_excluded_from_evaluation = @($TrainingFilesExcludedFromEvaluation)
    model_variant = "undistilled Base 9B"
    rank = $ExpectedRank
    differential_output_preservation_required = [bool]$RequireDiffOutputPreservation
    reference_conditioning = $false
    identity_pass = $false
    face_swap = $false
    checkpoint_steps = @($CheckpointSteps | Sort-Object -Unique)
    strengths = @($Strengths | Sort-Object -Unique)
    ranking_is_diagnostic_only = $true
    manual_scene_and_identity_review_required = $true
    results = $ranked
}
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null
$summary | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $summaryPath -Encoding utf8
& $comfyPython $sheetScript $summaryPath
if ($LASTEXITCODE -ne 0) {
    throw "Coarse-screen contact sheet failed."
}
$summary = Get-Content -Raw -LiteralPath $summaryPath | ConvertFrom-Json
$summary | ConvertTo-Json -Depth 20
