[CmdletBinding()]
param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [int]$Port = 8190,
    [int]$StartupTimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $ComfyRoot ".venv\Scripts\python.exe"
$MainPath = Join-Path $ComfyRoot "main.py"
$RuntimeRoot = Join-Path $RepoRoot "local\infiniteyou-comfy"
$UserRoot = Join-Path $RuntimeRoot "user"
$TempRoot = Join-Path $RuntimeRoot "temp"
$DatabasePath = (Join-Path $UserRoot "comfyui.db").Replace("\", "/")
$GpuUuid = "GPU-c2ca4516-2c9f-e87b-3a20-f459947ddb17"
$ExpectedDevice = "NVIDIA GeForce RTX 3090"

if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "ComfyUI Python was not found: $PythonPath"
}
if (-not (Test-Path -LiteralPath $MainPath -PathType Leaf)) {
    throw "ComfyUI main.py was not found: $MainPath"
}

try {
    $existing = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/system_stats" -TimeoutSec 2
    $deviceName = [string](@($existing.devices)[0].name)
    if ($deviceName -notlike "*$ExpectedDevice*") {
        throw "Port $Port serves '$deviceName', not $ExpectedDevice."
    }
    Write-Host "InfiniteYou worker already online at http://127.0.0.1:$Port [$deviceName]"
    exit 0
}
catch {
    if ($_.Exception.Message -like "Port $Port serves*") {
        throw
    }
}

foreach ($workerPort in 8188, 8189) {
    try {
        $queue = Invoke-RestMethod -Uri "http://127.0.0.1:$workerPort/queue" -TimeoutSec 5
        if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
            throw "Port $workerPort has active GPU work. Refusing to start the InfiniteYou worker."
        }
    }
    catch {
        if ($_.Exception.Message -like "Port $workerPort has active GPU work*") {
            throw
        }
        Write-Warning "Could not inspect optional worker on port $workerPort`: $($_.Exception.Message)"
    }
}

# The normal 3090 worker may retain 10-20 GB of cached models even with an idle
# queue. Unload only its model cache; the worker and all queues stay online.
try {
    Invoke-RestMethod `
        -Method Post `
        -Uri "http://127.0.0.1:8188/free" `
        -ContentType "application/json" `
        -Body '{"unload_models":true,"free_memory":true}' `
        -TimeoutSec 15 | Out-Null
}
catch {
    Write-Warning "Could not clear the idle 3090 worker cache: $($_.Exception.Message)"
}

New-Item -ItemType Directory -Path $RuntimeRoot, $UserRoot, $TempRoot -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$stdoutPath = Join-Path $RuntimeRoot "worker-$Port-$stamp.stdout.log"
$stderrPath = Join-Path $RuntimeRoot "worker-$Port-$stamp.stderr.log"
$arguments = @(
    $MainPath,
    "--cuda-device", $GpuUuid,
    "--port", [string]$Port,
    "--disable-auto-launch",
    "--lowvram",
    "--user-directory", $UserRoot,
    "--database-url", "sqlite:///$DatabasePath",
    "--temp-directory", $TempRoot
)

$process = Start-Process `
    -FilePath $PythonPath `
    -ArgumentList $arguments `
    -WorkingDirectory $ComfyRoot `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Starting isolated InfiniteYou worker on port $Port (PID $($process.Id))"
$deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
while ([DateTime]::UtcNow -lt $deadline) {
    Start-Sleep -Milliseconds 1000
    $process.Refresh()
    if ($process.HasExited) {
        break
    }
    try {
        $stats = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/system_stats" -TimeoutSec 2
        $deviceName = [string](@($stats.devices)[0].name)
        if ($deviceName -notlike "*$ExpectedDevice*") {
            throw "Port $Port started on '$deviceName', not $ExpectedDevice."
        }
        Write-Host "InfiniteYou worker ready at http://127.0.0.1:$Port [$deviceName]"
        Write-Host "Logs: $stdoutPath | $stderrPath"
        exit 0
    }
    catch {
        if ($_.Exception.Message -like "Port $Port started on*") {
            throw
        }
    }
}

$stderrTail = if (Test-Path -LiteralPath $stderrPath) {
    (Get-Content -LiteralPath $stderrPath -Tail 80) -join [Environment]::NewLine
}
else {
    "No stderr log was created."
}
if ($process.HasExited) {
    throw "InfiniteYou worker exited with code $($process.ExitCode).`n$stderrTail"
}
throw "InfiniteYou worker did not become ready within $StartupTimeoutSeconds seconds.`n$stderrTail"
