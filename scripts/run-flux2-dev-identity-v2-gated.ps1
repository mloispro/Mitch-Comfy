param(
    [ValidateSet("Validate", "Smoke", "To200", "To300", "To500", "To1100", "To1200", "BroadSmoke", "BroadTo200")]
    [string]$Phase = "Validate",
    [switch]$ResolutionFallback
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$repoRoot = Split-Path -Parent $PSScriptRoot
$workRoot = Join-Path $repoRoot "work\flux2-dev-identity-v2"
$baseConfig = Join-Path $repoRoot "config\flux2-dev-identity-v2.yaml"
$manifestPath = Join-Path $repoRoot "datasets\mitch-identity-stills-v3\manifest.json"
$validator = Join-Path $repoRoot "scripts\validate-flux2-dev-v2-checkpoint.py"
$toolkitRoot = "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit"
$trainingRoot = Join-Path $toolkitRoot "output"
$python = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$runPy = Join-Path $toolkitRoot "run.py"
$flux2Loader = Join-Path $toolkitRoot "extensions_built_in\diffusion_models\flux2\flux2_model.py"
$memoryManager = Join-Path $toolkitRoot "toolkit\memory_management\manager_modules.py"
$primaryName = "m1tch-flux2-dev-identity-v2"
$broadName = "m1tch-flux2-dev-identity-v2-broad-fallback"
$expectedModules = if ($Phase -like "Broad*") { 160 } else { 128 }
$jobName = if ($Phase -like "Broad*") { $broadName } else { $primaryName }
$outputDirectory = Join-Path $trainingRoot $jobName

function Assert-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required local file is missing: $Path"
    }
}

function Get-CheckpointStep([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    $snippet = "import json; from safetensors import safe_open; f=safe_open(r'''$Path''',framework='pt',device='cpu'); print(json.loads((f.metadata() or {}).get('training_info','{}')).get('step',''))"
    $value = & $python -c $snippet
    if ($LASTEXITCODE -ne 0 -or -not $value) { return $null }
    return [int]$value
}

function Save-MilestoneArchive([int]$Step, [string]$SourcePath, [string]$ArchiveDirectory) {
    New-Item -ItemType Directory -Path $ArchiveDirectory -Force | Out-Null
    $destination = Join-Path $ArchiveDirectory "m1tch-flux2-dev-identity-v2-step-$($Step.ToString('0000')).safetensors"
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        if ((Get-CheckpointStep $destination) -ne $Step) { throw "Existing milestone archive has incorrect metadata: $destination" }
        return $true
    }
    if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) { return $false }
    $sourceStep = Get-CheckpointStep $SourcePath
    if ($sourceStep -ne $Step) { return $false }
    $temporary = "$destination.partial"
    Copy-Item -LiteralPath $SourcePath -Destination $temporary -Force
    $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $SourcePath).Hash
    $temporaryHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $temporary).Hash
    if ($sourceHash -ne $temporaryHash) { throw "Milestone archive copy hash mismatch at step $Step." }
    Move-Item -LiteralPath $temporary -Destination $destination -Force
    Write-Host "Archived milestone checkpoint at step ${Step}: $destination"
    return $true
}

function Get-LastLossState([string]$Path) {
    $state = [ordered]@{ step = 0; loss = $null; divergent = $false }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return [pscustomobject]$state }
    $values = @{}
    $raw = Get-Content -Raw -LiteralPath $Path
    foreach ($match in [regex]::Matches($raw, '(?<step>\d+)/\d+[^\r\n]*?loss:\s*(?<loss>[0-9]+(?:\.[0-9]*)?(?:e[+-]?\d+)?)', 'IgnoreCase')) {
        $values[[int]$match.Groups['step'].Value] = [double]::Parse($match.Groups['loss'].Value, [Globalization.CultureInfo]::InvariantCulture)
    }
    if ($values.Count -eq 0) { return [pscustomobject]$state }
    $ordered = @($values.GetEnumerator() | Sort-Object { [int]$_.Key })
    $state.step = [int]$ordered[-1].Key
    $state.loss = [double]$ordered[-1].Value
    if ($ordered.Count -ge 40) {
        $baseline = @($ordered[($ordered.Count - 40)..($ordered.Count - 21)] | ForEach-Object { [double]$_.Value } | Sort-Object)
        $median = ($baseline[9] + $baseline[10]) / 2.0
        $recent = @($ordered[($ordered.Count - 20)..($ordered.Count - 1)] | ForEach-Object { [double]$_.Value })
        $state.divergent = $median -gt 0 -and @($recent | Where-Object { $_ -gt (10.0 * $median) }).Count -eq 20
    }
    return [pscustomobject]$state
}

