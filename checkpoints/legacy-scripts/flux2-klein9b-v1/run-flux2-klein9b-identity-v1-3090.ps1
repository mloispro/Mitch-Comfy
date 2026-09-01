[CmdletBinding()]
param(
    [ValidateSet("Validate", "Smoke", "AcceptSmoke", "Train")]
    [string]$Phase = "Validate",
    [string]$SourceDatasetName = "mitch-identity-stills-v3",
    [string]$RunName = "flux2-klein9b-identity-v1",
    [string]$JobName = "m1tch-flux2-klein9b-identity-v1",
    [string]$ExpectedManifestHash = "D56FE2D752FEBFA63CA0E76689DFD9D4EAAC7443CA086FFA9DFEF51186563003",
    [ValidateRange(1, 1000)][int]$ExpectedTrainCount = 13,
    [ValidateRange(2, 1000)][int]$ExpectedValidationCount = 6,
    [ValidateRange(100, 10000)][int]$ProductionSteps = 1200,
    [ValidateRange(1, 256)][int]$Rank = 16
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ToolkitRoot = "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit"
$ToolkitPython = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$ToolkitRun = Join-Path $ToolkitRoot "run.py"
$SourceRoot = Join-Path $RepoRoot ("datasets\{0}" -f $SourceDatasetName)
$SourceDataset = Join-Path $SourceRoot "dataset"
$SourceManifest = Join-Path $SourceRoot "manifest.json"
$RunRoot = Join-Path $RepoRoot ("work\{0}" -f $RunName)
$ProductionConfig = Join-Path $RepoRoot ("config\{0}-3090.yaml" -f $RunName)
$SmokeConfig = Join-Path $RepoRoot ("config\{0}-3090-smoke.yaml" -f $RunName)
$LoraValidator = Join-Path $RepoRoot "scripts\validate-zimage-lora.py"
$ExpectedToolkitCommit = "0f788923aef28e3a87fa68cfa15a761d9d499d6c"
$ExpectedBaseSnapshot = "32773329fbe7e81a90ef971740e8ba4b0364ecf3"
$ExpectedTextEncoderSnapshot = "b968826d9c46dd6066d109eabc6255188de91218"
$ExpectedVaeSnapshot = "3f679cf232e6d91d28396522d9502c31e8f7ccbe"
$BaseSnapshotPath = "C:\Users\Mitch\.cache\huggingface\hub\models--black-forest-labs--FLUX.2-klein-base-9B\snapshots\$ExpectedBaseSnapshot"
$TextEncoderSnapshotPath = "C:\Users\Mitch\.cache\huggingface\hub\models--Qwen--Qwen3-8B\snapshots\$ExpectedTextEncoderSnapshot"
$VaeSnapshotPath = "C:\Users\Mitch\.cache\huggingface\hub\models--ai-toolkit--flux2_vae\snapshots\$ExpectedVaeSnapshot"

$ToolkitFileLocks = [ordered]@{
    "extensions_built_in\diffusion_models\flux2\src\model.py" = "1BE7E797CFCC44C7E29713CA4EAF21319BEA2591F5F3444576B5AE524583EEAB"
    "extensions_built_in\diffusion_models\flux2\flux2_model.py" = "EFA361AADEA21153E552662E6BE9C52C3764B0B52B2C73661889188B5EEF0E20"
    "extensions_built_in\diffusion_models\flux2\flux2_klein_model.py" = "D1F007D3B75C768EA6EEC41C8D5A517F977927BD15C80B9006DA7E4FD408F404"
    "toolkit\memory_management\manager_modules.py" = "64B1E76250A21EAF63AC97CF5C807C2667A92E46254C56EA5937DF80A7773D0C"
}

$ModelFileLocks = [ordered]@{
    (Join-Path $BaseSnapshotPath "flux-2-klein-base-9b.safetensors") = [ordered]@{ bytes = 18157185168; sha256 = "4A54FAD7F5F741B99EEE217198DAAC20B8D8E515E2A1F5B064FD51CF074F95BD" }
    (Join-Path $TextEncoderSnapshotPath "model-00001-of-00005.safetensors") = [ordered]@{ bytes = 3996250744; sha256 = "31D6A825AE35F11FB85B195B4C42C146C051E446433125A215336ABDF95CBF5F" }
    (Join-Path $TextEncoderSnapshotPath "model-00002-of-00005.safetensors") = [ordered]@{ bytes = 3993160032; sha256 = "5991236CEA6FE21F3D43CAB0F0E84448734FBBE0789816202989F2DDC9D18282" }
    (Join-Path $TextEncoderSnapshotPath "model-00003-of-00005.safetensors") = [ordered]@{ bytes = 3959604768; sha256 = "C5185C4794BE2D8A9784D5753C9922DB38DF478CE11F9ED0B415B7304D896836" }
    (Join-Path $TextEncoderSnapshotPath "model-00004-of-00005.safetensors") = [ordered]@{ bytes = 3187841392; sha256 = "B5EE7DE71FBF17DB3D5704E0C8F2BC7D005CA9E1D7CA2AEB19827B0CFCAA917A" }
    (Join-Path $TextEncoderSnapshotPath "model-00005-of-00005.safetensors") = [ordered]@{ bytes = 1244659840; sha256 = "20C2D6366AB85C90786CCDD829CD2B9E7D30EF3B2EBBB998280E7E4014B542FF" }
    (Join-Path $VaeSnapshotPath "ae.safetensors") = [ordered]@{ bytes = 336211292; sha256 = "868FE7B343CC8F3A19DBCFCAFBC3D5F888802BE3F89BD81B65B3621A066CE8F3" }
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Assert-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required file is missing: $Path"
    }
}

