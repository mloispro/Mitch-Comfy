param([ValidateSet('verify','start','run','stop','interrupt','wddm','capture')][string]$Action='verify',
 [switch]$ExclusiveWindowAccepted,[switch]$Resume,[string]$Run,[string]$Reason,[switch]$DefinitionsOnly)
$ErrorActionPreference='Stop'
$V2Invocation=@{Action=$Action;ExclusiveWindowAccepted=$ExclusiveWindowAccepted;Resume=$Resume;Run=$Run;Reason=$Reason;DefinitionsOnly=$DefinitionsOnly}
if((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'fresh.ps1')).Hash -cne 'F4902FF8338C4F772BC0009CB063578698B888307C709D08BC2687F394C13560'){throw 'Original fresh facade changed.'}
. (Join-Path $PSScriptRoot 'fresh.ps1') -DefinitionsOnly
$Action=$V2Invocation.Action;$ExclusiveWindowAccepted=$V2Invocation.ExclusiveWindowAccepted;$Resume=$V2Invocation.Resume
$Run=$V2Invocation.Run;$Reason=$V2Invocation.Reason;$DefinitionsOnly=$V2Invocation.DefinitionsOnly
# Original worker argv, native registration, GuardReady and ALL command bodies remain.
Import-FreshFunction 'Start-CaseWatch' @(
 @("'watch_case.py'","'fresh_runtime_v2.py'",1),@("'--case',`$Case","'--watch','--case',`$Case",1))
$script:OriginalFreshApproval=(Get-Command Assert-FreshApproval).ScriptBlock
function Assert-FreshApproval([switch]$RequireOwned){
 & $script:OriginalFreshApproval -RequireOwned:$RequireOwned
 $taskApproval=Get-Content -LiteralPath (Join-Path $PackageRoot 'root-approval.json') -Raw|ConvertFrom-Json -DateKind String
 if($taskApproval.supplement_prepared_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $PackageRoot 'prepared-v2.json')).Hash){throw 'Root approval does not bind exact desktop supplement.'}
}
function Assert-PackagePins {
 $taskResult=& $CpuPython -X utf8 -B (Join-Path $PackageRoot 'fresh_runtime_v2.py') --verify
 if($LASTEXITCODE -ne 0){throw "Supplement/original verification failed: $taskResult"}
}
if($DefinitionsOnly){return}
if($Action -eq 'verify'){Assert-PackagePins;Write-Output 'All original and supplemental pins verified; no live actions.';return}
if($Action -in @('start','run')){
 if(!$ExclusiveWindowAccepted){throw 'Explicit exclusive experiment window required.'}
 Assert-PackagePins;Assert-FreshApproval -RequireOwned:($Action -eq 'run')
}
switch($Action){
 'start'{& (Get-FreshCommand 'start-worker.ps1') -ExclusiveWindowAccepted:$ExclusiveWindowAccepted}
 'run'{& (Get-FreshCommand 'run-case.ps1') -Case pilot -Name ready-amber-hook-pilot -GraphFile (Join-Path $GateRoot 'amber-hook-pilot-payload.json') -Resume:$Resume -ExclusiveWindowAccepted:$ExclusiveWindowAccepted}
 'stop'{& (Get-FreshCommand 'stop-worker.ps1') -ExclusiveWindowAccepted:$ExclusiveWindowAccepted}
 'interrupt'{& (Get-FreshCommand 'interrupt-owned.ps1') -Run $Run -Reason $Reason}
 'wddm'{& (Join-Path $PackageRoot 'wddm-lifetimes-v2.ps1')}
 'capture'{Assert-PackagePins;& (Join-Path $PackageRoot 'wddm-lifetimes-v2.ps1') -Capture}
}
