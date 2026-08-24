#Requires -RunAsAdministrator
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$badDriver = "oem3.inf"
$badVersion = "32.0.15.6094"
$goodDriver = "oem54.inf"
$goodVersion = "32.0.15.9636"
$rtx4070Instance = "PCI\VEN_10DE&DEV_2786&SUBSYS_51371462&REV_A1\8&2be10feb&0&000800000012"
$rtx3090Instance = "PCI\VEN_10DE&DEV_2204&SUBSYS_87AF1043&REV_A1\4&1babdf5b&0&0009"
$policyPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate"
$logRoot = Join-Path (Split-Path -Parent $PSScriptRoot) "local\gpu-recovery"
$logPath = Join-Path $logRoot ("repair-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

function Invoke-PnpUtil {
    param([Parameter(Mandatory)][string[]]$Arguments)

    $output = @(& pnputil.exe @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    $output | ForEach-Object { Write-Host $_ }
    if ($exitCode -ne 0) {
        throw "pnputil failed with exit code ${exitCode}: $($Arguments -join ' ')"
    }
    return ($output -join [Environment]::NewLine)
}

function Assert-Contains {
    param(
        [Parameter(Mandatory)][string]$Text,
        [Parameter(Mandatory)][string]$Expected,
        [Parameter(Mandatory)][string]$FailureMessage
    )

    if ($Text -notmatch [regex]::Escape($Expected)) {
        throw $FailureMessage
    }
}

New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
Start-Transcript -LiteralPath $logPath -Force | Out-Null
try {
    Write-Host "Validating the exact diagnosed NVIDIA package state ..."
    $displayDrivers = Invoke-PnpUtil -Arguments @("/enum-drivers", "/class", "Display")
    Assert-Contains -Text $displayDrivers -Expected $badDriver -FailureMessage "Expected bad package $badDriver is no longer installed. Aborting without changes."
    Assert-Contains -Text $displayDrivers -Expected $badVersion -FailureMessage "Package $badDriver is not expected version $badVersion. Aborting without changes."
    Assert-Contains -Text $displayDrivers -Expected $goodDriver -FailureMessage "Recovery package $goodDriver is missing. Aborting without changes."
    Assert-Contains -Text $displayDrivers -Expected $goodVersion -FailureMessage "Recovery package $goodDriver is not expected version $goodVersion. Aborting without changes."

    $rtx4070State = Invoke-PnpUtil -Arguments @("/enum-devices", "/instanceid", $rtx4070Instance, "/drivers")
    $rtx3090State = Invoke-PnpUtil -Arguments @("/enum-devices", "/instanceid", $rtx3090Instance, "/drivers")
    if ($rtx4070State -notmatch "(?m)^Driver Name:\s+$([regex]::Escape($badDriver))\s*$") {
        throw "RTX 4070 is no longer bound to $badDriver. Aborting without changes."
    }
    if ($rtx3090State -notmatch "(?m)^Driver Name:\s+$([regex]::Escape($goodDriver))\s*$") {
        throw "RTX 3090 is no longer assigned $goodDriver. Aborting without changes."
    }
    Assert-Contains -Text $rtx3090State -Expected "Problem Code:               31" -FailureMessage "RTX 3090 is no longer in diagnosed Code 31 state. Aborting without changes."

    Write-Host "Blocking driver-class updates from Windows Update ..."
    New-Item -Path $policyPath -Force | Out-Null
    New-ItemProperty `
        -Path $policyPath `
        -Name "ExcludeWUDriversInQualityUpdate" `
        -PropertyType DWord `
        -Value 1 `
        -Force | Out-Null
    $policyValue = (Get-ItemProperty -Path $policyPath -Name "ExcludeWUDriversInQualityUpdate").ExcludeWUDriversInQualityUpdate
    if ($policyValue -ne 1) {
        throw "Windows Update driver exclusion policy did not persist."
    }
    Write-Host "Policy set: ExcludeWUDriversInQualityUpdate=1"

    Write-Host "Stopping Windows Update for this repair session ..."
    Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue

    Write-Host "Removing only the conflicting NVIDIA 560.94 package $badDriver ..."
    Invoke-PnpUtil -Arguments @("/delete-driver", $badDriver, "/uninstall", "/force") | Out-Null

    $driversAfter = Invoke-PnpUtil -Arguments @("/enum-drivers", "/class", "Display")
    if ($driversAfter -match [regex]::Escape($badDriver)) {
        throw "Conflicting package $badDriver is still present after removal."
    }
    Assert-Contains -Text $driversAfter -Expected $goodDriver -FailureMessage "Recovery package $goodDriver disappeared unexpectedly."
    Assert-Contains -Text $driversAfter -Expected $goodVersion -FailureMessage "Recovery package $goodDriver changed unexpectedly."

    Write-Host ""
    Write-Host "REPAIR STAGED SUCCESSFULLY" -ForegroundColor Green
    Write-Host "- Windows Update GPU drivers are excluded by policy."
    Write-Host "- Conflicting NVIDIA package $badDriver ($badVersion) was removed."
    Write-Host "- Unified NVIDIA package $goodDriver ($goodVersion) remains installed."
    Write-Host "- Reboot Windows now, then run scripts\verify-nvidia-driver-state.ps1."
    Write-Host "- Log: $logPath"
}
finally {
    Stop-Transcript | Out-Null
}
