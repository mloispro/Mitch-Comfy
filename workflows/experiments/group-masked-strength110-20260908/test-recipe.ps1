$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'run_recipe.ps1') -DefinitionsOnly
$taskChecks=0
function Check($Value,[string]$Message){if(!$Value){throw $Message};$script:taskChecks++}
Check ($PackageRoot -ceq $PSScriptRoot) 'Wrong fresh package'
Check ($WorkerRoot -ceq (Join-Path $PSScriptRoot 'worker')) 'Wrong fresh worker'
Check ($MinimumRamBytes -eq 41GB) 'RAM threshold changed'
Check (@(Get-FixedCases).Count -eq 1) 'Only pilot permitted'
Check ((Get-FixedCases)[0].payload_sha256 -ceq 'DFE5EDBF8205188C6DA053FE74C747A234D050DA0889D44017A610ACE8657CD1') 'Payload changed'
Check ((Get-ExpectedArgv 8191) -contains (Join-Path $PSScriptRoot 'extra-paths-v3.yaml')) 'Wrong private registration route'
Check ((Get-ExpectedArgv 8191) -contains '--cache-none') 'Cache mode changed'
Check ((Get-ExpectedArgv 8191) -contains '--disable-dynamic-vram') 'Legacy mode changed'
Check ((Get-Command Assert-Admission).ScriptBlock.ToString().Contains('41GB')) 'Admission changed'
Check ((Get-Command Start-CaseWatch).ScriptBlock.ToString().Contains("'--watch'")) 'Watcher missing mode'
Check ((Get-Command Start-CaseWatch).ScriptBlock.ToString().Contains("'recipe_runtime.py'")) 'Watcher route wrong'
Check ((Get-Command Assert-GuardReady).ScriptBlock.ToString().Contains("'recipe_runtime.py'")) 'Guard hash route wrong'
Check ((Get-Command Assert-WatchHealthy).ScriptBlock.ToString().Contains('-Action interrupt')) 'Stale watch interrupt route'
Check (Test-GraphEqual ([pscustomobject]@{n=1}) ([pscustomobject]@{n=1.0})) 'Numeric semantic equivalence failed'
Check (!(Test-GraphEqual ([pscustomobject]@{n=1}) ([pscustomobject]@{n=$true}))) 'Bool equal to number'
foreach($taskEntry in @('start-worker.ps1','run-case.ps1','stop-worker.ps1','interrupt-owned.ps1','wddm-lifetimes-v3.ps1')){
 $taskCmd=Get-FreshCommand $taskEntry
 Check (!$taskCmd.ToString().Contains(". (Join-Path `$PSScriptRoot 'runtime-common-v3.ps1')")) 'Nested frozen lifetime import survived'
 Check ($taskCmd.File -ceq (Join-Path $PSScriptRoot $taskEntry)) 'Assembled command has wrong script root'
}
Check ((Get-FreshCommand 'run-case.ps1').ToString().Contains('$watchDeadline=[DateTime]::UtcNow.AddSeconds(30)')) 'Terminal join changed'
Check (!(Get-FreshCommand 'stop-worker.ps1').ToString().Contains('Get-TerminalCases $owned -RequireAny')) 'Cannot stop unused ready worker'
# Exercise the actual CLI bodies before their explicit exclusive-window barrier.
function Snapshot {throw 'TEST FORBIDS live snapshot'}
function Start-Process {throw 'TEST FORBIDS process launch'}
function Invoke-RestMethod {throw 'TEST FORBIDS network'}
foreach($taskEntry in @('start-worker.ps1','run-case.ps1','stop-worker.ps1')){
 $taskCaught=$false
 try {
  if($taskEntry -eq 'run-case.ps1'){ & (Get-FreshCommand $taskEntry) -Case pilot -Name ready-amber-hook-pilot }
  else { & (Get-FreshCommand $taskEntry) }
 }catch{$taskCaught=$_.Exception.Message -match '(exclusive|Exclusive)'}
 Check $taskCaught 'Actual entry did not refuse before live work'
}
# Old archived IDs must not be accepted as live history on the fresh server.
$taskHistoryMode='empty'
function Invoke-RestMethod([string]$Uri){
 if($Uri -notmatch '/history'){throw 'TEST FORBIDS non-history API'}
 if($taskHistoryMode -eq 'empty'){return [pscustomobject]@{}}
 return [pscustomobject]@{'9dd2aab3-2000-4e6e-aeb2-38ce2567b8d4'=[pscustomobject]@{}}
}
$taskTerminal=Get-TerminalCases ([pscustomobject]@{})
Check (@($taskTerminal.records).Count -eq 0 -and $null -eq $taskTerminal.latest) 'Fresh history not empty'
$taskHistoryMode='historical'
$taskCaught=$false
try{Get-TerminalCases ([pscustomobject]@{})|Out-Null}catch{$taskCaught=$_.Exception.Message -match 'Unknown/missing history'}
Check $taskCaught 'Historical control adopted into new worker'
# Full signature regression: tiny owned temp file, no source/evidence overwrite.
$taskDir=Join-Path ([IO.Path]::GetTempPath()) ('group-fresh-contract-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskDir|Out-Null
$taskPath=Join-Path $taskDir 'roundtrip.json'
try{
 Save-Json ([pscustomobject]@{value=73}) $taskPath
 Check ((Get-Content -LiteralPath $taskPath -Raw|ConvertFrom-Json).value -eq 73) 'Save-Json signature regression'
}finally{
 if(Test-Path -LiteralPath $taskPath){Remove-Item -LiteralPath $taskPath}
 Remove-Item -LiteralPath $taskDir
}
Write-Output "PASS $taskChecks offline fresh routing/actual entry/signature checks; no live actions."
