[CmdletBinding()]
param(
    [ValidateSet("Validate", "Smoke", "Train")]
    [string]$Phase = "Validate",
    [int]$MinimumAvailableMemoryMB = 16384,
    [switch]$SkipMemoryGate
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$repoRoot = Split-Path -Parent $PSScriptRoot
$toolkitRoot = "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit"
$python = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$runPy = Join-Path $toolkitRoot "run.py"
$manifestPath = Join-Path $repoRoot "datasets\mitch-identity-stills-v3\manifest.json"
$workRoot = Join-Path $repoRoot "work\flux2-klein-identity-v3"
$configPath = if ($Phase -eq "Smoke") {
    Join-Path $repoRoot "config\flux2-klein-identity-v3-4070-smoke.yaml"
} else {
    Join-Path $repoRoot "config\flux2-klein-identity-v3-4070.yaml"
}
$expectedToolkitCommit = "0f788923aef28e3a87fa68cfa15a761d9d499d6c"
$expectedManifestHash = "d56fe2d752febfa63ca0e76689dfd9d4eaac7443ca086ffa9dfef51186563003"

function Assert-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required local file is missing: $Path"
    }
}

function Get-ComfyWorker([int]$Port) {
    try {
        $stats = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/system_stats" -TimeoutSec 10
        $queue = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/queue" -TimeoutSec 10
        return [pscustomobject]@{
            port = $Port
            device = [string](@($stats.devices)[0].name)
            running = @($queue.queue_running).Count
            pending = @($queue.queue_pending).Count
        }
    } catch {
        return [pscustomobject]@{ port = $Port; device = "offline"; running = 0; pending = 0 }
    }
}

function Write-DatasetAudit {
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    $failures = [System.Collections.Generic.List[string]]::new()
    $train = @($manifest.records | Where-Object split -eq "train")
    $validation = @($manifest.records | Where-Object split -eq "validation")
    if ($manifest.trigger_word -ne "m1tch_person") { $failures.Add("Unexpected trigger word") }
    if ($train.Count -ne 13) { $failures.Add("Expected 13 training images; found $($train.Count)") }
    if ($validation.Count -ne 6) { $failures.Add("Expected 6 validation images; found $($validation.Count)") }
    $trainHashes = [System.Collections.Generic.HashSet[string]]::new()
    $validationHashes = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($record in $manifest.records) {
        $path = [string]$record.dataset_file
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            $failures.Add("Missing dataset image: $path")
            continue
        }
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
        if ($hash -ne [string]$record.dataset_sha256) { $failures.Add("Image hash mismatch: $path") }
        if ($record.split -eq "train") {
            [void]$trainHashes.Add($hash)
            $captionPath = [IO.Path]::ChangeExtension($path, ".txt")
            if (-not (Test-Path -LiteralPath $captionPath -PathType Leaf)) {
                $failures.Add("Missing caption: $captionPath")
            } else {
                $caption = (Get-Content -Raw -LiteralPath $captionPath).Trim()
                if ($caption -ne ([string]$record.caption).Trim()) { $failures.Add("Caption mismatch: $captionPath") }
                if (-not $caption.StartsWith("m1tch_person")) { $failures.Add("Trigger is not first: $captionPath") }
            }
        } else {
            [void]$validationHashes.Add($hash)
        }
    }
    if ($trainHashes.Overlaps($validationHashes)) { $failures.Add("Training and validation hashes overlap") }
    $auditPath = Join-Path $workRoot "dataset-audit.json"
    New-Item -ItemType Directory -Path $workRoot -Force | Out-Null
    [ordered]@{
        audited_utc = (Get-Date).ToUniversalTime().ToString("o")
        manifest = $manifestPath
        manifest_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
        training_images = $train.Count
        validation_images = $validation.Count
        trigger = $manifest.trigger_word
        valid = $failures.Count -eq 0
        failures = $failures
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $auditPath -Encoding utf8
    if ($failures.Count -gt 0) { throw "Dataset audit failed: $($failures -join '; ')" }
    return $auditPath
}

foreach ($path in @($python, $runPy, $manifestPath, $configPath)) { Assert-File $path }
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if ($manifestHash -ne $expectedManifestHash) { throw "Dataset manifest changed; research and re-audit it before training." }
$toolkitCommit = (& git -c safe.directory='C:/projects/AI-Tools/ai-toolkit/AI-Toolkit' -C $toolkitRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $toolkitCommit -ne $expectedToolkitCommit) {
    throw "AI-Toolkit revision differs from the tested project lock: $toolkitCommit"
}