function Write-DatasetAudit {
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    $train = @($manifest.records | Where-Object split -eq "train")
    $validation = @($manifest.records | Where-Object split -eq "validation")
    $failures = [System.Collections.Generic.List[string]]::new()
    if ($manifest.trigger_word -ne "m1tch_person") { $failures.Add("Manifest trigger is not m1tch_person") }
    if ($train.Count -ne 13) { $failures.Add("Expected 13 training records; found $($train.Count)") }
    if ($validation.Count -ne 6) { $failures.Add("Expected 6 validation records; found $($validation.Count)") }
    $checked = [System.Collections.Generic.List[object]]::new()
    foreach ($record in $manifest.records) {
        $datasetPath = [string]$record.dataset_file
        if (-not (Test-Path -LiteralPath $datasetPath -PathType Leaf)) {
            $failures.Add("Missing dataset file: $datasetPath")
            continue
        }
        $datasetHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $datasetPath).Hash.ToLowerInvariant()
        if ($datasetHash -ne $record.dataset_sha256) { $failures.Add("Dataset hash mismatch: $datasetPath") }
        $sourceHash = $null
        if (Test-Path -LiteralPath $record.source -PathType Leaf) {
            $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $record.source).Hash.ToLowerInvariant()
            if ($sourceHash -ne $record.source_sha256) { $failures.Add("Source hash mismatch: $($record.source)") }
        } else {
            $failures.Add("Missing manifest source: $($record.source)")
        }
        if ($record.split -eq "train") {
            $captionPath = [IO.Path]::ChangeExtension($datasetPath, ".txt")
            if (-not (Test-Path -LiteralPath $captionPath -PathType Leaf)) {
                $failures.Add("Missing caption: $captionPath")
            } elseif ((Get-Content -Raw -LiteralPath $captionPath).Trim() -ne ([string]$record.caption).Trim()) {
                $failures.Add("Caption differs from manifest: $captionPath")
            }
        }
        $checked.Add([pscustomobject]@{ id = $record.id; split = $record.split; dataset_sha256 = $datasetHash; source_sha256 = $sourceHash })
    }
    $audit = [ordered]@{
        audited_utc = (Get-Date).ToUniversalTime().ToString("o")
        manifest = $manifestPath
        manifest_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
        trigger = $manifest.trigger_word
        training_records = $train.Count
        validation_records = $validation.Count
        records = $checked
        valid = $failures.Count -eq 0
        failures = $failures
    }
    $auditPath = Join-Path $workRoot "hashes\dataset-audit.json"
    New-Item -ItemType Directory -Path (Split-Path -Parent $auditPath) -Force | Out-Null
    $audit | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $auditPath -Encoding utf8
    if ($failures.Count -gt 0) { throw "Dataset audit failed: $($failures -join '; ')" }
    return $auditPath
}

function Get-ComfyState {
    $workers = [System.Collections.Generic.List[object]]::new()
    foreach ($port in 8188, 8189) {
        $queue = Invoke-RestMethod -Uri "http://127.0.0.1:$port/queue" -TimeoutSec 10
        $stats = Invoke-RestMethod -Uri "http://127.0.0.1:$port/system_stats" -TimeoutSec 10
        $workers.Add([pscustomobject]@{
            port = $port
            device = [string]$stats.devices[0].name
            queue_running = @($queue.queue_running).Count
            queue_pending = @($queue.queue_pending).Count
        })
    }
    $w3090 = $workers | Where-Object port -eq 8188
    $w4070 = $workers | Where-Object port -eq 8189
    if ($w3090.device -notmatch "RTX 3090" -or $w4070.device -notmatch "RTX 4070") {
        throw "Comfy worker-to-GPU mapping is not the expected 8188=3090, 8189=4070."
    }
    if (@($workers | Where-Object { $_.queue_running -gt 0 -or $_.queue_pending -gt 0 }).Count -gt 0) {
        throw "At least one ComfyUI queue is active; refusing to start training."
    }
    return $workers
}

foreach ($path in @($baseConfig, $manifestPath, $validator, $python, $runPy, $flux2Loader, $memoryManager)) { Assert-File $path }
if (-not (Select-String -LiteralPath $flux2Loader -Quiet -SimpleMatch "Keep the 24B encoder on CPU until it has been quantized")) {
    throw "Required FLUX.2 Dev Mistral load-order patch is absent."
}
if (-not (Select-String -LiteralPath $memoryManager -Quiet -SimpleMatch "AI_TOOLKIT_PIN_QUANTIZED_OFFLOAD")) {
    throw "Required quantized-offload patch is absent."
}

