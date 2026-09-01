[CmdletBinding()]
param(
    [ValidateSet("Validate", "Smoke", "Train", "Benchmark", "Publish")]
    [string]$Phase = "Validate",
    [string]$CandidatePath = "",
    [switch]$MitchApproved
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ToolkitRoot = "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit"
$ToolkitPython = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$ToolkitRun = Join-Path $ToolkitRoot "run.py"
$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
$SourceRoot = "C:\projects\AI-Tools\Mitch photos\mitch-identity-stills-v3"
$SourceDataset = Join-Path $SourceRoot "dataset"
$RunRoot = Join-Path $RepoRoot "work\zimage-base-identity-v1"
$ExpectedManifestHash = "8DDC058D0A223343721D4665EB07ED319D6F26038697C3F619124CC599175664"
$ExpectedToolkitCommit = "0f788923aef28e3a87fa68cfa15a761d9d499d6c"
$DeclaredPatchDigest = "99a8e6c62771d72e04a83f4f1b3bbb950f773cd8"
$ExpectedSnapshot = "04cc4abb7c5069926f75c9bfde9ef43d49423021"
$SnapshotPath = "C:\Users\Mitch\.cache\huggingface\hub\models--Tongyi-MAI--Z-Image\snapshots\$ExpectedSnapshot"
$ProductionConfig = Join-Path $RepoRoot "config\zimage-base-identity-v1-3090.yaml"
$SmokeConfig = Join-Path $RepoRoot "config\zimage-base-identity-v1-3090-smoke.yaml"
$LoraValidator = Join-Path $RepoRoot "scripts\validate-zimage-lora.py"
$BenchmarkRunner = Join-Path $RepoRoot "scripts\benchmark-zimage-base-identity-v1.ps1"

$ToolkitFileLocks = [ordered]@{
    "extensions_built_in\diffusion_models\z_image\z_image.py" = "3F40AAC47CF212145C3DBD81520CE3DFF9FE94B6C40BB4F3B0635C302534B154"
    "extensions_built_in\diffusion_models\flux2\flux2_model.py" = "B46F580380C49F024CB71CA430A07A48CBE6BE2AD91685C3E91B42A21636D6B8"
    "jobs\process\BaseSDTrainProcess.py" = "B8F25B79ABB6B50B20F2855508B263A1996EA36E0C60B9DFD971E30C07B6D4D3"
    "toolkit\memory_management\manager_modules.py" = "64B1E76250A21EAF63AC97CF5C807C2667A92E46254C56EA5937DF80A7773D0C"
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Assert-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required file is missing: $Path"
    }
}

function Assert-Config([string]$Path, [int]$ExpectedSteps, [string]$ExpectedName) {
    Assert-File $Path
    $text = Get-Content -Raw -LiteralPath $Path
    $required = @(
        "name: $ExpectedName",
        "training_seed: 42",
        "trigger_word: m1tch_person",
        "linear: 16",
        "linear_alpha: 16",
        "resolution: [768, 1024]",
        "steps: $ExpectedSteps",
        "optimizer: adamw8bit",
        "lr: 0.0001",
        "lr_scheduler: constant",
        "content_or_style: balanced",
        "name_or_path: C:\Users\Mitch\.cache\huggingface\hub\models--Tongyi-MAI--Z-Image\snapshots\04cc4abb7c5069926f75c9bfde9ef43d49423021",
        "arch: zimage",
        "qtype: qfloat8",
        "qtype_te: qfloat8",
        "low_vram: true",
        "layer_offloading: false"
    )
    foreach ($needle in $required) {
        if (-not $text.Contains($needle)) {
            throw "Locked config value is missing from ${Path}: $needle"
        }
    }
    if ($text -match "(?i)Z-Image-Turbo|assistant_lora") {
        throw "The Base config contains a forbidden Turbo model or assistant adapter: $Path"
    }
}

