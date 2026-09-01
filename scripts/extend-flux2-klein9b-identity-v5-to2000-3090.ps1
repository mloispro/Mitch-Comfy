[CmdletBinding()]
param(
    [ValidateSet("Validate", "Train")]
    [string]$Phase = "Validate",
    [string]$RunName = "flux2-klein9b-identity-v5-r32-dop-body",
    [string]$JobName = "m1tch-flux2-klein9b-identity-v5-r32-dop-body",
    [string]$ProductionConfigName = "flux2-klein9b-identity-v5-r32-dop-body-3090.yaml",
    [string]$SmokeConfigName = "flux2-klein9b-identity-v5-r32-dop-body-3090-smoke.yaml",
    [string]$SourceDatasetName = "mitch-identity-stills-v4-klein9b",
    [string]$ExpectedManifestHash = "460AECB7D7A13AFAB6C186368A3711A86E415AF72D04D738A6F20BA1D7CEB9D1",
    [int]$ExpectedTrainCount = 15,
    [int]$ExpectedValidationCount = 4,
    [string]$ExtensionConfigName = "flux2-klein9b-identity-v5-r32-dop-body-3090-continue-to2000.yaml",
    [string]$ExpectedMetadataDataset = "mitch-identity-stills-v4-klein9b",
    [string]$RunLabel = "V5"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$RequestedPhase = $Phase
$SharedRunner = Join-Path $PSScriptRoot "run-flux2-klein9b-identity-v2-r32-3090.ps1"

# Load the pinned dataset, toolkit, model, GPU, and service safety checks from the
# runner that produced the validated step-1200 adapter.
. $SharedRunner `
    -Phase Library `
    -RunName $RunName `
    -JobName $JobName `
    -ProductionConfigName $ProductionConfigName `
    -SmokeConfigName $SmokeConfigName `
    -SourceDatasetName $SourceDatasetName `
    -ExpectedManifestHash $ExpectedManifestHash `
    -ExpectedTrainCount $ExpectedTrainCount `
    -ExpectedValidationCount $ExpectedValidationCount `
    -RequireDiffOutputPreservation

$ExtensionConfig = Join-Path $RepoRoot "config\$ExtensionConfigName"
$TrainRoot = Join-Path $RunRoot "train"
$OutputRoot = Join-Path $TrainRoot "ai-toolkit-output\$JobName"
$ExistingCompletionPath = Join-Path $TrainRoot "training-validation.json"
$ExtensionPreflightPath = Join-Path $TrainRoot "extension-to2000-preflight.json"
$ExtensionCompletionPath = Join-Path $TrainRoot "training-extension-to2000-validation.json"
$ExtensionArchiveRoot = Join-Path $TrainRoot "extension-source-step1200"
$Step1200 = Join-Path $OutputRoot ("{0}_{1:D9}.safetensors" -f $JobName, 1200)
$FinalLora = Join-Path $OutputRoot "$JobName.safetensors"
$OptimizerPath = Join-Path $OutputRoot "optimizer.pt"
$OutputConfig = Join-Path $OutputRoot "config.yaml"

function Assert-ContinuationConfig {
    Assert-Config $ExtensionConfig 2000 $JobName $false
    $compare = @'
import copy,sys,yaml
p=yaml.safe_load(open(sys.argv[1],encoding="utf-8"))
c=yaml.safe_load(open(sys.argv[2],encoding="utf-8"))
pp=p["config"]["process"][0]
cc=c["config"]["process"][0]
assert pp["train"]["steps"]==1200
assert cc["train"]["steps"]==2000
assert "start_step" not in cc["train"]
assert pp["save"]["max_step_saves_to_keep"]==12
assert cc["save"]["max_step_saves_to_keep"]==20
cc["train"]["steps"]=1200
cc["save"]["max_step_saves_to_keep"]=12
c["meta"]["version"]=p["meta"]["version"]
c["meta"]["controlled_change"]=p["meta"]["controlled_change"]
c["meta"]["acceptance"]=p["meta"]["acceptance"]
assert p==c, "continuation changes more than steps, retention, and provenance text"
print("CONTINUATION_CONFIG=PASS")
'@
    & $ToolkitPython -c $compare $ProductionConfig $ExtensionConfig | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Continuation config is not an exact controlled extension of $RunLabel." }
}

function Assert-ExistingStep1200 {
    foreach ($path in @($ExistingCompletionPath, $Step1200, $FinalLora, $OptimizerPath, $OutputConfig)) { Assert-File $path }
    $completion = Get-Content -Raw -LiteralPath $ExistingCompletionPath | ConvertFrom-Json
    if (-not [bool]$completion.valid -or [int]$completion.steps -ne 1200 -or -not [bool]$completion.zero_ooms -or
        [string]$completion.gpu -notmatch "RTX 3090" -or $null -ne $completion.fallback_gpu -or
        -not [bool]$completion.diff_output_preservation -or -not [bool]$completion.dop_execution_proven -or
        [int]$completion.dop_prior_prediction_proven_updates -ne 1200) {
        throw "The existing completion record does not prove a valid 1,200-update RTX 3090 DOP run."
    }
    $expectedSteps = @(100..1200 | Where-Object { $_ % 100 -eq 0 })
    $actual = @(Get-ChildItem -LiteralPath $OutputRoot -File -Filter "${JobName}_*.safetensors" | ForEach-Object {
        if ($_.BaseName -match '_(\d{9})$') { [int]$Matches[1] }
    } | Sort-Object)
    if ((Compare-Object $expectedSteps $actual).Count -ne 0) { throw "Existing numbered saves do not exactly cover steps 100 through 1200." }
    $stepHash = Get-Sha256 $Step1200
    if ($stepHash -cne (Get-Sha256 $FinalLora) -or $stepHash -cne [string]$completion.final_lora_sha256) {
        throw "The numbered and final step-1,200 adapters are not identical."
    }
    $validationPath = Join-Path $TrainRoot "extension-step1200-validation.json"
    & $ToolkitPython $LoraValidator $Step1200 --expected-modules 112 --expected-rank 32 --require-nonzero --json-output $validationPath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Step 1,200 failed tensor validation." }
    $adapter = Get-Content -Raw -LiteralPath $validationPath | ConvertFrom-Json
    $trainingInfo = [string]$adapter.metadata.training_info | ConvertFrom-Json
    if (-not [bool]$adapter.valid -or [int]$trainingInfo.step -ne 1200 -or
        [string]$adapter.metadata.name -cne $JobName -or
        [string]$adapter.metadata.dataset -cne $ExpectedMetadataDataset -or
        [string]$adapter.metadata.source_manifest_sha256 -cne $ExpectedManifestHash -or
        [string]$adapter.metadata.target_gpu -notmatch "RTX 3090") {
        throw "Step 1,200 metadata does not match the locked $RunLabel run."
    }
    return [ordered]@{
        completion = $ExistingCompletionPath
        completion_sha256 = Get-Sha256 $ExistingCompletionPath
        checkpoint = $Step1200
        checkpoint_sha256 = $stepHash
        optimizer = $OptimizerPath
        optimizer_sha256 = Get-Sha256 $OptimizerPath
        adapter_validation = $validationPath
    }
}

function Assert-TrainingDatasetCopy {
    $target = Join-Path $TrainRoot "dataset"
    $files = @(Get-ChildItem -LiteralPath $target -File -Force)
    $images = @($files | Where-Object Extension -In @(".jpg", ".jpeg", ".png", ".webp"))
    $captions = @($files | Where-Object Extension -eq ".txt")
    if ($images.Count -ne $ExpectedTrainCount -or $captions.Count -ne $ExpectedTrainCount) {
        throw "Training copy is no longer exactly $ExpectedTrainCount image/TXT pairs."
    }
    $unexpectedFiles = @($files | Where-Object { $_.Extension.ToLowerInvariant() -notin @(".jpg", ".jpeg", ".png", ".webp", ".txt") -and $_.Name -cne ".aitk_size.json" })
    if ($unexpectedFiles.Count -gt 0) { throw "Unexpected top-level training-data file: $($unexpectedFiles[0].FullName)" }
    $directories = @(Get-ChildItem -LiteralPath $target -Directory -Force)
    $unexpectedDirectories = @($directories | Where-Object Name -NotIn @("_latent_cache", "_t_e_cache"))
    if ($unexpectedDirectories.Count -gt 0) { throw "Unexpected training-data directory: $($unexpectedDirectories[0].FullName)" }
    $latentCache = Join-Path $target "_latent_cache"
    $textCache = Join-Path $target "_t_e_cache"
    foreach ($path in @($latentCache, $textCache)) {
        if (-not (Test-Path -LiteralPath $path -PathType Container)) { throw "Expected continuation cache is missing: $path" }
    }
    $latentCacheFiles = @(Get-ChildItem -LiteralPath $latentCache -Recurse -File)
    $textCacheFiles = @(Get-ChildItem -LiteralPath $textCache -Recurse -File)
    $expectedCacheEntries = $ExpectedTrainCount * 2
    if ($latentCacheFiles.Count -ne $expectedCacheEntries -or $textCacheFiles.Count -ne $expectedCacheEntries) {
        throw "Continuation caches must contain exactly $expectedCacheEntries latent and $expectedCacheEntries text-embedding entries."
    }
    foreach ($image in $images) {
        $sourceImage = Join-Path $SourceDataset $image.Name
        $targetCaption = [IO.Path]::ChangeExtension($image.FullName, ".txt")
        $sourceCaption = [IO.Path]::ChangeExtension($sourceImage, ".txt")
        foreach ($path in @($sourceImage, $targetCaption, $sourceCaption)) { Assert-File $path }
        if ((Get-Sha256 $image.FullName) -cne (Get-Sha256 $sourceImage)) { throw "Training image changed: $($image.Name)" }
        if ((Get-Content -Raw -LiteralPath $targetCaption).Trim() -cne (Get-Content -Raw -LiteralPath $sourceCaption).Trim()) { throw "Training caption changed: $($image.Name)" }
    }
    return [ordered]@{
        path = $target
        images = $ExpectedTrainCount
        captions = $ExpectedTrainCount
        latent_cache_files = $latentCacheFiles.Count
        text_embedding_cache_files = $textCacheFiles.Count
        size_index_sha256 = Get-Sha256 (Join-Path $target ".aitk_size.json")
    }
}

function Get-ExtensionPreflight {
    Assert-ContinuationConfig
    $existing = Assert-ExistingStep1200
    $dataset = Assert-TrainingDatasetCopy
    $models = Assert-ModelLocks
    $workers = @(
        Get-ComfyState 8188
        Get-ComfyState 8189
        Get-ComfyState 8190
    )
    if ($workers[0].online -and $workers[0].device -notmatch "RTX 3090") { throw "Port 8188 is not the RTX 3090 worker." }
    if ($workers[1].online -and $workers[1].device -notmatch "RTX 4070") { throw "Port 8189 is not the RTX 4070 worker." }
    if ($workers[2].online -and $workers[2].device -notmatch "RTX 3090") { throw "Port 8190 is not the auxiliary RTX 3090 worker." }
    return [ordered]@{
        valid = $true
        validated_utc = (Get-Date).ToUniversalTime().ToString("o")
        source = $sourceReport
        toolkit = $toolkitReport
        models = $models
        dataset = $dataset
        existing_step1200 = $existing
        continuation_config = $ExtensionConfig
        continuation_config_sha256 = Get-Sha256 $ExtensionConfig
        workers = $workers
        target_gpu = "physical GPU 0 / NVIDIA GeForce RTX 3090"
        fallback_gpu = $null
        start_update_index = 1200
        additional_updates = 800
        target_completed_updates = 2000
    }
}

function Stop-Auxiliary3090Worker([object]$State) {
    if (-not $State.online) { return [ordered]@{ online = $false; stopped = $false } }
    if ($State.device -notmatch "RTX 3090" -or $State.running -gt 0 -or $State.pending -gt 0) { throw "Auxiliary RTX 3090 worker is unsafe to stop." }
    Invoke-RestMethod -Uri "http://127.0.0.1:8190/free" -Method Post -ContentType "application/json" -Body '{"unload_models":true,"free_memory":true}' -TimeoutSec 30 | Out-Null
    Start-Sleep -Seconds 3
    $owners = @(Get-NetTCPConnection -LocalPort 8190 -State Listen | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($owners.Count -ne 1) { throw "Could not identify exactly one idle auxiliary RTX 3090 listener." }
    $pidToStop = [int]$owners[0]
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$pidToStop"
    $commandLine = [string]$process.CommandLine
    if ($commandLine -notmatch "(?i)ComfyUI.*main\.py" -or $commandLine -notmatch "--port\s+8190" -or $commandLine -notmatch "infiniteyou-comfy") {
        throw "Refusing to stop unverified port-8190 process $pidToStop`: $commandLine"
    }
    Stop-Process -Id $pidToStop
    $deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Seconds 1
        $listeners = @(Get-NetTCPConnection -LocalPort 8190 -State Listen -ErrorAction SilentlyContinue)
    } while ($listeners.Count -gt 0 -and (Get-Date) -lt $deadline)
    if ($listeners.Count -gt 0) { throw "Auxiliary RTX 3090 worker did not stop cleanly." }
    return [ordered]@{ online = $true; stopped = $true; pid = $pidToStop; command_line = $commandLine }
}

function Stop-IdleForge3090 {
    try {
        $progress = Invoke-RestMethod -Uri "http://127.0.0.1:7860/sdapi/v1/progress?skip_current_image=true" -TimeoutSec 5
    } catch {
        $listeners = @(Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue)
        if ($listeners.Count -gt 0) { throw "Forge port 7860 is listening but its idle state cannot be verified." }
        return [ordered]@{ online = $false; stopped = $false }
    }
    if ([double]$progress.progress -gt 0 -or -not [string]::IsNullOrWhiteSpace([string]$progress.state.job)) { throw "Forge has active RTX 3090 work; nothing will be stopped." }
    $owners = @(Get-NetTCPConnection -LocalPort 7860 -State Listen | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($owners.Count -ne 1) { throw "Could not identify exactly one idle Forge listener." }
    $childPid = [int]$owners[0]
    $child = Get-CimInstance Win32_Process -Filter "ProcessId=$childPid"
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($child.ParentProcessId)"
    $commandLine = [string]$child.CommandLine
    $parentCommandLine = [string]$parent.CommandLine
    $forgeRoot = "C:\projects\AI-Tools\sd-webui-forge-classic-neo"
    $forgePython = Join-Path $forgeRoot "venv\Scripts\python.exe"
    if ($commandLine -notmatch "(?i)launch\.py" -or $commandLine -notmatch "--port\s+7860" -or
        $parentCommandLine -notmatch "(?i)launch\.py" -or $parentCommandLine -notmatch "--port\s+7860" -or
        [IO.Path]::GetFullPath([string]$parent.ExecutablePath) -cne [IO.Path]::GetFullPath($forgePython)) {
        throw "Refusing to stop an unverified Forge process tree."
    }
    Stop-Process -Id $childPid
    if (Get-Process -Id ([int]$parent.ProcessId) -ErrorAction SilentlyContinue) { Stop-Process -Id ([int]$parent.ProcessId) }
    $deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Seconds 1
        $listeners = @(Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue)
    } while ($listeners.Count -gt 0 -and (Get-Date) -lt $deadline)
    if ($listeners.Count -gt 0) { throw "Forge did not stop cleanly." }
    return [ordered]@{
        online = $true
        stopped = $true
        pid = $childPid
        parent_pid = [int]$parent.ProcessId
        command_line = $commandLine
        parent_command_line = $parentCommandLine
        working_directory = $forgeRoot
        executable = $forgePython
    }
}

function Restore-Forge3090([object]$Record) {
    if (-not $Record.stopped) { return }
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $stdout = Join-Path $TrainRoot "restored-forge-extension-$stamp.stdout.log"
    $stderr = Join-Path $TrainRoot "restored-forge-extension-$stamp.stderr.log"
    $args = @("launch.py", "--uv", "--cuda-malloc", "--cuda-stream", "--pin-shared-memory", "--fast-fp8", "--disable-sage", "--api", "--port", "7860", "--forge-ref-comfy-home", "C:\projects\AI-Tools\ComfyUI")
    $process = Start-Process -FilePath ([string]$Record.executable) -ArgumentList $args -WorkingDirectory ([string]$Record.working_directory) -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
    $deadline = (Get-Date).AddSeconds(120)
    do {
        Start-Sleep -Seconds 2
        $process.Refresh()
        if ($process.HasExited) { break }
        try {
            $progress = Invoke-RestMethod -Uri "http://127.0.0.1:7860/sdapi/v1/progress?skip_current_image=true" -TimeoutSec 3
            $ready = $null -ne $progress.state
        } catch { $ready = $false }
    } while (-not $ready -and (Get-Date) -lt $deadline)
    if (-not $ready) { throw "Failed to restore Forge after extension. Logs: $stdout | $stderr" }
}

function Invoke-ExtensionTraining {
    if (Test-Path -LiteralPath $ExtensionCompletionPath -PathType Leaf) { throw "The 2,000-step extension is already complete; refusing to overwrite it." }
    $existingManifests = @(Get-ChildItem -LiteralPath $TrainRoot -File -Filter "extension-to2000-manifest-*.json" -ErrorAction SilentlyContinue)
    if ($existingManifests.Count -gt 0) { throw "A prior extension attempt is already recorded; refusing an ambiguous restart." }
    $preflight = Get-ExtensionPreflight
    $preflight | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $ExtensionPreflightPath -Encoding utf8

    if (Test-Path -LiteralPath $ExtensionArchiveRoot) { throw "Extension archive already exists: $ExtensionArchiveRoot" }
    New-Item -ItemType Directory -Path $ExtensionArchiveRoot | Out-Null
    $archivedFinal = Join-Path $ExtensionArchiveRoot "$JobName-step1200-final.safetensors"
    Move-Item -LiteralPath $FinalLora -Destination $archivedFinal
    Copy-Item -LiteralPath $OptimizerPath -Destination (Join-Path $ExtensionArchiveRoot "optimizer-step1200.pt")
    Copy-Item -LiteralPath $ExistingCompletionPath -Destination (Join-Path $ExtensionArchiveRoot "training-validation-step1200.json")
    Copy-Item -LiteralPath $OutputConfig -Destination (Join-Path $ExtensionArchiveRoot "config-step1200.yaml")

    $workerStopped = $false
    $auxRecord = [ordered]@{ online = $false; stopped = $false }
    $forgeRecord = [ordered]@{ online = $false; stopped = $false }
    try {
        $state3090 = Get-ComfyState 8188
        if ($state3090.online) {
            $workerRecord = Stop-Verified3090Worker
            $workerStopped = $true
        } else {
            $listeners = @(Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue)
            if ($listeners.Count -gt 0) { throw "Port 8188 is listening but the RTX 3090 worker cannot be verified." }
            $state4070 = Get-ComfyState 8189
            if ($state4070.online -and ($state4070.device -notmatch "RTX 4070" -or $state4070.running -gt 0 -or $state4070.pending -gt 0)) {
                throw "The RTX 4070 worker is not safely idle; it will not be touched."
            }
            $workerRecord = [ordered]@{ stopped = $false; already_offline = $true; preserved_4070 = $state4070 }
        }
        $auxRecord = Stop-Auxiliary3090Worker (Get-ComfyState 8190)
        $forgeRecord = Stop-IdleForge3090
        $hardware = Assert-HardwareHeadroom
        $cuda = Assert-IsolatedCuda

        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $logRoot = Join-Path $TrainRoot "logs"
        New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
        $trainingLog = Join-Path $logRoot "train-extension-to2000-$stamp.log"
        $consoleLog = Join-Path $logRoot "train-extension-to2000-$stamp-console.log"
        $manifestPath = Join-Path $TrainRoot "extension-to2000-manifest-$stamp.json"
        [ordered]@{
            started_utc = (Get-Date).ToUniversalTime().ToString("o")
            kind = "controlled-training-extension"
            source_completed_updates = 1200
            start_update_index = 1200
            target_completed_updates = 2000
            additional_updates = 800
            reason = "Mitch requested an unchanged extension to compare steps 1200, 1400, 1600, and 2000."
            continuation_config = $ExtensionConfig
            continuation_config_sha256 = Get-Sha256 $ExtensionConfig
            source_checkpoint = $Step1200
            source_checkpoint_sha256 = Get-Sha256 $Step1200
            archived_source_final = $archivedFinal
            archived_source_final_sha256 = Get-Sha256 $archivedFinal
            optimizer = $OptimizerPath
            optimizer_sha256 = Get-Sha256 $OptimizerPath
            preflight = $ExtensionPreflightPath
            preflight_sha256 = Get-Sha256 $ExtensionPreflightPath
            hardware = $hardware
            cuda = $cuda
            worker = $workerRecord
            auxiliary_3090 = $auxRecord
            forge_3090 = $forgeRecord
            offline = $true
            target_gpu = "physical GPU 0 / NVIDIA GeForce RTX 3090"
            fallback_gpu = $null
        } | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $manifestPath -Encoding utf8

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
            & $ToolkitPython $ToolkitRun $ExtensionConfig -l $trainingLog 2>&1 | Tee-Object -FilePath $consoleLog
            $exitCode = $LASTEXITCODE
        } finally {
            Pop-Location
        }
        if ($exitCode -ne 0) { throw "AI-Toolkit extension exited with code $exitCode. See $trainingLog and $consoleLog" }

        $text = (@($trainingLog, $consoleLog) | ForEach-Object { Get-Content -Raw -LiteralPath $_ }) -join "`n"
        if ($text -match "(?i)CUDA out of memory|OOM during training|RuntimeError:.*memory|Traceback|\bloss:\s*(nan|inf)|all NaN|solid-black") {
            throw "Extension logs contain an OOM, exception, or nonfinite-loss marker."
        }
        if ($text -notmatch [regex]::Escape("#### IMPORTANT RESUMING FROM $Step1200 ####") -or
            $text -notmatch [regex]::Escape("Loading optimizer state from $OptimizerPath") -or
            $text -notmatch "Found step 1200 in metadata, starting from there") {
            throw "AI-Toolkit did not prove an exact adapter-and-optimizer continuation from step 1,200."
        }
        $dop = Get-AitkDopTimerEvidence -Paths @($trainingLog, $consoleLog) -Steps 2000 -PerformanceLogEvery 10 -TimerMaxBuffer 10 -StartStep 1200
        if (-not [bool]$dop.valid -or [int]$dop.proven_updates -ne 800) { throw "DOP execution is not proven for all 800 extension updates." }

        $lossSteps = [System.Collections.Generic.HashSet[int]]::new()
        foreach ($path in @($trainingLog, $consoleLog)) {
            $logText = Get-Content -Raw -LiteralPath $path
            foreach ($match in [regex]::Matches($logText, "([0-9]{1,4})/2000[^\r\n]*?loss:\s*([0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?)", [Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
                $step = [int]$match.Groups[1].Value
                $loss = [double]::Parse($match.Groups[2].Value, [Globalization.CultureInfo]::InvariantCulture)
                if ([double]::IsFinite($loss) -and $step -ge 1200 -and $step -le 1999) { [void]$lossSteps.Add($step) }
            }
        }
        if ($lossSteps.Count -ne 800 -or -not $lossSteps.Contains(1200) -or -not $lossSteps.Contains(1999)) {
            throw "Logs do not prove 800 distinct finite extension loss indices."
        }

        Assert-File $FinalLora
        $step2000 = Join-Path $OutputRoot ("{0}_{1:D9}.safetensors" -f $JobName, 2000)
        if (Test-Path -LiteralPath $step2000) { throw "Unexpected pre-existing step-2,000 checkpoint." }
        Copy-Item -LiteralPath $FinalLora -Destination $step2000
        $newValidations = @()
        foreach ($step in @(1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000)) {
            $checkpoint = Join-Path $OutputRoot ("{0}_{1:D9}.safetensors" -f $JobName, $step)
            Assert-File $checkpoint
            $validation = Join-Path $TrainRoot ("extension-step-{0:D4}-validation.json" -f $step)
            & $ToolkitPython $LoraValidator $checkpoint --expected-modules 112 --expected-rank 32 --require-nonzero --json-output $validation | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "Extended checkpoint $step failed tensor validation." }
            $probe = Get-Content -Raw -LiteralPath $validation | ConvertFrom-Json
            $trainingInfo = [string]$probe.metadata.training_info | ConvertFrom-Json
            if (-not [bool]$probe.valid -or [int]$trainingInfo.step -ne $step) { throw "Extended checkpoint $step has invalid training metadata." }
            $newValidations += [ordered]@{ step = $step; path = $checkpoint; sha256 = Get-Sha256 $checkpoint; validation = $validation }
        }
        if ((Get-Sha256 $step2000) -cne (Get-Sha256 $FinalLora)) { throw "Step 2,000 differs from the final adapter." }
        $allSteps = @(Get-ChildItem -LiteralPath $OutputRoot -File -Filter "${JobName}_*.safetensors" | ForEach-Object {
            if ($_.BaseName -match '_(\d{9})$') { [int]$Matches[1] }
        } | Sort-Object)
        $expectedAll = @(100..2000 | Where-Object { $_ % 100 -eq 0 })
        if ((Compare-Object $expectedAll $allSteps).Count -ne 0) { throw "Numbered saves do not exactly cover steps 100 through 2000." }

        $prior = Get-Content -Raw -LiteralPath $ExistingCompletionPath | ConvertFrom-Json
        [ordered]@{
            valid = $true
            completed_utc = (Get-Date).ToUniversalTime().ToString("o")
            steps = 2000
            source_steps = 1200
            extension_updates = 800
            total_steps = 2000
            gpu = "NVIDIA GeForce RTX 3090"
            fallback_gpu = $null
            zero_ooms = $true
            finite_extension_loss_records = $lossSteps.Count
            finite_extension_loss_index_range = @(1200, 1999)
            source_checkpoint = $Step1200
            source_checkpoint_sha256 = Get-Sha256 $Step1200
            final_lora = $FinalLora
            final_lora_sha256 = Get-Sha256 $FinalLora
            checkpoints = @($newValidations)
            training_log = $trainingLog
            console_log = $consoleLog
            manifest = $manifestPath
            diff_output_preservation = $true
            diff_output_preservation_class = "man"
            diff_output_preservation_multiplier = 1.0
            dop_source_proven_updates = [int]$prior.dop_prior_prediction_proven_updates
            dop_extension_proven_updates = [int]$dop.proven_updates
            dop_total_proven_updates = [int]$prior.dop_prior_prediction_proven_updates + [int]$dop.proven_updates
            dop_prior_prediction_proven_updates = [int]$prior.dop_prior_prediction_proven_updates + [int]$dop.proven_updates
            dop_execution_proven = ([int]$prior.dop_prior_prediction_proven_updates + [int]$dop.proven_updates) -eq 2000
            dop_timer_accounting = [ordered]@{
                valid = [bool]$prior.dop_timer_accounting.valid -and [bool]$dop.valid
                source = $prior.dop_timer_accounting
                extension = $dop
                proven_updates = [int]$prior.dop_prior_prediction_proven_updates + [int]$dop.proven_updates
                exact_nonoverlapping_ranges = @("0-1199", "1200-1999")
            }
            dop_extension_timer_accounting = $dop
            exact_continuation_proven = $true
            retained_numbered_checkpoints = 20
        } | ConvertTo-Json -Depth 18 | Set-Content -LiteralPath $ExtensionCompletionPath -Encoding utf8
        Write-Host "$RunLabel continuation passed through 2,000 updates on the RTX 3090: $FinalLora"
    } finally {
        if (-not (Test-Path -LiteralPath $FinalLora -PathType Leaf) -and (Test-Path -LiteralPath $archivedFinal -PathType Leaf)) {
            Copy-Item -LiteralPath $archivedFinal -Destination $FinalLora
        }
        if ($workerStopped) { Restart-3090Worker }
        if ($auxRecord.stopped) {
            & (Join-Path $RepoRoot "scripts\start-infiniteyou-comfy.ps1")
            if ($LASTEXITCODE -ne 0) { throw "Failed to restore the auxiliary RTX 3090 worker." }
        }
        Restore-Forge3090 $forgeRecord
    }
}

switch ($RequestedPhase) {
    "Validate" {
        $report = Get-ExtensionPreflight
        $report | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $ExtensionPreflightPath -Encoding utf8
        $report | ConvertTo-Json -Depth 6
    }
    "Train" { Invoke-ExtensionTraining }
}
