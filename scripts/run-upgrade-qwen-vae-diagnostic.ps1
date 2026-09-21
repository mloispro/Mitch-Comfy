[CmdletBinding()]
param(
    [string]$ReferenceManifest='work/upgrade-source-faithful-20260903/qwen-source-expression-house-fullnative/experiment.json',
    [string]$OutputDirectory='work/upgrade-source-faithful-20260903/qwen-house-vae-diagnostic'
)
$ErrorActionPreference='Stop'
$ProjectRoot=Split-Path -Parent $PSScriptRoot
$Destination=[IO.Path]::GetFullPath((Join-Path $ProjectRoot $OutputDirectory))
if (-not $Destination.StartsWith($ProjectRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Output must stay in project.' }
if (Test-Path -LiteralPath (Join-Path $Destination 'submission.json')) { throw 'Already submitted; poll the saved prompt ID.' }
$ReferenceManifest=[IO.Path]::GetFullPath($ReferenceManifest)
$Reference=Get-Content -LiteralPath $ReferenceManifest -Raw | ConvertFrom-Json -AsHashtable
if ($Reference.stage -ne 'qwen_native_high_edit' -or $Reference.prompt.'160'.class_type -ne 'ImageScale' -or $Reference.prompt.'160'.inputs.crop -ne 'disabled') { throw 'Expected audited whole-frame native Qwen test.' }
$Source=$Reference.references[0]
if ($Reference.prompt.'41'.class_type -ne 'LoadImage' -or $Reference.prompt.'41'.inputs.image -cne $Source.name -or
    $Reference.prompt.'146'.class_type -ne 'VAELoader' -or $Reference.prompt.'146'.inputs.vae_name -cne 'qwen_image_vae.safetensors' -or
    $Reference.prompt.'156'.class_type -ne 'VAEEncode' -or
    ($Reference.prompt.'160'.inputs.image -join ',') -ne '41,0' -or
    ($Reference.prompt.'156'.inputs.pixels -join ',') -ne '160,0' -or
    ($Reference.prompt.'156'.inputs.vae -join ',') -ne '146,0') { throw 'Unsupported reference codec wiring.' }
if ((Get-FileHash -LiteralPath $Source.path).Hash.ToLowerInvariant() -cne $Source.sha256) { throw 'Source bytes changed.' }
$Vae=@($Reference.verified_models | Where-Object { [IO.Path]::GetFileName($_.path) -eq 'qwen_image_vae.safetensors' })
if ($Vae.Count -ne 1 -or $Vae[0].sha256 -cne 'a70580f0213e67967ee9c95f05bb400e8fb08307e017a924bf3441223e023d1f') { throw 'Expected protected Qwen VAE.' }
if ((Get-FileHash -LiteralPath $Vae[0].path).Hash.ToLowerInvariant() -cne $Vae[0].sha256) { throw 'VAE bytes changed.' }
$Workers=foreach ($Port in 8188,8189) {
    $Stats=Invoke-RestMethod "http://127.0.0.1:$Port/system_stats" -TimeoutSec 5
    $Queue=Invoke-RestMethod "http://127.0.0.1:$Port/queue" -TimeoutSec 5
    [pscustomobject]@{port=$Port;device=$Stats.devices[0].name;running=@($Queue.queue_running).Count;pending=@($Queue.queue_pending).Count}
}
$Target=@($Workers | Where-Object port -eq 8188)[0]
if ($Target.device -notmatch 'RTX 3090' -or $Target.running -or $Target.pending) { throw 'Locked 3090 unavailable or active.' }
$Hardware=@(& nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader,nounits)
$Cards=@($Hardware | Where-Object { $_ -match 'RTX 3090' })
if ($Cards.Count -ne 1) { throw 'Cannot identify hardware.' }
$Fields=$Cards[0] -split ',\s*'
if ([int]$Fields[2] -gt 4096 -or [int]$Fields[3] -gt 10) { throw 'Hardware is active or contains unowned cache; preserve it.' }
$Info=Invoke-RestMethod http://127.0.0.1:8188/object_info -TimeoutSec 20
if ('qwen_image_vae.safetensors' -notin $Info.VAELoader.input.required.vae_name[0]) { throw 'VAE not visible to worker.' }
$Graph=[ordered]@{}
foreach ($Id in '41','160','146','156') { $Graph[$Id]=$Reference.prompt[$Id] }
$Graph['158']=@{class_type='VAEDecode';inputs=@{vae=@('146',0);samples=@('156',0)}}
$Prefix='upgrade-source-faithful/'+(Split-Path -Leaf $Destination)
$Graph['9']=@{class_type='SaveImage';inputs=@{images=@('160',0);filename_prefix=$Prefix+'/matched-input'}}
$Graph['10']=@{class_type='SaveImage';inputs=@{images=@('158',0);filename_prefix=$Prefix+'/roundtrip'}}
foreach ($Node in $Graph.Values) { if (-not $Info.($Node.class_type)) { throw "Missing native node $($Node.class_type)" } }
$Manifest=[ordered]@{stage='qwen_vae_diagnostic';purpose='Isolate resize/codec loss from diffusion; no beauty or identity generation';
    reference_manifest=$ReferenceManifest;reference_manifest_sha256=(Get-FileHash -LiteralPath $ReferenceManifest).Hash.ToLowerInvariant();
    source=$Source;vae=$Vae[0];workers=$Workers;hardware=$Hardware;generation_steps=0;production_changed=$false;
    research_gate='docs/upgrade-qwen-high-evaluation-2026-09-03.md';prompt=$Graph}
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$Manifest | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath (Join-Path $Destination 'experiment.json') -Encoding utf8
$Queue=Invoke-RestMethod http://127.0.0.1:8188/queue -TimeoutSec 5
if (@($Queue.queue_running).Count -or @($Queue.queue_pending).Count) { throw 'Queue became busy; preserve it.' }
$Body=@{prompt=$Graph;client_id="upgrade-qwen-codec-$([guid]::NewGuid().ToString('N'))"} | ConvertTo-Json -Depth 25
$Submission=Invoke-RestMethod -Method Post http://127.0.0.1:8188/prompt -ContentType application/json -Body $Body -TimeoutSec 30
$Submission | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $Destination 'submission.json') -Encoding utf8
$Submission | ConvertTo-Json -Depth 12