function Get-ToolkitFingerprint {
    foreach ($path in @($ToolkitPython, $ToolkitRun, $LoraValidator)) { Assert-File $path }
    $head = (& git -c safe.directory=C:/projects/AI-Tools/ai-toolkit/AI-Toolkit -C $ToolkitRoot rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $head -ne $ExpectedToolkitCommit) {
        throw "AI-Toolkit commit mismatch. Expected $ExpectedToolkitCommit, found $head"
    }
    $fileHashes = [ordered]@{}
    foreach ($relative in $ToolkitFileLocks.Keys) {
        $path = Join-Path $ToolkitRoot $relative
        Assert-File $path
        $actual = Get-Sha256 $path
        if ($actual -ne $ToolkitFileLocks[$relative]) {
            throw "Pinned AI-Toolkit file changed: $relative`nExpected $($ToolkitFileLocks[$relative])`nActual   $actual"
        }
        $fileHashes[$relative] = $actual
    }
    return [ordered]@{
        commit = $head
        declared_patch_digest = $DeclaredPatchDigest
        verification = "commit plus individual SHA-256 file locks"
        files = $fileHashes
    }
}

function Assert-ModelLocks([switch]$IncludeTextEncoder) {
    if (-not (Test-Path -LiteralPath $SnapshotPath -PathType Container)) {
        throw "Pinned offline Z-Image snapshot is missing: $SnapshotPath"
    }
    $modelLocks = [ordered]@{
        zimage_snapshot = $ExpectedSnapshot
        zimage_inference = [ordered]@{
            path = Join-Path $ComfyRoot "models\diffusion_models\z_image_bf16.safetensors"
            sha256 = "996A67D3FF666946B1C25CBC16D1B1918B6CC0AC166309E23FE3B3D830263DEE"
        }
        vae = [ordered]@{
            path = Join-Path $ComfyRoot "models\vae\ae.safetensors"
            sha256 = "AFC8E28272CD15DB3919BACDB6918CE9C1ED22E96CB12C4D5ED0FBA823529E38"
        }
    }
    foreach ($item in @($modelLocks.zimage_inference, $modelLocks.vae)) {
        Assert-File $item.path
        $actual = Get-Sha256 $item.path
        if ($actual -ne $item.sha256) { throw "Model hash mismatch: $($item.path)" }
    }
    $textEncoder = Join-Path $ComfyRoot "models\text_encoders\qwen_3_4b_fp8_mixed.safetensors"
    Assert-File $textEncoder
    if ($IncludeTextEncoder) {
        $modelLocks.text_encoder = [ordered]@{ path = $textEncoder; sha256 = Get-Sha256 $textEncoder }
    } else {
        $modelLocks.text_encoder = [ordered]@{ path = $textEncoder; sha256 = "record-after-3090-worker-stop" }
    }
    return $modelLocks
}

function Assert-SourceDataset {
    $manifest = Join-Path $SourceRoot "manifest.json"
    Assert-File $manifest
    $actualManifestHash = Get-Sha256 $manifest
    if ($actualManifestHash -ne $ExpectedManifestHash) {
        throw "Source manifest mismatch. Expected $ExpectedManifestHash, found $actualManifestHash"
    }
    $images = @(Get-ChildItem -LiteralPath $SourceDataset -File | Where-Object Extension -In @(".jpg", ".jpeg", ".png", ".webp"))
    $captions = @(Get-ChildItem -LiteralPath $SourceDataset -Filter "*.txt" -File)
    if ($images.Count -ne 13 -or $captions.Count -ne 13) {
        throw "Expected 13 source images and 13 captions; found $($images.Count) and $($captions.Count)."
    }
    foreach ($image in $images) {
        $captionPath = Join-Path $SourceDataset ($image.BaseName + ".txt")
        Assert-File $captionPath
        $caption = (Get-Content -Raw -LiteralPath $captionPath).Trim()
        if (-not $caption.StartsWith("m1tch_person", [System.StringComparison]::Ordinal)) {
            throw "Caption must start with m1tch_person: $captionPath"
        }
    }
    foreach ($caption in $captions) {
        $matches = @($images | Where-Object BaseName -eq $caption.BaseName)
        if ($matches.Count -ne 1) { throw "Orphan or ambiguous caption: $($caption.FullName)" }
    }
    return [ordered]@{ manifest_path = $manifest; manifest_sha256 = $actualManifestHash; images = 13; captions = 13 }
}