New-Item -ItemType Directory -Path $workRoot -Force | Out-Null
$auditPath = Write-DatasetAudit
$workers = Get-ComfyState
$gpuSnapshot = & nvidia-smi --query-gpu=index,name,uuid,memory.total,memory.used,utilization.gpu,temperature.gpu --format=csv,noheader,nounits
$statePath = Join-Path $workRoot "hashes\preflight-state.json"
[ordered]@{
    captured_utc = (Get-Date).ToUniversalTime().ToString("o")
    phase = $Phase
    dataset_audit = $auditPath
    workers = $workers
    nvidia_smi = @($gpuSnapshot)
    v1_preserved = Test-Path -LiteralPath (Join-Path $trainingRoot "m1tch-flux2-dev-identity-v1")
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding utf8

if ($Phase -eq "Validate") {
    Write-Host "Preflight passed. Dataset, captions, workers, queues, and compatibility patches are valid."
    exit 0
}

$targetStep = switch ($Phase) {
    "Smoke" { 2 }
    "BroadSmoke" { 2 }
    "To200" { 200 }
    "BroadTo200" { 200 }
    "To300" { 300 }
    "To500" { 500 }
    "To1100" { 1100 }
    "To1200" { 1200 }
}
$isSmoke = $Phase -in @("Smoke", "BroadSmoke")
$baseCheckpoint = Join-Path $outputDirectory "$jobName.safetensors"
$optimizerPath = Join-Path $outputDirectory "optimizer.pt"

if ($isSmoke) {
    if (Test-Path -LiteralPath $outputDirectory) {
        throw "Fresh smoke requires a new output directory; refusing to overwrite: $outputDirectory"
    }
} else {
    $requiredPreviousStep = if ($Phase -eq "To1100") { 1000 } elseif ($Phase -eq "To1200") { 300 } elseif ($Phase -in @("To300", "To500")) { 200 } else { 2 }
    $resumeCheckpoint = if ($Phase -eq "To1100") {
        Join-Path $outputDirectory "$jobName`_000001000.safetensors"
    } else {
        $baseCheckpoint
    }
    $actualPreviousStep = Get-CheckpointStep $resumeCheckpoint
    if ($Phase -eq "To1100") {
        if ($actualPreviousStep -ne 1000) { throw "To1100 requires the same job at step 1000; found $actualPreviousStep." }
        $resumeArchive = Join-Path $workRoot "checkpoint-archives\m1tch-flux2-dev-identity-v2-step-1000.safetensors"
        Assert-File $resumeArchive
        if ((Get-CheckpointStep $resumeArchive) -ne 1000) { throw "The protected step-1000 archive has incorrect metadata." }
        $resumeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $resumeCheckpoint).Hash
        $archiveHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $resumeArchive).Hash
        if ($resumeHash -ne $archiveHash) { throw "The live step-1000 checkpoint does not match its protected archive." }
    } elseif ($Phase -eq "To1200" -and $actualPreviousStep -gt 300 -and $actualPreviousStep -lt 1200) {
        if ($actualPreviousStep % 50 -ne 0) {
            throw "To1200 interruption recovery requires a durable 50-step checkpoint; found step $actualPreviousStep."
        }
        $resumeArchive = Join-Path $workRoot "checkpoint-archives\m1tch-flux2-dev-identity-v2-step-$($actualPreviousStep.ToString('0000')).safetensors"
        Assert-File $resumeArchive
        if ((Get-CheckpointStep $resumeArchive) -ne $actualPreviousStep) {
            throw "Resume archive metadata does not match step $actualPreviousStep."
        }
        $baseHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $baseCheckpoint).Hash
        $archiveHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $resumeArchive).Hash
        if ($baseHash -ne $archiveHash) {
            throw "Live checkpoint does not exactly match the archived step-$actualPreviousStep checkpoint."
        }
        Write-Host "Verified interruption recovery from archived step $actualPreviousStep."
    } elseif ($actualPreviousStep -ne $requiredPreviousStep) {
        throw "$Phase requires the same job at step $requiredPreviousStep or a verified 50-step recovery point; found $actualPreviousStep."
    }
    Assert-File $optimizerPath
}