function Assert-Config([string]$Path, [int]$ExpectedSteps, [string]$ExpectedName, [bool]$SamplingExpected) {
    Assert-File $Path
    $text = Get-Content -Raw -LiteralPath $Path
    $required = @(
        "name: $ExpectedName",
        "device: cuda:0",
        "training_seed: 42",
        "trigger_word: m1tch_person",
        "linear: $Rank",
        "linear_alpha: $Rank",
        "resolution: [768, 1024]",
        "steps: $ExpectedSteps",
        "gradient_accumulation: 1",
        "optimizer: adamw8bit",
        "lr: 0.00008",
        "lr_scheduler: constant",
        "content_or_style: balanced",
        "arch: flux2_klein_9b",
        "qtype: qfloat8",
        "qtype_te: qfloat8",
        "low_vram: false",
        "layer_offloading: false"
    )
    foreach ($needle in $required) {
        if (-not $text.Contains($needle)) { throw "Locked config value is missing from ${Path}: $needle" }
    }
    $expectedSamplingLine = if ($SamplingExpected) { "disable_sampling: false" } else { "disable_sampling: true" }
    if (-not $text.Contains($expectedSamplingLine)) { throw "Unexpected sampling mode in $Path" }
    if ($text -match "(?i)flux-2-klein-9b-fp8|FLUX\.2-klein-9B(?!-base)|assistant_lora|train_text_encoder:\s*true|diff_output_preservation:\s*true") {
        throw "The config contains a distilled model, assistant adapter, text-encoder training, or DOP: $Path"
    }
    & $ToolkitPython -c "import sys,yaml; d=yaml.safe_load(open(sys.argv[1],encoding='utf-8')); assert d['config']['process'][0]['model']['arch']=='flux2_klein_9b'; print('CONFIG_PARSE=PASS')" $Path | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "AI-Toolkit YAML parsing failed: $Path" }
}

function Get-ToolkitFingerprint {
    foreach ($path in @($ToolkitPython, $ToolkitRun, $LoraValidator)) { Assert-File $path }
    $head = (& git -c safe.directory=C:/projects/AI-Tools/ai-toolkit/AI-Toolkit -C $ToolkitRoot rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $head -ne $ExpectedToolkitCommit) {
        throw "AI-Toolkit commit mismatch. Expected $ExpectedToolkitCommit, found $head"
    }
    $files = [ordered]@{}
    foreach ($relative in $ToolkitFileLocks.Keys) {
        $path = Join-Path $ToolkitRoot $relative
        Assert-File $path
        $actual = Get-Sha256 $path
        if ($actual -ne $ToolkitFileLocks[$relative]) {
            throw "Pinned AI-Toolkit file changed: $relative`nExpected $($ToolkitFileLocks[$relative])`nActual   $actual"
        }
        $files[$relative] = $actual
    }
    return [ordered]@{ commit = $head; version = "0.12.23"; files = $files }
}