function Initialize-DatasetCopy([ValidateSet("smoke", "train")][string]$Kind) {
    $phaseRoot = Join-Path $RunRoot $Kind
    $target = Join-Path $phaseRoot "dataset"
    $output = Join-Path $phaseRoot "ai-toolkit-output"
    if (Test-Path -LiteralPath $output) {
        throw "Refusing to overwrite an existing $Kind output: $output"
    }
    if (-not (Test-Path -LiteralPath $target -PathType Container)) {
        New-Item -ItemType Directory -Path $target -Force | Out-Null
        Get-ChildItem -LiteralPath $SourceDataset -File | Where-Object Extension -In @(".jpg", ".jpeg", ".png", ".webp", ".txt") | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $target $_.Name)
        }
    }
    $unexpected = @(Get-ChildItem -LiteralPath $target -Recurse -Force | Where-Object {
        $_.PSIsContainer -or $_.Extension.ToLowerInvariant() -notin @(".jpg", ".jpeg", ".png", ".webp", ".txt")
    })
    if ($unexpected.Count -gt 0) {
        throw "The fresh $Kind dataset contains a cache, directory, or unsupported file: $($unexpected[0].FullName)"
    }
    $sourceFiles = @(Get-ChildItem -LiteralPath $SourceDataset -File | Where-Object Extension -In @(".jpg", ".jpeg", ".png", ".webp", ".txt") | Sort-Object Name)
    $targetFiles = @(Get-ChildItem -LiteralPath $target -File | Sort-Object Name)
    if ($sourceFiles.Count -ne 26 -or $targetFiles.Count -ne 26) {
        throw "The $Kind copy must contain exactly 26 files."
    }
    $entries = [System.Collections.Generic.List[object]]::new()
    for ($index = 0; $index -lt $sourceFiles.Count; $index++) {
        if ($sourceFiles[$index].Name -ne $targetFiles[$index].Name) { throw "Dataset filename mismatch." }
        $sourceHash = Get-Sha256 $sourceFiles[$index].FullName
        $targetHash = Get-Sha256 $targetFiles[$index].FullName
        if ($sourceHash -ne $targetHash) { throw "Dataset copy hash mismatch: $($sourceFiles[$index].Name)" }
        $entries.Add([ordered]@{ name = $sourceFiles[$index].Name; sha256 = $sourceHash; bytes = $sourceFiles[$index].Length })
    }
    if (-not (Test-Path -LiteralPath $phaseRoot -PathType Container)) { New-Item -ItemType Directory -Path $phaseRoot -Force | Out-Null }
    $lock = [ordered]@{
        created_utc = (Get-Date).ToUniversalTime().ToString("o")
        source_manifest_sha256 = $ExpectedManifestHash
        kind = $Kind
        training_files = $entries
        validation_files_included = 0
        cache_files_included = 0
    }
    $lock | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $phaseRoot "dataset-lock.json") -Encoding utf8
    return $target
}

function Get-ComfyState([int]$Port) {
    try {
        $queue = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/queue" -TimeoutSec 10
        $stats = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/system_stats" -TimeoutSec 10
        return [ordered]@{
            port = $Port
            online = $true
            device = [string]$stats.devices[0].name
            running = @($queue.queue_running).Count
            pending = @($queue.queue_pending).Count
        }
    } catch {
        return [ordered]@{ port = $Port; online = $false; device = "offline"; running = -1; pending = -1 }
    }
}

function Assert-HardwareHeadroom {
    $rows = @(& nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits)
    if ($LASTEXITCODE -ne 0 -or $rows.Count -lt 2) { throw "nvidia-smi did not return both GPUs." }
    $fields = @($rows[0] -split "," | ForEach-Object { $_.Trim() })
    if ($fields[0] -ne "0" -or $fields[1] -notmatch "RTX 3090") {
        throw "Physical GPU 0 is not the expected RTX 3090: $($rows[0])"
    }
    # Two long-running local UI services (InfiniteYou on 8190 and Forge on 7860)
    # keep small idle WDDM/CUDA contexts on this display GPU. Preserve them and
    # require the headroom already proven by the earlier Z-Image Base run.
    if ([double]$fields[4] -lt 22000) { throw "RTX 3090 has only $($fields[4]) MiB free; 22000 MiB is required." }
    if ([double]$fields[5] -gt 5) { throw "RTX 3090 utilization is $($fields[5])%; it is not idle." }
    $os = Get-CimInstance Win32_OperatingSystem
    $freeRamGb = [math]::Round(([double]$os.FreePhysicalMemory * 1KB / 1GB), 2)
    if ($freeRamGb -lt 24) { throw "Only $freeRamGb GB host memory is free; 24 GB is required." }
    $freeDiskGb = [math]::Round((Get-PSDrive -Name C).Free / 1GB, 2)
    if ($freeDiskGb -lt 20) { throw "Only $freeDiskGb GB is free on C:; 20 GB is required." }
    $infiniteYou = Get-ComfyState 8190
    if ($infiniteYou.online -and ($infiniteYou.running -gt 0 -or $infiniteYou.pending -gt 0)) {
        throw "The auxiliary RTX 3090 worker on port 8190 has active work; it was not disturbed."
    }
    $forge = [ordered]@{ port = 7860; online = $false; active = $false }
    try {
        $progress = Invoke-RestMethod -Uri "http://127.0.0.1:7860/sdapi/v1/progress?skip_current_image=true" -TimeoutSec 5
        $forge.online = $true
        $forge.active = ([double]$progress.progress -gt 0 -or -not [string]::IsNullOrWhiteSpace([string]$progress.state.job))
        if ($forge.active) { throw "Forge on port 7860 has active GPU work; it was not disturbed." }
    } catch {
        if ($_.Exception.Message -match "active GPU work") { throw }
    }
    return [ordered]@{
        gpu_rows = $rows
        free_ram_gb = $freeRamGb
        free_disk_gb = $freeDiskGb
        minimum_free_vram_mib = 22000
        preserved_auxiliary_services = @($infiniteYou, $forge)
    }
}

