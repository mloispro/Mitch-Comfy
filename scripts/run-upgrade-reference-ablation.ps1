[CmdletBinding()]
param(
    [ValidateSet('no_identity','four','source_only')][string]$ReferenceMode = 'no_identity',
    [double]$IdentityStrength = 0.9,
    [ValidateRange(0.0,0.25)][double]$PhoneStyleStrength = 0.25,
    [string]$OutputDirectory = 'work/upgrade-source-faithful-20260903/no-identity-canyon',
    [string]$BaselineReport = 'C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-upgrade-photo-detail-realism-v1\20260903-005704-305944\report.json',
    [string]$SourceName = 'mitch-canyon-source-edit-05333f6f.png',
    [string]$PromptOverride = '',
    [string]$PromptFile = '',
    [string]$NegativePromptFile = '',
    [string]$GuideOverride = '',
    [string]$IdentityReferenceOverride = '',
    [ValidateSet('geometry','expression')][string]$ReferenceTwoRole = 'geometry',
    [string]$AllowOwnedCachePromptId = '',
    [int]$IdentitySplitStep = -1,
    [double]$LateIdentityStrength = 0.9,
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ComfyRoot = 'C:\projects\AI-Tools\ComfyUI'
$Server = 'http://127.0.0.1:8188'
function Get-ComfyImageName([string]$Path) {
    $FullPath = [IO.Path]::GetFullPath($Path)
    foreach ($Kind in 'input','output') {
        $RootPath = (Join-Path $ComfyRoot $Kind) + [IO.Path]::DirectorySeparatorChar
        if ($FullPath.StartsWith($RootPath,[StringComparison]::OrdinalIgnoreCase)) {
            return $FullPath.Substring($RootPath.Length) + " [$Kind]"
        }
    }
    throw 'Image must be staged in the local Comfy input/output directories.'
}
$Destination = [IO.Path]::GetFullPath((Join-Path $ProjectRoot $OutputDirectory))
if (-not $Destination.StartsWith($ProjectRoot + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Output must stay inside the project.' }
if (Test-Path -LiteralPath (Join-Path $Destination 'submission.json')) { throw 'Already submitted: poll the saved prompt ID.' }
$Baseline = Get-Content -Raw -LiteralPath $BaselineReport | ConvertFrom-Json
if ($Baseline.turbo -or -not $Baseline.phone_camera_style -or $Baseline.steps -ne 50 -or $Baseline.cfg -ne 4) { throw 'Expected non-Turbo, phone-on, 50-step CFG4 baseline.' }
if ($IdentityStrength -lt 0.1 -or $IdentityStrength -gt 1.5) { throw 'Diagnostic identity strength out of range.' }
if ($IdentityReferenceOverride -and $ReferenceMode -ne 'four') { throw 'Identity replacement requires the verified four-reference layout.' }
if ($ReferenceTwoRole -eq 'expression' -and ($ReferenceMode -ne 'four' -or -not $GuideOverride)) { throw 'Expression reference requires four references and explicit guide provenance.' }
$WorkerSnapshots = foreach ($Port in 8188,8189,8190) {
    try {
        $Stats = Invoke-RestMethod "http://127.0.0.1:$Port/system_stats" -TimeoutSec 3
        $Queue = Invoke-RestMethod "http://127.0.0.1:$Port/queue" -TimeoutSec 3
        [pscustomobject]@{port=$Port;online=$true;device=$Stats.devices[0].name;running=@($Queue.queue_running).Count;pending=@($Queue.queue_pending).Count}
    } catch {
        $Socket = [Net.Sockets.TcpClient]::new()
        try { $Listening = $Socket.ConnectAsync('127.0.0.1',$Port).Wait(500) -and $Socket.Connected } catch { $Listening=$false } finally { $Socket.Dispose() }
        if ($Listening) { throw "Cannot inspect listening worker $Port." }
        [pscustomobject]@{port=$Port;online=$false;device='offline';running=0;pending=0}
    }
}
$Target = @($WorkerSnapshots | Where-Object port -eq 8188)[0]
if (-not $Target.online -or $Target.device -notmatch 'RTX 3090' -or $Target.running -or $Target.pending) { throw 'Locked3090 worker unavailable/busy.' }
if (@($WorkerSnapshots | Where-Object { $_.device -match '3090' -and ($_.running -or $_.pending) }).Count) { throw 'Other3090 work active.' }
$Hardware = @(& nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader,nounits)
$Card = @($Hardware | Where-Object { $_ -match 'RTX 3090' })
if ($Card.Count -ne 1) { throw 'Cannot identify hardware.' }
$Fields = $Card[0] -split ',\s*'
if ([int]$Fields[3] -gt 10) { throw '3090 hardware is active; do not interrupt it.' }
$OwnedCache = $null
if ([int]$Fields[2] -gt 4096) {
    if ($AllowOwnedCachePromptId -notin @('359b70af-a7a5-4c9f-8ea9-5bd484082b59','9f9b660d-06b9-4e00-af27-425b6d4f6195','2901d734-bdd7-4d6c-80a4-c4a628e770d5','884126c1-2967-460f-a14b-81b982e11fd1','29957d55-f1c2-4f05-8f08-c2bc064b7ddb')) { throw '3090 memory is occupied without explicitly verified owned cache.' }
    $History = Invoke-RestMethod "$Server/history?max_items=1" -TimeoutSec 10
    $Recent = @($History.PSObject.Properties)
    if ($Recent.Count -ne 1 -or $Recent[0].Name -ne $AllowOwnedCachePromptId -or -not $Recent[0].Value.status.completed -or $Recent[0].Value.status.status_str -ne 'success') { throw 'Latest3090 job is not the recorded owned terminal success.' }
    $CachedGraph = $Recent[0].Value.prompt[2]
    if ($CachedGraph.'1'.inputs.unet_name -ne $Baseline.model -or $CachedGraph.'2'.inputs.lora_name -ne $Baseline.lora -or $CachedGraph.'3'.inputs.lora_name -ne $Baseline.additional_loras[0].name) { throw 'Owned cached model set differs from the protected baseline.' }
    $OwnedCache = [ordered]@{prompt_id=$AllowOwnedCachePromptId;status='success';models_unloaded=$false;policy='Reuse the idle owned server cache through normal Comfy memory management; never free another worker.'}
}
$Info = Invoke-RestMethod "$Server/object_info" -TimeoutSec 20
$ModelPaths = @(
    @($Baseline.model_path,$Baseline.model_sha256),
    @($Baseline.text_encoder_path,$Baseline.text_encoder_sha256),
    @($Baseline.vae_path,$Baseline.vae_sha256),
    @($Baseline.lora_path,$Baseline.lora_sha256),
    @($Baseline.phone_camera_style_path,$Baseline.additional_loras[0].sha256)
)
$Verified = foreach ($Pair in $ModelPaths) {
    if (-not $Pair[0] -or -not $Pair[1]) { throw 'Baseline model provenance incomplete.' }
    $Hash = (Get-FileHash -LiteralPath $Pair[0] -Algorithm SHA256).Hash
    if ($Hash -cne $Pair[1].ToUpperInvariant()) { throw "Protected file changed: $($Pair[0])" }
    [ordered]@{path=$Pair[0];sha256=$Hash}
}
if ($PromptFile) {
    if ($PromptOverride) { throw 'Specify one prompt override mechanism.' }
    $PromptOverride = Get-Content -Raw -LiteralPath $PromptFile
}
$NegativePrompt = ''
if ($NegativePromptFile) {
    if ($ReferenceMode -ne 'four') { throw 'Negative-conditioning diagnostic is restricted to the verified four-reference experiment.' }
    $NegativePrompt = (Get-Content -Raw -LiteralPath $NegativePromptFile).Trim()
    if (-not $NegativePrompt -or $NegativePrompt.Length -gt 2000) { throw 'Use one short, nonempty diagnostic negative prompt.' }
}
$EffectivePrompt = $Baseline.effective_prompt
if ($ReferenceMode -eq 'no_identity') {
    $Pattern = 'Picture 3 is a protected genuine photograph.*?(?=Picture 4 is)'
    if (-not [regex]::IsMatch($EffectivePrompt,$Pattern)) { throw 'This baseline has an unsupported identity-role paragraph.' }
    $EffectivePrompt = [regex]::Replace($EffectivePrompt,$Pattern,'The man is m1tch_person. ')
    $EffectivePrompt = $EffectivePrompt.Replace('Picture 4 is','Picture 3 is')
} elseif ($ReferenceMode -eq 'source_only' -and -not $PromptOverride) { throw 'Source-only test requires an explicit source-edit prompt.' }
if ($PromptOverride) { $EffectivePrompt = $PromptOverride }
if ($EffectivePrompt -notmatch 'm1tch_person' -or $EffectivePrompt -notmatch 'casual snapshot') { throw 'Required trained triggers missing.' }
$SourcePath = if ([IO.Path]::IsPathRooted($SourceName)) { $SourceName } else { Join-Path $ComfyRoot "input\$SourceName" }
if (-not (Test-Path -LiteralPath $SourcePath)) { throw 'Source missing.' }
$References = @([ordered]@{name=(Get-ComfyImageName $SourcePath);path=$SourcePath;megapixels=1.0;method='bicubic';role='source edit, pose, expression and composition; identity influence unisolated'})
if ($ReferenceMode -ne 'source_only') {
    $GuidePath = Join-Path (Split-Path -Parent $BaselineReport) 'structure-guide_00001_.png'
    if ($GuideOverride) { $GuidePath = [IO.Path]::GetFullPath($GuideOverride) }
    $GuideRole = if ($ReferenceTwoRole -eq 'expression') { 'original-source facial expression crop; not a genuine identity anchor; see crop provenance' } elseif ($GuideOverride) { 'experimental geometry; see guide provenance' } else { 'face-free geometry' }
    $References += [ordered]@{name=(Get-ComfyImageName $GuidePath);path=$GuidePath;megapixels=0.5;method='nearest-exact';role=$GuideRole}
    if ($ReferenceMode -eq 'four') {
        $IdentityPath = if ($IdentityReferenceOverride) { [IO.Path]::GetFullPath($IdentityReferenceOverride) } else { $Baseline.identity_reference_path }
        $IdentityName = if ($IdentityReferenceOverride) { Get-ComfyImageName $IdentityPath } else { $Baseline.identity_reference }
        $References += [ordered]@{name=$IdentityName;path=$IdentityPath;megapixels=0.5;method='nearest-exact';role='explicit genuine identity portrait'}
    }
    $References += [ordered]@{name=$Baseline.hair_reference;path=$Baseline.hair_reference_path;megapixels=0.1;method='bicubic';role='hair material'}
}
foreach ($Reference in $References) {
    if (-not (Test-Path -LiteralPath $Reference.path)) { throw "Reference missing: $($Reference.path)" }
    $Reference.sha256=(Get-FileHash -LiteralPath $Reference.path).Hash
}
$Graph=[ordered]@{
    '1'=@{class_type='UNETLoader';inputs=@{unet_name=$Baseline.model;weight_dtype='fp8_e4m3fn'}}
    '2'=@{class_type='LoraLoaderModelOnly';inputs=@{model=@('1',0);lora_name=$Baseline.lora;strength_model=$IdentityStrength}}
    '3'=@{class_type='LoraLoaderModelOnly';inputs=@{model=@('2',0);lora_name=$Baseline.additional_loras[0].name;strength_model=$PhoneStyleStrength}}
    '4'=@{class_type='CLIPLoader';inputs=@{clip_name=$Baseline.text_encoder;type='flux2';device='default'}}
    '5'=@{class_type='VAELoader';inputs=@{vae_name=$Baseline.vae}}
    '6'=@{class_type='CLIPTextEncode';inputs=@{clip=@('4',0);text=$EffectivePrompt}}
    '7'=@{class_type='CLIPTextEncode';inputs=@{clip=@('4',0);text=$NegativePrompt}}
}
$Positive='6';$Negative='7';$Index=0
foreach ($Reference in $References) {
    $Base=100+10*$Index
    $Load=[string]$Base;$Scale=[string]($Base+1);$Encode=[string]($Base+2);$Pos=[string]($Base+3);$Neg=[string]($Base+4)
    $Graph[$Load]=@{class_type='LoadImage';inputs=@{image=$Reference.name}}
    $Graph[$Scale]=@{class_type='ImageScaleToTotalPixels';inputs=@{image=@($Load,0);upscale_method=$Reference.method;megapixels=$Reference.megapixels;resolution_steps=1}}
    $Graph[$Encode]=@{class_type='VAEEncode';inputs=@{pixels=@($Scale,0);vae=@('5',0)}}
    $Graph[$Pos]=@{class_type='ReferenceLatent';inputs=@{conditioning=@($Positive,0);latent=@($Encode,0)}}
    $Graph[$Neg]=@{class_type='ReferenceLatent';inputs=@{conditioning=@($Negative,0);latent=@($Encode,0)}}
    $Positive=$Pos;$Negative=$Neg;$Index++
}
$Graph['20']=@{class_type='RandomNoise';inputs=@{noise_seed=[UInt64]$Baseline.seed}}
$Graph['21']=@{class_type='CFGGuider';inputs=@{model=@('3',0);positive=@($Positive,0);negative=@($Negative,0);cfg=4.0}}
$Graph['22']=@{class_type='KSamplerSelect';inputs=@{sampler_name='euler'}}
$Graph['23']=@{class_type='Flux2Scheduler';inputs=@{steps=50;width=$Baseline.width;height=$Baseline.height}}
$Graph['24']=@{class_type='EmptyFlux2LatentImage';inputs=@{width=$Baseline.width;height=$Baseline.height;batch_size=1}}
$Graph['25']=@{class_type='SamplerCustomAdvanced';inputs=@{noise=@('20',0);guider=@('21',0);sampler=@('22',0);sigmas=@('23',0);latent_image=@('24',0)}}
$Graph['26']=@{class_type='VAEDecode';inputs=@{samples=@('25',0);vae=@('5',0)}}
$Prefix='upgrade-source-faithful/'+(Split-Path -Leaf $Destination)+'/raw'
$Graph['27']=@{class_type='SaveImage';inputs=@{images=@('26',0);filename_prefix=$Prefix}}
$IdentitySchedule=$null
if ($IdentitySplitStep -ne -1) {
    . "$PSScriptRoot/upgrade-identity-schedule.ps1"
    $IdentitySchedule=Add-UpgradeIdentitySchedule -Graph $Graph -SplitStep $IdentitySplitStep -LateStrength $LateIdentityStrength
}
foreach ($Node in $Graph.Values) {
    if (-not $Info.($Node.class_type)) { throw "Live node missing: $($Node.class_type)" }
}
foreach ($Check in @(@('UNETLoader','unet_name',$Baseline.model),@('CLIPLoader','clip_name',$Baseline.text_encoder),@('VAELoader','vae_name',$Baseline.vae),@('LoraLoaderModelOnly','lora_name',$Baseline.lora),@('LoraLoaderModelOnly','lora_name',$Baseline.additional_loras[0].name))) {
    if ($Check[2] -notin $Info.($Check[0]).input.required.($Check[1])[0]) { throw "Model not visible: $($Check[2])" }
}
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$Manifest=[ordered]@{status='prepared';reference_mode=$ReferenceMode;identity_strength=$IdentityStrength;baseline_report=$BaselineReport;effective_prompt=$EffectivePrompt;identity_mechanism='genuine-photo-trained protected Base9B character LoRA, not generic image conditioning alone';references=$References;verified_models=$Verified;workers=$WorkerSnapshots;hardware=$Hardware;production_changed=$false;postprocess=$false;turbo=$false;phone_camera_style=($PhoneStyleStrength -gt 0);phone_camera_style_strength=$PhoneStyleStrength;upstream_phone_camera_style=[bool]$Baseline.phone_camera_style;seed=$Baseline.seed;steps=50;cfg=4;author_template='comfyui_workflow_templates_json/templates/image_flux2_klein_image_edit_9b_base.json';prompt=$Graph}
$Manifest['owned_idle_cache']=$OwnedCache
$Manifest['baseline_report_sha256']=(Get-FileHash -LiteralPath $BaselineReport -Algorithm SHA256).Hash
if ($IdentitySchedule) { $Manifest['identity_schedule']=$IdentitySchedule }
$Manifest | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath (Join-Path $Destination 'experiment.json') -Encoding utf8
if ($PrepareOnly) { Write-Output "Prepared $Destination"; return }
# Recheck the target queue after hashing; never submit behind unrelated work.
$Queue=Invoke-RestMethod "$Server/queue"
if (@($Queue.queue_running).Count -or @($Queue.queue_pending).Count) { throw 'Queue became busy during preflight.' }
if ($OwnedCache) {
    $Recent = @((Invoke-RestMethod "$Server/history?max_items=1" -TimeoutSec 10).PSObject.Properties)
    if ($Recent.Count -ne 1 -or $Recent[0].Name -ne $AllowOwnedCachePromptId -or -not $Recent[0].Value.status.completed) { throw 'Owned cache provenance changed during preflight.' }
}
$Body=@{prompt=$Graph;client_id="upgrade-ablation-$([guid]::NewGuid().ToString('N'))"} | ConvertTo-Json -Depth 25
$Submission=Invoke-RestMethod -Method Post "$Server/prompt" -ContentType 'application/json' -Body $Body -TimeoutSec 30
$Submission | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $Destination 'submission.json') -Encoding utf8
$Submission | ConvertTo-Json -Depth 12
