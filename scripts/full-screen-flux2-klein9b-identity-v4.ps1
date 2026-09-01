[CmdletBinding()]
param(
    [double[]]$Strengths = @(0.7, 0.9, 1.1),
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [int]$Steps = 50,
    [string]$RunName = "flux2-klein9b-identity-v4-r16-diverse",
    [string]$JobName = "m1tch-flux2-klein9b-identity-v4-r16-diverse",
    [string]$OutputNamespace = "klein9b-v4-r16-diverse",
    [string]$ReferenceDatasetName = "mitch-identity-stills-v4-klein9b",
    [int]$ExpectedRank = 16,
    [ValidateRange(1, 20)][int]$LeaderCount = 2,
    [string]$ReportSubdirectory = "",
    [string]$BenchmarkScript = "",
    [string[]]$HeldOutReferenceFiles = @(
        "val_03_navy_upper_body.jpg",
        "val_04_window_small_smile.jpg",
        "val_05_balcony_opposite_angle.jpg",
        "val_06_car_daylight.jpg"
    ),
    [string[]]$CoreSceneLabels = @("portrait", "waist-up-social", "near-profile-candid"),
    [string]$FullBodySceneLabel = "full-body-walking",
    [ValidateRange(0, 20)][int]$ExpectedCalibrationReferenceCount = 0,
    [switch]$RequireDiffOutputPreservation
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runRoot = Join-Path $repoRoot ("work\{0}" -f $RunName)
$reportRoot = if ($ReportSubdirectory) { Join-Path $runRoot ("benchmarks\{0}" -f $ReportSubdirectory) } else { Join-Path $runRoot "benchmarks" }
$coarseSummaryPath = Join-Path $reportRoot "coarse-screen-summary.json"
$fullSummaryPath = Join-Path $reportRoot "full-screen-summary.json"
if (-not $BenchmarkScript) { $BenchmarkScript = Join-Path $PSScriptRoot "benchmark-flux2-klein9b-identity-v4.ps1" }
$sheetScript = Join-Path $PSScriptRoot "build-flux2-klein9b-v3-dop-screen-sheet.py"
$comfyPython = "C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe"

function Get-Median([double[]]$Values) {
    if (-not $Values -or $Values.Count -eq 0) {
        throw "Cannot compute the median of an empty score set."
    }
    $sorted = @($Values | Sort-Object)
    $middle = [math]::Floor($sorted.Count / 2)
    if ($sorted.Count % 2 -eq 1) {
        return [double]$sorted[$middle]
    }
    return ([double]$sorted[$middle - 1] + [double]$sorted[$middle]) / 2.0
}

if (-not (Test-Path -LiteralPath $coarseSummaryPath -PathType Leaf)) {
    throw "The v4 coarse screen has not completed: $coarseSummaryPath"
}
if ($Strengths.Count -lt 1 -or @($Strengths | Where-Object { $_ -le 0 -or $_ -gt 1.5 }).Count -gt 0) {
    throw "Strengths must contain values greater than 0 and no greater than 1.5."
}
$calibrationReferenceCount = if ($ExpectedCalibrationReferenceCount -gt 0) {
    $ExpectedCalibrationReferenceCount
} else {
    $HeldOutReferenceFiles.Count
}

$coarse = Get-Content -Raw -LiteralPath $coarseSummaryPath | ConvertFrom-Json
if ([string]$coarse.dataset -cne $ReferenceDatasetName -or
    [int]$coarse.rank -ne $ExpectedRank -or
    ($RequireDiffOutputPreservation -and -not [bool]$coarse.differential_output_preservation_required) -or
    @($coarse.held_out_reference_files).Count -ne $HeldOutReferenceFiles.Count -or
    (Compare-Object @($coarse.held_out_reference_files) @($HeldOutReferenceFiles)).Count -ne 0 -or
    [bool]$coarse.reference_conditioning -or
    [bool]$coarse.identity_pass -or
    [bool]$coarse.face_swap) {
    throw "The coarse summary provenance does not match the locked v4 LoRA-only evaluation."
}
$leaders = @($coarse.results | Sort-Object rank | Select-Object -First $LeaderCount)
if ($leaders.Count -ne $LeaderCount) {
    throw "Expected $LeaderCount coarse checkpoint leaders."
}
$leaderSteps = @($leaders | ForEach-Object { [int]$_.step } | Sort-Object -Unique)
if ($leaderSteps.Count -ne $LeaderCount) {
    throw "The coarse screen did not produce $LeaderCount distinct checkpoint leaders."
}

$records = [System.Collections.Generic.List[object]]::new()
foreach ($step in $leaderSteps) {
    $loraName = "{0}-step{1:D4}.safetensors" -f $JobName, $step
    foreach ($strength in @($Strengths | Sort-Object -Unique)) {
        $benchmarkOutput = @(& $BenchmarkScript `
            -LoraName $loraName `
            -LoraStrength $strength `
            -Profile Full `
            -ComfyUrl $ComfyUrl `
            -ComfyOutputRoot (Join-Path $ComfyRoot "output") `
            -Steps $Steps `
            -OutputNamespace $OutputNamespace)

        $reportPath = @($benchmarkOutput | Where-Object {
            $_ -is [string] -and (Test-Path -LiteralPath $_ -PathType Leaf)
        } | Select-Object -Last 1)[0]
        if (-not $reportPath) {
            throw "Full benchmark did not return its report path for step $step at strength $strength."
        }
        $report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
        if ([string]$report.benchmark.lora_name -cne $loraName -or
            [double]$report.benchmark.lora_strength -ne [double]$strength -or
            [string]$report.benchmark.profile -cne "Full" -or
            [string]$report.benchmark.reference_dataset_name -cne $ReferenceDatasetName -or
            @($report.benchmark.held_out_references).Count -ne $HeldOutReferenceFiles.Count -or
            @($report.benchmark.calibration_references).Count -ne $calibrationReferenceCount -or
            [math]::Abs([double]$report.reference_calibration.pairwise_minimum - [double]$coarse.reference_pairwise_floor) -gt 0.0001 -or
            [math]::Abs([double]$report.reference_calibration.pairwise_mean - [double]$coarse.reference_pairwise_mean) -gt 0.0001 -or
            [bool]$report.benchmark.reference_conditioning -or
            [bool]$report.benchmark.identity_pass -or
            [bool]$report.benchmark.face_swap) {
            throw "Full benchmark provenance does not match the locked v4 screen for step $step at strength $strength."
        }
        $coreScenes = @($report.scenes | Where-Object { $_.label -in $CoreSceneLabels })
        if ($coreScenes.Count -ne $CoreSceneLabels.Count) {
            throw "Expected $($CoreSceneLabels.Count) face-sized core scenes in $reportPath."
        }
        $centroids = @($coreScenes | ForEach-Object { [double]$_.centroid_similarity })
        $fullBody = @($report.scenes | Where-Object label -eq $FullBodySceneLabel)
        if ($fullBody.Count -ne 1) {
            throw "Expected one full-body scene in $reportPath."
        }
        $records.Add([ordered]@{
            candidate_key = ("{0:D4}@{1}" -f [int]$step, ([double]$strength).ToString("0.00", [Globalization.CultureInfo]::InvariantCulture))
            step = [int]$step
            strength = [double]$strength
            automatic_gates_passed = [bool]$report.acceptance.automatic_gates_passed
            core_gate_passed = [bool]$report.acceptance.core_gate_passed
            core_strong_match_count = [int]$report.acceptance.core_strong_match_count
            crowd_gate_passed = [bool]$report.acceptance.crowd_gate_passed
            crowd_main_identity_passed = [bool]$report.acceptance.crowd_main_identity_passed
            crowd_main_centroid_similarity = [double]$report.crowd_stress.main_identity_similarity
            crowd_main_mean_reference_similarity = [double]$report.crowd_stress.main_mean_reference_similarity
            crowd_leakage_failures = @($report.acceptance.crowd_leakage_failures)
            crowd_identity_leakage_passed = @($report.acceptance.crowd_leakage_failures).Count -eq 0
            average_core_centroid_similarity = [math]::Round(($centroids | Measure-Object -Average).Average, 4)
            median_core_centroid_similarity = [math]::Round((Get-Median $centroids), 4)
            full_body_status = [string]$fullBody[0].calibrated_status
            full_body_manual_anatomy_review_required = $true
            report = $reportPath
            outputs = $report.benchmark.outputs
        })
    }
}

$primaryRanked = @($records | Sort-Object `
    @{ Expression = { [int]$_.automatic_gates_passed }; Descending = $true },
    @{ Expression = { [int]$_.crowd_identity_leakage_passed }; Descending = $true },
    @{ Expression = { [int]$_.crowd_gate_passed }; Descending = $true },
    @{ Expression = { [int]$_.core_gate_passed }; Descending = $true },
    @{ Expression = { $_.median_core_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.core_strong_match_count }; Descending = $true },
    @{ Expression = { $_.crowd_main_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.average_core_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.strength }; Descending = $false },
    @{ Expression = { $_.step }; Descending = $false })
$categoricalBest = $primaryRanked[0]
$equivalentCandidates = @($records | Where-Object {
    [bool]$_.automatic_gates_passed -eq [bool]$categoricalBest.automatic_gates_passed -and
    [bool]$_.crowd_identity_leakage_passed -eq [bool]$categoricalBest.crowd_identity_leakage_passed -and
    [bool]$_.crowd_gate_passed -eq [bool]$categoricalBest.crowd_gate_passed -and
    [bool]$_.core_gate_passed -eq [bool]$categoricalBest.core_gate_passed
})
$bestMedian = [double](($equivalentCandidates.median_core_centroid_similarity | Measure-Object -Maximum).Maximum)
$identityTolerance = 0.02
$withinTolerance = @($equivalentCandidates | Where-Object {
    [double]$_.median_core_centroid_similarity -ge ($bestMedian - $identityTolerance)
})
$preferredStrength = [double](($withinTolerance.strength | Measure-Object -Minimum).Minimum)
$leader = @($withinTolerance | Where-Object {
    [double]$_.strength -eq $preferredStrength
} | Sort-Object `
    @{ Expression = { $_.median_core_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.crowd_main_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.average_core_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.step }; Descending = $false } | Select-Object -First 1)[0]
$ranked = @($leader) + @($primaryRanked | Where-Object {
    [string]$_.candidate_key -cne [string]$leader.candidate_key
})
for ($index = 0; $index -lt $ranked.Count; $index++) {
    $ranked[$index].rank = $index + 1
}

$summary = [ordered]@{
    schema_version = 1
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    purpose = "Full held-out identity, full-body, and group-leakage screen of the $LeaderCount selected AI-Toolkit checkpoints"
    coarse_summary = $coarseSummaryPath
    dataset = $ReferenceDatasetName
    rank = $ExpectedRank
    differential_output_preservation_required = [bool]$RequireDiffOutputPreservation
    held_out_reference_files = @($coarse.held_out_reference_files)
    held_out_reference_calibration = [string]$coarse.held_out_reference_calibration
    reference_pairwise_floor = [double]$coarse.reference_pairwise_floor
    reference_pairwise_mean = [double]$coarse.reference_pairwise_mean
    core_scene_labels = @($CoreSceneLabels)
    promoted_training_files_excluded_from_evaluation = @($coarse.promoted_training_files_excluded_from_evaluation)
    leader_steps = $leaderSteps
    strengths = @($Strengths | Sort-Object -Unique)
    generation_steps = $Steps
    selection_rule = "Reject identity leakage before comparing core identity; within the best categorical gate tier, choose the highest median core identity score; when candidates are within 0.02, prefer the lower LoRA strength."
    identity_score_tolerance = $identityTolerance
    lower_strength_preferred_within_tolerance = $true
    identity_pass = $false
    reference_conditioning = $false
    face_swap = $false
    results = $ranked
    manual_full_size_and_thumbnail_review_required = $true
    manual_full_body_anatomy_review_required = $true
    published = $false
}
$summary | ConvertTo-Json -Depth 24 | Set-Content -LiteralPath $fullSummaryPath -Encoding utf8
& $comfyPython $sheetScript $fullSummaryPath
if ($LASTEXITCODE -ne 0) {
    throw "Full-screen contact sheet failed."
}
$summary = Get-Content -Raw -LiteralPath $fullSummaryPath | ConvertFrom-Json
$summary | ConvertTo-Json -Depth 24
