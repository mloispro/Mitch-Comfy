[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runRoot = Join-Path $repoRoot "work\flux2-klein9b-identity-v3-r32-dop"
$sourceManifestPath = Join-Path $repoRoot "datasets\mitch-identity-stills-v3\manifest.json"
$preflightPath = Join-Path $runRoot "preflight-validation.json"
$smokePath = Join-Path $runRoot "smoke\smoke-validation.json"
$trainingPath = Join-Path $runRoot "train\training-validation.json"
$stagingPath = Join-Path $runRoot "checkpoint-staging.json"
$coarsePath = Join-Path $runRoot "benchmarks\coarse-screen-summary.json"
$fullPath = Join-Path $runRoot "benchmarks\full-screen-summary.json"
$nineCompletionPath = Join-Path $runRoot "nine-scene-completion.json"
$auditPath = Join-Path $runRoot "completion-audit.json"
$expectedManifestHash = "D56FE2D752FEBFA63CA0E76689DFD9D4EAAC7443CA086FFA9DFEF51186563003"
$trainDatasetRoot = Join-Path $runRoot "train\dataset"
$datasetLockPath = Join-Path $runRoot "train\dataset-lock.json"
$runManifestPath = Join-Path $runRoot "train\run-manifest.json"
$productionConfigPath = Join-Path $repoRoot "config\flux2-klein9b-identity-v3-r32-dop-3090.yaml"
$toolkitRoot = "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit"
$sheetScript = Join-Path $PSScriptRoot "build-flux2-klein9b-v3-dop-screen-sheet.py"
$comfyPython = "C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe"
$toolkitPython = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$loraValidator = Join-Path $PSScriptRoot "validate-zimage-lora.py"
$faceCalibrationScript = Join-Path $PSScriptRoot "evaluate-face-likeness.py"
$faceCalibrationPath = Join-Path $runRoot "completion-heldout-reference-calibration.json"
$jobName = "m1tch-flux2-klein9b-identity-v3-r32-dop"
$sourceSceneLockPath = Join-Path $repoRoot "work\zimage-base-identity-v1\scene-source-lock-test.json"
$expectedSourceSceneLockSha256 = "CCF3F4B04C23C4915ABEE2073618B9953D1F7FCCCFFE84F8276208238B52092F"
. (Join-Path $PSScriptRoot "aitk-dop-timer-evidence.ps1")

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}
function Get-Sha256([string]$Path) {
    Assert-True (Test-Path -LiteralPath $Path -PathType Leaf) "Missing file: $Path"
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}
function Read-Json([string]$Path) {
    Assert-True (Test-Path -LiteralPath $Path -PathType Leaf) "Missing JSON artifact: $Path"
    return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}