function Stop-Verified3090Worker {
    $state3090 = Get-ComfyState 8188
    $state4070 = Get-ComfyState 8189
    if (-not $state3090.online -or $state3090.device -notmatch "RTX 3090") { throw "Port 8188 is not the RTX 3090 ComfyUI worker." }
    if ($state3090.running -gt 0 -or $state3090.pending -gt 0) { throw "RTX 3090 ComfyUI has active work; nothing was stopped." }
    if ($state4070.online -and $state4070.device -notmatch "RTX 4070") { throw "Port 8189 is online but is not the expected RTX 4070 worker." }
    Invoke-RestMethod -Uri "http://127.0.0.1:8188/free" -Method Post -ContentType "application/json" -Body '{"unload_models":true,"free_memory":true}' -TimeoutSec 30 | Out-Null
    Start-Sleep -Seconds 3
    $owners = @(Get-NetTCPConnection -LocalPort 8188 -State Listen | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($owners.Count -ne 1) { throw "Could not identify exactly one listener for port 8188." }
    $workerPid = [int]$owners[0]
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$workerPid"
    $commandLine = [string]$processInfo.CommandLine
    if ($commandLine -notmatch "(?i)ComfyUI.*main\.py" -or $commandLine -notmatch "8188") {
        throw "Refusing to stop unverified port-8188 process $workerPid`: $commandLine"
    }
    Stop-Process -Id $workerPid
    $deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Seconds 1
        $listener = @(Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue)
    } while ($listener.Count -gt 0 -and (Get-Date) -lt $deadline)
    if ($listener.Count -gt 0) { throw "RTX 3090 ComfyUI worker did not stop cleanly." }
    return [ordered]@{ stopped = $true; pid = $workerPid; command_line = $commandLine; state_4070 = $state4070 }
}

function Restart-3090Worker {
    $state = Get-ComfyState 8188
    if ($state.online -and $state.device -match "RTX 3090") { return }
    & (Join-Path $RepoRoot "scripts\start-dual-comfy.ps1")
    if ($LASTEXITCODE -ne 0) { throw "Failed to restart the dual ComfyUI workers." }
    $state = Get-ComfyState 8188
    if (-not $state.online -or $state.device -notmatch "RTX 3090") { throw "RTX 3090 worker did not return on port 8188." }
}

function Assert-IsolatedCuda {
    $env:CUDA_VISIBLE_DEVICES = "0"
    $probe = & $ToolkitPython -c "import json,torch; print(json.dumps({'count':torch.cuda.device_count(),'name':torch.cuda.get_device_name(0) if torch.cuda.device_count() else ''}))"
    if ($LASTEXITCODE -ne 0) { throw "CUDA probe failed." }
    $result = $probe | ConvertFrom-Json
    if ($result.count -ne 1 -or [string]$result.name -notmatch "RTX 3090") {
        throw "AI-Toolkit CUDA isolation failed: $probe"
    }
    return $result
}

