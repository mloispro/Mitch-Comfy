[CmdletBinding()]
param(
    [ValidateSet("Validate", "Smoke", "AcceptSmoke", "Train", "Resume", "Library")]
    [string]$Phase = "Validate",
    [string]$RunName = "flux2-klein9b-identity-v2-r32",
    [string]$JobName = "m1tch-flux2-klein9b-identity-v2-r32",
    [string]$ProductionConfigName = "flux2-klein9b-identity-v2-r32-3090.yaml",
    [string]$SmokeConfigName = "flux2-klein9b-identity-v2-r32-3090-smoke.yaml",
    [string]$ResumeConfigName = "",
    [ValidateRange(0, 1199)][int]$ResumeCheckpointStep = 0,
    [string]$SourceDatasetName = "mitch-identity-stills-v3",
    [string]$ExpectedManifestHash = "D56FE2D752FEBFA63CA0E76689DFD9D4EAAC7443CA086FFA9DFEF51186563003",
    [ValidateRange(1, 1000)][int]$ExpectedTrainCount = 13,
    [ValidateRange(2, 1000)][int]$ExpectedValidationCount = 6,
    [switch]$RequireDiffOutputPreservation
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "aitk-dop-timer-evidence.ps1")
$ProgressPreference = "SilentlyContinue"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ToolkitRoot = "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit"
$ToolkitPython = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$ToolkitRun = Join-Path $ToolkitRoot "run.py"
$SourceRoot = Join-Path $RepoRoot ("datasets\{0}" -f $SourceDatasetName)
$SourceDataset = Join-Path $SourceRoot "dataset"
$SourceManifest = Join-Path $SourceRoot "manifest.json"
$RunRoot = Join-Path $RepoRoot "work\$RunName"
$ProductionConfig = Join-Path $RepoRoot "config\$ProductionConfigName"
$SmokeConfig = Join-Path $RepoRoot "config\$SmokeConfigName"
$ResumeConfig = if ($ResumeConfigName) { Join-Path $RepoRoot "config\$ResumeConfigName" } else { $null }
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
    "toolkit\config_modules.py" = "F42A637600D90A6267930D3C881754A0FB2CE3B5556D77999E24A1188636434E"
    "jobs\process\BaseSDTrainProcess.py" = "B8F25B79ABB6B50B20F2855508B263A1996EA36E0C60B9DFD971E30C07B6D4D3"
    "extensions_built_in\sd_trainer\SDTrainer.py" = "8F30CB3FB9C10FF82FC5B1EF6488FF7A40ADCD9278E9D5FB4561FBA729D69D99"
    "toolkit\dataloader_mixins.py" = "EF846E4037ECB17F997ADE621F8B3E1EE12875B36E0A8551229730E0B6B01577"
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
        "linear: 32",
        "linear_alpha: 32",
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
    if ($RequireDiffOutputPreservation) {
        foreach ($needle in @(
            "diff_output_preservation: true",
            "diff_output_preservation_multiplier: 1.0",
            "diff_output_preservation_class: man"
        )) {
            if (-not $text.Contains($needle)) { throw "Differential output preservation is not locked in ${Path}: $needle" }
        }
    } elseif ($text -match "(?m)^\s*diff_output_preservation:\s*true\s*$") {
        throw "Differential output preservation was enabled unexpectedly in $Path"
    }
    if ($text -match "(?i)flux-2-klein-9b-fp8|FLUX\.2-klein-9B(?!-base)|assistant_lora|train_text_encoder:\s*true") {
        throw "The config contains a distilled model, assistant adapter, or text-encoder training: $Path"
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
    $minimumFree3090MiB = 22900
    # WDDM can retain a small amount of process VRAM for several seconds after
    # the verified 3090 workers exit. Keep the locked 23 GB gate, but measure
    # after the driver has had a bounded opportunity to release that memory.
    $headroomDeadline = (Get-Date).AddSeconds(30)
    do {
        $rows = @(& nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits)
        if ($LASTEXITCODE -ne 0 -or $rows.Count -lt 2) { throw "nvidia-smi did not return both GPUs." }
        $gpu0 = @($rows[0] -split "," | ForEach-Object Trim)
        if ($gpu0[0] -ne "0" -or $gpu0[1] -notmatch "RTX 3090") { throw "Physical GPU 0 is not the RTX 3090: $($rows[0])" }
        if ([double]$gpu0[4] -ge $minimumFree3090MiB -and [double]$gpu0[5] -le 5) { break }
        if ((Get-Date) -lt $headroomDeadline) { Start-Sleep -Seconds 2 }
    } while ((Get-Date) -lt $headroomDeadline)
    if ([double]$gpu0[4] -lt $minimumFree3090MiB) { throw "RTX 3090 has only $($gpu0[4]) MiB free; at least $minimumFree3090MiB MiB is required." }
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
    $smokeName = "$JobName-smoke"
    $outputRoot = Join-Path $phaseRoot "ai-toolkit-output\$smokeName"
    $finalLora = Join-Path $outputRoot "$smokeName.safetensors"
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
    $dopEvidence = $null
    if ($RequireDiffOutputPreservation) {
        $dopEvidence = Get-AitkDopTimerEvidence -Paths @($logs.FullName) -Steps 40 -PerformanceLogEvery 1 -TimerMaxBuffer 10
        if (-not $dopEvidence.valid -or [int]$dopEvidence.proven_updates -ne 40) {
            throw "Existing DOP smoke does not match the exact pinned timer sequence for all 40 updates."
        }
    }
    $validationPath = Join-Path $phaseRoot "smoke-lora-validation.json"
    & $ToolkitPython $LoraValidator $finalLora --expected-modules 112 --expected-rank 32 --require-nonzero --json-output $validationPath | Out-Null
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
        diff_output_preservation = [bool]$RequireDiffOutputPreservation
        diff_output_preservation_class = if ($RequireDiffOutputPreservation) { "man" } else { $null }
        diff_output_preservation_multiplier = if ($RequireDiffOutputPreservation) { 1.0 } else { $null }
        dop_prior_prediction_records = if ($RequireDiffOutputPreservation) { [int]((@($dopEvidence.logs | ForEach-Object { [int]$_.record_count }) | Measure-Object -Sum).Sum) } else { 0 }
        dop_prior_prediction_max_updates = if ($RequireDiffOutputPreservation) { [int]((@($dopEvidence.logs | ForEach-Object { [int]$_.reported_updates }) | Measure-Object -Maximum).Maximum) } else { 0 }
        dop_prior_prediction_proven_updates = if ($RequireDiffOutputPreservation) { [int]$dopEvidence.proven_updates } else { 0 }
        dop_timer_accounting = if ($RequireDiffOutputPreservation) { $dopEvidence } else { $null }
        dop_execution_proven = if ($RequireDiffOutputPreservation) { [bool]$dopEvidence.valid -and [int]$dopEvidence.proven_updates -eq 40 } else { $null }
    }
    $completion | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $phaseRoot "smoke-validation.json") -Encoding utf8
    $completion | ConvertTo-Json -Depth 8
}