if ($Phase -like "Broad*") {
    $rejectionPath = Join-Path $workRoot "approvals\step-200-rejected.json"
    Assert-File $rejectionPath
    $rejection = Get-Content -Raw -LiteralPath $rejectionPath | ConvertFrom-Json
    if ($rejection.decision -ne "rejected") { throw "Broad fallback requires an explicit step-200 rejection record." }
}
if ($Phase -in @("To300", "To500")) {
    $approvalPath = Join-Path $workRoot "approvals\step-200-approved.json"
    Assert-File $approvalPath
    $approval = Get-Content -Raw -LiteralPath $approvalPath | ConvertFrom-Json
    $checkpointHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $baseCheckpoint).Hash.ToLowerInvariant()
    if (
        $approval.decision -ne "approved" -or
        $approval.checkpoint_sha256 -ne $checkpointHash -or
        [int]$approval.approved_through_step -lt $targetStep
    ) {
        throw "$Phase requires explicit approval bound to the current step-200 checkpoint hash."
    }
}
if ($Phase -eq "To1200") {
    $approvalPath = Join-Path $workRoot "approvals\step-300-approved.json"
    Assert-File $approvalPath
    $approval = Get-Content -Raw -LiteralPath $approvalPath | ConvertFrom-Json
    $approvalCheckpoint = Join-Path $workRoot "checkpoint-archives\m1tch-flux2-dev-identity-v2-step-0300.safetensors"
    Assert-File $approvalCheckpoint
    $checkpointHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $approvalCheckpoint).Hash.ToLowerInvariant()
    if (
        $approval.decision -ne "approved" -or
        $approval.checkpoint_sha256 -ne $checkpointHash -or
        [int]$approval.approved_through_step -lt $targetStep
    ) {
        throw "To1200 requires explicit approval bound to the current step-300 checkpoint hash."
    }
}
if ($Phase -eq "To1100") {
    $approvalPath = Join-Path $workRoot "approvals\step-1000-approved.json"
    Assert-File $approvalPath
    $approval = Get-Content -Raw -LiteralPath $approvalPath | ConvertFrom-Json
    $approvalCheckpoint = Join-Path $workRoot "checkpoint-archives\m1tch-flux2-dev-identity-v2-step-1000.safetensors"
    Assert-File $approvalCheckpoint
    $checkpointHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $approvalCheckpoint).Hash.ToLowerInvariant()
    if (
        $approval.decision -ne "approved" -or
        $approval.checkpoint_sha256 -ne $checkpointHash -or
        [int]$approval.approved_through_step -lt $targetStep
    ) {
        throw "To1100 requires explicit approval bound to the current step-1000 checkpoint hash."
    }
}
if ($ResolutionFallback -and -not $isSmoke) { throw "Resolution fallback is allowed only for a fresh smoke run." }

$runtimeDirectory = Join-Path $workRoot "runtime-configs"
$logDirectory = Join-Path $workRoot "logs"
$monitorDirectory = Join-Path $workRoot "monitoring"
$validationDirectory = Join-Path $workRoot "checkpoint-validation"
$archiveDirectory = Join-Path $workRoot "checkpoint-archives"
New-Item -ItemType Directory -Path $runtimeDirectory, $logDirectory, $monitorDirectory, $validationDirectory, $archiveDirectory -Force | Out-Null
$phaseTag = $Phase.ToLowerInvariant()
$attempt = 1
$tag = $phaseTag
while (Test-Path -LiteralPath (Join-Path $logDirectory "$tag-training.log")) {
    $attempt += 1
    $tag = "$phaseTag-attempt-$attempt"
}
$runtimeConfig = Join-Path $runtimeDirectory "$tag.yaml"
$trainingLog = Join-Path $logDirectory "$tag-training.log"
$stdoutLog = Join-Path $logDirectory "$tag-stdout.log"
$stderrLog = Join-Path $logDirectory "$tag-stderr.log"
$monitorCsv = Join-Path $monitorDirectory "$tag.csv"
$healthJsonl = Join-Path $monitorDirectory "$tag-health.jsonl"