function Invoke-Training([ValidateSet("smoke", "train")][string]$Kind) {
    $config = if ($Kind -eq "smoke") { $SmokeConfig } else { $ProductionConfig }
    $steps = if ($Kind -eq "smoke") { 40 } else { 2000 }
    $name = if ($Kind -eq "smoke") { "m1tch-zimage-base-identity-v1-smoke" } else { "m1tch-zimage-base-identity-v1" }
    Assert-Config $config $steps $name
    Initialize-DatasetCopy $Kind | Out-Null
    if ($Kind -eq "train") {
        $smokeRecord = Join-Path $RunRoot "smoke\smoke-validation.json"
        Assert-File $smokeRecord
        $smokeResult = Get-Content -Raw -LiteralPath $smokeRecord | ConvertFrom-Json
        if (-not $smokeResult.valid) { throw "The isolated 40-step smoke has not passed." }
    }
    $workerRecord = Stop-Verified3090Worker
    $workerStopped = $true
    try {
        $headroom = Assert-HardwareHeadroom
        $cuda = Assert-IsolatedCuda
        $models = Assert-ModelLocks -IncludeTextEncoder
        $phaseRoot = Join-Path $RunRoot $Kind
        $logRoot = Join-Path $phaseRoot "logs"
        New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $trainingLog = Join-Path $logRoot "$Kind-$stamp.log"
        $consoleLog = Join-Path $logRoot "$Kind-$stamp-console.log"
        $manifestPath = Join-Path $phaseRoot "run-manifest.json"
        if (Test-Path -LiteralPath $manifestPath) { throw "Run manifest already exists; refusing an ambiguous repeat: $manifestPath" }
        $manifest = [ordered]@{
            started_utc = (Get-Date).ToUniversalTime().ToString("o")
            kind = $Kind
            config_path = $config
            config_sha256 = Get-Sha256 $config
            source = Assert-SourceDataset
            toolkit = Get-ToolkitFingerprint
            models = $models
            hardware = $headroom
            cuda_probe = $cuda
            worker = $workerRecord
            offline = $true
        }
        $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding utf8
        $env:HF_HUB_OFFLINE = "1"
        $env:TRANSFORMERS_OFFLINE = "1"
        $env:PYTHONUNBUFFERED = "1"
        $env:CUDA_VISIBLE_DEVICES = "0"
        Push-Location $ToolkitRoot
        try {
            & $ToolkitPython $ToolkitRun $config -l $trainingLog 2>&1 | Tee-Object -FilePath $consoleLog
            $exitCode = $LASTEXITCODE
        } finally {
            Pop-Location
        }
        if ($exitCode -ne 0) { throw "AI-Toolkit exited with code $exitCode. See $trainingLog and $consoleLog" }
        $allLog = (@($trainingLog, $consoleLog) | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { Get-Content -Raw -LiteralPath $_ }) -join "`n"
        if ($allLog -match "(?i)CUDA out of memory|OOM during training|\bNaN\b|\binfinite\b") {
            throw "Training log contains an OOM or nonfinite-value marker."
        }
        if ($allLog -notmatch "create LoRA for U-Net:\s*240 modules\.") {
            throw "The log did not confirm exactly 240 targeted Z-Image LoRA modules."
        }
        if (($allLog | Select-String -Pattern "Bucket sizes for" -AllMatches).Matches.Count -lt 2 -or $allLog -notmatch "768" -or $allLog -notmatch "1024") {
            throw "The log did not prove creation of both 768 and 1024 dataset bucket sets."
        }
        $outputRoot = Join-Path (Join-Path $phaseRoot "ai-toolkit-output") $name
        $finalLora = Join-Path $outputRoot "$name.safetensors"
        Assert-File $finalLora
        $numberedCheckpointCount = $null
        $step2000Checkpoint = $null
        if ($Kind -eq "train") {
            # AI-Toolkit writes its terminal save only as the unnumbered adapter. Keep that
            # immutable final and also preserve the plan-required numbered step-2000 candidate.
            $step2000Checkpoint = Join-Path $outputRoot "${name}_000002000.safetensors"
            if (Test-Path -LiteralPath $step2000Checkpoint -PathType Leaf) {
                if ((Get-Sha256 $step2000Checkpoint) -ne (Get-Sha256 $finalLora)) {
                    throw "The existing numbered step-2000 checkpoint does not match the final adapter."
                }
            } else {
                Copy-Item -LiteralPath $finalLora -Destination $step2000Checkpoint
                if ((Get-Sha256 $step2000Checkpoint) -ne (Get-Sha256 $finalLora)) {
                    throw "The numbered step-2000 checkpoint copy failed hash verification."
                }
            }
            & $ToolkitPython $LoraValidator $step2000Checkpoint --expected-modules 240 | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "The numbered step-2000 checkpoint failed safetensors validation." }
            $expectedCheckpointNames = 1..20 | ForEach-Object { "{0}_{1:D9}.safetensors" -f $name, ($_ * 100) }
            foreach ($checkpointName in $expectedCheckpointNames) {
                Assert-File (Join-Path $outputRoot $checkpointName)
            }
            $numberedCheckpointCount = $expectedCheckpointNames.Count
        }
        $validationName = if ($Kind -eq "smoke") { "smoke-lora-validation.json" } else { "final-lora-validation.json" }
        $validationPath = Join-Path $phaseRoot $validationName
        & $ToolkitPython $LoraValidator $finalLora --expected-modules 240 --json-output $validationPath
        if ($LASTEXITCODE -ne 0) { throw "The saved Z-Image LoRA failed safetensors validation." }
        $result = Get-Content -Raw -LiteralPath $validationPath | ConvertFrom-Json
        $completion = [ordered]@{
            valid = [bool]$result.valid
            kind = $Kind
            completed_utc = (Get-Date).ToUniversalTime().ToString("o")
            steps = $steps
            final_lora = $finalLora
            final_lora_sha256 = Get-Sha256 $finalLora
            numbered_checkpoint_count = $numberedCheckpointCount
            step_2000_checkpoint = $step2000Checkpoint
            step_2000_checkpoint_sha256 = if ($step2000Checkpoint) { Get-Sha256 $step2000Checkpoint } else { $null }
            tensor_count = $result.tensor_count
            module_count = $result.module_count
            zero_ooms = $true
            buckets = @(768, 1024)
            gpu = "NVIDIA GeForce RTX 3090"
            training_log = $trainingLog
            console_log = $consoleLog
        }
        $recordName = if ($Kind -eq "smoke") { "smoke-validation.json" } else { "training-validation.json" }
        $completion | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $phaseRoot $recordName) -Encoding utf8
        Write-Host "$Kind training passed: $finalLora"
    } finally {
        if ($workerStopped) { Restart-3090Worker }
    }
}

