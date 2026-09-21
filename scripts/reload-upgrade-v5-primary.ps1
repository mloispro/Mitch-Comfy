[CmdletBinding()]
param([switch]$Execute)

# Reload this task's tested code, never a cache-management helper for another task.
# The default mode is read-only. Execute targets the verified primary listener only.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$comfy = 'C:\projects\AI-Tools\ComfyUI'
$python = Join-Path $comfy '.venv\Scripts\python.exe'
$previous = Join-Path $root 'work\upgrade-source-faithful-20260903\native-masked-high-source-geometry-house'
$expectedManifest = 'E15287686A84C8ADE7A6D795248D23D21D25FCF6173F43731C8624D26536F80F'
$codePins = @{
    'flux2_klein9b_deterministic_polish.py' = '3F37FD5632D4AE1236314DF795AADDBF73FA55EF74CAE2BAB62C7359A5778676'
    'flux2_klein9b_photo_realism_upgrade.py' = 'DAF621973E8B3EBBC555DADC293E1C74EDC1BA42930D6883616970E1E55DFC24'
    'flux2_klein9b_attractiveness.py' = '0E38B630FEF04272EBBF667EFB81C31E90FBDB8EFF6D503DBF0CE31BAA4502F9'
}
if ((Get-FileHash -LiteralPath (Join-Path $previous 'experiment.json')).Hash -ne $expectedManifest) {
    throw 'Frozen previous native experiment changed.'
}
foreach ($name in $codePins.Keys) {
    $path = Join-Path $root "custom_nodes\ComfyUI-AIToolkit-Training\$name"
    if ((Get-FileHash -LiteralPath $path).Hash -ne $codePins[$name]) { throw "Unreviewed code: $name" }
}

function Get-PrimaryListener {
    $ids = @((Get-NetTCPConnection -LocalPort 8188 -State Listen).OwningProcess | Select-Object -Unique)
    if ($ids.Count -ne 1) { throw 'Ambiguous primary listener.' }
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($ids[0])"
    if ($proc.CommandLine -notmatch [regex]::Escape((Join-Path $comfy 'main.py')) -or
        $proc.CommandLine -notmatch '--port 8188(?:\s|$)' -or
        $proc.CommandLine -notmatch '--cuda-device GPU-c2ca4516-2c9f-e87b-3a20-f459947ddb17(?:\s|$)') {
        throw 'Listener is not the exact expected primary ComfyUI worker.'
    }
    return $proc
}

function Get-OwnedIdleSnapshot {
    Push-Location $root
    try {
        $result = & $python -c "import sys,runpy,pathlib,json; sys.path.insert(0,'scripts'); g=runpy.run_path('scripts/run-upgrade-dev-high.py'); s=g['idle_snapshot'](pathlib.Path('work/upgrade-source-faithful-20260903/native-masked-high-source-geometry-house')); assert all(not w.get('running') and not w.get('pending') for w in s['workers']); print(json.dumps(s))"
        if ($LASTEXITCODE -ne 0) { throw 'Owned-terminal graph / GPU / queue guard failed.' }
        return ($result | ConvertFrom-Json)
    } finally { Pop-Location }
}

$before = Get-OwnedIdleSnapshot
$primary = Get-PrimaryListener
$secondaryIds = @((Get-NetTCPConnection -LocalPort 8189 -State Listen).OwningProcess | Select-Object -Unique)
$stats = Invoke-RestMethod 'http://127.0.0.1:8188/system_stats'
$expectedArgs = @((Join-Path $comfy 'main.py'), '--cuda-device', 'GPU-c2ca4516-2c9f-e87b-3a20-f459947ddb17', '--port', '8188', '--disable-auto-launch')
if (($stats.system.argv -join '|') -cne ($expectedArgs -join '|')) { throw 'Unexpected primary launch flags.' }
$summary = [ordered]@{
    purpose = 'activate CPU-verified ParseNet v5 repair for an actual public-workflow validation'
    mode = $(if ($Execute) {'execute'} else {'read_only_preflight'})
    before = $before
    primary_pid = $primary.ProcessId
    secondary_listener_pids = $secondaryIds
    code_hashes = $codePins
    argv = $expectedArgs
    does_not_call_free = $true
    does_not_restart_secondary = $true
}
if (-not $Execute) { $summary | ConvertTo-Json -Depth 12; exit 0 }

$run = Join-Path $root ('work\upgrade-source-faithful-20260903\v5-live-reload-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (Test-Path -LiteralPath $run) { throw 'Reload audit folder already exists.' }
New-Item -ItemType Directory -Path $run | Out-Null
$history = Invoke-RestMethod ('http://127.0.0.1:8188/history/' + $before.owned_cache_prompt_id)
[IO.File]::WriteAllText((Join-Path $run 'previous-terminal-history.json'), ($history | ConvertTo-Json -Depth 100))
[IO.File]::WriteAllText((Join-Path $run 'reload-intent.json'), ($summary | ConvertTo-Json -Depth 20))
$secondCheck = Get-OwnedIdleSnapshot
$confirmed = Get-PrimaryListener
if ($confirmed.ProcessId -ne $primary.ProcessId -or $confirmed.CreationDate -ne $primary.CreationDate) {
    throw 'Primary process changed before reload.'
}
Stop-Process -Id $confirmed.ProcessId -ErrorAction Stop
$old = Get-Process -Id $confirmed.ProcessId -ErrorAction SilentlyContinue
if ($old -and -not $old.WaitForExit(10000)) { throw 'Primary did not exit; do not launch a duplicate.' }
$stdout = Join-Path $run 'primary.stdout.log'
$stderr = Join-Path $run 'primary.stderr.log'
$launcher = Start-Process -FilePath $python -ArgumentList $expectedArgs -WorkingDirectory $comfy `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
$deadline = [DateTime]::UtcNow.AddSeconds(55)
$ready = $null
while ([DateTime]::UtcNow -lt $deadline) {
    try { $ready = Invoke-RestMethod 'http://127.0.0.1:8188/system_stats' -TimeoutSec 2; break } catch {}
    Start-Sleep -Milliseconds 1000
}
if (-not $ready) { throw "Primary readiness not yet confirmed. Inspect existing process/log, do not restart again: $stderr" }
if ($ready.devices[0].name -notmatch '3090') { throw 'Wrong primary GPU after reload.' }
$afterPrimary = Get-PrimaryListener
$afterSecondary = @((Get-NetTCPConnection -LocalPort 8189 -State Listen).OwningProcess | Select-Object -Unique)
if (($afterSecondary -join ',') -ne ($secondaryIds -join ',')) { throw 'Secondary identity changed externally; inspect before proceeding.' }
$summary.mode = 'reloaded_pending_public_workflow_validation'
$summary['after_primary_pid'] = $afterPrimary.ProcessId
$summary['launcher_pid'] = $launcher.Id
$summary['secondary_listener_unchanged'] = $true
$summary['audit_directory'] = $run
$summary['stdout'] = $stdout
$summary['stderr'] = $stderr
[IO.File]::WriteAllText((Join-Path $run 'reload-result.json'), ($summary | ConvertTo-Json -Depth 20))
$summary | ConvertTo-Json -Depth 12
