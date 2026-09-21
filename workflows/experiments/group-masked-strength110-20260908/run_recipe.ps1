param(
 [ValidateSet('verify','start','run','stop','interrupt','wddm','capture')][string]$Action='verify',
 [switch]$ExclusiveWindowAccepted,[switch]$Resume,[string]$Run,[string]$Reason,
 [switch]$DefinitionsOnly
)
$ErrorActionPreference='Stop'
$FreshRoot=$PSScriptRoot
$Recipe=Get-Content -LiteralPath (Join-Path $FreshRoot 'recipe.json') -Raw|ConvertFrom-Json -DateKind String
$PayloadSha=[string]$Recipe.payload_sha256
$FrozenRoot='C:\projects\AI-Tools\Mitch-Comfy\work\9b-readiness-resume-20260907\group-identity-hook-gate\runtime-3090'
foreach($taskPin in @(
 @('runtime-common-v3.ps1','859286A90BDD43795D7EF819C88B307949A7BEF9614E3E02BA18348EF3867749'),
 @('reviewed-command-v3.ps1','1C47E167D44B9841FF578C5A726591BEEEF59DCE74B6C06E4FCCB7E9356326B8'))){
 if((Get-FileHash -LiteralPath (Join-Path $FrozenRoot $taskPin[0])).Hash -cne $taskPin[1]){throw 'Frozen facade source drift.'}
}
# Existing V3 imports already preserve complete function signatures. No probes.
. (Join-Path $FrozenRoot 'runtime-common-v3.ps1')
. (Join-Path $FrozenRoot 'reviewed-command-v3.ps1')
$FreshCommands=@{}
foreach($taskEntry in @('start-worker.ps1','run-case.ps1','stop-worker.ps1','interrupt-owned.ps1')){
 $taskText=(Get-V3Command $taskEntry).ToString()
 $taskBefore=". (Join-Path `$PSScriptRoot 'runtime-common-v3.ps1')"
 if([regex]::Matches($taskText,[regex]::Escape($taskBefore)).Count -ne 1){throw 'Fresh nested import anchor differs.'}
 $taskText=$taskText.Replace($taskBefore,'# Exact reviewed definitions are already imported by run_recipe.ps1.')
 if($taskEntry -ceq 'run-case.ps1'){
  $taskBefore='$watchDeadline=[DateTime]::UtcNow.AddSeconds(5)'
  if([regex]::Matches($taskText,[regex]::Escape($taskBefore)).Count -ne 1){throw 'Reviewed terminal join anchor differs.'}
  $taskText=$taskText.Replace($taskBefore,'$watchDeadline=[DateTime]::UtcNow.AddSeconds(30)')
 }
 if($taskEntry -ceq 'stop-worker.ps1'){
  # Fresh admission may fail before a prompt. Exact owned lifetime + empty full
  # history/queues is sufficient to stop ONLY this disposable ready worker.
  $taskBefore='$terminal=Get-TerminalCases $owned -RequireAny'
  if([regex]::Matches($taskText,[regex]::Escape($taskBefore)).Count -ne 1){throw 'Stop terminal anchor differs.'}
  $taskText=$taskText.Replace($taskBefore,'$terminal=Get-TerminalCases $owned')
 }
 $FreshCommands[$taskEntry]=$taskText
}
$taskWddm=Get-Content -LiteralPath (Join-Path $FrozenRoot 'wddm-lifetimes-v3.ps1') -Raw
$taskBefore=". (Join-Path `$PSScriptRoot 'runtime-common-v3.ps1')"
if([regex]::Matches($taskWddm,[regex]::Escape($taskBefore)).Count -ne 1){throw 'Desktop import anchor differs.'}
$FreshCommands['wddm-lifetimes-v3.ps1']=$taskWddm.Replace($taskBefore,'# Exact reviewed definitions are already imported by run_recipe.ps1.')

# Separate new recipe graph paths from immutable historical provenance.
$ProvenanceGate=$GateRoot
$GateRoot=$FreshRoot
# Desktop reference capture keeps the historical source root, never the new graph root.
$FreshCommands['wddm-lifetimes-v3.ps1']=$FreshCommands['wddm-lifetimes-v3.ps1'].Replace('(Split-Path $GateRoot -Parent)','(Split-Path $ProvenanceGate -Parent)')
$PackageRoot=$FreshRoot
$WorkerRoot=Join-Path $PackageRoot 'worker'
$NativeOutputRoot=Join-Path $WorkerRoot 'output'
$OwnedPath=Join-Path $WorkerRoot 'owned.json'

function Import-FreshFunction([string]$Name,[object[]]$Deltas){
 $taskTokens=$null;$taskErrors=$null
 $taskAst=[Management.Automation.Language.Parser]::ParseFile((Join-Path $FrozenRoot 'runtime-common.ps1'),[ref]$taskTokens,[ref]$taskErrors)
 $taskDefs=@($taskAst.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $Name},$true))
 if($taskErrors.Count -or $taskDefs.Count -ne 1){throw 'Fresh function source differs.'}
 $taskText=$taskDefs[0].Extent.Text
 foreach($taskDelta in $Deltas){
  if([regex]::Matches($taskText,[regex]::Escape($taskDelta[0])).Count -ne $taskDelta[2]){throw ('Fresh function route differs: '+$Name)}
  $taskText=$taskText.Replace($taskDelta[0],$taskDelta[1])
 }
 # Complete declaration, not Body: Save-Json/other signature arguments survive.
 $taskText='function script:'+$taskText.Substring('function '.Length)
 . ([scriptblock]::Create($taskText))
}
Import-FreshFunction 'Assert-GuardReady' @(
 ,@("'guard_runtime.py'","'recipe_runtime.py'",1))