function Assert-SourceDataset {
    Assert-File $SourceManifest
    $manifestHash = Get-Sha256 $SourceManifest
    if ($manifestHash -ne $ExpectedManifestHash) {
        throw "Dataset manifest mismatch. Expected $ExpectedManifestHash, found $manifestHash"
    }
    $manifest = Get-Content -Raw -LiteralPath $SourceManifest | ConvertFrom-Json
    $train = @($manifest.records | Where-Object split -eq "train")
    $validation = @($manifest.records | Where-Object split -eq "validation")
    if ($manifest.trigger_word -ne "m1tch_person" -or $train.Count -ne $ExpectedTrainCount -or $validation.Count -ne $ExpectedValidationCount) {
        throw "Expected trigger m1tch_person, $ExpectedTrainCount train photos, and $ExpectedValidationCount validation photos."
    }
    $trainHashes = [System.Collections.Generic.HashSet[string]]::new()
    $validationHashes = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($record in $manifest.records) {
        $image = [string]$record.dataset_file
        Assert-File $image
        $actual = (Get-Sha256 $image).ToLowerInvariant()
        if ($actual -ne ([string]$record.dataset_sha256).ToLowerInvariant()) { throw "Dataset image hash mismatch: $image" }
        if ($record.split -eq "train") {
            [void]$trainHashes.Add($actual)
            $captionPath = [IO.Path]::ChangeExtension($image, ".txt")
            Assert-File $captionPath
            $caption = (Get-Content -Raw -LiteralPath $captionPath).Trim()
            if ($caption -ne ([string]$record.caption).Trim()) { throw "Caption mismatch: $captionPath" }
            if (-not $caption.StartsWith("m1tch_person", [StringComparison]::Ordinal)) { throw "Trigger is not first: $captionPath" }
        } else {
            [void]$validationHashes.Add($actual)
        }
    }
    if ($trainHashes.Overlaps($validationHashes)) { throw "Training and validation hashes overlap." }
    $sourceImages = @(Get-ChildItem -LiteralPath $SourceDataset -File | Where-Object Extension -In @(".jpg", ".jpeg", ".png", ".webp"))
    $sourceCaptions = @(Get-ChildItem -LiteralPath $SourceDataset -File -Filter "*.txt")
    if ($sourceImages.Count -ne $ExpectedTrainCount -or $sourceCaptions.Count -ne $ExpectedTrainCount) { throw "Source training folder does not contain exactly $ExpectedTrainCount image/TXT pairs." }
    return [ordered]@{ manifest = $SourceManifest; sha256 = $manifestHash; train = $ExpectedTrainCount; validation = $ExpectedValidationCount; trigger = "m1tch_person" }
}

function Initialize-DatasetCopy([ValidateSet("smoke", "train")][string]$Kind) {
    $phaseRoot = Join-Path $RunRoot $Kind
    $target = Join-Path $phaseRoot "dataset"
    $output = Join-Path $phaseRoot "ai-toolkit-output"
    if (Test-Path -LiteralPath $output) { throw "Refusing to overwrite or resume existing $Kind output: $output" }
    if (-not (Test-Path -LiteralPath $target -PathType Container)) {
        New-Item -ItemType Directory -Path $target -Force | Out-Null
        Get-ChildItem -LiteralPath $SourceDataset -File | Where-Object Extension -In @(".jpg", ".jpeg", ".png", ".webp", ".txt") | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $target $_.Name)
        }
    }
    $unexpected = @(Get-ChildItem -LiteralPath $target -Recurse -Force | Where-Object {
        $_.PSIsContainer -or $_.Extension.ToLowerInvariant() -notin @(".jpg", ".jpeg", ".png", ".webp", ".txt")
    })
    if ($unexpected.Count -gt 0) { throw "Fresh $Kind dataset contains a cache, subdirectory, or unsupported file: $($unexpected[0].FullName)" }
    $files = @(Get-ChildItem -LiteralPath $target -File)
    $images = @($files | Where-Object Extension -In @(".jpg", ".jpeg", ".png", ".webp"))
    $captions = @($files | Where-Object Extension -eq ".txt")
    if ($images.Count -ne $ExpectedTrainCount -or $captions.Count -ne $ExpectedTrainCount -or $files.Count -ne (2 * $ExpectedTrainCount)) { throw "Fresh $Kind copy must contain exactly $ExpectedTrainCount image/TXT pairs and nothing else." }
    foreach ($image in $images) {
        $source = Join-Path $SourceDataset $image.Name
        $caption = Join-Path $target ($image.BaseName + ".txt")
        Assert-File $caption
        if ((Get-Sha256 $source) -ne (Get-Sha256 $image.FullName)) { throw "Dataset copy hash mismatch: $($image.Name)" }
    }
    New-Item -ItemType Directory -Path $phaseRoot -Force | Out-Null
    [ordered]@{
        created_utc = (Get-Date).ToUniversalTime().ToString("o")
        kind = $Kind
        source_manifest_sha256 = $ExpectedManifestHash
        images = $ExpectedTrainCount
        captions = $ExpectedTrainCount
        validation_files = 0
        cache_files = 0
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $phaseRoot "dataset-lock.json") -Encoding utf8
    return $target
}