function Get-UniqueFiniteLossSteps([string[]]$Paths, [int]$ExpectedUpdates) {
    $steps = [System.Collections.Generic.HashSet[int]]::new()
    $pattern = '(?m)([0-9]{1,6})/' + $ExpectedUpdates + '[^\r\n]*?loss:\s*([0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?)'
    foreach ($path in $Paths) {
        Assert-True (Test-Path -LiteralPath $path -PathType Leaf) "Missing finite-loss evidence log: $path"
        $text = Get-Content -Raw -LiteralPath $path
        foreach ($match in [regex]::Matches($text, $pattern, [Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
            $step = [int]$match.Groups[1].Value
            $loss = [double]::Parse($match.Groups[2].Value, [Globalization.CultureInfo]::InvariantCulture)
            Assert-True ([double]::IsFinite($loss)) "A nonfinite loss was parsed at progress index $step."
            $null = $steps.Add($step)
        }
    }
    return @($steps | Sort-Object)
}
function Assert-KleinTransformerOnlyLoraHeader([string]$Path) {
    Assert-True (Test-Path -LiteralPath $Path -PathType Leaf) "Missing safetensors adapter: $Path"
    $stream = [IO.File]::OpenRead($Path)
    $reader = $null
    try {
        $reader = [IO.BinaryReader]::new($stream)
        $headerLength = $reader.ReadInt64()
        Assert-True ($headerLength -gt 0 -and $headerLength -le 16MB -and $headerLength -le ($stream.Length - 8)) "Invalid safetensors header length: $Path"
        $headerBytes = $reader.ReadBytes([int]$headerLength)
        Assert-True ($headerBytes.Length -eq $headerLength) "Truncated safetensors header: $Path"
        $header = [Text.Encoding]::UTF8.GetString($headerBytes) | ConvertFrom-Json
        $keys = @($header.PSObject.Properties.Name | Where-Object { $_ -ne '__metadata__' })
        $invalidKeys = @($keys | Where-Object { $_ -notmatch '^diffusion_model\.(double_blocks|single_blocks)\..+\.lora_[AB]\.weight$' })
        $aKeys = @($keys | Where-Object { $_ -match '\.lora_A\.weight$' })
        $bKeys = @($keys | Where-Object { $_ -match '\.lora_B\.weight$' })
        $aModules = @($aKeys | ForEach-Object { $_ -replace '\.lora_A\.weight$', '' } | Sort-Object)
        $bModules = @($bKeys | ForEach-Object { $_ -replace '\.lora_B\.weight$', '' } | Sort-Object)
        Assert-True ($keys.Count -eq 224 -and $invalidKeys.Count -eq 0) "Adapter is not transformer-only across exactly 224 Klein 9B LoRA tensors: $Path"
        Assert-True ($aKeys.Count -eq 112 -and $bKeys.Count -eq 112 -and @(Compare-Object $aModules $bModules).Count -eq 0) "Adapter does not contain 112 matched LoRA A/B module pairs: $Path"
        $doubleModules = @($aModules | Where-Object { $_ -match '^diffusion_model\.double_blocks\.' }).Count
        $singleModules = @($aModules | Where-Object { $_ -match '^diffusion_model\.single_blocks\.' }).Count
        Assert-True ($doubleModules -eq 64 -and $singleModules -eq 48) "Adapter target distribution is not 64 double-block plus 48 single-block modules: $Path"
        return [ordered]@{ tensors = 224; modules = 112; lora_a = 112; lora_b = 112; double_block_modules = 64; single_block_modules = 48; text_encoder_tensors = 0 }
    }
    finally {
        if ($reader) { $reader.Dispose() } else { $stream.Dispose() }
    }
}
function Assert-BenchmarkProvenance(
    [object]$Item,
    [string]$ExpectedProfile,
    [int]$ExpectedOutputCount,
    [object[]]$StagedCheckpoints
) {
    $report = Read-Json ([string]$Item.report)
    $expectedLoraName = "{0}-step{1:D4}.safetensors" -f $jobName, [int]$Item.step
    $stageRecord = @($StagedCheckpoints | Where-Object { [int]$_.step -eq [int]$Item.step })
    Assert-True ($stageRecord.Count -eq 1) "No unique staging record exists for benchmark step $($Item.step)."
    Assert-True ([string]$report.benchmark.lora_name -ceq $expectedLoraName) "Benchmark report selected the wrong LoRA at step $($Item.step)."
    Assert-True ([double]$report.benchmark.lora_strength -eq [double]$Item.strength) "Benchmark strength provenance mismatch at step $($Item.step)."
    Assert-True ([string]$report.benchmark.profile -ceq $ExpectedProfile) "Benchmark profile provenance mismatch at step $($Item.step)."
    Assert-True ([string]$report.benchmark.base_variant -ceq 'undistilled FLUX.2 Klein Base 9B') "Benchmark used the wrong base variant."
    Assert-True (-not [bool]$report.benchmark.reference_conditioning -and -not [bool]$report.benchmark.identity_pass -and -not [bool]$report.benchmark.face_swap) "Benchmark report used forbidden identity conditioning."
    Assert-True ([bool]$report.benchmark.live_node_and_model_validation_passed) "Live Klein 9B compatibility validation was not recorded."
    Assert-True ([bool]$report.benchmark.other_rtx_3090_work_checked) "Benchmark did not check auxiliary RTX 3090 work."
    Assert-True ([int]$report.benchmark.auxiliary_rtx_3090.running -eq 0 -and [int]$report.benchmark.auxiliary_rtx_3090.pending -eq 0) "Benchmark competed with active auxiliary RTX 3090 ComfyUI work."
    Assert-True (-not [bool]$report.benchmark.forge_rtx_3090.active) "Benchmark competed with active Forge RTX 3090 work."
    Assert-True ([string]$report.benchmark.lora_sha256 -ceq [string]$stageRecord[0].sha256) "Benchmark LoRA hash differs from checkpoint staging at step $($Item.step)."
    Assert-True ((Get-Sha256 ([string]$report.benchmark.lora_path)) -ceq [string]$report.benchmark.lora_sha256) "Benchmark LoRA bytes changed at step $($Item.step)."
    Assert-True ((Get-Sha256 ([string]$report.benchmark.staging_manifest)) -ceq (Get-Sha256 $stagingPath)) "Benchmark points to a different checkpoint-staging manifest."

    $outputs = @($report.benchmark.outputs.PSObject.Properties)
    $outputHashes = @($report.benchmark.output_sha256.PSObject.Properties)
    $scenes = @($report.benchmark.scenes)
    Assert-True ($outputs.Count -eq $ExpectedOutputCount -and $outputHashes.Count -eq $ExpectedOutputCount -and $scenes.Count -eq $ExpectedOutputCount) "Benchmark output, hash, or scene provenance is incomplete at step $($Item.step)."
    for ($index = 0; $index -lt $scenes.Count; $index++) {
        $scene = $scenes[$index]
        $label = [string]$scene.label
        $outputProperty = @($outputs | Where-Object Name -ceq $label)
        $hashProperty = @($outputHashes | Where-Object Name -ceq $label)
        Assert-True ($outputProperty.Count -eq 1 -and $hashProperty.Count -eq 1) "Missing output provenance for scene '$label' at step $($Item.step)."
        Assert-True ([string]$scene.prompt -match '\bm1tch_person\b') "Scene '$label' omitted the LoRA trigger at step $($Item.step)."
        Assert-True ([long]$scene.seed -eq ([long]$report.benchmark.seed_base + $index)) "Scene seed provenance is inconsistent for '$label' at step $($Item.step)."
        Assert-True ((Get-Sha256 ([string]$outputProperty[0].Value)) -ceq [string]$hashProperty[0].Value) "Generated output hash mismatch for scene '$label' at step $($Item.step)."
    }
    return $report
}

$manifest = Read-Json $sourceManifestPath
$preflight = Read-Json $preflightPath
$datasetLock = Read-Json $datasetLockPath
$runManifest = Read-Json $runManifestPath
$smoke = Read-Json $smokePath
$training = Read-Json $trainingPath
$staging = Read-Json $stagingPath
$coarse = Read-Json $coarsePath
$full = Read-Json $fullPath
if (-not $coarse.contact_sheet -or -not (Test-Path -LiteralPath ([string]$coarse.contact_sheet) -PathType Leaf)) {
    & $comfyPython $sheetScript $coarsePath
    if ($LASTEXITCODE -ne 0) { throw "Could not build the coarse-screen contact sheet." }
    $coarse = Read-Json $coarsePath
}
if (-not $full.contact_sheet -or -not (Test-Path -LiteralPath ([string]$full.contact_sheet) -PathType Leaf)) {
    & $comfyPython $sheetScript $fullPath
    if ($LASTEXITCODE -ne 0) { throw "Could not build the full-screen contact sheet." }
    $full = Read-Json $fullPath
}
$nine = Read-Json $nineCompletionPath
$nineManifest = Read-Json ([string]$nine.manifest)
$nineEvaluation = Read-Json ([string]$nine.evaluation)
$sourceSceneLock = Read-Json $sourceSceneLockPath

Assert-True ((Get-Sha256 $sourceManifestPath) -eq $expectedManifestHash) "Source manifest hash changed."
Assert-True ($manifest.trigger_word -eq "m1tch_person") "Unexpected dataset trigger."
Assert-True ([int]$manifest.training_image_count -eq 13) "Expected 13 genuine training photographs."
Assert-True ([int]$manifest.validation_image_count -eq 6) "Expected six held-out photographs."
$trainRecords = @($manifest.records | Where-Object split -eq 'train')
$validationRecords = @($manifest.records | Where-Object split -eq 'validation')
Assert-True ($trainRecords.Count -eq 13) "Manifest training records are incomplete."
Assert-True ($validationRecords.Count -eq 6) "Manifest validation records are incomplete."
foreach ($record in $trainRecords) {
    Assert-True ($record.kind -eq 'camera_still') "Non-camera-still entered training: $($record.id)"
    Assert-True ([string]$record.caption -like 'm1tch_person*') "Caption trigger is not first: $($record.id)"
    $dopCaption = ([string]$record.caption).Replace('m1tch_person', 'man')
    Assert-True (-not $dopCaption.Contains('m1tch_person') -and $dopCaption.StartsWith('man')) "DOP class caption transformation is invalid: $($record.id)"
    Assert-True ((Get-Sha256 ([string]$record.dataset_file)) -eq ([string]$record.dataset_sha256).ToUpperInvariant()) "Dataset image hash mismatch: $($record.id)"
    $copiedImage = Join-Path $trainDatasetRoot (Split-Path -Leaf ([string]$record.dataset_file))
    $copiedCaption = [IO.Path]::ChangeExtension($copiedImage, '.txt')
    Assert-True ((Get-Sha256 $copiedImage) -eq ([string]$record.dataset_sha256).ToUpperInvariant()) "Run-local training image mismatch: $($record.id)"
    Assert-True (Test-Path -LiteralPath $copiedCaption -PathType Leaf) "Run-local caption is missing: $($record.id)"
    Assert-True ((Get-Content -Raw -LiteralPath $copiedCaption).Trim() -eq ([string]$record.caption).Trim()) "Run-local caption mismatch: $($record.id)"
}
$copiedImages = @(Get-ChildItem -LiteralPath $trainDatasetRoot -File | Where-Object Extension -in @('.jpg','.jpeg','.png','.webp'))
$copiedCaptions = @(Get-ChildItem -LiteralPath $trainDatasetRoot -Filter '*.txt' -File)
Assert-True ($copiedImages.Count -eq 13 -and $copiedCaptions.Count -eq 13) "Run-local training folder does not contain exactly 13 image/TXT pairs."
foreach ($validation in $validationRecords) {
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $trainDatasetRoot (Split-Path -Leaf ([string]$validation.dataset_file))) -PathType Leaf)) "Validation image entered the run-local training folder: $($validation.id)"
}
$calibrationArgs = [System.Collections.Generic.List[string]]::new()
$calibrationArgs.Add($faceCalibrationScript)
foreach ($validation in $validationRecords) {
    $calibrationArgs.Add('--reference')
    $calibrationArgs.Add([string]$validation.dataset_file)
}
$calibrationArgs.Add('--candidate')
$calibrationArgs.Add([string]$validationRecords[0].dataset_file)
$calibrationArgs.Add('--candidate-label')
$calibrationArgs.Add('heldout-calibration-probe')
$calibrationArgs.Add('--json-output')
$calibrationArgs.Add($faceCalibrationPath)
& $comfyPython @calibrationArgs | Out-Null
Assert-True ($LASTEXITCODE -eq 0) "Held-out AntelopeV2 reference calibration failed."
$faceCalibration = Read-Json $faceCalibrationPath
Assert-True ([string]$faceCalibration.method -eq 'InsightFace AntelopeV2 glintr100 cosine similarity') "Unexpected identity-calibration model."
Assert-True (@($faceCalibration.reference_calibration.paths).Count -eq 6 -and @($faceCalibration.reference_calibration.pairwise_similarity).Count -eq 15) "Held-out identity calibration did not use all six genuine references and 15 pairs."
Assert-True ([math]::Abs([double]$faceCalibration.reference_calibration.pairwise_minimum - 0.5533) -le 0.0001) "Held-out identity calibration floor changed."
Assert-True ([math]::Abs([double]$faceCalibration.reference_calibration.pairwise_mean - 0.6931) -le 0.0001) "Held-out identity calibration mean changed."
$runStartedUtc = ([datetime]$runManifest.started_utc).ToUniversalTime()
Assert-True ([int]$datasetLock.images -eq 13 -and [int]$datasetLock.captions -eq 13) "Prelaunch dataset lock did not contain exactly 13 image/caption pairs."
Assert-True ([int]$datasetLock.validation_files -eq 0) "Prelaunch dataset lock contained validation files."
Assert-True ([int]$datasetLock.cache_files -eq 0) "Prelaunch dataset lock contained stale AI-Toolkit caches."
Assert-True ([string]$datasetLock.source_manifest_sha256 -eq $expectedManifestHash) "Prelaunch dataset lock used another source manifest."
Assert-True ([string]$runManifest.config_sha256 -eq (Get-Sha256 $productionConfigPath)) "Production launch manifest used another config."
Assert-True ([string]$runManifest.source.sha256 -eq $expectedManifestHash) "Production launch manifest used another dataset manifest."
Assert-True ([string]$runManifest.cuda.name -match 'RTX 3090' -and [int]$runManifest.cuda.count -eq 1) "Production launch did not expose exactly one RTX 3090 CUDA device."
Assert-True ([bool]$runManifest.offline -and $null -eq $runManifest.fallback_gpu) "Production launch was not locked offline without a fallback GPU."
$latentCacheFiles = @(Get-ChildItem -LiteralPath (Join-Path $trainDatasetRoot '_latent_cache') -File -Recurse)
$textCacheFiles = @(Get-ChildItem -LiteralPath (Join-Path $trainDatasetRoot '_t_e_cache') -File -Recurse)
Assert-True ($latentCacheFiles.Count -eq 26 -and $textCacheFiles.Count -eq 26) "Current AI-Toolkit caches do not contain exactly two resolution entries for each of 13 images."
foreach ($cacheFile in @($latentCacheFiles + $textCacheFiles)) {
    Assert-True ($cacheFile.CreationTimeUtc -ge $runStartedUtc) "Cache file predates this production launch: $($cacheFile.FullName)"
}
$sizeRecord = Get-Item -LiteralPath (Join-Path $trainDatasetRoot '.aitk_size.json')
Assert-True ($sizeRecord.CreationTimeUtc -ge $runStartedUtc) ".aitk_size.json predates this production launch."

