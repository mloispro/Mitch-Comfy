param([switch]$VerifyFinalManifest)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'fresh-v2.ps1') -DefinitionsOnly
$taskChecks=0
function Check($Value,[string]$Message){if(!$Value){throw $Message};$script:taskChecks++}
Check ($Action -eq 'verify' -and $DefinitionsOnly) 'Facade caller parameters not restored'
Check ((Get-Command Start-CaseWatch).ScriptBlock.ToString().Contains("'fresh_runtime_v2.py'")) 'New observer not selected'
Check ((Get-Command Assert-GuardReady).ScriptBlock.ToString().Contains("'fresh_runtime.py'")) 'Native registration must remain old'
Check ((Get-ExpectedArgv 8191) -contains (Join-Path $PSScriptRoot 'extra-paths-v3.yaml')) 'Worker argv registration changed'
Check ((Get-ExpectedArgv 8191) -contains '--cache-none') 'Cache-none changed'
Check ((Get-ExpectedArgv 8191) -contains '--disable-dynamic-vram') 'Legacy mode changed'
Check ($MinimumRamBytes -eq 41GB) 'Threshold changed'
Check ((Get-Command Assert-FreshApproval).ScriptBlock.ToString().Contains('supplement_prepared_sha256')) 'Root approval not bound to supplement'
foreach($entry in @('start-worker.ps1','run-case.ps1','stop-worker.ps1','interrupt-owned.ps1')){
 $command=Get-FreshCommand $entry
 Check ($command.File -ceq (Join-Path $PSScriptRoot $entry)) 'Complete command source path changed'
 Check ($command.ToString().Contains('param(')) 'Complete command signature missing'
}
# Actual facade CLI: no exclusive flag must refuse before any live call.
foreach($actionName in @('start','run')){
 $caught=$false
 try{& (Join-Path $PSScriptRoot 'fresh-v2.ps1') -Action $actionName}catch{$caught=$_.Exception.Message -match 'Explicit exclusive'}
 Check $caught 'Actual Action was clobbered by original param block'
}
if($VerifyFinalManifest){
 $result=& (Join-Path $PSScriptRoot 'fresh-v2.ps1') -Action verify
 Check (($result -join "`n").Contains('All original and supplemental pins verified')) 'Actual verify silently returned before dispatch'
}
Write-Output "PASS $taskChecks v2 facade checks; no live probes, generation or approval/capture writes."
