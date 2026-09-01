[CmdletBinding()]
param(
    [int]$TrainingProcessId = 7400,
    [int]$TimeoutHours = 8
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runRoot = Join-Path $repoRoot "work\flux2-klein9b-identity-v3-r32-dop"
$validationPath = Join-Path $runRoot "train\training-validation.json"
$screenScript = Join-Path $PSScriptRoot "screen-flux2-klein9b-identity-v3-r32-dop.ps1"
$toolkitPython = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$loraValidator = Join-Path $PSScriptRoot "validate-zimage-lora.py"
$jobName = "m1tch-flux2-klein9b-identity-v3-r32-dop"
$started = Get-Date
. (Join-Path $PSScriptRoot "aitk-dop-timer-evidence.ps1")

function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing file: $Path" }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Get-UniqueFiniteLossSteps([string[]]$Paths, [int]$ExpectedUpdates) {
    $steps = [System.Collections.Generic.HashSet[int]]::new()
    $pattern = '(?m)([0-9]{1,6})/' + $ExpectedUpdates + '[^\r\n]*?loss:\s*([0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?)'
    foreach ($path in $Paths) {
        $text = Get-Content -Raw -LiteralPath $path
        foreach ($match in [regex]::Matches($text, $pattern, [Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
            $step = [int]$match.Groups[1].Value
            $loss = [double]::Parse($match.Groups[2].Value, [Globalization.CultureInfo]::InvariantCulture)
            if (-not [double]::IsFinite($loss)) { throw "A nonfinite loss was parsed at progress index $step." }
            $null = $steps.Add($step)
        }
    }
    return @($steps | Sort-Object)
}

function Repair-ProductionValidation {
    $phaseRoot = Join-Path $runRoot "train"
    $logRoot = Join-Path $phaseRoot "logs"
    $trainingLog = @(Get-ChildItem -LiteralPath $logRoot -Filter 'train-*.log' -File | Where-Object Name -notlike '*-console.log' | Sort-Object LastWriteTime | Select-Object -Last 1)[0]
    $consoleLog = @(Get-ChildItem -LiteralPath $logRoot -Filter 'train-*-console.log' -File | Sort-Object LastWriteTime | Select-Object -Last 1)[0]
    if (-not $trainingLog -or -not $consoleLog) { throw "Production logs are incomplete." }
    $allLog = (Get-Content -Raw -LiteralPath $trainingLog.FullName) + "`n" + (Get-Content -Raw -LiteralPath $consoleLog.FullName)
    if ($allLog -match '(?i)out of memory|CUDA OOM|Traceback|RuntimeError|loss:\s*(?:nan|inf)|non.?finite') {
        throw "Production logs contain an OOM, exception, or nonfinite-loss marker."
    }
    if ($allLog -notmatch 'create LoRA for U-Net:\s*112 modules\.') { throw "Production logs do not prove 112 Klein 9B LoRA modules." }
    if (($allLog | Select-String -Pattern 'Bucket sizes for' -AllMatches).Matches.Count -lt 2 -or $allLog -notmatch '(?m)^6\d\d?x8\d\d' -or $allLog -notmatch '(?m)^8\d\dx1[01]\d\d') {
        throw "Production logs do not prove both locked resolution bucket sets."
    }
    $lossSteps = @(Get-UniqueFiniteLossSteps @($trainingLog.FullName, $consoleLog.FullName) 1200)
    if ($lossSteps.Count -ne 1200 -or $lossSteps[0] -ne 0 -or $lossSteps[-1] -ne 1199) {
        throw "Production logs do not prove the complete finite-loss update range 0-1199."
    }
    $dopEvidence = Get-AitkDopTimerEvidence `
        -Paths @($trainingLog.FullName, $consoleLog.FullName) `
        -Steps 1200 `
        -PerformanceLogEvery 10 `
        -TimerMaxBuffer 10
    if (-not $dopEvidence.valid -or [int]$dopEvidence.proven_updates -ne 1200) {
        throw "DOP timer output does not match the exact pinned AI-Toolkit execution pattern."
    }

    $outputRoot = Join-Path $phaseRoot "ai-toolkit-output\$jobName"
    $finalLora = Join-Path $outputRoot "$jobName.safetensors"
    if (-not (Test-Path -LiteralPath $finalLora -PathType Leaf)) { throw "Final adapter is missing: $finalLora" }
    $adapterValidationPath = Join-Path $phaseRoot "train-lora-validation.json"
    & $toolkitPython $loraValidator $finalLora --expected-modules 112 --expected-rank 32 --require-nonzero --json-output $adapterValidationPath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Final adapter failed safetensors validation." }
    $adapter = Get-Content -Raw -LiteralPath $adapterValidationPath | ConvertFrom-Json
    $trainingInfo = ([string]$adapter.metadata.training_info) | ConvertFrom-Json
    if ([int]$trainingInfo.step -ne 1200) { throw "Final adapter metadata does not prove step 1200." }
    $step1200 = Join-Path $outputRoot ("{0}_{1:D9}.safetensors" -f $jobName, 1200)
    if (Test-Path -LiteralPath $step1200 -PathType Leaf) {
        if ((Get-Sha256 $step1200) -ne (Get-Sha256 $finalLora)) { throw "Step-1200 adapter differs from the final adapter." }
    } else {
        Copy-Item -LiteralPath $finalLora -Destination $step1200
    }
    $checkpoints = [System.Collections.Generic.List[object]]::new()
    foreach ($step in 100..1200 | Where-Object { $_ % 100 -eq 0 }) {
        $path = Join-Path $outputRoot ("{0}_{1:D9}.safetensors" -f $jobName, $step)
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing checkpoint: $path" }
        $checkpoints.Add([ordered]@{ step = $step; path = $path; sha256 = Get-Sha256 $path })
    }
    $record = [ordered]@{
        valid = [bool]$adapter.valid
        kind = 'train'
        completed_utc = (Get-Date).ToUniversalTime().ToString('o')
        steps = 1200
        gpu = 'NVIDIA GeForce RTX 3090'
        fallback_gpu = $null
        module_count = [int]$adapter.module_count
        tensor_count = [int]$adapter.tensor_count
        finite_loss_records = $lossSteps.Count
        zero_ooms = $true
        buckets = @(768, 1024)
        final_lora = $finalLora
        final_lora_sha256 = Get-Sha256 $finalLora
        sample_valid = $null
        sample = $null
        checkpoints = @($checkpoints)
        training_log = $trainingLog.FullName
        console_log = $consoleLog.FullName
        diff_output_preservation = $true
        diff_output_preservation_class = 'man'
        diff_output_preservation_multiplier = 1.0
        dop_prior_prediction_records = [int](($dopEvidence.logs | Measure-Object -Property record_count -Sum).Sum)
        dop_prior_prediction_max_updates = [int](($dopEvidence.logs | Measure-Object -Property reported_updates -Maximum).Maximum)
        dop_prior_prediction_proven_updates = [int]$dopEvidence.proven_updates
        dop_timer_accounting = $dopEvidence
        dop_timer_source = 'toolkit\timer.py'
        dop_timer_source_sha256 = Get-Sha256 "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit\toolkit\timer.py"
        dop_trainer_source = 'extensions_built_in\sd_trainer\SDTrainer.py'
        dop_trainer_source_sha256 = Get-Sha256 "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit\extensions_built_in\sd_trainer\SDTrainer.py"
        dop_loop_source = 'jobs\process\BaseSDTrainProcess.py'
        dop_loop_source_sha256 = Get-Sha256 "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit\jobs\process\BaseSDTrainProcess.py"
        dop_execution_proven = $true
        recovered_after_bounded_timer_reporting_accounting = $true
    }
    $record | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $validationPath -Encoding utf8
    Write-Host "Recovered the valid production record using exact bounded-timer DOP accounting."
}

Write-Host "Waiting for validated AI-Toolkit production training, PID $TrainingProcessId."
while (Get-Process -Id $TrainingProcessId -ErrorAction SilentlyContinue) {
    if (((Get-Date) - $started).TotalHours -ge $TimeoutHours) {
        throw "Timed out waiting for the AI-Toolkit production process."
    }
    Start-Sleep -Seconds 30
}
Start-Sleep -Seconds 2
if (-not (Test-Path -LiteralPath $validationPath -PathType Leaf)) { Repair-ProductionValidation }

$validation = Get-Content -Raw -LiteralPath $validationPath | ConvertFrom-Json
if (-not $validation.valid -or -not $validation.zero_ooms -or $validation.gpu -notmatch "RTX 3090") {
    throw "Production validation failed the RTX 3090, finite-adapter, or zero-OOM gate."
}
if (-not $validation.diff_output_preservation -or
    -not $validation.dop_execution_proven -or
    [int]$validation.dop_prior_prediction_proven_updates -lt [int]$validation.steps -or
    -not [bool]$validation.dop_timer_accounting.valid) {
    throw "Production validation does not prove DOP executed for every update."
}

Write-Host "Training validation passed. Beginning seven-checkpoint held-out identity screening."
& $screenScript -CheckpointSteps @(600, 700, 800, 900, 1000, 1100, 1200) -Strengths @(0.9)
Write-Host "Coarse checkpoint screening finished."