Assert-True ([bool]$preflight.valid) "Preflight did not pass."
Assert-True ($preflight.source.sha256 -eq $expectedManifestHash) "Preflight used another dataset manifest."
Assert-True ($preflight.toolkit.commit -eq '0f788923aef28e3a87fa68cfa15a761d9d499d6c') "Unexpected AI-Toolkit commit."
Assert-True ($preflight.toolkit.version -eq '0.12.23') "Unexpected AI-Toolkit version."
Assert-True ([bool]$preflight.models.full_local_sha256_verification) "Local model files were not fully hashed."
Assert-True ($preflight.target_gpu -match 'RTX 3090') "Preflight target was not the RTX 3090."
Assert-True ($null -eq $preflight.fallback_gpu) "A fallback GPU was configured."
Assert-True ((Get-Sha256 $productionConfigPath) -eq ([string]$preflight.production_config_sha256).ToUpperInvariant()) "Locked production config changed after preflight."
foreach ($property in $preflight.toolkit.files.PSObject.Properties) {
    $toolkitFile = Join-Path $toolkitRoot $property.Name
    Assert-True ((Get-Sha256 $toolkitFile) -eq ([string]$property.Value).ToUpperInvariant()) "Pinned AI-Toolkit file changed: $($property.Name)"
}

