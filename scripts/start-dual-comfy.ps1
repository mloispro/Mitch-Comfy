param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [int]$PrimaryPort = 8188,
    [int]$SecondaryPort = 8189,
    [int]$StartupTimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $ComfyRoot ".venv\Scripts\python.exe"
$MainPath = Join-Path $ComfyRoot "main.py"
$RuntimeRoot = Join-Path $RepoRoot "local\dual-comfy"
$SecondaryUserRoot = Join-Path $ComfyRoot "user-4070"
$SecondaryDatabasePath = (Join-Path $SecondaryUserRoot "comfyui.db").Replace("\", "/")

$workers = @(
    [pscustomobject]@{
        Label = "RTX 3090 primary"
        ExpectedName = "NVIDIA GeForce RTX 3090"
        Uuid = "GPU-c2ca4516-2c9f-e87b-3a20-f459947ddb17"
        Port = $PrimaryPort
        ExtraArguments = @()
    },
    [pscustomobject]@{
        Label = "RTX 4070 secondary"
        ExpectedName = "NVIDIA GeForce RTX 4070"
        Uuid = "GPU-de12eec8-4b3d-f2ae-791c-8423a86915fd"
        Port = $SecondaryPort
        ExtraArguments = @(
            "--user-directory", $SecondaryUserRoot,
            "--database-url", "sqlite:///$SecondaryDatabasePath",
            "--temp-directory", (Join-Path $ComfyRoot "temp\gpu-4070"),
            "--output-directory", (Join-Path $ComfyRoot "output\gpu-4070")
        )
    }
)

function Get-ComfyDeviceName {
    param([int]$Port)

    try {
        $stats = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/system_stats" -TimeoutSec 2
        return [string](@($stats.devices)[0].name)
    }
    catch {
        return $null
    }
}

function Assert-WorkerIdentity {
    param($Worker, [string]$DeviceName)

    if ($DeviceName -notlike "*$($Worker.ExpectedName)*") {
        throw "Port $($Worker.Port) is already serving '$DeviceName', not $($Worker.ExpectedName). Stop that server before relaunching."
    }
}

if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "ComfyUI Python was not found: $PythonPath"
}
if (-not (Test-Path -LiteralPath $MainPath -PathType Leaf)) {
    throw "ComfyUI main.py was not found: $MainPath"
}

$detectedGpus = @(& nvidia-smi --query-gpu=uuid,name --format=csv,noheader)
if ($LASTEXITCODE -ne 0) {
    throw "nvidia-smi could not enumerate the GPUs."
}
foreach ($worker in $workers) {
    $matchingGpu = @($detectedGpus | Where-Object {
        $_ -like "$($worker.Uuid),*$($worker.ExpectedName)*"
    })
    if ($matchingGpu.Count -ne 1) {
        throw "$($worker.Label) was not found with expected UUID $($worker.Uuid). Detected: $($detectedGpus -join '; ')"
    }
}

New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null

$secondaryUserRoot = $SecondaryUserRoot
$secondaryWorkflowParent = Join-Path $secondaryUserRoot "default\workflows"
$secondaryWorkflowLink = Join-Path $secondaryWorkflowParent "Mitch"
New-Item -ItemType Directory -Path $secondaryWorkflowParent -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $ComfyRoot "temp\gpu-4070") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $ComfyRoot "output\gpu-4070") -Force | Out-Null

if (-not (Test-Path -LiteralPath $secondaryWorkflowLink)) {
    New-Item -ItemType Junction -Path $secondaryWorkflowLink -Target (Join-Path $RepoRoot "workflows") | Out-Null
}
else {
    $workflowLinkItem = Get-Item -LiteralPath $secondaryWorkflowLink -Force
    if (-not ($workflowLinkItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "The secondary workflow path exists but is not a junction: $secondaryWorkflowLink"
    }
    $resolvedWorkflowTarget = (Resolve-Path -LiteralPath @($workflowLinkItem.Target)[0]).Path
    $expectedWorkflowTarget = (Resolve-Path -LiteralPath (Join-Path $RepoRoot "workflows")).Path
    if ($resolvedWorkflowTarget -ne $expectedWorkflowTarget) {
        throw "The secondary workflow junction points to '$resolvedWorkflowTarget', not '$expectedWorkflowTarget'."
    }
}

$startedWorkers = [System.Collections.Generic.List[object]]::new()
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"

foreach ($worker in $workers) {
    $deviceName = Get-ComfyDeviceName -Port $worker.Port
    if ($deviceName) {
        Assert-WorkerIdentity -Worker $worker -DeviceName $deviceName
        Write-Host "$($worker.Label) already online at http://127.0.0.1:$($worker.Port)"
        continue
    }

    $arguments = @(
        $MainPath,
        "--cuda-device", $worker.Uuid,
        "--port", [string]$worker.Port,
        "--disable-auto-launch"
    ) + @($worker.ExtraArguments)

    $safeLabel = $worker.Label.ToLowerInvariant() -replace "[^a-z0-9]+", "-"
    $stdoutPath = Join-Path $RuntimeRoot "$safeLabel-$stamp.stdout.log"
    $stderrPath = Join-Path $RuntimeRoot "$safeLabel-$stamp.stderr.log"
    $process = Start-Process `
        -FilePath $PythonPath `
        -ArgumentList $arguments `
        -WorkingDirectory $ComfyRoot `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -WindowStyle Hidden `
        -PassThru

    $startedWorkers.Add([pscustomobject]@{
        Worker = $worker
        Process = $process
        StdoutPath = $stdoutPath
        StderrPath = $stderrPath
    })
    Write-Host "Starting $($worker.Label) on port $($worker.Port) (PID $($process.Id))"
}

foreach ($started in $startedWorkers) {
    $deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
    $deviceName = $null
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($started.Process.HasExited) {
            break
        }
        $deviceName = Get-ComfyDeviceName -Port $started.Worker.Port
        if ($deviceName) {
            break
        }
        Start-Sleep -Milliseconds 1000
        $started.Process.Refresh()
    }

    if (-not $deviceName) {
        $stderrTail = if (Test-Path -LiteralPath $started.StderrPath) {
            (Get-Content -LiteralPath $started.StderrPath -Tail 30) -join [Environment]::NewLine
        }
        else {
            "No stderr log was created."
        }
        throw "$($started.Worker.Label) did not become ready. Log: $($started.StderrPath)`n$stderrTail"
    }

    Assert-WorkerIdentity -Worker $started.Worker -DeviceName $deviceName
    Write-Host "$($started.Worker.Label) ready at http://127.0.0.1:$($started.Worker.Port) [$deviceName]"
}

Write-Host "Dual-GPU ComfyUI is ready. Primary: http://127.0.0.1:$PrimaryPort | Secondary: http://127.0.0.1:$SecondaryPort"
