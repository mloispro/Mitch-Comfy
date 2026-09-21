[CmdletBinding()]
param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [int]$Port = 8189,
    [int]$StartupTimeoutSeconds = 90,
    [double]$ReserveVramGb = 1.0,
    [bool]$LowVram = $true
)

$ErrorActionPreference = "Stop"

$expectedGpuName = "NVIDIA GeForce RTX 4070"
$expectedGpuUuid = "GPU-de12eec8-4b3d-f2ae-791c-8423a86915fd"
$repoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'comfy-workflow-library.ps1')
$pythonPath = Join-Path $ComfyRoot ".venv\Scripts\python.exe"
$mainPath = Join-Path $ComfyRoot "main.py"
$userRoot = Join-Path $ComfyRoot "user-4070"
$databasePath = (Join-Path $userRoot "comfyui.db").Replace("\", "/")
$tempPath = Join-Path $ComfyRoot "temp\gpu-4070"
$outputPath = Join-Path $ComfyRoot "output\gpu-4070"
$runtimeRoot = Join-Path $repoRoot "local\dual-comfy"

function Get-ComfyDeviceName {
    try {
        $stats = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/system_stats" -TimeoutSec 2
        return [string](@($stats.devices)[0].name)
    }
    catch {
        return $null
    }
}

foreach ($requiredFile in @($pythonPath, $mainPath)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required ComfyUI file was not found: $requiredFile"
    }
}

$gpuRows = @(& nvidia-smi --query-gpu=uuid,name --format=csv,noheader)
if ($LASTEXITCODE -ne 0) {
    throw "nvidia-smi could not enumerate GPUs."
}
$gpuMatch = @($gpuRows | Where-Object { $_ -like "$expectedGpuUuid,*$expectedGpuName*" })
if ($gpuMatch.Count -ne 1) {
    throw "Expected RTX 4070 UUID $expectedGpuUuid was not found. Detected: $($gpuRows -join '; ')"
}

$existingDevice = Get-ComfyDeviceName
if ($existingDevice) {
    if ($existingDevice -notlike "*$expectedGpuName*") {
        throw "Port $Port is already serving '$existingDevice', not the RTX 4070."
    }
    Write-Host "RTX 4070 ComfyUI is already ready at http://127.0.0.1:$Port [$existingDevice]"
    exit 0
}

$workflowParent = Join-Path $userRoot "default\workflows"
$workflowLink = Join-Path $workflowParent "Mitch"
New-Item -ItemType Directory -Path $workflowParent, $tempPath, $outputPath, $runtimeRoot -Force | Out-Null
$workflowLibrary = Initialize-ComfyWorkflowLibrary -RepoRoot $repoRoot
Ensure-ComfyWorkflowEntry -Path $workflowLink -LibraryRoot $workflowLibrary

$arguments = @(
    $mainPath,
    "--cuda-device", $expectedGpuUuid,
    "--port", [string]$Port,
    "--disable-auto-launch",
    "--user-directory", $userRoot,
    "--database-url", "sqlite:///$databasePath",
    "--temp-directory", $tempPath,
    "--output-directory", $outputPath,
    "--reserve-vram", [string]$ReserveVramGb
)
if ($LowVram) {
    $arguments += "--lowvram"
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$stdoutPath = Join-Path $runtimeRoot "rtx-4070-$stamp.stdout.log"
$stderrPath = Join-Path $runtimeRoot "rtx-4070-$stamp.stderr.log"
$process = Start-Process `
    -FilePath $pythonPath `
    -ArgumentList $arguments `
    -WorkingDirectory $ComfyRoot `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Starting only RTX 4070 ComfyUI on port $Port (PID $($process.Id))."
$deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
$deviceName = $null
while ([DateTime]::UtcNow -lt $deadline) {
    if ($process.HasExited) {
        break
    }
    $deviceName = Get-ComfyDeviceName
    if ($deviceName) {
        break
    }
    Start-Sleep -Milliseconds 1000
    $process.Refresh()
}

if (-not $deviceName) {
    $stderrTail = if (Test-Path -LiteralPath $stderrPath) {
        (Get-Content -LiteralPath $stderrPath -Tail 40) -join [Environment]::NewLine
    }
    else {
        "No stderr log was created."
    }
    throw "RTX 4070 ComfyUI did not become ready. Log: $stderrPath`n$stderrTail"
}
if ($deviceName -notlike "*$expectedGpuName*") {
    throw "Port $Port started on unexpected device '$deviceName'."
}

Write-Host "RTX 4070 ComfyUI ready at http://127.0.0.1:$Port [$deviceName]"
Write-Host "No prompt was submitted and no image was generated."