Assert-True ([bool]$smoke.valid -and [bool]$smoke.zero_ooms) "Smoke run did not pass cleanly."
Assert-True ($smoke.gpu -match 'RTX 3090') "Smoke run was not on the RTX 3090."
Assert-True ([int]$smoke.steps -eq 40) "Smoke update count changed."
Assert-True ([int]$smoke.module_count -eq 112 -and [int]$smoke.tensor_count -eq 224) "Smoke adapter structure is wrong."
Assert-True ([bool]$smoke.diff_output_preservation -and [bool]$smoke.dop_execution_proven) "Smoke DOP execution was not proven."
$smokeDop = Get-AitkDopTimerEvidence -Paths @($smoke.training_logs) -Steps 40 -PerformanceLogEvery 1 -TimerMaxBuffer 10
Assert-True ([bool]$smokeDop.valid -and [int]$smokeDop.proven_updates -eq 40) "Smoke logs do not match the exact pinned DOP timer sequence for all 40 updates."

Assert-True ([bool]$training.valid -and [bool]$training.zero_ooms) "Production training did not pass cleanly."
Assert-True ($training.gpu -match 'RTX 3090' -and $null -eq $training.fallback_gpu) "Production GPU provenance is wrong."
Assert-True ([int]$training.steps -eq 1200) "Production update count is not 1200."
Assert-True ([int]$training.module_count -eq 112 -and [int]$training.tensor_count -eq 224) "Production adapter structure is wrong."
Assert-True ([int]$training.finite_loss_records -ge 1200) "Insufficient finite loss evidence."
$uniqueFiniteLossSteps = @(Get-UniqueFiniteLossSteps @([string]$training.training_log, [string]$training.console_log) 1200)
Assert-True ($uniqueFiniteLossSteps.Count -eq 1200) "Production logs do not contain 1,200 distinct finite-loss update indices."
Assert-True ([int]$uniqueFiniteLossSteps[0] -eq 0 -and [int]$uniqueFiniteLossSteps[-1] -eq 1199) "Production finite-loss indices do not cover the complete zero-based 0–1199 range."
Assert-True ([bool]$training.diff_output_preservation) "Production DOP was disabled."
Assert-True ($training.diff_output_preservation_class -eq 'man') "Wrong DOP class."
Assert-True ([double]$training.diff_output_preservation_multiplier -eq 1.0) "Wrong DOP multiplier."
$productionDop = Get-AitkDopTimerEvidence `
    -Paths @([string]$training.training_log, [string]$training.console_log) `
    -Steps 1200 `
    -PerformanceLogEvery 10 `
    -TimerMaxBuffer 10