$configText = Get-Content -Raw -LiteralPath $baseConfig
$stepsNeedle = "        steps: 500"
if (-not $configText.Contains($stepsNeedle)) { throw "Final config no longer contains the expected 500-step field." }
$configText = $configText.Replace($stepsNeedle, "        steps: $targetStep")
if ($jobName -ne $primaryName) {
    $configText = $configText.Replace($primaryName, $jobName)
    $filterBlock = @"
        network_kwargs:
          only_if_contains:
            - ".img_attn."
            - ".txt_attn."
            - ".single_blocks."
"@
    if (-not $configText.Contains($filterBlock)) { throw "Could not locate the attention filter for broad fallback removal." }
    $configText = $configText.Replace($filterBlock, "")
}
if ($ResolutionFallback) {
    $resolutionNeedle = "          resolution: 1024"
    if (-not $configText.Contains($resolutionNeedle)) { throw "Could not locate the primary resolution field." }
    $configText = $configText.Replace($resolutionNeedle, "          resolution: [768, 1024]")
}
$configText | Set-Content -LiteralPath $runtimeConfig -Encoding utf8

$archiveSteps = @()
$archivedMilestones = [System.Collections.Generic.HashSet[int]]::new()
if ($Phase -in @("To1100", "To1200")) {
    $archiveSteps = @(250) + @(300..$targetStep | Where-Object { $_ % 50 -eq 0 })
    $step250Source = Join-Path $outputDirectory "$jobName`_000000250.safetensors"
    if (-not (Save-MilestoneArchive -Step 250 -SourcePath $step250Source -ArchiveDirectory $archiveDirectory)) {
        throw "Could not preserve the required step-250 baseline before the long run."
    }
    [void]$archivedMilestones.Add(250)
    if (-not (Save-MilestoneArchive -Step 300 -SourcePath $baseCheckpoint -ArchiveDirectory $archiveDirectory)) {
        throw "Could not preserve the required step-300 baseline before the long run."
    }
    [void]$archivedMilestones.Add(300)
}

# Free only the idle 3090 worker's loaded model allocations. The 4070 worker stays online.
Invoke-RestMethod -Uri "http://127.0.0.1:8188/free" -Method Post -ContentType "application/json" -Body '{"unload_models":true,"free_memory":true}' -TimeoutSec 30 | Out-Null

$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:PYTHONUNBUFFERED = "1"
$env:CUDA_VISIBLE_DEVICES = "0"
$env:AI_TOOLKIT_PIN_QUANTIZED_OFFLOAD = "0"

$process = Start-Process -FilePath $python -ArgumentList @($runPy, $runtimeConfig, "-l", $trainingLog) -WorkingDirectory $toolkitRoot -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -WindowStyle Hidden -PassThru
$lastHealthStep = -1
$stopReason = $null
try {
    while (-not $process.HasExited) {
        Start-Sleep -Seconds 30
        $process.Refresh()
        $lossState = Get-LastLossState $trainingLog
        try {
            $gpu = (& nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader,nounits | Select-Object -First 1) -split ',' | ForEach-Object Trim
            if ($gpu.Count -lt 5) { throw "nvidia-smi returned incomplete telemetry" }
            $os = Get-CimInstance Win32_OperatingSystem
            [pscustomobject]@{
                timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
                phase = $Phase
                optimizer_step = $lossState.step
                loss = $lossState.loss
                gpu_memory_used_mib = $gpu[1]
                gpu_memory_total_mib = $gpu[2]
                gpu_utilization_percent = $gpu[3]
                gpu_temperature_c = $gpu[4]
                system_memory_used_gib = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 3)
                system_memory_total_gib = [math]::Round($os.TotalVisibleMemorySize / 1MB, 3)
            } | Export-Csv -LiteralPath $monitorCsv -NoTypeInformation -Append
        } catch {
            [ordered]@{
                timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
                optimizer_step = $lossState.step
                monitor_warning = $_.Exception.Message
            } | ConvertTo-Json -Compress | Add-Content -LiteralPath $healthJsonl -Encoding utf8
        }

        $combined = (@($trainingLog, $stdoutLog, $stderrLog) | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { Get-Content -Raw -LiteralPath $_ }) -join "`n"
        if ($combined -match '(?i)(CUDA out of memory|OutOfMemoryError)') { $stopReason = "OOM" }
        if ($combined -match '(?i)loss:\s*(nan|[+-]?inf)\b') { $stopReason = "NaN or Inf loss" }
        if ($combined -match 'create LoRA for U-Net:\s*(\d+) modules\.' -and [int]$Matches[1] -ne $expectedModules) {
            $stopReason = "Target module count $($Matches[1]) does not equal $expectedModules"
        }
        $missingKeysMatch = [regex]::Match($combined, 'Missing keys:\s*(?<keys>[^\r\n]+)')
        if ($missingKeysMatch.Success -and $missingKeysMatch.Groups['keys'].Value.Trim() -ne '[]') {
            $stopReason = "Missing LoRA keys: $($missingKeysMatch.Groups['keys'].Value.Trim())"
        }
        if ($lossState.divergent) { $stopReason = "Loss exceeded ten times its preceding rolling median for 20 optimizer steps" }

        if ($Phase -in @("To1100", "To1200")) {
            foreach ($archiveStep in @($archiveSteps | Where-Object { $_ -gt 300 -and $_ -lt $targetStep -and -not $archivedMilestones.Contains([int]$_) })) {
                $numberedSource = Join-Path $outputDirectory "$jobName`_$($archiveStep.ToString('000000000')).safetensors"
                if (Save-MilestoneArchive -Step $archiveStep -SourcePath $numberedSource -ArchiveDirectory $archiveDirectory) {
                    [void]$archivedMilestones.Add([int]$archiveStep)
                }
            }
        }

        $healthStep = [int]([math]::Floor($lossState.step / 10) * 10)
        if ($healthStep -gt 0 -and $healthStep -gt $lastHealthStep) {
            $latestCheckpoint = Get-ChildItem -LiteralPath $outputDirectory -Filter "*.safetensors" -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
            [ordered]@{
                timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
                optimizer_step = $lossState.step
                loss = $lossState.loss
                latest_checkpoint = if ($latestCheckpoint) { $latestCheckpoint.FullName } else { $null }
                latest_checkpoint_size = if ($latestCheckpoint) { $latestCheckpoint.Length } else { $null }
                hard_stop = $stopReason
            } | ConvertTo-Json -Compress | Add-Content -LiteralPath $healthJsonl -Encoding utf8
            $lastHealthStep = $healthStep
        }
        if ($stopReason) {
            Stop-Process -Id $process.Id -Force
            throw "Training hard-stopped: $stopReason"
        }
    }
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {
        throw "AI-Toolkit exited with code $($process.ExitCode). See $stderrLog and $trainingLog."
    }
}
finally {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue }
}