function Assert-ModelLocks([switch]$FullHash) {
    $requiredTextFiles = @("config.json", "model.safetensors.index.json", "tokenizer.json", "tokenizer_config.json")
    foreach ($name in $requiredTextFiles) { Assert-File (Join-Path $TextEncoderSnapshotPath $name) }
    $files = [ordered]@{}
    foreach ($path in $ModelFileLocks.Keys) {
        Assert-File $path
        $item = Get-Item -LiteralPath $path
        $expected = $ModelFileLocks[$path]
        if ($item.Length -ne [long]$expected.bytes) { throw "Model size mismatch: $path" }
        $actualHash = if ($FullHash) { Get-Sha256 $path } else { $null }
        if ($FullHash -and $actualHash -ne $expected.sha256) { throw "Model hash mismatch: $path" }
        $files[$path] = [ordered]@{ bytes = $item.Length; sha256 = if ($actualHash) { $actualHash } else { $expected.sha256 } }
    }
    $report = [ordered]@{
        valid = $true
        verified_utc = (Get-Date).ToUniversalTime().ToString("o")
        full_local_sha256_verification = [bool]$FullHash
        base_snapshot = $ExpectedBaseSnapshot
        text_encoder_snapshot = $ExpectedTextEncoderSnapshot
        vae_snapshot = $ExpectedVaeSnapshot
        files = $files
    }
    if ($FullHash) {
        New-Item -ItemType Directory -Path $RunRoot -Force | Out-Null
        $report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $RunRoot "model-locks.json") -Encoding utf8
    } else {
        $lockPath = Join-Path $RunRoot "model-locks.json"
        Assert-File $lockPath
        $saved = Get-Content -Raw -LiteralPath $lockPath | ConvertFrom-Json
        if (-not $saved.valid -or -not $saved.full_local_sha256_verification) { throw "A full local model hash validation has not passed." }
    }
    return $report
}

function Get-ComfyState([int]$Port) {
    try {
        $queue = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/queue" -TimeoutSec 10
        $stats = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/system_stats" -TimeoutSec 10
        return [ordered]@{ port = $Port; online = $true; device = [string]$stats.devices[0].name; running = @($queue.queue_running).Count; pending = @($queue.queue_pending).Count }
    } catch {
        return [ordered]@{ port = $Port; online = $false; device = "offline"; running = -1; pending = -1 }
    }
}

