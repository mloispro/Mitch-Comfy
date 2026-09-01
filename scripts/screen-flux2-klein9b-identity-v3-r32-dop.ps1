[CmdletBinding()]
param(
    [int[]]$CheckpointSteps = @(600, 700, 800, 900, 1000, 1100, 1200),
    [double[]]$Strengths = @(0.9),
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runName = "flux2-klein9b-identity-v3-r32-dop"
$jobName = "m1tch-flux2-klein9b-identity-v3-r32-dop"
$namespace = "klein9b-v3-r32-dop"
$runRoot = Join-Path $repoRoot ("work\{0}" -f $runName)
$trainingRecordPath = Join-Path $runRoot "train\training-validation.json"
$reportRoot = Join-Path $runRoot "benchmarks"
$summaryPath = Join-Path $reportRoot "coarse-screen-summary.json"
$stageScript = Join-Path $PSScriptRoot "stage-flux2-klein9b-identity-v3-r32-dop-checkpoints.ps1"
$benchmarkScript = Join-Path $PSScriptRoot "benchmark-flux2-klein9b-identity-v1.ps1"
$sheetScript = Join-Path $PSScriptRoot "build-flux2-klein9b-v3-dop-screen-sheet.py"
$comfyPython = "C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $trainingRecordPath -PathType Leaf)) {
    throw "Validated production training is incomplete: $trainingRecordPath"
}

& $stageScript -Steps $CheckpointSteps -ComfyRoot $ComfyRoot

$records = [System.Collections.Generic.List[object]]::new()
foreach ($step in @($CheckpointSteps | Sort-Object -Unique)) {
    $loraName = "{0}-step{1:D4}.safetensors" -f $jobName, $step
    foreach ($strength in @($Strengths | Sort-Object -Unique)) {
        $benchmarkOutput = @(& $benchmarkScript `
            -LoraName $loraName `
            -LoraStrength $strength `
            -Profile Quick `
            -ComfyUrl $ComfyUrl `
            -ComfyOutputRoot (Join-Path $ComfyRoot "output") `
            -WorkRunName $runName `
            -OutputNamespace $namespace)

        $reportPath = @($benchmarkOutput | Where-Object {
            $_ -is [string] -and (Test-Path -LiteralPath $_ -PathType Leaf)
        } | Select-Object -Last 1)[0]
        if (-not $reportPath) { throw "Benchmark did not return its report path for step $step at strength $strength." }
        $result = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
        if ([string]$result.benchmark.lora_name -cne $loraName -or
            [double]$result.benchmark.lora_strength -ne [double]$strength -or
            [string]$result.benchmark.profile -cne 'Quick') {
            throw "Benchmark report provenance does not match step $step at strength $strength."
        }
        $candidates = @($result.candidates)
        if ($candidates.Count -ne 2) { throw "Expected two Quick candidates in $reportPath." }
        $centroids = @($candidates | ForEach-Object { [double]$_.centroid_similarity })
        $means = @($candidates | ForEach-Object { [double]$_.mean_reference_similarity })
        $records.Add([ordered]@{
            step = [int]$step
            strength = [double]$strength
            average_centroid_similarity = [math]::Round(($centroids | Measure-Object -Average).Average, 4)
            minimum_centroid_similarity = [math]::Round(($centroids | Measure-Object -Minimum).Minimum, 4)
            average_mean_reference_similarity = [math]::Round(($means | Measure-Object -Average).Average, 4)
            minimum_mean_reference_similarity = [math]::Round(($means | Measure-Object -Minimum).Minimum, 4)
            strong_count = @($candidates | Where-Object { $_.calibrated_status -eq 'strong_match' }).Count
            near_count = @($candidates | Where-Object { $_.calibrated_status -eq 'near_match' }).Count
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
    @{ Expression = { $_.average_mean_reference_similarity }; Descending = $true })
for ($index = 0; $index -lt $ranked.Count; $index++) {
    $ranked[$index].rank = $index + 1
}

$summary = [ordered]@{
    schema_version = 1
    created_utc = (Get-Date).ToUniversalTime().ToString('o')
    purpose = "Coarse held-out identity screening for AI-Toolkit FLUX.2 Klein Base 9B DOP LoRA checkpoints"
    training_record = $trainingRecordPath
    model = "FLUX.2 Klein Base 9B"
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
if ($LASTEXITCODE -ne 0) { throw "Coarse-screen contact sheet failed." }
$summary = Get-Content -Raw -LiteralPath $summaryPath | ConvertFrom-Json
$summary | ConvertTo-Json -Depth 20
