[CmdletBinding()]
param(
    [int]$CoarseScreenProcessId = 28400,
    [int]$TimeoutHours = 10,
    [double[]]$Strengths = @(0.7, 0.9, 1.1)
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runName = "flux2-klein9b-identity-v3-r32-dop"
$jobName = "m1tch-flux2-klein9b-identity-v3-r32-dop"
$runRoot = Join-Path $repoRoot ("work\{0}" -f $runName)
$reportRoot = Join-Path $runRoot "benchmarks"
$coarseSummaryPath = Join-Path $reportRoot "coarse-screen-summary.json"
$fullSummaryPath = Join-Path $reportRoot "full-screen-summary.json"
$benchmarkScript = Join-Path $PSScriptRoot "benchmark-flux2-klein9b-identity-v1.ps1"
$sheetScript = Join-Path $PSScriptRoot "build-flux2-klein9b-v3-dop-screen-sheet.py"
$comfyPython = "C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe"
$started = Get-Date

function Get-Median([double[]]$Values) {
    if (-not $Values -or $Values.Count -eq 0) { throw "Cannot compute the median of an empty score set." }
    $sorted = @($Values | Sort-Object)
    $middle = [math]::Floor($sorted.Count / 2)
    if ($sorted.Count % 2 -eq 1) { return [double]$sorted[$middle] }
    return ([double]$sorted[$middle - 1] + [double]$sorted[$middle]) / 2.0
}

Write-Host "Waiting for coarse-screen process PID $CoarseScreenProcessId."
while (Get-Process -Id $CoarseScreenProcessId -ErrorAction SilentlyContinue) {
    if (((Get-Date) - $started).TotalHours -ge $TimeoutHours) {
        throw "Timed out waiting for coarse checkpoint screening."
    }
    Start-Sleep -Seconds 30
}
if (-not (Test-Path -LiteralPath $coarseSummaryPath -PathType Leaf)) {
    throw "Coarse-screen process exited without a summary: $coarseSummaryPath"
}

$coarse = Get-Content -Raw -LiteralPath $coarseSummaryPath | ConvertFrom-Json
$leaders = @($coarse.results | Sort-Object rank | Select-Object -First 2)
if ($leaders.Count -ne 2) { throw "Expected two coarse checkpoint leaders." }
$leaderSteps = @($leaders | ForEach-Object { [int]$_.step } | Sort-Object -Unique)
if ($leaderSteps.Count -ne 2) { throw "The coarse screen did not produce two distinct checkpoint leaders." }

$records = [System.Collections.Generic.List[object]]::new()
foreach ($step in $leaderSteps) {
    $loraName = "{0}-step{1:D4}.safetensors" -f $jobName, $step
    foreach ($strength in @($Strengths | Sort-Object -Unique)) {
        $benchmarkOutput = @(& $benchmarkScript `
            -LoraName $loraName `
            -LoraStrength $strength `
            -Profile Full `
            -WorkRunName $runName `
            -OutputNamespace "klein9b-v3-r32-dop")

        $reportPath = @($benchmarkOutput | Where-Object {
            $_ -is [string] -and (Test-Path -LiteralPath $_ -PathType Leaf)
        } | Select-Object -Last 1)[0]
        if (-not $reportPath) { throw "Full benchmark did not return its report path for step $step at strength $strength." }
        $report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
        if ([string]$report.benchmark.lora_name -cne $loraName -or
            [double]$report.benchmark.lora_strength -ne [double]$strength -or
            [string]$report.benchmark.profile -cne 'Full') {
            throw "Full benchmark report provenance does not match step $step at strength $strength."
        }
        $coreScenes = @($report.scenes | Where-Object { $_.label -in @('portrait','waist-up-social','near-profile-candid') })
        $centroids = @($coreScenes | ForEach-Object { [double]$_.centroid_similarity })
        $records.Add([ordered]@{
            candidate_key = ("{0:D4}@{1}" -f [int]$step, ([double]$strength).ToString('0.00', [Globalization.CultureInfo]::InvariantCulture))
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
            full_body_status = [string](@($report.scenes | Where-Object label -eq 'full-body-walking')[0].calibrated_status)
            report = $reportPath
            outputs = $report.benchmark.outputs
        })
    }
}

$primaryRanked = @($records | Sort-Object `
    @{ Expression = { [int]$_.automatic_gates_passed }; Descending = $true },
    @{ Expression = { [int]$_.crowd_gate_passed }; Descending = $true },
    @{ Expression = { [int]$_.crowd_identity_leakage_passed }; Descending = $true },
    @{ Expression = { [int]$_.core_gate_passed }; Descending = $true },
    @{ Expression = { $_.median_core_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.core_strong_match_count }; Descending = $true },
    @{ Expression = { $_.crowd_main_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.average_core_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.strength }; Descending = $false })
$categoricalBest = $primaryRanked[0]
$equivalentCandidates = @($records | Where-Object {
    [bool]$_.automatic_gates_passed -eq [bool]$categoricalBest.automatic_gates_passed -and
    [bool]$_.crowd_gate_passed -eq [bool]$categoricalBest.crowd_gate_passed -and
    [bool]$_.crowd_identity_leakage_passed -eq [bool]$categoricalBest.crowd_identity_leakage_passed -and
    [bool]$_.core_gate_passed -eq [bool]$categoricalBest.core_gate_passed
})
$bestMedian = [double](($equivalentCandidates.median_core_centroid_similarity | Measure-Object -Maximum).Maximum)
$identityTolerance = 0.02
$withinTolerance = @($equivalentCandidates | Where-Object { [double]$_.median_core_centroid_similarity -ge ($bestMedian - $identityTolerance) })
$preferredStrength = [double](($withinTolerance.strength | Measure-Object -Minimum).Minimum)
$leader = @($withinTolerance | Where-Object { [double]$_.strength -eq $preferredStrength } | Sort-Object `
    @{ Expression = { $_.median_core_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.crowd_main_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.average_core_centroid_similarity }; Descending = $true },
    @{ Expression = { $_.step }; Descending = $false } | Select-Object -First 1)[0]
$ranked = @($leader) + @($primaryRanked | Where-Object { [string]$_.candidate_key -cne [string]$leader.candidate_key })
for ($index = 0; $index -lt $ranked.Count; $index++) { $ranked[$index].rank = $index + 1 }

$summary = [ordered]@{
    schema_version = 1
    created_utc = (Get-Date).ToUniversalTime().ToString('o')
    purpose = "Full held-out identity, full-body, and group-leakage screen of the two leading AI-Toolkit DOP checkpoints at strengths 0.7, 0.9, and 1.1"
    coarse_summary = $coarseSummaryPath
    leader_steps = $leaderSteps
    strengths = @($Strengths | Sort-Object -Unique)
    selection_rule = "Reject identity leakage before comparing core identity; within the best categorical gate tier, choose the highest median core identity score; when candidates are within 0.02, prefer the lower LoRA strength."
    identity_score_tolerance = $identityTolerance
    lower_strength_preferred_within_tolerance = $true
    identity_pass = $false
    reference_conditioning = $false
    face_swap = $false
    results = $ranked
    manual_full_size_and_thumbnail_review_required = $true
    published = $false
}
$summary | ConvertTo-Json -Depth 24 | Set-Content -LiteralPath $fullSummaryPath -Encoding utf8
& $comfyPython $sheetScript $fullSummaryPath
if ($LASTEXITCODE -ne 0) { throw "Full-screen contact sheet failed." }
$summary = Get-Content -Raw -LiteralPath $fullSummaryPath | ConvertFrom-Json
$summary | ConvertTo-Json -Depth 24