function Stop-Verified3090Worker {
    $state3090 = Get-ComfyState 8188
    $state4070 = Get-ComfyState 8189
    $stateAux3090 = Get-ComfyState 8190
    if (-not $state3090.online -or $state3090.device -notmatch "RTX 3090") { throw "Port 8188 is not the expected RTX 3090 worker." }
    if ($state3090.running -gt 0 -or $state3090.pending -gt 0) { throw "RTX 3090 ComfyUI has active work; nothing was stopped." }
    if ($state4070.online -and $state4070.device -notmatch "RTX 4070") { throw "Port 8189 is not the expected RTX 4070 worker." }
    if ($state4070.online -and ($state4070.running -gt 0 -or $state4070.pending -gt 0)) { throw "RTX 4070 has queued work. It will not be interrupted; wait for both queues to be idle." }
    if ($stateAux3090.online -and ($stateAux3090.running -gt 0 -or $stateAux3090.pending -gt 0)) { throw "Auxiliary RTX 3090 worker on port 8190 has active work; nothing was stopped." }
    $forge = [ordered]@{ port = 7860; online = $false; active = $false }
    try {
        $progress = Invoke-RestMethod -Uri "http://127.0.0.1:7860/sdapi/v1/progress?skip_current_image=true" -TimeoutSec 5
        $forge.online = $true
        $forge.active = ([double]$progress.progress -gt 0 -or -not [string]::IsNullOrWhiteSpace([string]$progress.state.job))
        if ($forge.active) { throw "Forge on port 7860 has active RTX 3090 work; nothing was stopped." }
    } catch {
        if ($_.Exception.Message -match "active RTX 3090 work") { throw }
    }
    Invoke-RestMethod -Uri "http://127.0.0.1:8188/free" -Method Post -ContentType "application/json" -Body '{"unload_models":true,"free_memory":true}' -TimeoutSec 30 | Out-Null
    Start-Sleep -Seconds 3
    $owners = @(Get-NetTCPConnection -LocalPort 8188 -State Listen | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($owners.Count -ne 1) { throw "Could not identify exactly one listener for port 8188." }
    $workerPid = [int]$owners[0]
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$workerPid"
    $commandLine = [string]$processInfo.CommandLine
    if ($commandLine -notmatch "(?i)ComfyUI.*main\.py" -or $commandLine -notmatch "8188") { throw "Refusing to stop unverified process $workerPid`: $commandLine" }
    Stop-Process -Id $workerPid
    $deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Seconds 1
        $listener = @(Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue)
    } while ($listener.Count -gt 0 -and (Get-Date) -lt $deadline)
    if ($listener.Count -gt 0) { throw "RTX 3090 worker did not stop cleanly." }
    return [ordered]@{ stopped = $true; pid = $workerPid; command_line = $commandLine; preserved_4070 = $state4070; preserved_aux_3090 = $stateAux3090; preserved_forge = $forge }
}

function Restart-3090Worker {
    $state = Get-ComfyState 8188
    if ($state.online -and $state.device -match "RTX 3090") { return }
    & (Join-Path $RepoRoot "scripts\start-dual-comfy.ps1")
    if ($LASTEXITCODE -ne 0) { throw "Failed to restart the RTX 3090 ComfyUI worker." }
    $state = Get-ComfyState 8188
    if (-not $state.online -or $state.device -notmatch "RTX 3090") { throw "RTX 3090 worker did not return on port 8188." }
}

function Assert-HardwareHeadroom {
    $rows = @(& nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits)
    if ($LASTEXITCODE -ne 0 -or $rows.Count -lt 2) { throw "nvidia-smi did not return both GPUs." }
    $gpu0 = @($rows[0] -split "," | ForEach-Object Trim)
    if ($gpu0[0] -ne "0" -or $gpu0[1] -notmatch "RTX 3090") { throw "Physical GPU 0 is not the RTX 3090: $($rows[0])" }
    if ([double]$gpu0[4] -lt 22000) { throw "RTX 3090 has only $($gpu0[4]) MiB free; at least 22000 MiB is required." }
    if ([double]$gpu0[5] -gt 5) { throw "RTX 3090 is not idle: $($gpu0[5])% utilization." }
    $system = Get-CimInstance Win32_ComputerSystem
    $os = Get-CimInstance Win32_OperatingSystem
    $totalRamGb = [math]::Round([double]$system.TotalPhysicalMemory / 1GB, 2)
    $freeRamGb = [math]::Round([double]$os.FreePhysicalMemory * 1KB / 1GB, 2)
    if ($totalRamGb -lt 60) { throw "Klein Base 9B training requires approximately 64 GB installed RAM; found $totalRamGb GB." }
    if ($freeRamGb -lt 24) { throw "Only $freeRamGb GB RAM is free; at least 24 GB is required before model loading." }
    $freeDiskGb = [math]::Round((Get-PSDrive C).Free / 1GB, 2)
    if ($freeDiskGb -lt 100) { throw "Only $freeDiskGb GB is free on C:; at least 100 GB is required." }
    return [ordered]@{ gpu_rows = $rows; total_ram_gb = $totalRamGb; free_ram_gb = $freeRamGb; free_disk_gb = $freeDiskGb }
}

function Assert-IsolatedCuda {
    $env:CUDA_VISIBLE_DEVICES = "0"
    $probe = & $ToolkitPython -c "import json,torch; print(json.dumps({'count':torch.cuda.device_count(),'name':torch.cuda.get_device_name(0) if torch.cuda.device_count() else ''}))"
    if ($LASTEXITCODE -ne 0) { throw "CUDA probe failed." }
    $result = $probe | ConvertFrom-Json
    if ($result.count -ne 1 -or [string]$result.name -notmatch "RTX 3090") { throw "CUDA isolation failed: $probe" }
    return $result
}

