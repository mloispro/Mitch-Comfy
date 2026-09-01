[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$summaryPath = Join-Path $repoRoot 'work\flux2-klein9b-identity-v3-r32-dop\benchmarks\full-screen-summary.json'
$sheetScript = Join-Path $PSScriptRoot 'build-flux2-klein9b-v3-dop-screen-sheet.py'
$comfyPython = 'C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $summaryPath -PathType Leaf)) { throw "Missing full-screen summary: $summaryPath" }
$summary = Get-Content -Raw -LiteralPath $summaryPath | ConvertFrom-Json
$records = @($summary.results)
if ($records.Count -ne 6) { throw "Expected six completed full-screen candidates." }

foreach ($record in $records) {
    $leakagePassed = @($record.crowd_leakage_failures).Count -eq 0
    if ($record.PSObject.Properties.Name -contains 'crowd_identity_leakage_passed') {
        $record.crowd_identity_leakage_passed = $leakagePassed
    } else {
        $record | Add-Member -NotePropertyName crowd_identity_leakage_passed -NotePropertyValue $leakagePassed
    }
}

$primaryRanked = @($records | Sort-Object `
    @{ Expression = { [int]$_.automatic_gates_passed }; Descending = $true },
    @{ Expression = { [int]$_.crowd_gate_passed }; Descending = $true },
    @{ Expression = { [int]$_.crowd_identity_leakage_passed }; Descending = $true },
    @{ Expression = { [int]$_.core_gate_passed }; Descending = $true },
    @{ Expression = { [double]$_.median_core_centroid_similarity }; Descending = $true },
    @{ Expression = { [int]$_.core_strong_match_count }; Descending = $true },
    @{ Expression = { [double]$_.crowd_main_centroid_similarity }; Descending = $true },
    @{ Expression = { [double]$_.average_core_centroid_similarity }; Descending = $true },
    @{ Expression = { [double]$_.strength }; Descending = $false })
$categoricalBest = $primaryRanked[0]
$equivalentCandidates = @($records | Where-Object {
    [bool]$_.automatic_gates_passed -eq [bool]$categoricalBest.automatic_gates_passed -and
    [bool]$_.crowd_gate_passed -eq [bool]$categoricalBest.crowd_gate_passed -and
    [bool]$_.crowd_identity_leakage_passed -eq [bool]$categoricalBest.crowd_identity_leakage_passed -and
    [bool]$_.core_gate_passed -eq [bool]$categoricalBest.core_gate_passed
})
$bestMedian = [double](($equivalentCandidates.median_core_centroid_similarity | Measure-Object -Maximum).Maximum)
$identityTolerance = 0.02
$withinTolerance = @($equivalentCandidates | Where-Object {
    [double]$_.median_core_centroid_similarity -ge ($bestMedian - $identityTolerance)
})
$preferredStrength = [double](($withinTolerance.strength | Measure-Object -Minimum).Minimum)
$leader = @($withinTolerance | Where-Object { [double]$_.strength -eq $preferredStrength } | Sort-Object `
    @{ Expression = { [double]$_.median_core_centroid_similarity }; Descending = $true },
    @{ Expression = { [double]$_.crowd_main_centroid_similarity }; Descending = $true },
    @{ Expression = { [double]$_.average_core_centroid_similarity }; Descending = $true },
    @{ Expression = { [int]$_.step }; Descending = $false } | Select-Object -First 1)[0]

if (-not [bool]$leader.automatic_gates_passed -or -not [bool]$leader.crowd_identity_leakage_passed) {
    throw "No fully passing, leakage-free full-screen candidate exists."
}

$ranked = @($leader) + @($primaryRanked | Where-Object { [string]$_.candidate_key -cne [string]$leader.candidate_key })
for ($index = 0; $index -lt $ranked.Count; $index++) { $ranked[$index].rank = $index + 1 }
$summary.results = $ranked
$summary.selection_rule = 'Among candidates that pass every scene/count/leakage gate, choose the highest median core identity score; when candidates are within 0.02, prefer the lower LoRA strength.'
$summary.identity_score_tolerance = $identityTolerance
$summary.lower_strength_preferred_within_tolerance = $true
$summary | Add-Member -Force -NotePropertyName selection_logic_version -NotePropertyValue 2
$summary | Add-Member -Force -NotePropertyName selection_rebuilt_utc -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o'))
$summary | ConvertTo-Json -Depth 24 | Set-Content -LiteralPath $summaryPath -Encoding utf8

& $comfyPython $sheetScript $summaryPath
if ($LASTEXITCODE -ne 0) { throw "Could not rebuild the corrected full-screen contact sheet." }
Get-Content -Raw -LiteralPath $summaryPath
