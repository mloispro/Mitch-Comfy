param([switch]$Capture)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'fresh.ps1') -DefinitionsOnly
$taskEvidencePath=Join-Path $PackageRoot 'desktop-parent-evidence-20260908.json'
$taskEvidenceSha='6DB95A535879701647228C5271948EE01FD353640730C4D2659EF7E3BF1776C0'
if((Get-FileHash -LiteralPath $taskEvidencePath).Hash -cne $taskEvidenceSha){throw 'Exact parent evidence changed.'}
$taskEvidence=Get-Content -LiteralPath $taskEvidencePath -Raw|ConvertFrom-Json -DateKind String
$taskPriorPath=Join-Path $PackageRoot 'wddm-candidate-v3.json'
if((Get-FileHash -LiteralPath $taskPriorPath).Hash -cne 'A83F7325972CA5393BFA8C12ADFF149DB42BC095BB2E5F208A848B40837EFC51'){throw 'Original20 candidate changed.'}
$taskPrior=Get-Content -LiteralPath $taskPriorPath -Raw|ConvertFrom-Json -DateKind String
# Original complete capture command still supplies the previously reviewed lifetimes.
$taskOld=(& (Get-FreshCommand 'wddm-lifetimes-v3.ps1'))|ConvertFrom-Json -DateKind String
$taskLive=@(Get-CimInstance Win32_Process -Filter 'ProcessId=2012 OR ProcessId=39712 OR ProcessId=14796 OR ProcessId=54788' -ErrorAction Stop)
$taskNew=@(foreach($taskExpected in $taskEvidence.processes){
 $taskP=@($taskLive|Where-Object ProcessId -eq $taskExpected.pid)
 if($taskP.Count -ne 1){throw 'Required exact new desktop/parent is missing or ambiguous.'}
 $taskP=$taskP[0];$taskArgs=$null
 if($taskP.CommandLine){$taskArgs=@(Split-WindowsArgv $taskP.CommandLine)}
 [pscustomobject][ordered]@{pid=[int]$taskP.ProcessId;parent_pid=[int]$taskP.ParentProcessId;name=[string]$taskP.Name;creation_utc=(Convert-UtcInstant $taskP.CreationDate).ToString('o');executable_path=$taskP.ExecutablePath;argv=$taskArgs}
})
$taskRows=@($taskOld.processes|Where-Object pid -in @($taskPrior.processes.pid))
if($taskRows.Count -ne 20){throw 'Original20 desktop lifetime capture incomplete.'}
foreach($taskRow in @($taskNew|Where-Object pid -in @(39712,54788))){
 $taskRow|Add-Member -NotePropertyName matches_prior_lifetime -NotePropertyValue $false
 $taskRow|Add-Member -NotePropertyName review_basis -NotePropertyValue 'explicit_new_lifetime'
 $taskRows+= $taskRow
}
$taskReceipt=[ordered]@{captured_utc=[DateTime]::UtcNow.ToString('o');scope='GROUP_FRESH_V2_DESKTOP_CANDIDATE';approved=$false;
 prior_candidate_sha256=(Get-FileHash -LiteralPath $taskPriorPath).Hash;parent_evidence_sha256=$taskEvidenceSha;
 wddm_helper_sha256=(Get-FileHash -LiteralPath (Join-Path $PackageRoot 'wddm_admission_v2.py')).Hash;
 processes=$taskRows;parents=@($taskNew|Where-Object pid -in @(2012,14796));new_or_reused_pids_are_not_authorized=$true}
if($Capture){
 $taskReceipt.nvml_pids=@(& nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits|ForEach-Object {[int]$_.Trim()})
 if($LASTEXITCODE -ne 0){throw 'GPU process inventory failed.'}
 $taskOutput=Join-Path $PackageRoot 'wddm-candidate-v2.json'
 if(Test-Path -LiteralPath $taskOutput){throw 'Preserve existing candidate; no overwrite.'}
 Save-Json $taskReceipt $taskOutput;Write-Output $taskOutput
}else{$taskReceipt|ConvertTo-Json -Depth 30 -Compress}