$fullLog = (@($trainingLog, $stdoutLog, $stderrLog) | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { Get-Content -Raw -LiteralPath $_ }) -join "`n"
if ($fullLog -notmatch "create LoRA for U-Net:\s*$expectedModules modules\.") { throw "Expected $expectedModules targeted modules were not confirmed in the smoke log." }
if (-not $isSmoke -and $fullLog -notmatch "Missing keys:\s*\[\]") { throw "The resume log did not confirm an empty missing-key list." }
if (-not $isSmoke -and $fullLog -notmatch "Loading optimizer state from") { throw "Resume phase did not confirm optimizer-state loading." }

$validationReport = Join-Path $validationDirectory "$tag-step-$targetStep.json"
& $python $validator $baseCheckpoint --expected-step $targetStep --expected-modules $expectedModules --optimizer $optimizerPath --json-output $validationReport
if ($LASTEXITCODE -ne 0) { throw "Checkpoint or optimizer validation failed: $validationReport" }

if ($Phase -in @("To1100", "To1200")) {
    if (-not (Save-MilestoneArchive -Step $targetStep -SourcePath $baseCheckpoint -ArchiveDirectory $archiveDirectory)) {
        throw "Could not preserve the final step-$targetStep milestone."
    }
    foreach ($archiveStep in $archiveSteps) {
        $archivePath = Join-Path $archiveDirectory "m1tch-flux2-dev-identity-v2-step-$($archiveStep.ToString('0000')).safetensors"
        Assert-File $archivePath
        $archiveValidation = Join-Path $validationDirectory "archive-step-$($archiveStep.ToString('0000')).json"
        $validatorOutput = & $python $validator $archivePath --expected-step $archiveStep --expected-modules $expectedModules --json-output $archiveValidation
        if ($LASTEXITCODE -ne 0) { throw "Archived milestone validation failed at step $archiveStep." }
    }
}

[ordered]@{
    completed_utc = (Get-Date).ToUniversalTime().ToString("o")
    phase = $Phase
    job_name = $jobName
    target_step = $targetStep
    expected_modules = $expectedModules
    runtime_config = $runtimeConfig
    checkpoint = $baseCheckpoint
    checkpoint_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $baseCheckpoint).Hash.ToLowerInvariant()
    optimizer = $optimizerPath
    validation = $validationReport
    monitoring = $monitorCsv
    resolution_fallback = [bool]$ResolutionFallback
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $workRoot "$tag-complete.json") -Encoding utf8

Write-Host "$Phase completed and validated at optimizer step $targetStep with $expectedModules LoRA modules."
