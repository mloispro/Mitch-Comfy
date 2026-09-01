param(
    [int]$TrainerProcessId = 16936,
    [int]$TrainingWrapperProcessId = 7400,
    [int]$PostExitGraceSeconds = 300,
    [int[]]$Steps = @(700, 800, 900, 1000, 1100, 1200)
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runRoot = Join-Path $repoRoot "work\flux2-klein9b-identity-v3-r32-dop\train"
$checkpointRoot = Join-Path $runRoot "ai-toolkit-output\m1tch-flux2-klein9b-identity-v3-r32-dop"
$checkpointStem = "m1tch-flux2-klein9b-identity-v3-r32-dop"
$toolkitPython = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$validator = Join-Path $PSScriptRoot "validate-zimage-lora.py"

foreach ($requiredPath in @($checkpointRoot, $toolkitPython, $validator)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required path is missing: $requiredPath"
    }
}

foreach ($step in $Steps) {
    $stepText = $step.ToString("000000000")
    $checkpointPath = Join-Path $checkpointRoot "${checkpointStem}_${stepText}.safetensors"
    $validationPath = Join-Path $runRoot ("checkpoint-{0}-validation.json" -f $step.ToString("0000"))

    $bothProcessesExitedAt = $null
    while (-not (Test-Path -LiteralPath $checkpointPath)) {
        $trainerAlive = [bool](Get-Process -Id $TrainerProcessId -ErrorAction SilentlyContinue)
        $wrapperAlive = [bool](Get-Process -Id $TrainingWrapperProcessId -ErrorAction SilentlyContinue)
        if (-not $trainerAlive -and -not $wrapperAlive) {
            if ($null -eq $bothProcessesExitedAt) { $bothProcessesExitedAt = Get-Date }
            if (((Get-Date) - $bothProcessesExitedAt).TotalSeconds -ge $PostExitGraceSeconds) {
                throw "Trainer and wrapper exited, and checkpoint $step did not appear during the $PostExitGraceSeconds-second recovery grace period."
            }
        }
        Start-Sleep -Seconds 5
    }

    # Do not inspect a file while safetensors is still being flushed to disk.
    do {
        $firstLength = (Get-Item -LiteralPath $checkpointPath).Length
        Start-Sleep -Seconds 2
        $secondLength = (Get-Item -LiteralPath $checkpointPath).Length
    } while ($firstLength -ne $secondLength -or $secondLength -le 0)

    & $toolkitPython $validator $checkpointPath `
        --expected-modules 112 `
        --expected-rank 32 `
        --require-nonzero `
        --json-output $validationPath | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Checkpoint validator failed for step $step with exit code $LASTEXITCODE."
    }

    $validation = Get-Content -Raw -LiteralPath $validationPath | ConvertFrom-Json
    $trainingInfo = [string]$validation.metadata.training_info | ConvertFrom-Json
    if (-not $validation.valid -or [int]$trainingInfo.step -ne $step) {
        throw "Checkpoint $step failed validation or contains incorrect step metadata."
    }
    $expectedMetadata = [ordered]@{
        architecture = "flux2_klein_9b"
        ss_base_model_version = "flux2_klein_9b"
        base_model = "black-forest-labs/FLUX.2-klein-base-9B"
        trigger = "m1tch_person"
        target_gpu = "NVIDIA GeForce RTX 3090"
        fallback_gpu = "none"
        ai_toolkit_commit = "0f788923aef28e3a87fa68cfa15a761d9d499d6c"
        source_manifest_sha256 = "D56FE2D752FEBFA63CA0E76689DFD9D4EAAC7443CA086FFA9DFEF51186563003"
    }
    foreach ($entry in $expectedMetadata.GetEnumerator()) {
        if ([string]$validation.metadata.($entry.Key) -cne [string]$entry.Value) {
            throw "Checkpoint $step metadata mismatch for $($entry.Key): expected '$($entry.Value)', got '$($validation.metadata.($entry.Key))'."
        }
    }

    $validation | Add-Member -NotePropertyName sha256 -NotePropertyValue ((Get-FileHash -Algorithm SHA256 -LiteralPath $checkpointPath).Hash) -Force
    $validation | Add-Member -NotePropertyName validated_utc -NotePropertyValue ([DateTime]::UtcNow.ToString("o")) -Force
    $validation | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $validationPath -Encoding utf8
    Write-Output ("CHECKPOINT_VALIDATED step={0} sha256={1}" -f $step, $validation.sha256)
}

Write-Output "ALL_REQUESTED_CHECKPOINTS_VALIDATED"