Assert-True (
    [bool]$training.dop_execution_proven -and
    [bool]$productionDop.valid -and
    [int]$productionDop.proven_updates -eq 1200 -and
    [int]$training.dop_prior_prediction_proven_updates -eq 1200 -and
    [bool]$training.dop_timer_accounting.valid -and
    [int]$training.dop_timer_accounting.ring_buffer_dropped_updates -eq 1 -and
    [int]$training.dop_timer_accounting.final_unflushed_updates -eq 9
) "DOP logs and bounded-timer accounting do not prove a prior pass for every production update."
Assert-True ((Get-Sha256 (Join-Path $toolkitRoot 'toolkit\timer.py')) -eq '5FB451F4647D4EA96EAC35BA43D7EE0A3603320D84045CA369B3FE3090BB6846') "Pinned AI-Toolkit Timer source changed."
Assert-True ([string]$training.dop_timer_source_sha256 -eq '5FB451F4647D4EA96EAC35BA43D7EE0A3603320D84045CA369B3FE3090BB6846') "Production DOP record used another Timer source."
Assert-True ([string]$training.dop_trainer_source_sha256 -eq '8F30CB3FB9C10FF82FC5B1EF6488FF7A40ADCD9278E9D5FB4561FBA729D69D99') "Production DOP record used another SDTrainer source."
Assert-True ([string]$training.dop_loop_source_sha256 -eq 'B8F25B79ABB6B50B20F2855508B263A1996EA36E0C60B9DFD971E30C07B6D4D3') "Production DOP record used another training-loop source."
$checkpoints = @($training.checkpoints | Sort-Object step)
Assert-True ($checkpoints.Count -eq 12) "Expected all 12 numbered checkpoints."
Assert-True ((@($checkpoints.step) -join ',') -eq ((100..1200 | Where-Object { $_ % 100 -eq 0 }) -join ',')) "Checkpoint steps are incomplete."
$checkpointValidationRoot = Join-Path $runRoot "train\checkpoint-validations"
New-Item -ItemType Directory -Path $checkpointValidationRoot -Force | Out-Null
foreach ($checkpoint in $checkpoints) {
    Assert-True ((Get-Sha256 ([string]$checkpoint.path)) -eq ([string]$checkpoint.sha256).ToUpperInvariant()) "Checkpoint hash mismatch at step $($checkpoint.step)."
    $checkpointValidationPath = Join-Path $checkpointValidationRoot ("step-{0:D4}.json" -f [int]$checkpoint.step)
    & $toolkitPython $loraValidator ([string]$checkpoint.path) --expected-modules 112 --expected-rank 32 --require-nonzero --json-output $checkpointValidationPath | Out-Null
    Assert-True ($LASTEXITCODE -eq 0) "Checkpoint tensor validation failed at step $($checkpoint.step)."
    $checkpointValidation = Read-Json $checkpointValidationPath
    $trainingInfo = ([string]$checkpointValidation.metadata.training_info) | ConvertFrom-Json
    Assert-True (
        [bool]$checkpointValidation.valid -and
        [int]$checkpointValidation.rank_counts.'32' -eq 112 -and
        @($checkpointValidation.rank_mismatch_modules).Count -eq 0 -and
        @($checkpointValidation.zero_tensors).Count -eq 0 -and
        @($checkpointValidation.nonfinite_tensors).Count -eq 0 -and
        [int]$trainingInfo.step -eq [int]$checkpoint.step -and
        [string]$checkpointValidation.metadata.architecture -eq 'flux2_klein_9b' -and
        [string]$checkpointValidation.metadata.trigger -eq 'm1tch_person' -and
        [string]$checkpointValidation.metadata.dataset -eq 'mitch-identity-stills-v3' -and
        [string]$checkpointValidation.metadata.ai_toolkit_commit -eq '0f788923aef28e3a87fa68cfa15a761d9d499d6c' -and
        [string]$checkpointValidation.metadata.target_gpu -match 'RTX 3090'
    ) "Checkpoint metadata or rank/nonzero evidence is invalid at step $($checkpoint.step)."
    $null = Assert-KleinTransformerOnlyLoraHeader ([string]$checkpoint.path)
}
Assert-True ((Get-Sha256 ([string]$training.final_lora)) -eq ([string]$training.final_lora_sha256).ToUpperInvariant()) "Final adapter hash mismatch."
Assert-True ($training.final_lora_sha256 -eq $checkpoints[-1].sha256) "Final adapter differs from step 1200."
$rankValidationPath = Join-Path $runRoot "train\completion-rank-validation.json"
& $toolkitPython $loraValidator ([string]$training.final_lora) --expected-modules 112 --expected-rank 32 --require-nonzero --json-output $rankValidationPath | Out-Null
Assert-True ($LASTEXITCODE -eq 0) "Final adapter failed the rank-32 tensor validation."
$rankValidation = Read-Json $rankValidationPath
Assert-True ([bool]$rankValidation.valid -and [int]$rankValidation.rank_counts.'32' -eq 112 -and @($rankValidation.rank_mismatch_modules).Count -eq 0 -and @($rankValidation.zero_tensors).Count -eq 0) "Final adapter is not nonzero rank 32 across all 112 modules."
$targetHeaderEvidence = Assert-KleinTransformerOnlyLoraHeader ([string]$training.final_lora)