Import-FreshFunction 'Start-CaseWatch' @(
 @("'watch_case.py'","'recipe_runtime.py'",1),
 @("'--case',`$Case","'--watch','--case',`$Case",1))
Import-FreshFunction 'Assert-WatchHealthy' @(
 ,@("& (Join-Path `$PackageRoot 'interrupt-owned.ps1') -Run", "& (Join-Path `$PackageRoot 'run_recipe.ps1') -Action interrupt -Run",1))

function Get-FixedCases {
 return @([pscustomobject]@{key='pilot';run_name='ready-amber-hook-pilot';
  payload_path=(Join-Path $GateRoot 'amber-hook-pilot-payload.json');
  payload_sha256=$PayloadSha})
}
function Assert-PackagePins {
 $taskResult=& $CpuPython -X utf8 -B (Join-Path $PackageRoot 'recipe_runtime.py') --verify
 if($LASTEXITCODE -ne 0){throw "Fresh/historical pin verification failed: $taskResult"}
}
function Get-HostMemory {
 $taskResult=& $CpuPython -X utf8 -B (Join-Path $PackageRoot 'recipe_runtime.py') --memory
 if($LASTEXITCODE -ne 0){throw 'Native host counter failed.'}
 return $taskResult|ConvertFrom-Json -DateKind String
}
function Assert-FreshApproval([switch]$RequireOwned){
 $taskApproval=Get-Content -LiteralPath (Join-Path $PackageRoot 'root-approval.json') -Raw|ConvertFrom-Json -DateKind String
 $taskNow=[DateTimeOffset]::UtcNow
 if($taskApproval.approved -ne $true -or $taskApproval.scope -cne 'ONE_FRESH_OWNED_GROUP_PILOT' -or
  $taskApproval.prepared_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $PackageRoot 'prepared.json')).Hash -or
  $taskApproval.supplement_prepared_sha256 -cne $taskApproval.prepared_sha256 -or
  $taskApproval.recipe_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $PackageRoot 'recipe.json')).Hash -or
  $taskApproval.parent_prepared_sha256 -cne $Recipe.parent_prepared_sha256 -or
  $taskApproval.parent_image_sha256 -cne $Recipe.parent_image_sha256 -or
  [IO.Path]::GetFullPath($taskApproval.worker_root) -cne $WorkerRoot -or
  $taskApproval.payload_sha256 -cne $PayloadSha -or
  $taskApproval.prior_stop_sha256 -cne 'BBBDB52FED8492E66DFB35F00C8F8EE5236F4800B8BCDB9C9B03F87C4B55ABD2' -or
  $taskApproval.interrupted_archive_sha256 -cne '6B27867387726B5493E1E39561FE907624B093C18FBEDA714625D9ABD98CB152' -or
  $taskApproval.control_image_sha256 -cne 'E6FB94C1944494EA5EDB4666AF7B00387D2680AADC8DC8AF5C9D78E8F7FCF739' -or
  (Convert-UtcInstant $taskApproval.issued_utc) -gt $taskNow -or
  (Convert-UtcInstant $taskApproval.expires_utc) -lt $taskNow){throw 'No current exact fresh-lifetime root approval.'}
 if($RequireOwned -and $taskApproval.worker_owned_sha256 -cne (Get-FileHash -LiteralPath $OwnedPath).Hash){throw 'Fresh approval is not bound to this actual worker.'}
}
function Assert-PriorRelease($Terminal,$Owned){
 # Historical control/interruption were on a STOPPED lifetime. They remain
 # hash-pinned offline, never inserted into this server's empty live history.
 if(@($Terminal.records).Count -ne 0 -or $null -ne $Terminal.latest){throw 'Only first fixed pilot on this fresh worker is authorized.'}
 Assert-FreshApproval -RequireOwned
 Assert-GuardReady $Owned
}
function Get-FreshCommand([string]$Entry){
 if(!$FreshCommands.ContainsKey($Entry)){throw 'Unknown fresh command.'}
 $taskTokens=$null;$taskErrors=$null
 $taskAst=[Management.Automation.Language.Parser]::ParseInput($FreshCommands[$Entry],(Join-Path $PackageRoot $Entry),[ref]$taskTokens,[ref]$taskErrors)
 if($taskErrors.Count){throw ($taskErrors|Out-String)}
 return $taskAst.GetScriptBlock()
}
if($DefinitionsOnly){return} # CPU test import: no probe, write, worker or API action.
if($Action -eq 'verify'){Assert-PackagePins;Write-Output 'Fresh pilot pins verified; no live actions.';return}
if($Action -in @('start','run')){
 if(!$ExclusiveWindowAccepted){throw 'Explicit exclusive experiment window required.'}
 Assert-PackagePins
 Assert-FreshApproval -RequireOwned:($Action -eq 'run')
}
switch($Action){
 'start' { & (Get-FreshCommand 'start-worker.ps1') -ExclusiveWindowAccepted:$ExclusiveWindowAccepted }
 'run' { & (Get-FreshCommand 'run-case.ps1') -Case pilot -Name ready-amber-hook-pilot -GraphFile (Join-Path $GateRoot 'amber-hook-pilot-payload.json') -Resume:$Resume -ExclusiveWindowAccepted:$ExclusiveWindowAccepted }
 'stop' { & (Get-FreshCommand 'stop-worker.ps1') -ExclusiveWindowAccepted:$ExclusiveWindowAccepted }
 'interrupt' { & (Get-FreshCommand 'interrupt-owned.ps1') -Run $Run -Reason $Reason }
 'wddm' { & (Join-Path $PackageRoot 'wddm-lifetimes.ps1') }
 'capture' { Assert-PackagePins; & (Join-Path $PackageRoot 'wddm-lifetimes.ps1') -Capture }
}
