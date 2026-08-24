[CmdletBinding()]
param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [int]$Port = 8189,
    [switch]$SkipHashes,
    [switch]$RequireIdentityLora
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$lockPath = Join-Path $repoRoot "config\krea2-sidewalk.lock.json"
$workflowPath = Join-Path $repoRoot "archive\krea2-workflows\Krea 2 Mitch - Busy Sidewalk (Unavailable Personal LoRA).json"
$errors = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()

function Add-CheckError([string]$Message) {
    $errors.Add($Message)
    Write-Host "FAIL  $Message" -ForegroundColor Red
}

function Add-CheckWarning([string]$Message) {
    $warnings.Add($Message)
    Write-Host "WAIT  $Message" -ForegroundColor Yellow
}

function Add-CheckPass([string]$Message) {
    Write-Host "PASS  $Message" -ForegroundColor Green
}

function Get-SafetensorsTensorCount {
    param([Parameter(Mandatory)][string]$Path)

    $stream = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        $reader = [IO.BinaryReader]::new($stream, [Text.Encoding]::UTF8, $true)
        $headerLength = $reader.ReadInt64()
        if ($headerLength -lt 2 -or $headerLength -gt 134217728) {
            throw "Invalid safetensors header length $headerLength"
        }
        $headerBytes = $reader.ReadBytes([int]$headerLength)
        if ($headerBytes.Length -ne $headerLength) {
            throw "Truncated safetensors header"
        }
        $header = [Text.Encoding]::UTF8.GetString($headerBytes) | ConvertFrom-Json -AsHashtable
        return @($header.Keys | Where-Object { $_ -ne "__metadata__" }).Count
    }
    finally {
        $stream.Dispose()
    }
}

if (-not (Test-Path -LiteralPath $lockPath -PathType Leaf)) {
    throw "Dependency lock was not found: $lockPath"
}
$lock = Get-Content -LiteralPath $lockPath -Raw | ConvertFrom-Json

$gpuRows = @(& nvidia-smi --query-gpu=index,uuid,name,memory.used,utilization.gpu --format=csv,noheader)
if ($LASTEXITCODE -ne 0) {
    Add-CheckError "nvidia-smi could not enumerate GPUs."
}
else {
    $gpuMatch = @($gpuRows | Where-Object { $_ -like "*$($lock.runtime.setupGpuUuid)*$($lock.runtime.setupGpu)*" })
    if ($gpuMatch.Count -eq 1) {
        Add-CheckPass "Expected RTX 4070 is present: $($gpuMatch[0])"
    }
    else {
        Add-CheckError "Expected RTX 4070 UUID $($lock.runtime.setupGpuUuid) was not found."
    }
}

$nodesPath = Join-Path $ComfyRoot "nodes.py"
$loraCodePath = Join-Path $ComfyRoot "comfy\lora.py"
if (-not (Test-Path -LiteralPath $nodesPath -PathType Leaf)) {
    Add-CheckError "ComfyUI nodes.py is missing: $nodesPath"
}
elseif ((Get-Content -LiteralPath $nodesPath -Raw) -notmatch '"krea2"') {
    Add-CheckError "This ComfyUI checkout does not expose CLIPLoader type krea2."
}
else {
    Add-CheckPass "ComfyUI has native CLIPLoader type krea2."
}
if (-not (Test-Path -LiteralPath $loraCodePath -PathType Leaf)) {
    Add-CheckError "ComfyUI Krea2 LoRA implementation file is missing: $loraCodePath"
}
elseif ((Get-Content -LiteralPath $loraCodePath -Raw) -notmatch 'krea2_to_diffusers') {
    Add-CheckError "This ComfyUI checkout does not contain Krea2 LoRA key conversion."
}
else {
    Add-CheckPass "ComfyUI has native Krea2 LoRA conversion."
}

