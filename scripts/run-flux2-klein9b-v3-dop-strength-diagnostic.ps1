[CmdletBinding()]
param(
    [switch]$FinalizeExisting
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$runName = 'flux2-klein9b-identity-v3-r32-dop'
$runRoot = Join-Path $repoRoot ("work\{0}" -f $runName)
$loraName = 'm1tch-flux2-klein9b-identity-v3-r32-dop-step1200.safetensors'
$runLabel = 'v3-dop-step1200-s1.10-acceptance-failures-diagnostic'
$sceneNumbers = @(1,2,3,4,5,7,8,9)
$diagnosticRoot = Join-Path $runRoot ("nine-scenes\{0}" -f $runLabel)
$baselineEvaluationPath = Join-Path $runRoot 'nine-scenes\v3-dop-step1200-s0.90-nine-scenes\evaluation.json'
$nineSceneScript = Join-Path $PSScriptRoot 'run-flux2-klein9b-lora-nine-scenes-3090.ps1'
$sheetScript = Join-Path $PSScriptRoot 'build-flux2-klein9b-lora-nine-scene-sheet.py'
$python = 'C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $baselineEvaluationPath -PathType Leaf)) {
    throw "Missing strength-0.90 baseline evaluation: $baselineEvaluationPath"
}
if ($FinalizeExisting) {
    $manifestPath = Join-Path $diagnosticRoot 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Cannot finalize the existing diagnostic because its manifest is missing: $manifestPath"
    }
} else {
    if (Test-Path -LiteralPath $diagnosticRoot) {
        throw "Refusing to overwrite an existing diagnostic run: $diagnosticRoot"
    }
    $manifestOutput = @(& $nineSceneScript `
        -LoraName $loraName `
        -LoraStrength 1.1 `
        -SceneNumbers $sceneNumbers `
        -RunLabel $runLabel `
        -WorkRunName $runName `
        -OutputNamespace 'klein9b-v3-r32-dop')
    $manifestPath = @($manifestOutput | Where-Object {
        $_ -is [string] -and (Test-Path -LiteralPath $_ -PathType Leaf)
    } | Select-Object -Last 1)[0]
    if (-not $manifestPath) { throw 'The strength diagnostic did not return a manifest path.' }
}

$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
$actualSceneNumbers = @($manifest.scenes | ForEach-Object { [int]$_.scene })
if (($actualSceneNumbers -join ',') -ne ($sceneNumbers -join ',')) {
    throw "Diagnostic manifest scenes '$($actualSceneNumbers -join ',')' do not match the locked subset '$($sceneNumbers -join ',')'."
}
$manifest | Add-Member -NotePropertyName evaluation_scene_numbers -NotePropertyValue $sceneNumbers -Force
$manifest | Add-Member -NotePropertyName evaluation_purpose -NotePropertyValue 'Controlled LoRA-strength diagnostic for the eight acceptance-failed scenes; not a complete nine-scene review.' -Force
$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding utf8

& $python $sheetScript $manifestPath
if ($LASTEXITCODE -ne 0) { throw 'The strength diagnostic comparison/evaluation builder failed.' }
$candidateEvaluationPath = Join-Path $diagnosticRoot 'evaluation.json'
if (-not (Test-Path -LiteralPath $candidateEvaluationPath -PathType Leaf)) {
    throw "Missing strength-1.10 evaluation: $candidateEvaluationPath"
}

$baseline = Get-Content -Raw -LiteralPath $baselineEvaluationPath | ConvertFrom-Json
$candidate = Get-Content -Raw -LiteralPath $candidateEvaluationPath | ConvertFrom-Json
$comparisons = [System.Collections.Generic.List[object]]::new()
foreach ($sceneNumber in $sceneNumbers) {
    $before = @($baseline.scenes | Where-Object { [int]$_.scene -eq $sceneNumber })
    $after = @($candidate.scenes | Where-Object { [int]$_.scene -eq $sceneNumber })
    if ($before.Count -ne 1 -or $after.Count -ne 1) { throw "Scene $sceneNumber is not unique in both evaluations." }
    $comparisons.Add([ordered]@{
        scene = $sceneNumber
        label = [string]$after[0].label
        baseline_output = [string]$before[0].selected_output
        candidate_output = [string]$after[0].selected_output
        baseline_identity_similarity = [double]$before[0].identity_similarity
        candidate_identity_similarity = [double]$after[0].identity_similarity
        identity_similarity_delta = [math]::Round(([double]$after[0].identity_similarity - [double]$before[0].identity_similarity), 4)
        baseline_mean_reference_similarity = [double]$before[0].identity_mean_reference_similarity
        candidate_mean_reference_similarity = [double]$after[0].identity_mean_reference_similarity
        mean_reference_similarity_delta = [math]::Round(([double]$after[0].identity_mean_reference_similarity - [double]$before[0].identity_mean_reference_similarity), 4)
        baseline_identity_status = [string]$before[0].identity_status
        candidate_identity_status = [string]$after[0].identity_status
        baseline_detected_faces = [int]$before[0].detected_faces
        candidate_detected_faces = [int]$after[0].detected_faces
        expected_faces = [int]$after[0].expected_faces
        baseline_face_count_passed = [bool]$before[0].face_count_passed
        candidate_face_count_passed = [bool]$after[0].face_count_passed
        baseline_maximum_secondary_identity_similarity = [double]$before[0].maximum_secondary_identity_similarity
        candidate_maximum_secondary_identity_similarity = [double]$after[0].maximum_secondary_identity_similarity
        baseline_failures = @($before[0].identity_diagnostic.failures)
        candidate_failures = @($after[0].identity_diagnostic.failures)
        candidate_automatic_passed = [string]$after[0].identity_diagnostic.status -eq 'passed' -and [bool]$after[0].face_count_passed
        manual_scene_gates = @($after[0].manual_scene_gates)
    })
}

$record = [ordered]@{
    schema_version = 1
    created_utc = (Get-Date).ToUniversalTime().ToString('o')
    purpose = 'One-variable diagnostic for the eight step-1200/0.90 scenes that failed identity or person-count acceptance; only LoRA strength changes to 1.10.'
    checkpoint_step = 1200
    baseline_strength = 0.9
    candidate_strength = 1.1
    controlled_variable = 'LoRA strength only'
    scene_numbers = $sceneNumbers
    reference_conditioning = $false
    identity_pass = $false
    face_swap = $false
    baseline_evaluation = $baselineEvaluationPath
    candidate_manifest = $manifestPath
    candidate_evaluation = $candidateEvaluationPath
    candidate_contact_sheet = [string]$candidate.contact_sheet
    candidate_face_geometry_contact_sheet = [string]$candidate.face_geometry_contact_sheet
    automatic_pass_count = @($comparisons | Where-Object candidate_automatic_passed).Count
    all_automatic_gates_passed = @($comparisons | Where-Object { -not $_.candidate_automatic_passed }).Count -eq 0
    comparisons = @($comparisons)
    manual_full_size_and_thumbnail_review_required = $true
    published = $false
}
$recordPath = Join-Path $diagnosticRoot 'strength-comparison.json'
$record | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $recordPath -Encoding utf8
$record | ConvertTo-Json -Depth 20