function Invoke-Training([ValidateSet("smoke", "train")][string]$Kind) {
    $config = if ($Kind -eq "smoke") { $SmokeConfig } else { $ProductionConfig }
    $steps = if ($Kind -eq "smoke") { 40 } else { 1200 }
    $name = if ($Kind -eq "smoke") { "$JobName-smoke" } else { $JobName }
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
            diff_output_preservation = [bool]$RequireDiffOutputPreservation
            diff_output_preservation_class = if ($RequireDiffOutputPreservation) { "man" } else { $null }
            diff_output_preservation_multiplier = if ($RequireDiffOutputPreservation) { 1.0 } else { $null }
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
        $dopEvidence = $null
        if ($RequireDiffOutputPreservation) {
            $performanceLogEvery = if ($Kind -eq 'smoke') { 1 } else { 10 }
            $dopEvidence = Get-AitkDopTimerEvidence `
                -Paths @($trainingLog, $consoleLog) `
                -Steps $steps `
                -PerformanceLogEvery $performanceLogEvery `
                -TimerMaxBuffer 10
            if (-not $dopEvidence.valid -or [int]$dopEvidence.proven_updates -ne $steps) {
                throw "DOP timer output does not match the exact pinned AI-Toolkit execution pattern for $steps updates."
            }
        }
        $outputRoot = Join-Path (Join-Path $phaseRoot "ai-toolkit-output") $name
        $finalLora = Join-Path $outputRoot "$name.safetensors"
        Assert-File $finalLora
        $validationPath = Join-Path $phaseRoot "$Kind-lora-validation.json"
        & $ToolkitPython $LoraValidator $finalLora --expected-modules 112 --expected-rank 32 --require-nonzero --json-output $validationPath | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Saved Klein 9B LoRA failed safetensors validation." }
        $adapter = Get-Content -Raw -LiteralPath $validationPath | ConvertFrom-Json
        $sample = $null
        if ($Kind -eq "smoke") { $sample = Assert-SmokeImage $phaseRoot }
        $checkpoints = @()
        if ($Kind -eq "train") {
            $step1200 = Join-Path $outputRoot "${name}_000001200.safetensors"
            if (Test-Path -LiteralPath $step1200) {
                if ((Get-Sha256 $step1200) -ne (Get-Sha256 $finalLora)) { throw "Existing step-1200 checkpoint differs from final adapter." }
            } else {
                Copy-Item -LiteralPath $finalLora -Destination $step1200
            }
            foreach ($step in 100..1200 | Where-Object { $_ % 100 -eq 0 }) {
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
            diff_output_preservation = [bool]$RequireDiffOutputPreservation
            diff_output_preservation_class = if ($RequireDiffOutputPreservation) { "man" } else { $null }
            diff_output_preservation_multiplier = if ($RequireDiffOutputPreservation) { 1.0 } else { $null }
            dop_prior_prediction_records = if ($RequireDiffOutputPreservation) { [int]((@($dopEvidence.logs | ForEach-Object { [int]$_.record_count }) | Measure-Object -Sum).Sum) } else { 0 }
            dop_prior_prediction_max_updates = if ($RequireDiffOutputPreservation) { [int]((@($dopEvidence.logs | ForEach-Object { [int]$_.reported_updates }) | Measure-Object -Maximum).Maximum) } else { 0 }
            dop_prior_prediction_proven_updates = if ($RequireDiffOutputPreservation) { [int]$dopEvidence.proven_updates } else { 0 }
            dop_timer_accounting = if ($RequireDiffOutputPreservation) { $dopEvidence } else { $null }
            dop_execution_proven = if ($RequireDiffOutputPreservation) { [bool]$dopEvidence.valid -and [int]$dopEvidence.proven_updates -eq $steps } else { $null }
        }
        $record = if ($Kind -eq "smoke") { "smoke-validation.json" } else { "training-validation.json" }
        $completion | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $phaseRoot $record) -Encoding utf8
        Write-Host "$Kind passed on the RTX 3090: $finalLora"
    } finally {
        if ($workerStopped) { Restart-3090Worker }
    }
}