$staged = @($staging.checkpoints | Sort-Object step)
Assert-True (-not [bool]$staging.published) "Checkpoint staging incorrectly claims publication."
Assert-True ((@($staged.step) -join ',') -eq '600,700,800,900,1000,1100,1200') "Wrong checkpoint screening set."
foreach ($checkpoint in $staged) {
    $sourceHash = Get-Sha256 ([string]$checkpoint.source)
    $destinationHash = Get-Sha256 ([string]$checkpoint.destination)
    Assert-True ($sourceHash -eq $destinationHash -and $sourceHash -eq ([string]$checkpoint.sha256).ToUpperInvariant()) "Staged checkpoint mismatch at step $($checkpoint.step)."
}

Assert-True (@($coarse.results).Count -eq 7) "Coarse screen is incomplete."
Assert-True (-not [bool]$coarse.reference_conditioning -and -not [bool]$coarse.identity_pass -and -not [bool]$coarse.face_swap) "Coarse screen used forbidden identity conditioning."
foreach ($item in @($coarse.results)) {
    $null = Assert-BenchmarkProvenance $item 'Quick' 2 $staged
}
Assert-True (@($full.results).Count -eq 6) "Top-two full screen at three strengths is incomplete."
Assert-True ((@($full.strengths | ForEach-Object { [double]$_ } | Sort-Object) -join ',') -eq '0.7,0.9,1.1') "The 0.7/0.9/1.1 strength sweep is incomplete."
Assert-True ([math]::Abs([double]$full.identity_score_tolerance - 0.02) -lt 1e-9 -and [bool]$full.lower_strength_preferred_within_tolerance) "Full-screen strength selection does not enforce the 0.02 lower-strength preference."
Assert-True (-not [bool]$full.reference_conditioning -and -not [bool]$full.identity_pass -and -not [bool]$full.face_swap) "Full screen used forbidden identity conditioning."
Assert-True (-not [bool]$full.published) "Full screen incorrectly claims publication."
foreach ($item in @($full.results)) {
    $null = Assert-BenchmarkProvenance $item 'Full' 5 $staged
}

