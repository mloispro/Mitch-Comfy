[CmdletBinding()]
param(
    [string]$SourcePath = 'C:/projects/AI-Tools/ComfyUI/output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260903-005704-305944/before-polish_00001_.png',
    [string]$BaselineReport = 'C:/projects/AI-Tools/ComfyUI/output/flux2-klein9b-upgrade-photo-detail-realism-v1/20260903-005704-305944/report.json',
    [string]$OutputDirectory = 'work/upgrade-source-faithful-20260903/qwen-high-canyon',
    [ValidateSet(20,40)][int]$Steps = 20,
    [ValidateSet(1.0,0.35)][double]$Denoise = 1.0,
    [ValidateSet('author','whole_frame')][string]$FramingMode = 'author',
    [ValidateSet('native','author32_explicit_native_latents')][string]$ReferencePacking = 'native',
    [string]$PromptFile = '',
    [string]$NegativePromptFile = '',
    [string]$IdentityReferencePath = '',
    [string]$ExpressionReferencePath = '',
    [string]$ExpressionReferenceAudit = '',
    [string]$UpstreamEvaluationAudit = '',
    [ValidateSet('generated_base','original_source')][string]$SourceRole = 'generated_base',
    [string]$OriginalSourceAudit = '',
    [switch]$PrepareOnly
)
$ErrorActionPreference='Stop'
if ($ReferencePacking -ne 'native' -and $FramingMode -ne 'whole_frame') {
    throw 'Explicit packing diagnostic requires whole-frame mode so original/reference aspect ratios match.'
}
$ProjectRoot=Split-Path -Parent $PSScriptRoot
$ComfyRoot='C:/projects/AI-Tools/ComfyUI'
$Server='http://127.0.0.1:8188'
$Destination=[IO.Path]::GetFullPath((Join-Path $ProjectRoot $OutputDirectory))
if (-not $Destination.StartsWith($ProjectRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Output must stay inside project.' }
if (Test-Path (Join-Path $Destination 'submission.json')) { throw 'Already submitted; poll saved prompt ID.' }
$Baseline=Get-Content -LiteralPath $BaselineReport -Raw | ConvertFrom-Json
if ($Baseline.turbo -or -not $Baseline.phone_camera_style -or $Baseline.steps -ne 50 -or $Baseline.cfg -ne 4) { throw 'Expected verified phone-on, non-Turbo Klein baseline.' }
$SourcePath=[IO.Path]::GetFullPath($SourcePath)
$SourceName=$null
foreach ($Kind in 'input','output') {
    $InputRoot=[IO.Path]::GetFullPath((Join-Path $ComfyRoot $Kind))+[IO.Path]::DirectorySeparatorChar
    if ($SourcePath.StartsWith($InputRoot,[StringComparison]::OrdinalIgnoreCase)) { $SourceName=$SourcePath.Substring($InputRoot.Length)+" [$Kind]" }
}
if (-not $SourceName -or -not (Test-Path -LiteralPath $SourcePath)) { throw 'Source must exist in local Comfy input/output.' }
$SourceHash=(Get-FileHash -LiteralPath $SourcePath).Hash.ToLowerInvariant()
if ($SourceRole -eq 'original_source') {
    if (-not $OriginalSourceAudit -or -not $IdentityReferencePath -or $ExpressionReferencePath -or $UpstreamEvaluationAudit) {
        throw 'Direct-original test needs its source audit and genuine identity input, without a generated upstream or third reference.'
    }
    $OriginalSourceAudit=[IO.Path]::GetFullPath($OriginalSourceAudit)
    $OriginalAudit=Get-Content -LiteralPath $OriginalSourceAudit -Raw | ConvertFrom-Json
    if (-not $OriginalAudit.executed_png_graph_verified -or $OriginalAudit.postprocess_applied -or
        $OriginalAudit.inputs.SOURCE.sha256.ToLowerInvariant() -cne $SourceHash) {
        throw 'Direct edit target must match the previously audited original source.'
    }
} elseif ($OriginalSourceAudit) { throw 'OriginalSourceAudit is only valid for original_source.' }
$IdentityReference=$null
if ($IdentityReferencePath) {
    $IdentityReferencePath=[IO.Path]::GetFullPath($IdentityReferencePath)
    $IdentityName=$null
    foreach ($Kind in 'input','output') {
        $ReferenceRoot=[IO.Path]::GetFullPath((Join-Path $ComfyRoot $Kind))+[IO.Path]::DirectorySeparatorChar
        if ($IdentityReferencePath.StartsWith($ReferenceRoot,[StringComparison]::OrdinalIgnoreCase)) {
            $IdentityName=$IdentityReferencePath.Substring($ReferenceRoot.Length)+" [$Kind]"
        }
    }
    if (-not $IdentityName -or -not (Test-Path -LiteralPath $IdentityReferencePath)) { throw 'Identity reference must already exist in local Comfy input/output.' }
    $IdentityHash=(Get-FileHash -LiteralPath $IdentityReferencePath).Hash.ToLowerInvariant()
    $IdentityDatasetPath=Join-Path $ProjectRoot 'datasets/mitch-identity-stills-v3/manifest.json'
    $IdentityDataset=Get-Content -LiteralPath $IdentityDatasetPath -Raw | ConvertFrom-Json
    $IdentityRecords=@($IdentityDataset.records | Where-Object { $_.dataset_sha256 -eq $IdentityHash -and $_.kind -eq 'camera_still' -and $_.split -eq 'train' })
    if ($IdentityRecords.Count -ne 1) { throw 'Identity input must match exactly one genuine training camera still, not a validation/scoring photo.' }
    if ((Get-FileHash -LiteralPath $IdentityRecords[0].dataset_file).Hash.ToLowerInvariant() -cne $IdentityHash) { throw 'Genuine dataset reference has changed.' }
    $IdentityReference=@{name=$IdentityName;path=$IdentityReferencePath;sha256=$IdentityHash;
        role='Picture 2: genuine same-person identity/appearance reference; not pose, expression, scene or scoring reference';
        provenance_manifest=$IdentityDatasetPath;provenance_manifest_sha256=(Get-FileHash -LiteralPath $IdentityDatasetPath).Hash;
        provenance_record_id=$IdentityRecords[0].id;kind='camera_still';split='train'}
}
$ExpressionReference=$null
if ($ExpressionReferencePath -or $ExpressionReferenceAudit) {
    if (-not $IdentityReference -or -not $ExpressionReferencePath -or -not $ExpressionReferenceAudit) {
        throw 'Original-expression input requires a genuine identity input and verified source/base audit.'
    }
    $ExpressionReferencePath=[IO.Path]::GetFullPath($ExpressionReferencePath)
    $ExpressionName=$null
    foreach ($Kind in 'input','output') {
        $ReferenceRoot=[IO.Path]::GetFullPath((Join-Path $ComfyRoot $Kind))+[IO.Path]::DirectorySeparatorChar
        if ($ExpressionReferencePath.StartsWith($ReferenceRoot,[StringComparison]::OrdinalIgnoreCase)) {
            $ExpressionName=$ExpressionReferencePath.Substring($ReferenceRoot.Length)+" [$Kind]"
        }
    }
    if (-not $ExpressionName -or -not (Test-Path -LiteralPath $ExpressionReferencePath)) { throw 'Original source must already exist in local Comfy input/output.' }
    $ExpressionHash=(Get-FileHash -LiteralPath $ExpressionReferencePath).Hash.ToLowerInvariant()
    $ExpressionReferenceAudit=[IO.Path]::GetFullPath($ExpressionReferenceAudit)
    $ExpressionAudit=Get-Content -LiteralPath $ExpressionReferenceAudit -Raw | ConvertFrom-Json
    if (-not $ExpressionAudit.executed_png_graph_verified -or $ExpressionAudit.postprocess_applied -or
        $ExpressionAudit.inputs.SOURCE.sha256.ToLowerInvariant() -cne $ExpressionHash -or
        $ExpressionAudit.inputs.'BASE RAW'.sha256.ToLowerInvariant() -cne $SourceHash) {
        throw 'Expression source and generated edit target must match the verified audit source/base pair.'
    }
    if ($ExpressionHash -in @($SourceHash,$IdentityReference.sha256)) { throw 'Original expression source must be distinct from the generated target and genuine identity input.' }
    $ExpressionReference=@{name=$ExpressionName;path=$ExpressionReferencePath;sha256=$ExpressionHash;
        kind='original_expression_source';identity_influence='unisolated_not_proven_absent';
        role='Picture 3: original source head direction, pupil focus and eye/brow/closed-lip expression; not a genuine identity/scoring reference';
        source_audit=$ExpressionReferenceAudit;source_audit_sha256=(Get-FileHash -LiteralPath $ExpressionReferenceAudit).Hash.ToLowerInvariant()}
}
. (Join-Path $PSScriptRoot 'upgrade-whole-frame-dimensions.ps1')
$SourceDimensions=Get-UpgradePngDimensions $SourcePath
$OutputDimensions=if ($FramingMode -eq 'whole_frame') { Get-UpgradeWholeFrameDimensions $SourceDimensions[0] $SourceDimensions[1] } else { $null }
$WorkerSnapshots=foreach ($Port in 8188,8189,8190) {
    try {
        $Stats=Invoke-RestMethod "http://127.0.0.1:$Port/system_stats" -TimeoutSec 3
        $Queue=Invoke-RestMethod "http://127.0.0.1:$Port/queue" -TimeoutSec 3
        [pscustomobject]@{port=$Port;online=$true;device=$Stats.devices[0].name;running=@($Queue.queue_running).Count;pending=@($Queue.queue_pending).Count;system=$Stats.system}
    } catch {
        $Socket=[Net.Sockets.TcpClient]::new()
        try { $Listening=$Socket.ConnectAsync('127.0.0.1',$Port).Wait(500) -and $Socket.Connected } catch { $Listening=$false } finally { $Socket.Dispose() }
        if ($Listening) { throw "Cannot inspect listening worker $Port." }
        [pscustomobject]@{port=$Port;online=$false;device='offline';running=0;pending=0}
    }
}
$Target=@($WorkerSnapshots | Where-Object port -eq 8188)[0]
if (-not $Target.online -or $Target.device -notmatch 'RTX 3090' -or $Target.running -or $Target.pending) { throw 'Locked3090 worker unavailable/busy.' }
if (@($WorkerSnapshots | Where-Object { $_.device -match '3090' -and ($_.running -or $_.pending) }).Count) { throw 'Other3090 work active.' }
$Hardware=@(& nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader,nounits)
$Card=@($Hardware | Where-Object { $_ -match 'RTX 3090' })
if ($Card.Count -ne 1) { throw 'Cannot identify hardware.' }
$Fields=$Card[0] -split ',\s*'
if ([int]$Fields[2] -gt 4096 -or [int]$Fields[3] -gt 10) { throw '3090 hardware busy; do not interrupt.' }
$Info=Invoke-RestMethod "$Server/object_info" -TimeoutSec 20
$ModelSpecs=@(
    @('UNETLoader','unet_name','diffusion_models','qwen_image_edit_2511_fp8mixed.safetensors','c9fdc158e46d3b61ef75f21ae866ca2fe808bf4a53643120d1c1e87c19280a4e'),
    @('CLIPLoader','clip_name','text_encoders','qwen_2.5_vl_7b_fp8_scaled.safetensors','cb5636d852a0ea6a9075ab1bef496c0db7aef13c02350571e388aea959c5c0b4'),
    @('VAELoader','vae_name','vae','qwen_image_vae.safetensors','a70580f0213e67967ee9c95f05bb400e8fb08307e017a924bf3441223e023d1f')
)
$Verified=foreach ($Spec in $ModelSpecs) {
    $ModelPath=Join-Path $ComfyRoot "models/$($Spec[2])/$($Spec[3])"
    $Hash=(Get-FileHash -LiteralPath $ModelPath).Hash.ToLowerInvariant()
    if ($Hash -cne $Spec[4]) { throw "Model hash differs from official file: $ModelPath" }
    if ($Spec[3] -notin $Info.($Spec[0]).input.required.($Spec[1])[0]) { throw "Model not visible: $($Spec[3])" }
    [ordered]@{path=$ModelPath;sha256=$Hash}
}
$TemplatePath=Join-Path $ComfyRoot '.venv/Lib/site-packages/comfyui_workflow_templates_json/templates/image_qwen_image_edit_2511.json'
$Template=Get-Content -LiteralPath $TemplatePath -Raw | ConvertFrom-Json
$Subgraph=@($Template.definitions.subgraphs | Where-Object id -eq 'cdb2cf24-c432-439b-b5c8-5f69838580c9')[0]
if (-not $Subgraph) { throw 'Inspected author subgraph missing.' }
$Prompt='Edit this same photograph to make the man noticeably more handsome while keeping him recognizably the same individual. Give him a relaxed, confident, slightly asymmetric closed-lip smile with no visible teeth. Relax the furrow between his eyebrows and soften forehead creases. Make his eyes more appealing with subtly refined almond-shaped eyelids and well-groomed, slightly fuller eyebrows; preserve the exact pupil direction and natural eye color. Refine his cheek and jaw contours to look lean and defined, not round or puffy. Give him clear, even, lightly sun-kissed skin with fine realistic pores, remove freckles and dark facial speckles, soften under-eye tiredness, and keep neat fine stubble. Preserve his adult character and recognizable nose and facial proportions. Keep his hairline and hairstyle, render natural individual brown hair strands with a few subtle lighter highlights. Keep the exact head angle, camera angle, crop, body pose, clothes, background geometry and lighting. Preserve a real casual phone photograph, detailed natural background, and consistent skin and scene texture. The beauty improvement should be clearly visible but not look like makeup, plastic skin, a different person or a glamour studio portrait.'
if ($PromptFile) { $Prompt=Get-Content -LiteralPath $PromptFile -Raw }
$NegativePrompt=''
if ($NegativePromptFile) { $NegativePrompt=(Get-Content -LiteralPath $NegativePromptFile -Raw).Trim() }
if ($ExpressionReference) {
    $Prompt='Picture 1 is the detailed photograph to edit and controls the environment, body pose, framing, hairstyle, clothes, lighting and phone-camera texture. Picture 2 is a genuine identity photograph of the same man; retain his distinctive identity and recognizable adult facial proportions, not its pose, expression, clothing or background. Picture 3 is the original photograph before upgrading: restore its exact head direction, pupil focus, appealing eye and eyebrow presentation, and relaxed asymmetric closed-lip expression instead of any expression drift in Picture 1. Use Picture 3 for those presentation details, not its skin texture, color or background softness. Return one edited Picture 1 containing only the same single man. ' + $Prompt
} elseif ($IdentityReference) {
    $Prompt='Picture 1 is the photograph to edit and controls the composition, head angle, pupil direction, starting expression, hairstyle, clothing, lighting and background. Picture 2 is a genuine identity reference of the same man; use it to retain his distinctive identity and recognizable facial proportions, not its pose, expression, clothes or background. Return only the edited Picture 1 with one person. ' + $Prompt
}
# Flatten only the inspected author graph's non-Lightning branch; preserve original node IDs.
$Graph=[ordered]@{
    '41'=@{class_type='LoadImage';inputs=@{image=$SourceName}}
    '160'=@{class_type='FluxKontextImageScale';inputs=@{image=@('41',0)}}
    '161'=@{class_type='UNETLoader';inputs=@{unet_name=$ModelSpecs[0][3];weight_dtype='default'}}
    '162'=@{class_type='CLIPLoader';inputs=@{clip_name=$ModelSpecs[1][3];type='qwen_image';device='default'}}
    '146'=@{class_type='VAELoader';inputs=@{vae_name=$ModelSpecs[2][3]}}
    '145'=@{class_type='ModelSamplingAuraFlow';inputs=@{model=@('161',0);shift=3.1}}
    '152'=@{class_type='CFGNorm';inputs=@{model=@('145',0);strength=1.0;pre_cfg=$false}}
    '151'=@{class_type='TextEncodeQwenImageEditPlus';inputs=@{clip=@('162',0);vae=@('146',0);image1=@('160',0);prompt=$Prompt}}
    '149'=@{class_type='TextEncodeQwenImageEditPlus';inputs=@{clip=@('162',0);vae=@('146',0);image1=@('160',0);prompt=$NegativePrompt}}
    '148'=@{class_type='FluxKontextMultiReferenceLatentMethod';inputs=@{conditioning=@('151',0);reference_latents_method='index_timestep_zero'}}
    '147'=@{class_type='FluxKontextMultiReferenceLatentMethod';inputs=@{conditioning=@('149',0);reference_latents_method='index_timestep_zero'}}
    '156'=@{class_type='VAEEncode';inputs=@{pixels=@('160',0);vae=@('146',0)}}
    '169'=@{class_type='KSampler';inputs=@{model=@('152',0);positive=@('148',0);negative=@('147',0);latent_image=@('156',0);seed=[UInt64]$Baseline.seed;steps=$Steps;cfg=4.0;sampler_name='euler';scheduler='simple';denoise=$Denoise}}
    '158'=@{class_type='VAEDecode';inputs=@{samples=@('169',0);vae=@('146',0)}}
    '9'=@{class_type='SaveImage';inputs=@{images=@('158',0);filename_prefix=('upgrade-source-faithful/'+(Split-Path -Leaf $Destination)+'/raw')}}
}
if ($FramingMode -eq 'whole_frame') {
    $Graph['160']=@{class_type='ImageScale';inputs=@{image=@('41',0);upscale_method='lanczos';width=$OutputDimensions[0];height=$OutputDimensions[1];crop='disabled'}}
}
if ($IdentityReference) {
    # Restore the shipped example's second-image input, on both CFG branches.
    $AuthorReference=@($Template.nodes | Where-Object id -eq 83)[0]
    if ($AuthorReference.type -ne 'LoadImage') { throw 'Author second reference loader changed.' }
    foreach ($EncoderId in 149,151) {
        if (-not @($Subgraph.links | Where-Object { $_.origin_id -eq -10 -and $_.origin_slot -eq 1 -and $_.target_id -eq $EncoderId -and $_.target_slot -eq 3 }).Count) { throw 'Author second-image conditioning link changed.' }
    }
    if (-not $Info.TextEncodeQwenImageEditPlus.input.optional.image2) { throw 'Live native encoder lacks image2.' }
    $Graph['83']=@{class_type='LoadImage';inputs=@{image=$IdentityReference.name}}
    $Graph['151'].inputs.image2=@('83',0)
    $Graph['149'].inputs.image2=@('83',0)
}
if ($ExpressionReference) {
    foreach ($EncoderId in 149,151) {
        if (-not @($Subgraph.links | Where-Object { $_.origin_id -eq -10 -and $_.origin_slot -eq 2 -and $_.target_id -eq $EncoderId -and $_.target_slot -eq 4 }).Count) { throw 'Author third-image conditioning link changed.' }
    }
    if (-not $Info.TextEncodeQwenImageEditPlus.input.optional.image3) { throw 'Live native encoder lacks image3.' }
    # Enable the author's optional image3 input using the same native loader type.
    $Graph['184']=@{class_type='LoadImage';inputs=@{image=$ExpressionReference.name}}
    $Graph['151'].inputs.image3=@('184',0)
    $Graph['149'].inputs.image3=@('184',0)
}
$PackingNodeIds=@()
$PackingGeometry=@()
if ($ReferencePacking -eq 'author32_explicit_native_latents') {
    . (Join-Path $PSScriptRoot 'upgrade-qwen-reference-packing.ps1')
    # Keep Plus's grounded VL path exactly as before. Build the appearance-latent
    # list with the same native append helper, using author-aligned VAE dimensions.
    [void]$Graph['151'].inputs.Remove('vae')
    [void]$Graph['149'].inputs.Remove('vae')
    $PackingSources=@(@{node='160';path=$SourcePath})
    if ($IdentityReference) { $PackingSources+=@{node='83';path=$IdentityReferencePath} }
    if ($ExpressionReference) { $PackingSources+=@{node='184';path=$ExpressionReferencePath} }
    $PreviousPositive='151';$PreviousNegative='149'
    for ($index=0;$index -lt $PackingSources.Count;$index++) {
        $item=$PackingSources[$index]
        $size=Get-UpgradeOrientedImageDimensions $item.path
        $aligned=Get-UpgradeQwenAlignedDimensions $size[0] $size[1]
        $scaleId=[string](190+4*$index);$encodeId=[string](191+4*$index)
        $positiveId=[string](192+4*$index);$negativeId=[string](193+4*$index)
        $Graph[$scaleId]=@{class_type='ImageScale';inputs=@{image=@($item.node,0);upscale_method='area';width=$aligned[0];height=$aligned[1];crop='disabled'}}
        $Graph[$encodeId]=@{class_type='VAEEncode';inputs=@{pixels=@($scaleId,0);vae=@('146',0)}}
        $Graph[$positiveId]=@{class_type='ReferenceLatent';inputs=@{conditioning=@($PreviousPositive,0);latent=@($encodeId,0)}}
        $Graph[$negativeId]=@{class_type='ReferenceLatent';inputs=@{conditioning=@($PreviousNegative,0);latent=@($encodeId,0)}}
        $PackingNodeIds+=@($scaleId,$encodeId,$positiveId,$negativeId)
        $PackingGeometry+=@{reference_index=$index+1;source_node=$item.node;source_dimensions=$size;vae_dimensions=$aligned;
            latent_dimensions=@(($aligned[0]/8),($aligned[1]/8));circular_patch_padding_required=$false}
        $PreviousPositive=$positiveId;$PreviousNegative=$negativeId
    }
    $Graph['148'].inputs.conditioning=@($PreviousPositive,0)
    $Graph['147'].inputs.conditioning=@($PreviousNegative,0)
}
foreach ($Entry in $Graph.GetEnumerator()) {
    if (-not $Info.($Entry.Value.class_type)) { throw "Missing live node: $($Entry.Value.class_type)" }
    if ($Entry.Key -notin @('41','9','83','184')+$PackingNodeIds) {
        $AuthorNode=@($Subgraph.nodes | Where-Object id -eq ([int]$Entry.Key))[0]
        $ExpectedType=if ($Entry.Key -eq '160' -and $FramingMode -eq 'whole_frame') { 'ImageScale' } else { $AuthorNode.type }
        if ($ExpectedType -ne $Entry.Value.class_type) { throw "Author topology changed at node $($Entry.Key)." }
    }
}
if ($UpstreamEvaluationAudit) {
    $UpstreamAudit=Get-Content -LiteralPath $UpstreamEvaluationAudit -Raw | ConvertFrom-Json
    if (-not $UpstreamAudit.executed_png_graph_verified -or $UpstreamAudit.postprocess_applied -or
        $UpstreamAudit.inputs.'CANDIDATE HIGH'.sha256 -cne $SourceHash) { throw 'Upstream native evaluation does not verify this exact edit target.' }
}
$References=@(@{name=$SourceName;path=$SourcePath;sha256=$SourceHash;role='Picture 1: generated edit target; pose/expression/scene and latent initialization; no scoring-reference status'})
if ($SourceRole -eq 'original_source') {
    $References[0].role='Picture 1: audited original edit source; composition, expression, color and appearance; not asserted to be a genuine identity scoring photograph'
    $References[0].source_audit=$OriginalSourceAudit
    $References[0].source_audit_sha256=(Get-FileHash -LiteralPath $OriginalSourceAudit).Hash.ToLowerInvariant()
}
if ($IdentityReference) { $References+=$IdentityReference }
if ($ExpressionReference) { $References+=$ExpressionReference }
$Manifest=[ordered]@{
    status='prepared';stage='qwen_native_high_edit';production_changed=$false;postprocess=$false;turbo=$false;lightning=$false
    phone_camera_style=$false;phone_camera_style_strength=0;upstream_phone_camera_style=($SourceRole -eq 'generated_base')
    source_role=$SourceRole
    phone_appearance_mode=$(if ($SourceRole -eq 'original_source') { 'experimental_native_prompt_only' } else { 'inherited_from_klein' })
    baseline_report_role=$(if ($SourceRole -eq 'original_source') { 'comparison_and_seed_only_not_upstream' } else { 'upstream' })
    baseline_report=$BaselineReport;baseline_report_sha256=(Get-FileHash -LiteralPath $BaselineReport).Hash
    upstream_evaluation_audit=$UpstreamEvaluationAudit
    upstream_evaluation_audit_sha256=$(if ($UpstreamEvaluationAudit) { (Get-FileHash -LiteralPath $UpstreamEvaluationAudit).Hash } else { $null })
    effective_prompt=$Prompt;effective_negative_prompt=$NegativePrompt;seed=$Baseline.seed;steps=$Steps;cfg=4
    denoise=$Denoise;latent_prior_note='For denoise below1, the source VAE latent also contributes to initialization. This is structural retention, not a new identity signal.'
    framing_mode=$FramingMode;source_dimensions=$SourceDimensions;output_dimensions=$OutputDimensions
    reference_packing=$ReferencePacking;reference_packing_geometry=$PackingGeometry
    reference_packing_note='Native mode leaves the installed Plus encoder unchanged. Author32 mode keeps its grounded VL inputs, omits its optional VAE, and appends ordered native VAEEncode tensors via ReferenceLatent with author32 sizing; no new identity mechanism.'
    framing_note='Whole-frame mode replaces only author resize node160 with exact-aspect Lanczos resize, no crop. All native reference/model/sampler connections are retained.'
    reference_mode=$(if ($ExpressionReference) { 'scene_identity_original_expression' } elseif ($IdentityReference) { 'scene_plus_genuine_identity' } else { 'edit_target_only' })
    identity_mechanism='Qwen2511 trained portrait/multi-image editing via ordered grounded QwenVL semantic encoding and native VAE appearance-reference latents; generated edit target is not a genuine scoring reference'
    references=$References
    verified_models=$Verified;workers=$WorkerSnapshots;hardware=$Hardware
    author_template=$TemplatePath;author_template_sha256=(Get-FileHash -LiteralPath $TemplatePath).Hash
    native_node_sha256=(Get-FileHash -LiteralPath (Join-Path $ComfyRoot 'comfy_extras/nodes_qwen.py')).Hash
    research_gate='docs/upgrade-qwen-high-evaluation-2026-09-03.md';prompt=$Graph
}
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$Manifest | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath (Join-Path $Destination 'experiment.json') -Encoding utf8
if ($PrepareOnly) { Write-Output "Prepared $Destination"; return }
$Queue=Invoke-RestMethod "$Server/queue"
if (@($Queue.queue_running).Count -or @($Queue.queue_pending).Count) { throw 'Queue became busy during preflight.' }
$Body=@{prompt=$Graph;client_id="upgrade-qwen-$([guid]::NewGuid().ToString('N'))"} | ConvertTo-Json -Depth 25
$Submission=Invoke-RestMethod -Method Post "$Server/prompt" -ContentType 'application/json' -Body $Body -TimeoutSec 30
$Submission | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $Destination 'submission.json') -Encoding utf8
$Submission | ConvertTo-Json -Depth 12