foreach ($model in @($lock.models)) {
    $relativeWindowsPath = ([string]$model.relativePath).Replace("/", "\")
    $modelPath = Join-Path (Join-Path $ComfyRoot "models") $relativeWindowsPath
    if (-not (Test-Path -LiteralPath $modelPath -PathType Leaf)) {
        Add-CheckError "Required model is missing: $modelPath"
        continue
    }
    $fileInfo = Get-Item -LiteralPath $modelPath
    if ($model.sizeBytes -and $fileInfo.Length -ne [int64]$model.sizeBytes) {
        Add-CheckError "File size mismatch for $relativeWindowsPath. Expected $($model.sizeBytes), got $($fileInfo.Length)."
        continue
    }
    if (-not $SkipHashes) {
        $actualHash = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash
        if ($actualHash -ne [string]$model.sha256) {
            Add-CheckError "SHA256 mismatch for $relativeWindowsPath. Expected $($model.sha256), got $actualHash."
            continue
        }
    }
    Add-CheckPass "Verified model $relativeWindowsPath"
}

if (-not (Test-Path -LiteralPath $workflowPath -PathType Leaf)) {
    Add-CheckError "Prepared workflow is missing: $workflowPath"
}
else {
    try {
        $workflow = Get-Content -LiteralPath $workflowPath -Raw | ConvertFrom-Json
        $requiredNodeTypes = @(
            "UNETLoader", "LoraLoaderModelOnly", "CLIPLoader", "CLIPTextEncode",
            "ConditioningZeroOut", "EmptyLatentImage", "KSampler", "VAELoader", "VAEDecode", "SaveImage"
        )
        foreach ($nodeType in $requiredNodeTypes) {
            if (@($workflow.nodes | Where-Object type -eq $nodeType).Count -ne 1) {
                Add-CheckError "Workflow must contain exactly one $nodeType node."
            }
        }

        $nodeIds = @($workflow.nodes | ForEach-Object { [int]$_.id })
        foreach ($link in @($workflow.links)) {
            if ([int]$link[1] -notin $nodeIds -or [int]$link[3] -notin $nodeIds) {
                Add-CheckError "Workflow link $($link[0]) references a missing node."
            }
        }

        $saveNode = $workflow.nodes | Where-Object type -eq "SaveImage" | Select-Object -First 1
        if ([int]$saveNode.mode -ne 4) {
            Add-CheckError "Save Image must remain bypassed (mode 4) during setup."
        }
        else {
            Add-CheckPass "Prepared workflow cannot generate because Save Image is bypassed."
        }

        $samplerNode = $workflow.nodes | Where-Object type -eq "KSampler" | Select-Object -First 1
        $latentNode = $workflow.nodes | Where-Object type -eq "EmptyLatentImage" | Select-Object -First 1
        $clipNode = $workflow.nodes | Where-Object type -eq "CLIPLoader" | Select-Object -First 1
        if ($samplerNode.widgets_values[2] -ne 8 -or $samplerNode.widgets_values[3] -ne 1.0 -or
            $samplerNode.widgets_values[4] -ne "euler" -or $samplerNode.widgets_values[5] -ne "simple") {
            Add-CheckError "Workflow sampler is not the locked 8-step, CFG 1, Euler/simple configuration."
        }
        elseif ($latentNode.widgets_values[0] -ne 896 -or $latentNode.widgets_values[1] -ne 1344 -or
                $clipNode.widgets_values[1] -ne "krea2") {
            Add-CheckError "Workflow resolution or CLIP type differs from the lock."
        }
        else {
            Add-CheckPass "Workflow settings match the clean Krea2 lock."
        }
    }
    catch {
        Add-CheckError "Workflow JSON could not be validated: $($_.Exception.Message)"
    }
}

$identityPath = Join-Path (Join-Path $ComfyRoot "models") (([string]$lock.identityLora.destinationRelativePath).Replace("/", "\"))
if (Test-Path -LiteralPath $identityPath -PathType Leaf) {
    try {
        $identityInfo = Get-Item -LiteralPath $identityPath
        if ($identityInfo.Length -ne [int64]$lock.identityLora.sizeBytes) {
            Add-CheckError "Mitch Krea2 LoRA size mismatch. Expected $($lock.identityLora.sizeBytes), got $($identityInfo.Length)."
        }
        elseif (-not $SkipHashes -and
                (Get-FileHash -LiteralPath $identityPath -Algorithm SHA256).Hash -ne [string]$lock.identityLora.sha256) {
            Add-CheckError "Mitch Krea2 LoRA SHA256 does not match the lock."
        }
        elseif ((Get-SafetensorsTensorCount -Path $identityPath) -ne [int]$lock.identityLora.tensorCount) {
            Add-CheckError "Mitch Krea2 LoRA tensor count does not match the lock."
        }
        else {
            Add-CheckPass "Verified canonical Mitch Krea2 LoRA: $identityPath"
        }
    }
    catch {
        Add-CheckError "Mitch Krea2 LoRA could not be validated: $($_.Exception.Message)"
    }
}
elseif ($RequireIdentityLora) {
    Add-CheckError "Canonical Mitch Krea2 LoRA is not published yet: $identityPath"
}
else {
    Add-CheckWarning "Mitch Krea2 LoRA is still pending training/publish: $identityPath"
}

try {
    $stats = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/system_stats" -TimeoutSec 3
    $deviceName = [string](@($stats.devices)[0].name)
    if ($deviceName -notlike "*$($lock.runtime.setupGpu)*") {
        Add-CheckError "ComfyUI port $Port is serving '$deviceName', not the RTX 4070."
    }
    else {
        Add-CheckPass "ComfyUI port $Port is isolated to $deviceName."
    }

    $queue = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/queue" -TimeoutSec 3
    if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
        Add-CheckWarning "ComfyUI port $Port has queued work; this verifier did not submit it."
    }
    else {
        Add-CheckPass "ComfyUI port $Port queue is empty."
    }

    $requiredLiveNodes = @(
        "UNETLoader", "LoraLoaderModelOnly", "CLIPLoader", "CLIPTextEncode",
        "ConditioningZeroOut", "EmptyLatentImage", "KSampler", "VAELoader", "VAEDecode", "SaveImage"
    )
    foreach ($nodeType in $requiredLiveNodes) {
        $nodeInfo = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/object_info/$nodeType" -TimeoutSec 10
        if ($nodeInfo.PSObject.Properties.Name -notcontains $nodeType) {
            Add-CheckError "Live ComfyUI is missing required node $nodeType."
        }
    }

    $unetInfo = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/object_info/UNETLoader" -TimeoutSec 10
    $loraInfo = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/object_info/LoraLoaderModelOnly" -TimeoutSec 10
    $clipInfo = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/object_info/CLIPLoader" -TimeoutSec 10
    $vaeInfo = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/object_info/VAELoader" -TimeoutSec 10
    $clipTypes = @($clipInfo.CLIPLoader.input.required.type[0])
    if ("krea2" -notin $clipTypes) {
        Add-CheckError "Live CLIPLoader does not advertise krea2."
    }
    else {
        Add-CheckPass "Live ComfyUI API advertises CLIPLoader type krea2."
    }
    if ($unetInfo.UNETLoader.input.required.unet_name[0] -notcontains "krea2_turbo_fp8_scaled.safetensors" -or
        $clipInfo.CLIPLoader.input.required.clip_name[0] -notcontains "qwen3vl_4b_fp8_scaled.safetensors" -or
        $vaeInfo.VAELoader.input.required.vae_name[0] -notcontains "qwen_image_vae.safetensors") {
        Add-CheckError "Live ComfyUI model registry is missing one or more locked Krea2 files."
    }
    else {
        Add-CheckPass "Live ComfyUI model registry contains all three locked Krea2 files."
    }
    $identityModelName = ([string]$lock.identityLora.destinationRelativePath).Substring("loras/".Length).Replace("/", "\")
    if ($loraInfo.LoraLoaderModelOnly.input.required.lora_name[0] -notcontains $identityModelName) {
        Add-CheckError "Live ComfyUI does not advertise $identityModelName."
    }
    else {
        Add-CheckPass "Live ComfyUI advertises the canonical Mitch Krea2 LoRA."
    }
}
catch {
    Add-CheckWarning "RTX 4070 ComfyUI is not online for API validation: $($_.Exception.Message)"
}

try {
    $body = @{ channel = "training:status"; args = @([string]$lock.identityLora.runId) } | ConvertTo-Json
    $trainingResponse = Invoke-RestMethod `
        -Uri "$($lock.identityLora.inlineStudioUrl)/rpc" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body `
        -TimeoutSec 5
    if ($trainingResponse.ok) {
        $run = $trainingResponse.value
        if ($run.hyperparams.arch -ne "krea2" -or $run.hyperparams.baseMode -ne "turbo_adapter") {
            Add-CheckError "Identity run is not Krea2 Turbo-adapter compatible."
        }
        elseif ($run.status -ne "done" -or $run.step -ne $lock.identityLora.completedSteps -or
                $run.totalSteps -ne $lock.identityLora.completedSteps) {
            Add-CheckError "Identity run is not the locked completed $($lock.identityLora.completedSteps)-step run."
        }
        else {
            Add-CheckPass "Identity run compatibility confirmed: $($run.status), step $($run.step)/$($run.totalSteps)."
        }
    }
    else {
        Add-CheckWarning "Inline Studio could not report the identity run: $($trainingResponse.error)"
    }
}
catch {
    Add-CheckWarning "Inline Studio status was unavailable: $($_.Exception.Message)"
}

Write-Host ""
if ($errors.Count -gt 0) {
    throw "Krea2 sidewalk verification failed with $($errors.Count) error(s) and $($warnings.Count) pending warning(s). No prompt was submitted."
}

Write-Host "Krea2 sidewalk setup verified with $($warnings.Count) pending warning(s). No prompt was submitted and no image was generated."