$leader = @($full.results | Sort-Object rank | Select-Object -First 1)[0]
Assert-True ([bool]$leader.automatic_gates_passed) "Full-screen leader did not pass every automatic identity, count, and leakage gate."
Assert-True (@($leader.crowd_leakage_failures).Count -eq 0) "Full-screen leader leaks Mitch identity into a secondary face."
$categoricalBest = @($full.results | Sort-Object `
    @{ Expression = { [int]$_.automatic_gates_passed }; Descending = $true },
    @{ Expression = { [int]$_.crowd_gate_passed }; Descending = $true },
    @{ Expression = { [int]$_.crowd_identity_leakage_passed }; Descending = $true },
    @{ Expression = { [int]$_.core_gate_passed }; Descending = $true },
    @{ Expression = { [double]$_.median_core_centroid_similarity }; Descending = $true } | Select-Object -First 1)[0]
$equivalentCandidates = @($full.results | Where-Object {
    [bool]$_.automatic_gates_passed -eq [bool]$categoricalBest.automatic_gates_passed -and
    [bool]$_.crowd_gate_passed -eq [bool]$categoricalBest.crowd_gate_passed -and
    [bool]$_.crowd_identity_leakage_passed -eq [bool]$categoricalBest.crowd_identity_leakage_passed -and
    [bool]$_.core_gate_passed -eq [bool]$categoricalBest.core_gate_passed
})
$bestMedian = [double](($equivalentCandidates.median_core_centroid_similarity | Measure-Object -Maximum).Maximum)
$withinTolerance = @($equivalentCandidates | Where-Object { [double]$_.median_core_centroid_similarity -ge ($bestMedian - 0.02) })
$preferredStrength = [double](($withinTolerance.strength | Measure-Object -Minimum).Minimum)
Assert-True ([double]$leader.strength -eq $preferredStrength -and [double]$leader.median_core_centroid_similarity -ge ($bestMedian - 0.02)) "Full-screen leader violates the median-identity/lower-strength selection rule."
Assert-True (-not [bool]$nine.source_scene_conditioning -and -not [bool]$nine.reference_conditioning -and -not [bool]$nine.identity_pass -and -not [bool]$nine.face_swap) "Nine-scene run used forbidden conditioning."
Assert-True (-not [bool]$nine.published) "Nine-scene candidate was published before approval."
Assert-True ([bool]$nineManifest.other_rtx_3090_work_checked -and [int]$nineManifest.auxiliary_rtx_3090.running -eq 0 -and [int]$nineManifest.auxiliary_rtx_3090.pending -eq 0 -and -not [bool]$nineManifest.forge_rtx_3090.active) "Nine-scene generation did not preserve other RTX 3090 work."
Assert-True ((Get-Sha256 $sourceSceneLockPath) -ceq $expectedSourceSceneLockSha256) "Original nine-scene metadata lock changed."
Assert-True ([string]$nineManifest.source_scene_metadata_lock_sha256 -ceq $expectedSourceSceneLockSha256 -and (Get-Sha256 ([string]$nineManifest.source_scene_metadata_lock)) -ceq $expectedSourceSceneLockSha256) "Nine-scene manifest does not use the locked source metadata."
Assert-True (-not [bool]$nineManifest.cross_architecture_seed_reuse) "Nine-scene manifest incorrectly claims Z-Image seeds are transferable composition controls for Klein."
$nineLoraPath = Join-Path "C:\projects\AI-Tools\ComfyUI\models\loras" ([string]$nineManifest.lora)
Assert-True ([string]$nineManifest.lora_sha256 -eq (Get-Sha256 $nineLoraPath)) "Nine-scene LoRA hash does not match the generated manifest."
$leaderLoraName = "{0}-step{1:D4}.safetensors" -f $jobName, [int]$leader.step
$leaderStage = @($staged | Where-Object { [int]$_.step -eq [int]$leader.step })
Assert-True ($leaderStage.Count -eq 1) "Full-screen leader has no unique staged checkpoint."
Assert-True ([int]$nine.checkpoint_step -eq [int]$leader.step -and [double]$nine.strength -eq [double]$leader.strength) "Nine-scene completion does not use the full-screen leader step and strength."
Assert-True ([string]$nine.lora -ceq $leaderLoraName -and [string]$nineManifest.lora -ceq $leaderLoraName) "Nine-scene run used a different LoRA filename than the full-screen leader."
Assert-True ([int]$nineManifest.staging_checkpoint_step -eq [int]$leader.step) "Nine-scene staging step differs from the selected leader."
Assert-True ([string]$nineManifest.staging_checkpoint_sha256 -ceq [string]$leaderStage[0].sha256 -and [string]$nineManifest.lora_sha256 -ceq [string]$leaderStage[0].sha256) "Nine-scene LoRA hash differs from the selected staged checkpoint."
Assert-True ((Get-Sha256 ([string]$nineManifest.staging_manifest)) -ceq (Get-Sha256 $stagingPath)) "Nine-scene run points to another staging manifest."
Assert-True (@($nineEvaluation.scenes).Count -eq 9) "Nine-scene evaluation is incomplete."
Assert-True (-not [bool]$nineEvaluation.source_scene_conditioning -and -not [bool]$nineEvaluation.reference_conditioning) "Nine-scene evaluation provenance is wrong."
Assert-True (Test-Path -LiteralPath ([string]$nineEvaluation.contact_sheet) -PathType Leaf) "Nine-scene full-frame contact sheet is missing."
Assert-True (Test-Path -LiteralPath ([string]$nineEvaluation.face_geometry_contact_sheet) -PathType Leaf) "Nine-scene face-geometry contact sheet is missing."
foreach ($scene in @($nineEvaluation.scenes)) {
    Assert-True (Test-Path -LiteralPath ([string]$scene.selected_output) -PathType Leaf) "Missing nine-scene output $($scene.scene)."
    Assert-True ([string]$scene.source_sha256 -eq (Get-Sha256 ([string]$scene.source))) "Source hash changed for scene $($scene.scene)."
    Assert-True ([string]$scene.selected_output_sha256 -eq (Get-Sha256 ([string]$scene.selected_output))) "Selected-output hash changed for scene $($scene.scene)."
    Assert-True ([string]$scene.raw_output_sha256 -eq (Get-Sha256 ([string]$scene.raw_output))) "Raw-output hash changed for scene $($scene.scene)."
    Assert-True ([string]$scene.selected_output_sha256 -eq [string]$scene.raw_output_sha256) "Selected output is not a byte-identical copy of the raw generation for scene $($scene.scene)."
    $sourceMetadata = @($sourceSceneLock.scenes | Where-Object { [int]$_.number -eq [int]$scene.scene })
    Assert-True ($sourceMetadata.Count -eq 1) "Source metadata is not unique for scene $($scene.scene)."
    Assert-True ([long]$scene.original_source_seed -eq [long]$sourceMetadata[0].seed -and [string]$scene.original_source_prompt -ceq [string]$sourceMetadata[0].prompt) "Original prompt/seed provenance mismatch for scene $($scene.scene)."
    Assert-True ([string]$scene.original_source_reference_preset -ceq [string]$sourceMetadata[0].reference_preset -and [double]$scene.original_source_control_strength -eq [double]$sourceMetadata[0].control_strength) "Original composition-preset provenance mismatch for scene $($scene.scene)."
    Assert-True ([long]$scene.generation_seed -eq (8675410 + [int]$scene.scene) -and [string]$scene.generation_prompt -ceq [string]$scene.prompt -and -not [bool]$scene.cross_architecture_seed_reuse) "Klein model-specific prompt/seed provenance mismatch for scene $($scene.scene)."
    Assert-True ($scene.intended_main_selection_method -in @('prompted_center_foreground_anchor','largest_face_single_subject_scene','none')) "Missing intended-main selection evidence for scene $($scene.scene)."
    Assert-True (@($scene.manual_scene_gates).Count -ge 4) "Scene-specific manual gates are incomplete for scene $($scene.scene)."
    $expectedFaceCount = if ([int]$scene.scene -eq 1) { 4 } elseif ([int]$scene.scene -eq 2) { 5 } else { 1 }
    Assert-True ([int]$scene.expected_faces -eq $expectedFaceCount) "Scene $($scene.scene) has the wrong expected-face-count gate."
    Assert-True ($null -ne $scene.face_count_passed) "Scene $($scene.scene) is missing its automatic face-count result."
    $countFailureRecorded = 'unexpected_scene_face_count' -in @($scene.identity_diagnostic.failures)
    Assert-True ($countFailureRecorded -eq (-not [bool]$scene.face_count_passed)) "Scene $($scene.scene) face-count evidence is internally inconsistent."
}
$rooftop = @($nineEvaluation.scenes | Where-Object { [int]$_.scene -eq 9 })[0]
Assert-True (($rooftop.manual_scene_gates -join ' ') -match 'down-left' -and ($rooftop.manual_scene_gates -join ' ') -match 'two complete arms') "Rooftop direction/anatomy gates are missing."

$automaticPass = [bool]$leader.automatic_gates_passed
$audit = [ordered]@{
    schema_version = 1
    audited_utc = (Get-Date).ToUniversalTime().ToString('o')
    valid = $true
    ai_toolkit_training_complete = $true
    target_gpu = 'NVIDIA GeForce RTX 3090'
    fallback_gpu = $null
    dataset = [ordered]@{ genuine_train = 13; held_out_validation = 6; trigger = 'm1tch_person'; manifest_sha256 = $expectedManifestHash; prelaunch_cache_files = 0; run_created_latent_cache_files = 26; run_created_text_embedding_cache_files = 26; caches_created_after_run_start = $true }
    smoke_passed = $true
    production = [ordered]@{ steps = 1200; unique_finite_loss_update_indices = $uniqueFiniteLossSteps.Count; finite_loss_index_range = @(0, 1199); checkpoints = 12; zero_ooms = $true; dop_max_proven_update = [int]$productionDop.proven_updates; dop_every_update = $true; transformer_only_lora = $true; target_header = $targetHeaderEvidence; final_lora = $training.final_lora; final_lora_sha256 = $training.final_lora_sha256 }
    evaluation = [ordered]@{ heldout_reference_calibration = $faceCalibrationPath; heldout_reference_calibration_sha256 = Get-Sha256 $faceCalibrationPath; pairwise_reference_floor = 0.5533; pairwise_reference_mean = 0.6931; coarse_candidates = 7; coarse_contact_sheet = $coarse.contact_sheet; full_candidates = 6; strengths = @(0.7, 0.9, 1.1); full_contact_sheet = $full.contact_sheet; nine_scenes = 9; nine_scene_contact_sheet = $nineEvaluation.contact_sheet; face_geometry_contact_sheet = $nineEvaluation.face_geometry_contact_sheet; automatic_leader_passed = $automaticPass; leader_step = [int]$leader.step; leader_strength = [double]$leader.strength; nine_scene_evaluation = $nine.evaluation }
    privacy = 'All training, generation, and identity diagnostics ran locally.'
    published = $false
    manual_visual_approval_required = $true
}
$audit | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $auditPath -Encoding utf8
$audit | ConvertTo-Json -Depth 20