$auditPath = Write-DatasetAudit
$workers = @(Get-ComfyWorker 8188; Get-ComfyWorker 8189)
$worker3090 = $workers | Where-Object port -eq 8188
$worker4070 = $workers | Where-Object port -eq 8189
if ($worker3090.device -ne "offline" -and $worker3090.device -notmatch "RTX 3090") {
    throw "Port 8188 is not the expected RTX 3090 worker: $($worker3090.device)"
}
if ($worker4070.device -ne "offline" -and $worker4070.device -notmatch "RTX 4070") {
    throw "Port 8189 is not the expected RTX 4070 worker: $($worker4070.device)"
}

$gpuSnapshot = @(& nvidia-smi --query-gpu=index,name,uuid,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu --format=csv,noheader,nounits)
$memorySample = Get-Counter '\Memory\Available MBytes','\Memory\Committed Bytes','\Memory\Commit Limit' | Select-Object -ExpandProperty CounterSamples
$availableMemoryMB = [int](($memorySample | Where-Object Path -like '*available mbytes').CookedValue)
$preflightPath = Join-Path $workRoot "preflight-$($Phase.ToLowerInvariant()).json"
[ordered]@{
    captured_utc = (Get-Date).ToUniversalTime().ToString("o")
    phase = $Phase
    config = $configPath
    config_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $configPath).Hash.ToLowerInvariant()
    dataset_audit = $auditPath
    ai_toolkit_commit = $toolkitCommit
    workers = $workers
    available_memory_mb = $availableMemoryMB
    minimum_available_memory_mb = $MinimumAvailableMemoryMB
    nvidia_smi = $gpuSnapshot
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $preflightPath -Encoding utf8

if ($Phase -eq "Validate") {
    Write-Host "Preflight passed. Dataset, config, toolkit revision, GPUs, and queues were recorded at $preflightPath"
    exit 0
}
if (@($workers | Where-Object { $_.running -gt 0 -or $_.pending -gt 0 }).Count -gt 0) {
    throw "A ComfyUI worker has active or pending work; refusing to start training."
}
if (-not $SkipMemoryGate -and $availableMemoryMB -lt $MinimumAvailableMemoryMB) {
    throw "Only $availableMemoryMB MB system memory is available; require $MinimumAvailableMemoryMB MB before loading Klein."
}

$outputName = if ($Phase -eq "Smoke") { "m1tch-flux2-klein-4b-identity-v3-smoke" } else { "m1tch-flux2-klein-4b-identity-v3" }
$outputDirectory = Join-Path (Join-Path $repoRoot "work\ai-toolkit-output") $outputName
if (Test-Path -LiteralPath $outputDirectory) {
    throw "Output already exists; refusing an ambiguous overwrite or resume: $outputDirectory"
}

$env:CUDA_VISIBLE_DEVICES = "1"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:HF_DATASETS_OFFLINE = "1"
$env:TOKENIZERS_PARALLELISM = "false"
$visibleGpu = (& $python -c "import torch; print(torch.cuda.device_count()); print(torch.cuda.get_device_name(0) if torch.cuda.device_count() else 'NONE')") -join "`n"
if ($LASTEXITCODE -ne 0 -or $visibleGpu -notmatch "(?m)^1\r?$" -or $visibleGpu -notmatch "RTX 4070") {
    throw "CUDA isolation failed; expected exactly one visible RTX 4070, got: $visibleGpu"
}

$logDirectory = Join-Path $workRoot "logs"
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$transcript = Join-Path $logDirectory "$($Phase.ToLowerInvariant())-$stamp.log"
Write-Host "Starting $Phase on isolated physical GPU 1 (RTX 4070). Transcript: $transcript"
& $python $runPy $configPath 2>&1 | Tee-Object -FilePath $transcript
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) { throw "AI-Toolkit exited with code $exitCode. See $transcript" }

$adapter = Join-Path $outputDirectory "$outputName.safetensors"
Assert-File $adapter
& $python -c "import json,sys,torch; from safetensors import safe_open; p=sys.argv[1]; f=safe_open(p,framework='pt',device='cpu'); tensors=[f.get_tensor(k) for k in f.keys()]; print(json.dumps({'path':p,'tensor_count':len(tensors),'element_count':sum(t.numel() for t in tensors),'all_finite':all(torch.isfinite(t).all().item() for t in tensors),'metadata':f.metadata()},default=str))" $adapter | Set-Content -LiteralPath (Join-Path $workRoot "$($Phase.ToLowerInvariant())-adapter-validation.json") -Encoding utf8
Write-Host "$Phase completed successfully on the RTX 4070: $adapter"