Assert-Config $ProductionConfig 2000 "m1tch-zimage-base-identity-v1"
Assert-Config $SmokeConfig 40 "m1tch-zimage-base-identity-v1-smoke"
$sourceReport = Assert-SourceDataset
$toolkitReport = Get-ToolkitFingerprint
$modelReport = Assert-ModelLocks

switch ($Phase) {
    "Validate" {
        $smokeDataset = Initialize-DatasetCopy "smoke"
        $trainDataset = Initialize-DatasetCopy "train"
        $report = [ordered]@{
            valid = $true
            validated_utc = (Get-Date).ToUniversalTime().ToString("o")
            source = $sourceReport
            toolkit = $toolkitReport
            models = $modelReport
            smoke_dataset = $smokeDataset
            train_dataset = $trainDataset
            production_config_sha256 = Get-Sha256 $ProductionConfig
            smoke_config_sha256 = Get-Sha256 $SmokeConfig
            target_gpu = "physical GPU 0 / NVIDIA GeForce RTX 3090"
            fallback_gpu = $null
        }
        New-Item -ItemType Directory -Path $RunRoot -Force | Out-Null
        $report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $RunRoot "preflight-validation.json") -Encoding utf8
        $report | ConvertTo-Json -Depth 6
    }
    "Smoke" { Invoke-Training "smoke" }
    "Train" { Invoke-Training "train" }
    "Benchmark" {
        Assert-File $BenchmarkRunner
        & $BenchmarkRunner -Mode Screen
        if ($LASTEXITCODE -ne 0) { throw "Checkpoint benchmark failed." }
    }
    "Publish" {
        Assert-File $BenchmarkRunner
        if (-not $CandidatePath) { throw "Publish requires -CandidatePath." }
        if (-not $MitchApproved) { throw "Publish requires explicit -MitchApproved after full-size visual review." }
        & $BenchmarkRunner -Mode Publish -CandidatePath $CandidatePath -MitchApproved
        if ($LASTEXITCODE -ne 0) { throw "Guarded publication failed." }
    }
}
