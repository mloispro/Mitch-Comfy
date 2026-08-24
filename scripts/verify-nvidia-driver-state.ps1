[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$expectedDriverVersion = "596.36"
$expectedPolicyPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate"
$requiredGpuUuids = @(
    "GPU-c2ca4516-2c9f-e87b-3a20-f459947ddb17",
    "GPU-de12eec8-4b3d-f2ae-791c-8423a86915fd"
)

$policyValue = (Get-ItemProperty `
    -Path $expectedPolicyPath `
    -Name "ExcludeWUDriversInQualityUpdate" `
    -ErrorAction Stop).ExcludeWUDriversInQualityUpdate
if ($policyValue -ne 1) {
    throw "Windows Update driver exclusion policy is not enabled."
}
Write-Host "PASS  Windows Update driver exclusion policy is enabled."

$gpuRows = @(& nvidia-smi --query-gpu=uuid,name,driver_version,memory.total --format=csv,noheader)
if ($LASTEXITCODE -ne 0) {
    throw "nvidia-smi failed."
}
foreach ($uuid in $requiredGpuUuids) {
    $match = @($gpuRows | Where-Object { $_ -like "$uuid,*" })
    if ($match.Count -ne 1) {
        throw "Required GPU $uuid was not returned by nvidia-smi. Detected: $($gpuRows -join '; ')"
    }
    if ($match[0] -notlike "*$expectedDriverVersion*") {
        throw "GPU $uuid is not using expected unified driver ${expectedDriverVersion}: $($match[0])"
    }
    Write-Host "PASS  $($match[0])"
}

$displayDevices = @(& pnputil.exe /enum-devices /class Display 2>&1)
if ($LASTEXITCODE -ne 0) {
    throw "pnputil could not enumerate display devices."
}
foreach ($gpuName in @("NVIDIA GeForce RTX 3090", "NVIDIA GeForce RTX 4070")) {
    $index = [Array]::IndexOf($displayDevices, "Device Description:         $gpuName")
    if ($index -lt 0) {
        throw "$gpuName is missing from Windows display devices."
    }
    $deviceBlock = ($displayDevices[$index..([Math]::Min($index + 12, $displayDevices.Count - 1))] -join [Environment]::NewLine)
    if ($deviceBlock -notmatch "Status:\s+Started") {
        throw "$gpuName is present but not started.`n$deviceBlock"
    }
    Write-Host "PASS  $gpuName is started without a PnP problem."
}

Write-Host "NVIDIA repair verified. It is safe to resume the interrupted Inline Studio run."