function Assert-SmokeImage([string]$PhaseRoot) {
    $samples = @(Get-ChildItem -LiteralPath $PhaseRoot -Recurse -File | Where-Object {
        $_.Extension.ToLowerInvariant() -in @(".png", ".jpg", ".jpeg", ".webp") -and $_.FullName -match "[\\/]samples[\\/]" -and $_.FullName -notmatch "[\\/]\.thumbs[\\/]"
    } | Sort-Object LastWriteTime)
    if ($samples.Count -lt 1) { throw "The Base 9B smoke did not produce an image sample." }
    $sample = $samples[-1].FullName
    $probe = & $ToolkitPython -c "import json,sys,numpy as np; from PIL import Image; a=np.asarray(Image.open(sys.argv[1]).convert('RGB'),dtype=np.float32)/255.; print(json.dumps({'path':sys.argv[1],'mean':float(a.mean()),'std':float(a.std()),'finite':bool(np.isfinite(a).all())}))" $sample | ConvertFrom-Json
    if (-not $probe.finite -or [double]$probe.mean -le 0.01 -or [double]$probe.mean -ge 0.99 -or [double]$probe.std -le 0.02) {
        throw "Smoke sample is black, blank, or nonfinite: $($probe | ConvertTo-Json -Compress)"
    }
    return $probe
}