function Invoke-TrainingResume {
    if (-not $ResumeConfig -or $ResumeCheckpointStep -lt 100 -or $ResumeCheckpointStep % 100 -ne 0) {
        throw "Resume requires an explicit resume config and a saved 100-step checkpoint."
    }
    $resumeStartStep = $ResumeCheckpointStep + 1
    Assert-Config $ProductionConfig 1200 $JobName $false
    Assert-Config $ResumeConfig 1200 $JobName $false
    & $ToolkitPython -c "import copy,sys,yaml; p=yaml.safe_load(open(sys.argv[1],encoding='utf-8')); r=yaml.safe_load(open(sys.argv[2],encoding='utf-8')); expected=int(sys.argv[3]); actual=r['config']['process'][0]['train'].pop('start_step',None); assert actual==expected,(actual,expected); assert p==r,'resume config differs from production beyond start_step'; print('RESUME_CONFIG=PASS')" $ProductionConfig $ResumeConfig $resumeStartStep | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Resume config is not an exact production-config copy with start_step $resumeStartStep." }

    $phaseRoot = Join-Path $RunRoot "train"
    $dataset = Join-Path $phaseRoot "dataset"
    $outputRoot = Join-Path $phaseRoot "ai-toolkit-output\$JobName"
    $manifestPath = Join-Path $phaseRoot "run-manifest.json"
    $trainingRecordPath = Join-Path $phaseRoot "training-validation.json"
    $optimizerPath = Join-Path $outputRoot "optimizer.pt"
    foreach ($path in @($manifestPath, $optimizerPath)) { Assert-File $path }
    if (Test-Path -LiteralPath $trainingRecordPath -PathType Leaf) { throw "Training already has a completion record; resume is forbidden." }
    $existingResumeManifests = @(Get-ChildItem -LiteralPath $phaseRoot -File -Filter "resume-manifest-*.json" -ErrorAction SilentlyContinue)
    if ($existingResumeManifests.Count -gt 0) { throw "A prior resume attempt is already recorded; refusing an ambiguous second resume." }

    $originalManifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    if ([string]$originalManifest.config_sha256 -cne (Get-Sha256 $ProductionConfig) -or
        [string]$originalManifest.source.sha256 -cne $ExpectedManifestHash -or
        [string]$originalManifest.cuda.name -notmatch "RTX 3090" -or
        [int]$originalManifest.cuda.count -ne 1 -or
        -not [bool]$originalManifest.offline -or
        $null -ne $originalManifest.fallback_gpu -or
        [bool]$originalManifest.diff_output_preservation -ne [bool]$RequireDiffOutputPreservation) {
        throw "The interrupted run manifest does not match the locked production run."
    }

    $datasetFiles = @(Get-ChildItem -LiteralPath $dataset -File)
    $datasetImages = @($datasetFiles | Where-Object Extension -In @(".jpg", ".jpeg", ".png", ".webp"))
    $datasetCaptions = @($datasetFiles | Where-Object Extension -eq ".txt")
    if ($datasetImages.Count -ne $ExpectedTrainCount -or $datasetCaptions.Count -ne $ExpectedTrainCount) {
        throw "Resume dataset does not contain the locked $ExpectedTrainCount image/TXT pairs."
    }
    foreach ($image in $datasetImages) {
        $sourceImage = Join-Path $SourceDataset $image.Name
        $caption = Join-Path $dataset ($image.BaseName + ".txt")
        Assert-File $sourceImage
        Assert-File $caption
        if ((Get-Sha256 $image.FullName) -cne (Get-Sha256 $sourceImage)) { throw "Resume dataset image changed: $($image.Name)" }
        if ((Get-Content -Raw -LiteralPath $caption).Trim() -cne (Get-Content -Raw -LiteralPath ([IO.Path]::ChangeExtension($sourceImage, ".txt"))).Trim()) { throw "Resume caption changed: $($image.Name)" }
    }

    $numbered = @(Get-ChildItem -LiteralPath $outputRoot -File -Filter "${JobName}_*.safetensors" | ForEach-Object {
        if ($_.Name -notmatch "_(\d{9})\.safetensors$") { throw "Unexpected numbered adapter filename: $($_.Name)" }
        [ordered]@{ step = [int]$Matches[1]; path = $_.FullName; item = $_ }
    } | Sort-Object step)
    $expectedExistingSteps = @(100..$ResumeCheckpointStep | Where-Object { $_ % 100 -eq 0 })
    if ((@($numbered.step) -join ',') -cne ($expectedExistingSteps -join ',')) {
        throw "Numbered checkpoints do not exactly cover 100 through $ResumeCheckpointStep."
    }
    $checkpointPath = Join-Path $outputRoot ("{0}_{1:D9}.safetensors" -f $JobName, $ResumeCheckpointStep)
    Assert-File $checkpointPath
    $finalPath = Join-Path $outputRoot "$JobName.safetensors"
    if (Test-Path -LiteralPath $finalPath -PathType Leaf) { throw "An unnumbered final adapter already exists; resume is ambiguous." }
    if ((Get-Item -LiteralPath $optimizerPath).LastWriteTimeUtc -lt (Get-Item -LiteralPath $checkpointPath).LastWriteTimeUtc) {
        throw "Optimizer state predates the selected checkpoint."
    }
    $resumeValidationPath = Join-Path $phaseRoot ("resume-checkpoint-{0:D4}-validation.json" -f $ResumeCheckpointStep)
    & $ToolkitPython $LoraValidator $checkpointPath --expected-modules 112 --expected-rank 32 --require-nonzero --json-output $resumeValidationPath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Resume checkpoint failed tensor validation." }
    $resumeAdapter = Get-Content -Raw -LiteralPath $resumeValidationPath | ConvertFrom-Json
    $trainingInfo = [string]$resumeAdapter.metadata.training_info | ConvertFrom-Json
    if (-not [bool]$resumeAdapter.valid -or [int]$trainingInfo.step -ne $ResumeCheckpointStep -or
        [string]$resumeAdapter.metadata.name -cne $JobName -or
        [string]$resumeAdapter.metadata.architecture -cne "flux2_klein_9b" -or
        [string]$resumeAdapter.metadata.base_model -cne "black-forest-labs/FLUX.2-klein-base-9B" -or
        [string]$resumeAdapter.metadata.dataset -cne $SourceDatasetName -or
        [string]$resumeAdapter.metadata.source_manifest_sha256 -cne $ExpectedManifestHash -or
        [string]$resumeAdapter.metadata.ai_toolkit_commit -cne $ExpectedToolkitCommit -or
        [string]$resumeAdapter.metadata.target_gpu -notmatch "RTX 3090") {
        throw "Resume checkpoint metadata does not match the locked run."
    }

    $logRoot = Join-Path $phaseRoot "logs"
    $originalLogs = @(Get-ChildItem -LiteralPath $logRoot -File | Where-Object { $_.Name -match '^train-\d{8}-\d{6}(-console)?\.log$' } | Sort-Object Name)
    if ($originalLogs.Count -ne 2) { throw "Expected exactly the original training log and console log before resume." }
    $originalText = ($originalLogs | ForEach-Object { Get-Content -Raw -LiteralPath $_.FullName }) -join "`n"
    if ($originalText -match "(?i)CUDA out of memory|OOM during training|RuntimeError:.*memory|Traceback|\bloss:\s*(nan|inf)|all NaN|solid-black") {
        throw "Interrupted-run logs contain an OOM, exception, or nonfinite-loss marker."
    }
    $segmentRoot = Join-Path $phaseRoot "resume-initial-segment"
    New-Item -ItemType Directory -Path $segmentRoot -Force | Out-Null
    $initialSegmentPaths = @()
    foreach ($log in $originalLogs) {
        $text = Get-Content -Raw -LiteralPath $log.FullName
        $needle = "$ResumeCheckpointStep/1200"
        $index = $text.IndexOf($needle, [StringComparison]::Ordinal)
        if ($index -lt 0) { throw "Original log does not reach selected checkpoint $ResumeCheckpointStep`: $($log.FullName)" }
        $lineStart = $text.LastIndexOf("`n", $index)
        if ($lineStart -lt 0) { $lineStart = 0 }
        $segmentPath = Join-Path $segmentRoot $log.Name
        Set-Content -LiteralPath $segmentPath -Value $text.Substring(0, $lineStart) -Encoding utf8NoBOM
        $initialSegmentPaths += $segmentPath
    }
    $initialDop = if ($RequireDiffOutputPreservation) {
        Get-AitkDopTimerEvidence -Paths $initialSegmentPaths -Steps $resumeStartStep -PerformanceLogEvery 10 -TimerMaxBuffer 10 -StartStep 0
    } else { $null }
    if ($RequireDiffOutputPreservation -and (-not [bool]$initialDop.valid -or [int]$initialDop.proven_updates -ne $resumeStartStep)) {
        throw "Original logs do not prove DOP execution through the selected checkpoint."
    }

    $auxiliaryStopped = $false
    $forgeStopped = $false
    $forgeRecord = [ordered]@{ port = 7860; online = $false; stopped = $false }
    try {
        $models = Assert-ModelLocks
        $state3090 = Get-ComfyState 8188
        if ($state3090.online) {
            $worker = Stop-Verified3090Worker
        } else {
            $listeners = @(Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue)
            if ($listeners.Count -gt 0) { throw "Port 8188 is listening but its RTX 3090 worker state is unverifiable." }
            $state4070 = Get-ComfyState 8189
            if ($state4070.online -and $state4070.device -notmatch "RTX 4070") { throw "Port 8189 is not the RTX 4070 worker." }
            $worker = [ordered]@{ stopped = $false; already_offline = $true; preserved_4070 = $state4070 }
        }

        $stateAux3090 = Get-ComfyState 8190
        if ($stateAux3090.online -and ($stateAux3090.device -notmatch "RTX 3090" -or $stateAux3090.running -gt 0 -or $stateAux3090.pending -gt 0)) { throw "Auxiliary RTX 3090 state is unsafe for resume." }
        $auxiliaryRecord = $stateAux3090
        if ($stateAux3090.online) {
            Invoke-RestMethod -Uri "http://127.0.0.1:8190/free" -Method Post -ContentType "application/json" -Body '{"unload_models":true,"free_memory":true}' -TimeoutSec 30 | Out-Null
            Start-Sleep -Seconds 3
            $auxOwners = @(Get-NetTCPConnection -LocalPort 8190 -State Listen | Select-Object -ExpandProperty OwningProcess -Unique)
            if ($auxOwners.Count -ne 1) { throw "Could not identify exactly one idle auxiliary RTX 3090 listener on port 8190." }
            $auxPid = [int]$auxOwners[0]
            $auxProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$auxPid"
            $auxCommandLine = [string]$auxProcess.CommandLine
            if ($auxCommandLine -notmatch "(?i)ComfyUI.*main\.py" -or $auxCommandLine -notmatch "--port\s+8190" -or $auxCommandLine -notmatch "infiniteyou-comfy") {
                throw "Refusing to stop unverified port-8190 process $auxPid`: $auxCommandLine"
            }
            Stop-Process -Id $auxPid
            $auxDeadline = (Get-Date).AddSeconds(30)
            do {
                Start-Sleep -Seconds 1
                $auxListener = @(Get-NetTCPConnection -LocalPort 8190 -State Listen -ErrorAction SilentlyContinue)
            } while ($auxListener.Count -gt 0 -and (Get-Date) -lt $auxDeadline)
            if ($auxListener.Count -gt 0) { throw "Auxiliary RTX 3090 worker did not stop cleanly." }
            $auxiliaryStopped = $true
            $auxiliaryRecord = [ordered]@{ port = 8190; stopped = $true; pid = $auxPid; command_line = $auxCommandLine; queue_running = 0; queue_pending = 0; restore_script = (Join-Path $RepoRoot "scripts\start-infiniteyou-comfy.ps1") }
        }

        try {
            $forgeProgress = Invoke-RestMethod -Uri "http://127.0.0.1:7860/sdapi/v1/progress?skip_current_image=true" -TimeoutSec 5
            $forgeActive = ([double]$forgeProgress.progress -gt 0 -or -not [string]::IsNullOrWhiteSpace([string]$forgeProgress.state.job))
            if ($forgeActive) { throw "Forge has active RTX 3090 work; resume will not disturb it." }
            $forgeOwners = @(Get-NetTCPConnection -LocalPort 7860 -State Listen | Select-Object -ExpandProperty OwningProcess -Unique)
            if ($forgeOwners.Count -ne 1) { throw "Could not identify exactly one idle Forge listener on port 7860." }
            $forgePid = [int]$forgeOwners[0]
            $forgeProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$forgePid"
            $forgeParent = Get-CimInstance Win32_Process -Filter "ProcessId=$($forgeProcess.ParentProcessId)"
            $forgeCommandLine = [string]$forgeProcess.CommandLine
            $forgeParentCommandLine = [string]$forgeParent.CommandLine
            $forgeRoot = "C:\projects\AI-Tools\sd-webui-forge-classic-neo"
            $forgePython = Join-Path $forgeRoot "venv\Scripts\python.exe"
            if ($forgeCommandLine -notmatch "(?i)launch\.py" -or $forgeCommandLine -notmatch "--port\s+7860" -or
                $forgeParentCommandLine -notmatch "(?i)launch\.py" -or $forgeParentCommandLine -notmatch "--port\s+7860" -or
                [IO.Path]::GetFullPath([string]$forgeParent.ExecutablePath) -cne [IO.Path]::GetFullPath($forgePython)) {
                throw "Refusing to stop unverified Forge process tree: $forgeParentCommandLine | $forgeCommandLine"
            }
            Stop-Process -Id $forgePid
            if (Get-Process -Id ([int]$forgeParent.ProcessId) -ErrorAction SilentlyContinue) { Stop-Process -Id ([int]$forgeParent.ProcessId) }
            $forgeDeadline = (Get-Date).AddSeconds(30)
            do {
                Start-Sleep -Seconds 1
                $forgeListener = @(Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue)
            } while ($forgeListener.Count -gt 0 -and (Get-Date) -lt $forgeDeadline)
            if ($forgeListener.Count -gt 0) { throw "Forge did not stop cleanly." }
            $forgeStopped = $true
            $forgeRecord = [ordered]@{ port = 7860; online = $true; stopped = $true; pid = $forgePid; parent_pid = [int]$forgeParent.ProcessId; command_line = $forgeCommandLine; parent_command_line = $forgeParentCommandLine; working_directory = $forgeRoot; executable = $forgePython }
        } catch {
            if ($_.Exception.Message -match "active RTX 3090 work|Refusing to stop|Could not identify|did not stop cleanly") { throw }
            $forgeListeners = @(Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue)
            if ($forgeListeners.Count -gt 0) { throw "Forge port 7860 is listening but its idle state could not be verified: $($_.Exception.Message)" }
        }
        $worker['resume_auxiliary_3090'] = $auxiliaryRecord
        $worker['resume_forge'] = $forgeRecord
        $workerStopped = $true
        try {
        $hardware = Assert-HardwareHeadroom
        $cuda = Assert-IsolatedCuda
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $trainingLog = Join-Path $logRoot "train-resume-$stamp.log"
        $consoleLog = Join-Path $logRoot "train-resume-$stamp-console.log"
        $resumeManifestPath = Join-Path $phaseRoot "resume-manifest-$stamp.json"
        [ordered]@{
            started_utc = (Get-Date).ToUniversalTime().ToString("o")
            kind = "train-resume"
            reason = "The original foreground process ended abruptly without an AI-Toolkit exception after progress step 387. Resume uses the last complete numbered adapter and matching optimizer state."
            original_run_manifest = $manifestPath
            original_run_manifest_sha256 = Get-Sha256 $manifestPath
            production_config = $ProductionConfig
            production_config_sha256 = Get-Sha256 $ProductionConfig
            resume_config = $ResumeConfig
            resume_config_sha256 = Get-Sha256 $ResumeConfig
            checkpoint_step = $ResumeCheckpointStep
            start_step = $resumeStartStep
            checkpoint = $checkpointPath
            checkpoint_sha256 = Get-Sha256 $checkpointPath
            checkpoint_validation = $resumeValidationPath
            optimizer = $optimizerPath
            optimizer_sha256 = Get-Sha256 $optimizerPath
            source = Assert-SourceDataset
            toolkit = Get-ToolkitFingerprint
            models = $models
            hardware = $hardware
            cuda = $cuda
            worker = $worker
            original_logs = @($originalLogs.FullName)
            original_log_sha256 = @($originalLogs | ForEach-Object { [ordered]@{ path = $_.FullName; sha256 = Get-Sha256 $_.FullName } })
            initial_dop_evidence = $initialDop
            offline = $true
            fallback_gpu = $null
            diff_output_preservation = [bool]$RequireDiffOutputPreservation
        } | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $resumeManifestPath -Encoding utf8

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
            & $ToolkitPython $ToolkitRun $ResumeConfig -l $trainingLog 2>&1 | Tee-Object -FilePath $consoleLog
            $exitCode = $LASTEXITCODE
        } finally {
            Pop-Location
        }
        if ($exitCode -ne 0) { throw "AI-Toolkit resume exited with code $exitCode. See $trainingLog and $consoleLog" }

        $resumeText = (@($trainingLog, $consoleLog) | ForEach-Object { Get-Content -Raw -LiteralPath $_ }) -join "`n"
        if ($resumeText -match "(?i)CUDA out of memory|OOM during training|RuntimeError:.*memory|Traceback|\bloss:\s*(nan|inf)|all NaN|solid-black") {
            throw "Resume logs contain an OOM, exception, or nonfinite-loss marker."
        }
        if ($resumeText -notmatch [regex]::Escape("#### IMPORTANT RESUMING FROM $checkpointPath ####") -or
            $resumeText -notmatch [regex]::Escape("Loading optimizer state from $optimizerPath")) {
            throw "AI-Toolkit did not prove loading both the selected checkpoint and optimizer state."
        }
        $resumeDop = if ($RequireDiffOutputPreservation) {
            Get-AitkDopTimerEvidence -Paths @($trainingLog, $consoleLog) -Steps 1200 -PerformanceLogEvery 10 -TimerMaxBuffer 10 -StartStep $resumeStartStep
        } else { $null }
        if ($RequireDiffOutputPreservation -and (-not [bool]$resumeDop.valid -or [int]$resumeDop.proven_updates -ne (1200 - $resumeStartStep))) {
            throw "Resume logs do not prove DOP execution for every resumed update."
        }

        $lossSteps = [System.Collections.Generic.HashSet[int]]::new()
        foreach ($log in @($originalLogs.FullName + @($trainingLog, $consoleLog))) {
            $text = Get-Content -Raw -LiteralPath $log
            foreach ($match in [regex]::Matches($text, "([0-9]{1,4})/1200[^\r\n]*?loss:\s*([0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?)", [Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
                $step = [int]$match.Groups[1].Value
                $loss = [double]::Parse($match.Groups[2].Value, [Globalization.CultureInfo]::InvariantCulture)
                if ([double]::IsFinite($loss) -and (($step -le $ResumeCheckpointStep) -or ($log -in @($trainingLog, $consoleLog) -and $step -ge $resumeStartStep))) { [void]$lossSteps.Add($step) }
            }
        }
        if ($lossSteps.Count -ne 1200 -or -not $lossSteps.Contains(0) -or -not $lossSteps.Contains(1199)) {
            throw "Combined original/resume logs do not prove 1,200 distinct finite-loss indices."
        }

        $finalLora = Join-Path $outputRoot "$JobName.safetensors"
        Assert-File $finalLora
        $validationPath = Join-Path $phaseRoot "train-lora-validation.json"
        & $ToolkitPython $LoraValidator $finalLora --expected-modules 112 --expected-rank 32 --require-nonzero --json-output $validationPath | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Final resumed LoRA failed safetensors validation." }
        $adapter = Get-Content -Raw -LiteralPath $validationPath | ConvertFrom-Json
        $step1200 = Join-Path $outputRoot ("{0}_{1:D9}.safetensors" -f $JobName, 1200)
        if (Test-Path -LiteralPath $step1200) {
            if ((Get-Sha256 $step1200) -cne (Get-Sha256 $finalLora)) { throw "Step-1200 checkpoint differs from final adapter." }
        } else { Copy-Item -LiteralPath $finalLora -Destination $step1200 }
        $checkpoints = foreach ($step in 100..1200 | Where-Object { $_ % 100 -eq 0 }) {
            $path = Join-Path $outputRoot ("{0}_{1:D9}.safetensors" -f $JobName, $step)
            Assert-File $path
            [ordered]@{ step = $step; path = $path; sha256 = Get-Sha256 $path }
        }
        $dopCombined = if ($RequireDiffOutputPreservation) {
            [ordered]@{ valid = [bool]$initialDop.valid -and [bool]$resumeDop.valid; initial = $initialDop; resume = $resumeDop; proven_updates = [int]$initialDop.proven_updates + [int]$resumeDop.proven_updates; exact_nonoverlapping_ranges = @("0-$ResumeCheckpointStep", "$resumeStartStep-1199") }
        } else { $null }
        $completion = [ordered]@{
            valid = [bool]$adapter.valid
            kind = "train"
            completed_utc = (Get-Date).ToUniversalTime().ToString("o")
            steps = 1200
            gpu = "NVIDIA GeForce RTX 3090"
            fallback_gpu = $null
            module_count = $adapter.module_count
            tensor_count = $adapter.tensor_count
            finite_loss_records = $lossSteps.Count
            finite_loss_index_range = @(0, 1199)
            zero_ooms = $true
            buckets = @(768, 1024)
            final_lora = $finalLora
            final_lora_sha256 = Get-Sha256 $finalLora
            checkpoints = @($checkpoints)
            training_log = $trainingLog
            console_log = $consoleLog
            training_logs = @($originalLogs.FullName + @($trainingLog, $consoleLog))
            resumed = $true
            resume_manifest = $resumeManifestPath
            resume_checkpoint_step = $ResumeCheckpointStep
            resume_start_step = $resumeStartStep
            diff_output_preservation = [bool]$RequireDiffOutputPreservation
            diff_output_preservation_class = if ($RequireDiffOutputPreservation) { "man" } else { $null }
            diff_output_preservation_multiplier = if ($RequireDiffOutputPreservation) { 1.0 } else { $null }
            dop_prior_prediction_records = if ($RequireDiffOutputPreservation) { [int]$dopCombined.proven_updates } else { 0 }
            dop_prior_prediction_max_updates = if ($RequireDiffOutputPreservation) { 1200 } else { 0 }
            dop_prior_prediction_proven_updates = if ($RequireDiffOutputPreservation) { [int]$dopCombined.proven_updates } else { 0 }
            dop_timer_accounting = $dopCombined
            dop_execution_proven = if ($RequireDiffOutputPreservation) { [bool]$dopCombined.valid -and [int]$dopCombined.proven_updates -eq 1200 } else { $null }
        }
        $completion | ConvertTo-Json -Depth 18 | Set-Content -LiteralPath $trainingRecordPath -Encoding utf8
        Write-Host "Resumed train passed on the RTX 3090: $finalLora"
        } finally {
            if ($workerStopped) { Restart-3090Worker }
        }
    } finally {
        if ($forgeStopped) {
            $forgeStamp = Get-Date -Format "yyyyMMdd-HHmmss"
            $forgeStdout = Join-Path $phaseRoot "restored-forge-$forgeStamp.stdout.log"
            $forgeStderr = Join-Path $phaseRoot "restored-forge-$forgeStamp.stderr.log"
            $forgeArgs = @("launch.py", "--uv", "--cuda-malloc", "--cuda-stream", "--pin-shared-memory", "--fast-fp8", "--disable-sage", "--api", "--port", "7860", "--forge-ref-comfy-home", "C:\projects\AI-Tools\ComfyUI")
            $forgeRestored = Start-Process -FilePath ([string]$forgeRecord.executable) -ArgumentList $forgeArgs -WorkingDirectory ([string]$forgeRecord.working_directory) -RedirectStandardOutput $forgeStdout -RedirectStandardError $forgeStderr -WindowStyle Hidden -PassThru
            $forgeRestoreDeadline = (Get-Date).AddSeconds(120)
            $forgeReady = $false
            do {
                Start-Sleep -Seconds 2
                $forgeRestored.Refresh()
                if ($forgeRestored.HasExited) { break }
                try {
                    $restoredProgress = Invoke-RestMethod -Uri "http://127.0.0.1:7860/sdapi/v1/progress?skip_current_image=true" -TimeoutSec 3
                    $forgeReady = $null -ne $restoredProgress.state
                } catch { $forgeReady = $false }
            } while (-not $forgeReady -and (Get-Date) -lt $forgeRestoreDeadline)
            if (-not $forgeReady) { throw "Failed to restore the idle Forge service on port 7860. Logs: $forgeStdout | $forgeStderr" }
        }
        if ($auxiliaryStopped) {
            & (Join-Path $RepoRoot "scripts\start-infiniteyou-comfy.ps1")
            if ($LASTEXITCODE -ne 0) { throw "Failed to restore the auxiliary RTX 3090 InfiniteYou worker." }
        }
    }
}

Assert-Config $ProductionConfig 1200 $JobName $false
Assert-Config $SmokeConfig 40 "$JobName-smoke" $true
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
    "Resume" { Invoke-TrainingResume }
    # Internal reuse point for narrowly scoped continuation runners. Dot-sourcing
    # this phase performs the same locked config/dataset/toolkit validation above
    # while exposing the already-audited GPU and service safety helpers.
    "Library" { }
}
