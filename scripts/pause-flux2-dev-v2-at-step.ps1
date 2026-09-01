param(
    [int]$TargetStep = 1000,
    [int]$SupervisorPid = 33420,
    [int]$PollSeconds = 5
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$workRoot = Join-Path $repoRoot "work\flux2-dev-identity-v2"
$outputRoot = "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit\output\m1tch-flux2-dev-identity-v2"
$python = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$validator = Join-Path $repoRoot "scripts\validate-flux2-dev-v2-checkpoint.py"
$checkpointName = "m1tch-flux2-dev-identity-v2_$($TargetStep.ToString('000000000')).safetensors"
$checkpoint = Join-Path $outputRoot $checkpointName
$optimizer = Join-Path $outputRoot "optimizer.pt"
$archiveDirectory = Join-Path $workRoot "checkpoint-archives"
$archive = Join-Path $archiveDirectory "m1tch-flux2-dev-identity-v2-step-$($TargetStep.ToString('0000')).safetensors"
$validation = Join-Path $workRoot "checkpoint-validation\pause-step-$($TargetStep.ToString('0000')).json"
$pauseRecord = Join-Path $workRoot "approvals\step-$TargetStep-paused.json"
$benchmark = Join-Path $repoRoot "scripts\benchmark-flux2-dev-v2-gate.ps1"
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source

New-Item -ItemType Directory -Path $archiveDirectory, (Split-Path -Parent $validation), (Split-Path -Parent $pauseRecord) -Force | Out-Null
if (Test-Path -LiteralPath $pauseRecord -PathType Leaf) {
    Write-Host "Pause record already exists: $pauseRecord"
    exit 0
}

function Get-TrainingProcess {
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $SupervisorPid" -ErrorAction Stop)
    return $children | Where-Object {
        $_.Name -ieq "python.exe" -and
        $_.CommandLine -match "run\.py" -and
        $_.CommandLine -match "to1200-attempt-2\.yaml"
    } | Select-Object -First 1
}

while ($true) {
    if (Test-Path -LiteralPath $checkpoint -PathType Leaf) {
        $checkpointBefore = Get-Item -LiteralPath $checkpoint
        $optimizerBefore = Get-Item -LiteralPath $optimizer -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        $checkpointAfter = Get-Item -LiteralPath $checkpoint
        $optimizerAfter = Get-Item -LiteralPath $optimizer -ErrorAction SilentlyContinue
        $filesAreStable = (
            $optimizerBefore -and $optimizerAfter -and
            $checkpointBefore.Length -eq $checkpointAfter.Length -and
            $checkpointBefore.LastWriteTimeUtc -eq $checkpointAfter.LastWriteTimeUtc -and
            $optimizerBefore.Length -eq $optimizerAfter.Length -and
            $optimizerBefore.LastWriteTimeUtc -eq $optimizerAfter.LastWriteTimeUtc -and
            $checkpointAfter.Length -gt 100MB -and
            $optimizerAfter.Length -gt 100MB -and
            $optimizerAfter.LastWriteTimeUtc -ge $checkpointAfter.LastWriteTimeUtc
        )
        if (-not $filesAreStable) {
            Start-Sleep -Seconds $PollSeconds
            continue
        }

        & $python $validator $checkpoint --expected-step $TargetStep --expected-modules 128 --optimizer $optimizer --json-output $validation
        $validationExit = $LASTEXITCODE
        $trainingProcess = Get-TrainingProcess
        if ($validationExit -ne 0) {
            if ($trainingProcess) { Stop-Process -Id $trainingProcess.ProcessId -Force }
            throw "Step-$TargetStep checkpoint or optimizer validation failed; training was stopped."
        }

        if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
            $temporary = "$archive.pause.partial"
            Copy-Item -LiteralPath $checkpoint -Destination $temporary -Force
            $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $checkpoint).Hash
            $copyHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $temporary).Hash
            if ($sourceHash -ne $copyHash) {
                if ($trainingProcess) { Stop-Process -Id $trainingProcess.ProcessId -Force }
                throw "Step-$TargetStep protected archive hash mismatch; training was stopped."
            }
            if (Test-Path -LiteralPath $archive -PathType Leaf) {
                Remove-Item -LiteralPath $temporary -Force
            } else {
                Move-Item -LiteralPath $temporary -Destination $archive
            }
        }

        if ($trainingProcess) {
            Stop-Process -Id $trainingProcess.ProcessId -Force
            Start-Sleep -Seconds 5
        }
        $stillRunning = Get-TrainingProcess
        if ($stillRunning) { throw "Training process did not stop at step $TargetStep." }

        $report = Get-Content -Raw -LiteralPath $validation | ConvertFrom-Json
        $pauseState = [ordered]@{
            paused_utc = (Get-Date).ToUniversalTime().ToString("o")
            target_step = $TargetStep
            checkpoint = $archive
            checkpoint_sha256 = $report.sha256
            optimizer = $optimizer
            optimizer_reloadable = $report.optimizer.reloadable
            training_process_stopped = $true
            resume_requires_mitch_approval = $true
            evaluation_status = "preparing"
            evaluation_manifest = $null
            evaluation_contact_sheet = $null
        }
        $pauseState | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $pauseRecord -Encoding utf8
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:8188/free" -Method Post -ContentType "application/json" -Body '{"unload_models":true,"free_memory":true}' -TimeoutSec 30 | Out-Null
        } catch {
            Write-Warning "The 3090 Comfy worker could not be freed after the pause: $($_.Exception.Message)"
        }

        $releaseDeadline = (Get-Date).AddMinutes(3)
        do {
            $usedMemory = [int](((& nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | Select-Object -First 1).Trim()))
            if ($usedMemory -le 4096) { break }
            Start-Sleep -Seconds 5
        } while ((Get-Date) -lt $releaseDeadline)
        if ($usedMemory -gt 4096) { throw "RTX 3090 memory did not release after the step-$TargetStep pause." }

        $pauseState.evaluation_status = "running"
        $pauseState | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $pauseRecord -Encoding utf8
        & $pwsh -NoProfile -ExecutionPolicy Bypass -File $benchmark -Mode Gate1000
        if ($LASTEXITCODE -ne 0) { throw "Gate1000 benchmark failed with exit code $LASTEXITCODE." }
        $reportDirectory = Join-Path $workRoot "comparisons\gate-1000"
        $manifest = Join-Path $reportDirectory "gate-1000-manifest.json"
        $sheet = Join-Path $reportDirectory "gate-1000-review-thumbnails.jpg"
        if (-not (Test-Path -LiteralPath $manifest -PathType Leaf) -or -not (Test-Path -LiteralPath $sheet -PathType Leaf)) {
            throw "Gate1000 benchmark did not create its manifest and contact sheet."
        }
        $pauseState.evaluation_status = "complete"
        $pauseState.evaluation_completed_utc = (Get-Date).ToUniversalTime().ToString("o")
        $pauseState.evaluation_manifest = $manifest
        $pauseState.evaluation_contact_sheet = $sheet
        $pauseState | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $pauseRecord -Encoding utf8
        Write-Host "Training paused and validated at step $TargetStep; Gate1000 benchmark completed."
        exit 0
    }

    if (-not (Get-Process -Id $SupervisorPid -ErrorAction SilentlyContinue)) {
        throw "Training supervisor exited before the step-$TargetStep checkpoint appeared."
    }
    Start-Sleep -Seconds $PollSeconds
}
