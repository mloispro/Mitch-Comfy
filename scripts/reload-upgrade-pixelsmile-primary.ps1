[CmdletBinding()]
param([switch]$Execute)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskComfy = 'C:\projects\AI-Tools\ComfyUI'
$taskPython = Join-Path $taskComfy '.venv\Scripts\python.exe'
$taskNode = Join-Path $taskRoot 'custom_nodes\ComfyUI-AIToolkit-Training\pixelsmile_experiment.py'
if ((Get-FileHash -LiteralPath $taskNode).Hash -ne '1774A79E93E25FADF7B97BB54AACC97858AEA1D5CC5D5E0E05F7F28E31A08F60') { throw 'Untested node changed.' }
function Get-TaskIdle {
    $result = & $taskPython -c "import sys,runpy,pathlib,json; sys.path.insert(0,'scripts'); g=runpy.run_path('scripts/run-upgrade-dev-high.py'); s=g['idle_snapshot'](pathlib.Path('work/upgrade-source-faithful-20260903/background-detail-house-scene-reference')); assert all(not w.get('running') and not w.get('pending') for w in s['workers']); print(json.dumps(s))"
    if ($LASTEXITCODE -ne 0) { throw 'Owned terminal / GPU / queue validation failed.' }
    return ($result | ConvertFrom-Json)
}
function Get-TaskPrimary {
    $taskPids = @((Get-NetTCPConnection -LocalPort 8188 -State Listen).OwningProcess | Select-Object -Unique)
    if ($taskPids.Count -ne 1) { throw 'Ambiguous primary listener.' }
    $taskProc = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskPids[0])"
    if ($taskProc.CommandLine -notmatch [regex]::Escape((Join-Path $taskComfy 'main.py')) -or
        $taskProc.CommandLine -notmatch '--port 8188(?:\s|$)' -or
        $taskProc.CommandLine -notmatch '--cuda-device GPU-c2ca4516-2c9f-e87b-3a20-f459947ddb17(?:\s|$)') { throw 'Wrong worker.' }
    return $taskProc
}
$taskBefore = Get-TaskIdle
$taskPrimary = Get-TaskPrimary
$taskSecondary = @((Get-NetTCPConnection -LocalPort 8189 -State Listen).OwningProcess | Select-Object -Unique)
$taskArgs = @((Join-Path $taskComfy 'main.py'),'--cuda-device','GPU-c2ca4516-2c9f-e87b-3a20-f459947ddb17','--port','8188','--disable-auto-launch')
$taskStats = Invoke-RestMethod 'http://127.0.0.1:8188/system_stats'
if (($taskStats.system.argv -join '|') -cne ($taskArgs -join '|')) { throw 'Unexpected launch flags.' }
$taskAudit = [ordered]@{purpose='Expose isolated user-authorized PixelSmile experiment';before=$taskBefore;primary_pid=$taskPrimary.ProcessId;secondary_pids=$taskSecondary;production_graph_changed=$false}
if (-not $Execute) { $taskAudit | ConvertTo-Json -Depth 15; exit 0 }
$taskOutput = Join-Path $taskRoot ('work\upgrade-source-faithful-20260903\pixelsmile-reload-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (Test-Path -LiteralPath $taskOutput) { throw 'Preserve previous reload evidence.' }
New-Item -ItemType Directory -Path $taskOutput | Out-Null
[IO.File]::WriteAllText((Join-Path $taskOutput 'intent.json'),($taskAudit | ConvertTo-Json -Depth 20))
$taskRecheck = Get-TaskIdle
$taskConfirmed = Get-TaskPrimary
if ($taskConfirmed.ProcessId -ne $taskPrimary.ProcessId -or $taskConfirmed.CreationDate -ne $taskPrimary.CreationDate) { throw 'Worker changed.' }
Stop-Process -Id $taskConfirmed.ProcessId -ErrorAction Stop
$taskOld = Get-Process -Id $taskConfirmed.ProcessId -ErrorAction SilentlyContinue
if ($taskOld -and -not $taskOld.WaitForExit(10000)) { throw 'Old worker still exiting; do not launch a duplicate.' }
$taskLauncher = Start-Process -FilePath $taskPython -ArgumentList $taskArgs -WorkingDirectory $taskComfy -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskOutput 'primary.stdout.log') -RedirectStandardError (Join-Path $taskOutput 'primary.stderr.log')
$taskDeadline = [DateTime]::UtcNow.AddSeconds(50)
$taskReady = $null
while ([DateTime]::UtcNow -lt $taskDeadline) {
    try { $taskReady = Invoke-RestMethod 'http://127.0.0.1:8188/object_info/AIToolkitPixelSmileProbe' -TimeoutSec 2; if ($taskReady.AIToolkitPixelSmileProbe) { break } } catch {}
    Start-Sleep -Milliseconds 1000
}
if (-not $taskReady.AIToolkitPixelSmileProbe) { throw "Readiness unresolved: inspect existing process/logs at $taskOutput, never restart blindly." }
$taskAfterSecondary = @((Get-NetTCPConnection -LocalPort 8189 -State Listen).OwningProcess | Select-Object -Unique)
if (($taskSecondary -join ',') -ne ($taskAfterSecondary -join ',')) { throw 'Secondary identity changed externally.' }
$taskAudit['new_primary_pid'] = (Get-TaskPrimary).ProcessId
$taskAudit['secondary_unchanged'] = $true
$taskAudit['launcher_pid'] = $taskLauncher.Id
$taskAudit['audit_directory'] = $taskOutput
[IO.File]::WriteAllText((Join-Path $taskOutput 'result.json'),($taskAudit | ConvertTo-Json -Depth 20))
$taskAudit | ConvertTo-Json -Depth 15