function Complete-ExistingSmoke {
    $phaseRoot = Join-Path $RunRoot "smoke"
    $smokeName = "${JobName}-smoke"
    $outputRoot = Join-Path $phaseRoot ("ai-toolkit-output\{0}" -f $smokeName)
    $finalLora = Join-Path $outputRoot ("{0}.safetensors" -f $smokeName)
    Assert-File $finalLora
    $logs = @(Get-ChildItem -LiteralPath (Join-Path $phaseRoot "logs") -File -Filter "smoke-*.log" | Sort-Object LastWriteTime)
    if ($logs.Count -lt 2) { throw "The completed smoke logs were not found." }
    $allLog = ($logs | ForEach-Object { Get-Content -Raw -LiteralPath $_.FullName }) -join "`n"
    if ($allLog -match "(?i)CUDA out of memory|OOM during training|RuntimeError:.*memory|Traceback|\bloss:\s*(nan|inf)|all NaN|solid-black") {
        throw "Existing smoke log contains an OOM, exception, or nonfinite-loss marker."
    }
    if ($allLog -notmatch "create LoRA for U-Net:\s*112 modules\.") { throw "Existing smoke did not target exactly 112 Klein 9B modules." }
    if (($allLog | Select-String -Pattern "Bucket sizes for" -AllMatches).Matches.Count -lt 2 -or $allLog -notmatch "(?m)^6\d\d?x8\d\d" -or $allLog -notmatch "(?m)^8\d\dx1[01]\d\d") {
        throw "Existing smoke did not prove both resolution bucket sets."
    }
    $lossMatches = [regex]::Matches($allLog, "loss:\s*([0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?)", [Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if ($lossMatches.Count -lt 40) { throw "Existing smoke has only $($lossMatches.Count) finite loss records." }
    $validationPath = Join-Path $phaseRoot "smoke-lora-validation.json"
    & $ToolkitPython $LoraValidator $finalLora --expected-modules 112 --json-output $validationPath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Existing smoke adapter failed safetensors validation." }
    $adapter = Get-Content -Raw -LiteralPath $validationPath | ConvertFrom-Json
    $sample = Assert-SmokeImage $phaseRoot
    $completion = [ordered]@{
        valid = [bool]$adapter.valid
        kind = "smoke"
        completed_utc = (Get-Date).ToUniversalTime().ToString("o")
        steps = 40
        gpu = "NVIDIA GeForce RTX 3090"
        fallback_gpu = $null
        module_count = $adapter.module_count
        tensor_count = $adapter.tensor_count
        finite_loss_records = $lossMatches.Count
        zero_ooms = $true
        buckets = @(768, 1024)
        final_lora = $finalLora
        final_lora_sha256 = Get-Sha256 $finalLora
        sample_valid = $true
        sample = $sample
        training_logs = @($logs.FullName)
        accepted_existing_run = $true
    }
    $completion | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $phaseRoot "smoke-validation.json") -Encoding utf8
    $completion | ConvertTo-Json -Depth 8
}

function Invoke-Training([ValidateSet("smoke", "train")][string]$Kind) {
    $config = if ($Kind -eq "smoke") { $SmokeConfig } else { $ProductionConfig }
    $steps = if ($Kind -eq "smoke") { 40 } else { $ProductionSteps }
    $name = if ($Kind -eq "smoke") { "${JobName}-smoke" } else { $JobName }
    Assert-Config $config $steps $name ($Kind -eq "smoke")
    if ($Kind -eq "train") {
        $smokeRecord = Join-Path $RunRoot "smoke\smoke-validation.json"
        Assert-File $smokeRecord
        $smoke = Get-Content -Raw -LiteralPath $smokeRecord | ConvertFrom-Json
        if (-not $smoke.valid -or -not $smoke.sample_valid) { throw "The isolated 40-step Klein Base 9B smoke has not passed." }
    }
    $dataset = Initialize-DatasetCopy $Kind
    $models = Assert-ModelLocks
    $worker = Stop-Verified3090Worker
    $workerStopped = $true
    try {
        $hardware = Assert-HardwareHeadroom
        $cuda = Assert-IsolatedCuda
        $phaseRoot = Join-Path $RunRoot $Kind
        $logRoot = Join-Path $phaseRoot "logs"
        New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $trainingLog = Join-Path $logRoot "$Kind-$stamp.log"
        $consoleLog = Join-Path $logRoot "$Kind-$stamp-console.log"
        $manifestPath = Join-Path $phaseRoot "run-manifest.json"
        if (Test-Path -LiteralPath $manifestPath) { throw "Run manifest already exists; refusing an ambiguous repeat: $manifestPath" }
        [ordered]@{
            started_utc = (Get-Date).ToUniversalTime().ToString("o")
            kind = $Kind
            config = $config
            config_sha256 = Get-Sha256 $config
            dataset = $dataset
            source = Assert-SourceDataset
            toolkit = Get-ToolkitFingerprint
            models = $models
            hardware = $hardware
            cuda = $cuda
            worker = $worker
            offline = $true
            fallback_gpu = $null
        } | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $manifestPath -Encoding utf8
        $env:CUDA_VISIBLE_DEVICES = "0"
        $env:HF_HUB_OFFLINE = "1"
        $env:TRANSFORMERS_OFFLINE = "1"
        $env:HF_DATASETS_OFFLINE = "1"
        $env:TOKENIZERS_PARALLELISM = "false"
        $env:PYTHONUNBUFFERED = "1"
        $env:AI_TOOLKIT_PIN_QUANTIZED_OFFLOAD = "0"
        $env:FLUX2_KLEIN_9B_TE_PATH = $TextEncoderSnapshotPath
        Push-Location $ToolkitRoot
        try {
            & $ToolkitPython $ToolkitRun $config -l $trainingLog 2>&1 | Tee-Object -FilePath $consoleLog
            $exitCode = $LASTEXITCODE
        } finally {
            Pop-Location
        }
        if ($exitCode -ne 0) { throw "AI-Toolkit exited with code $exitCode. See $trainingLog and $consoleLog" }
        $allLog = (@($trainingLog, $consoleLog) | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { Get-Content -Raw -LiteralPath $_ }) -join "`n"
        if ($allLog -match "(?i)CUDA out of memory|OOM during training|RuntimeError:.*memory|Traceback|\bloss:\s*(nan|inf)|all NaN|solid-black") {
            throw "Training log contains an OOM, exception, or nonfinite-loss marker."
        }
        if ($allLog -notmatch "create LoRA for U-Net:\s*112 modules\.") { throw "The log did not confirm exactly 112 Klein 9B LoRA modules." }
        if (($allLog | Select-String -Pattern "Bucket sizes for" -AllMatches).Matches.Count -lt 2 -or $allLog -notmatch "(?m)^6\d\d?x8\d\d" -or $allLog -notmatch "(?m)^8\d\dx1[01]\d\d") {
            throw "The log did not prove both 768-class and 1024-class aspect-ratio buckets."
        }
        $lossMatches = [regex]::Matches($allLog, "loss:\s*([0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?)", [Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if ($lossMatches.Count -lt $steps) { throw "Only $($lossMatches.Count) finite loss records were found for $steps updates." }
        $outputRoot = Join-Path (Join-Path $phaseRoot "ai-toolkit-output") $name
        $finalLora = Join-Path $outputRoot "$name.safetensors"
        Assert-File $finalLora
        $validationPath = Join-Path $phaseRoot "$Kind-lora-validation.json"
        & $ToolkitPython $LoraValidator $finalLora --expected-modules 112 --json-output $validationPath | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Saved Klein 9B LoRA failed safetensors validation." }
        $adapter = Get-Content -Raw -LiteralPath $validationPath | ConvertFrom-Json
        $sample = $null
        if ($Kind -eq "smoke") { $sample = Assert-SmokeImage $phaseRoot }
        $checkpoints = @()
        if ($Kind -eq "train") {
            $finalStepCheckpoint = Join-Path $outputRoot ("{0}_{1:D9}.safetensors" -f $name, $ProductionSteps)
            if (Test-Path -LiteralPath $finalStepCheckpoint) {
                if ((Get-Sha256 $finalStepCheckpoint) -ne (Get-Sha256 $finalLora)) { throw "Existing final-step checkpoint differs from final adapter." }
            } else {
                Copy-Item -LiteralPath $finalLora -Destination $finalStepCheckpoint
            }
            foreach ($step in 100..$ProductionSteps | Where-Object { $_ % 100 -eq 0 }) {
                $path = Join-Path $outputRoot ("{0}_{1:D9}.safetensors" -f $name, $step)
                Assert-File $path
                $checkpoints += [ordered]@{ step = $step; path = $path; sha256 = Get-Sha256 $path }
            }
        }
        $completion = [ordered]@{
            valid = [bool]$adapter.valid
            kind = $Kind
            completed_utc = (Get-Date).ToUniversalTime().ToString("o")
            steps = $steps
            gpu = "NVIDIA GeForce RTX 3090"
            fallback_gpu = $null
            module_count = $adapter.module_count
            tensor_count = $adapter.tensor_count
            finite_loss_records = $lossMatches.Count
            zero_ooms = $true
            buckets = @(768, 1024)
            final_lora = $finalLora
            final_lora_sha256 = Get-Sha256 $finalLora
            sample_valid = if ($sample) { $true } else { $null }
            sample = $sample
            checkpoints = $checkpoints
            training_log = $trainingLog
            console_log = $consoleLog
        }
        $record = if ($Kind -eq "smoke") { "smoke-validation.json" } else { "training-validation.json" }
        $completion | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $phaseRoot $record) -Encoding utf8
        Write-Host "$Kind passed on the RTX 3090: $finalLora"
    } finally {
        if ($workerStopped) { Restart-3090Worker }
    }
}

if ($ProductionSteps % 100 -ne 0) { throw 'ProductionSteps must be divisible by 100 so every retained checkpoint is unambiguous.' }
Assert-Config $ProductionConfig $ProductionSteps $JobName $false
Assert-Config $SmokeConfig 40 "${JobName}-smoke" $true
$sourceReport = Assert-SourceDataset
$toolkitReport = Get-ToolkitFingerprint

switch ($Phase) {
    "Validate" {
        $smokeDataset = Initialize-DatasetCopy "smoke"
        $trainDataset = Initialize-DatasetCopy "train"
        $modelReport = Assert-ModelLocks -FullHash
        $workers = @(Get-ComfyState 8188; Get-ComfyState 8189)
        if ($workers[0].online -and $workers[0].device -notmatch "RTX 3090") { throw "Port 8188 is not the RTX 3090." }
        if ($workers[1].online -and $workers[1].device -notmatch "RTX 4070") { throw "Port 8189 is not the RTX 4070." }
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
            workers = $workers
            target_gpu = "physical GPU 0 / NVIDIA GeForce RTX 3090"
            fallback_gpu = $null
        }
        New-Item -ItemType Directory -Path $RunRoot -Force | Out-Null
        $report | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath (Join-Path $RunRoot "preflight-validation.json") -Encoding utf8
        $report | ConvertTo-Json -Depth 6
    }
    "Smoke" { Invoke-Training "smoke" }
    "AcceptSmoke" { Complete-ExistingSmoke }
    "Train" { Invoke-Training "train" }
}
