[CmdletBinding()]
param(
    [int]$NineSceneProcessId = 33368,
    [int]$TimeoutHours = 14
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runRoot = Join-Path $repoRoot "work\flux2-klein9b-identity-v3-r32-dop"
$completionPath = Join-Path $runRoot "nine-scene-completion.json"
$auditScript = Join-Path $PSScriptRoot "audit-flux2-klein9b-v3-r32-dop.ps1"
$started = Get-Date

Write-Host "Waiting for nine-scene process PID $NineSceneProcessId."
while (Get-Process -Id $NineSceneProcessId -ErrorAction SilentlyContinue) {
    if (((Get-Date) - $started).TotalHours -ge $TimeoutHours) {
        throw "Timed out waiting for the nine-scene evaluation."
    }
    Start-Sleep -Seconds 30
}
if (-not (Test-Path -LiteralPath $completionPath -PathType Leaf)) {
    throw "Nine-scene process exited without a completion record."
}
& $auditScript
