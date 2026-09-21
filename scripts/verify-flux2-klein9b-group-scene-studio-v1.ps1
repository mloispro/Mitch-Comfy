[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8188",
    [switch]$Smoke
)

$ErrorActionPreference = "Stop"
$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VisualWorkflowRelative = "workflows/production/FLUX.2 Klein 9B Mitch Group Scene Studio v1.1 - Visual Presets.json"
$GroupSourceRelative = "custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_group_scene_studio.py"
$VisualWrapperRelative = "custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_group_scene_studio_visual_presets.py"
$ScenePresetsRelative = "custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_scene_presets.py"
$VisualSupportRelative = "custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_visual_preset_support.py"
$PresetManifestRelative = "custom_nodes/ComfyUI-AIToolkit-Training/web/assets/scene-presets/manifest.json"
$VisualScriptRelative = "custom_nodes/ComfyUI-AIToolkit-Training/web/visual_scene_presets.js"
$VisualWorkflowPath = Join-Path $ProjectRoot $VisualWorkflowRelative.Replace("/", "\")
$PresetManifestPath = Join-Path $ProjectRoot $PresetManifestRelative.Replace("/", "\")
$InternalNodeName = "Flux2Klein9BMitchGroupSceneStudioV1"
$VisualNodeName = "Flux2Klein9BMitchGroupSceneStudioVisualPresetsV11"
$DefaultPresetKey = "approved-lounge-center"
$DefaultPresetLabel = "Approved lounge — central Mitch"
$DefaultPresetSource = "assets/comfy-input/klein9b-scene-presets/group-approved-lounge-center.png"
$DefaultPresetSourceHash = "1B26AC58A4FAD8D03F69DB7A4085C31B6682C71ACBE22D5AEE51F9E53FA0332B"
$DefaultPresetPromptHash = "D67FEA4634274750F390BACC8C9C102D377FC3585DF79A15384ADAB008459C67"
$EngineBaselineId = "flux2-klein9b-mitch-group-engine-speed-seam-20260909"
$VisualBaselineId = "flux2-klein9b-production-gallery-st-barts-20260920"
$ModelHash = "4A54FAD7F5F741B99EEE217198DAAC20B8D8E515E2A1F5B064FD51CF074F95BD"
$ClipHash = "ABAD16806E0CBABC54E0325D6565847443FE396D5F0BE38BB3CD3FE75A1201D6"
$VaeHash = "D64F3A68E1CC4F9F4E29B6E0DA38A0204FE9A49F2D4053F0EC1FA1CA02F9C4B5"
$LoraName = "m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors"
$LoraHash = "D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC"
$StyleLoraName = "smartphone-snapshot\FLUX.2-klein-base-9B_SmartphoneSnapshotPhotoReality_v13.safetensors"
$StyleLoraHash = "1E0B419B1448F77CF7AEF430625325E46B16D1515CBF6C5C7E8C14D938CF1A90"
$TurboLoraName = "flux2-klein9b-turbo\Flux_Klein_9b_Turbo_lora_rank_256_bf16_standard.safetensors"
$TurboLoraHash = "A3BFA40E936AF059C2D0814DE8E9E5531FA0EB135087ADD22C27510685585600"
$IdentityName = "mitch-klein9b-ref-training04-front-neutral.jpg"
$IdentityHash = "31870369467B7A8FC19199D7877F56257FED2B0F28B08AA183006BCD3112DDAB"
$SourceName = "mitch-klein9b-layout-lounge-center-source.png"

function Assert-Hash([string]$Path, [string]$Expected, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing $Label`: $Path" }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
    if ($actual -cne $Expected.ToUpperInvariant()) {
        throw "$Label SHA-256 mismatch. Expected $($Expected.ToUpperInvariant()), found $actual."
    }
}

function Assert-ExactSequence([object[]]$Actual, [object[]]$Expected, [string]$Label) {
    if ((@($Actual) -join "`n") -cne (@($Expected) -join "`n")) {
        throw "$Label drifted. Expected [$(@($Expected) -join ', ')], found [$(@($Actual) -join ', ')]."
    }
}

function Get-TextSha256([string]$Text) {
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($Text)
        return ([System.BitConverter]::ToString($algorithm.ComputeHash($bytes))).Replace("-", "")
    } finally {
        $algorithm.Dispose()
    }
}

function Assert-FrozenArtifactHash(
    [object]$Registry,
    [string]$BaselineId,
    [string]$RelativePath,
    [string]$Label
) {
    $baselines = @($Registry.baselines | Where-Object id -eq $BaselineId)
    if ($baselines.Count -ne 1) { throw "Frozen-baseline registry must contain exactly one $BaselineId entry." }
    $artifacts = @($baselines[0].artifacts | Where-Object path -eq $RelativePath)
    if ($artifacts.Count -ne 1 -or -not $artifacts[0].sha256) {
        throw "Frozen baseline $BaselineId is missing one SHA-256 entry for $RelativePath."
    }
    Assert-Hash (Join-Path $ProjectRoot $RelativePath.Replace("/", "\")) ([string]$artifacts[0].sha256) $Label
}

function Test-JsonNumber([object]$Value) {
    return (
        $Value -is [byte] -or $Value -is [sbyte] -or
        $Value -is [int16] -or $Value -is [uint16] -or
        $Value -is [int32] -or $Value -is [uint32] -or
        $Value -is [int64] -or $Value -is [uint64] -or
        $Value -is [single] -or $Value -is [double] -or $Value -is [decimal]
    )
}

function Resolve-ContainedPath([string]$Root, [string]$RelativePath, [string]$Label) {
    if ([System.IO.Path]::IsPathRooted($RelativePath)) { throw "$Label must be relative: $RelativePath" }
    $rootPath = [System.IO.Path]::GetFullPath($Root).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
    $resolved = [System.IO.Path]::GetFullPath((Join-Path $Root $RelativePath.Replace("/", "\")))
    if (-not $resolved.StartsWith($rootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label escapes its approved root: $RelativePath"
    }
    return $resolved
}

if (-not (Test-Path -LiteralPath $PresetManifestPath -PathType Leaf)) {
    throw "Missing canonical visual-preset manifest: $PresetManifestPath"
}
$PresetManifest = Get-Content -Raw -LiteralPath $PresetManifestPath | ConvertFrom-Json
if ([int]$PresetManifest.schema_version -ne 1) { throw "Unsupported visual-preset manifest schema." }
$GroupRecords = @($PresetManifest.group)
if ($GroupRecords.Count -ne 5) { throw "Visual-preset manifest must define exactly five Group cards." }
$GroupPresetLabels = @($GroupRecords | ForEach-Object { [string]$_.label })
$GroupPresetKeys = @($GroupRecords | ForEach-Object { [string]$_.key })
if (@($GroupPresetLabels | Where-Object { -not $_ }).Count -gt 0 -or @($GroupPresetKeys | Where-Object { -not $_ }).Count -gt 0) {
    throw "Every Group visual preset must have a nonempty key and label."
}
if (@($GroupPresetLabels | Select-Object -Unique).Count -ne $GroupPresetLabels.Count) { throw "Group visual-preset labels must be unique." }
if (@($GroupPresetKeys | Select-Object -Unique).Count -ne $GroupPresetKeys.Count) { throw "Group visual-preset keys must be unique." }

$ThumbnailRoot = Split-Path -Parent $PresetManifestPath
$CustomPresets = @($GroupRecords | Where-Object key -eq "custom-group")
if ($CustomPresets.Count -ne 1) { throw "Visual-preset manifest must contain exactly one custom Group preset." }
$CustomPreset = $CustomPresets[0]
$DefaultPresets = @($GroupRecords | Where-Object key -eq $DefaultPresetKey)
if ($DefaultPresets.Count -ne 1) { throw "Visual-preset manifest must contain exactly one Group preset keyed $DefaultPresetKey." }
$DefaultPreset = $DefaultPresets[0]

foreach ($record in $GroupRecords) {
    $recordLabel = "Group preset $($record.key)"
    if (-not [string]$record.thumbnail) { throw "$recordLabel is missing its thumbnail." }
    $thumbnailPath = Resolve-ContainedPath $ThumbnailRoot ([string]$record.thumbnail) "$recordLabel thumbnail"
    if (-not (Test-Path -LiteralPath $thumbnailPath -PathType Leaf)) { throw "$recordLabel thumbnail is missing: $thumbnailPath" }
    if ($null -eq $record.PSObject.Properties["prompt"]) { throw "$recordLabel is missing its prompt field." }

    foreach ($geometryName in "target_x", "target_y", "head_scale") {
        $geometryValue = $record.$geometryName
        if (-not (Test-JsonNumber $geometryValue)) { throw "$recordLabel $geometryName must be a JSON number." }
        $number = [double]$geometryValue
        $minimum = if ($geometryName -eq "head_scale") { 0.75 } else { 0.0 }
        if ($number -lt $minimum -or $number -gt 1.0) { throw "$recordLabel $geometryName is outside the validated range." }
    }

    if ([string]$record.key -eq "custom-group") {
        if ($null -ne $record.source_asset -or $null -ne $record.source_sha256 -or [string]$record.prompt -cne "") {
            throw "Custom Group preset must have null source/provenance and a blank prompt."
        }
        continue
    }

    if (-not [string]$record.prompt) { throw "$recordLabel must include a nonempty prepared prompt." }
    if ([string]$record.source_sha256 -cnotmatch "^[0-9A-F]{64}$") { throw "$recordLabel has an invalid source SHA-256." }
    $assetPath = Resolve-ContainedPath $ProjectRoot ([string]$record.source_asset) "$recordLabel source"
    Assert-Hash $assetPath ([string]$record.source_sha256) "$recordLabel source"
}

if ([string]$CustomPreset.label -cne "Custom — uploaded group photo") { throw "Custom Group preset label drifted." }
if ([string]$DefaultPreset.label -cne $DefaultPresetLabel) { throw "Primary Group visual-preset label drifted." }
if ([string]$DefaultPreset.source_asset -cne $DefaultPresetSource) { throw "Primary Group visual-preset source path drifted." }
if ([string]$DefaultPreset.source_sha256 -cne $DefaultPresetSourceHash) { throw "Primary Group visual-preset source hash drifted." }
if ([double]$DefaultPreset.target_x -ne 0.50 -or [double]$DefaultPreset.target_y -ne 0.44 -or [double]$DefaultPreset.head_scale -ne 0.92) {
    throw "Primary Group visual-preset target geometry drifted."
}
if ((Get-TextSha256 ([string]$DefaultPreset.prompt)) -cne $DefaultPresetPromptHash) {
    throw "Primary Group visual-preset prompt drifted from the accepted 700-character prompt."
}

$queueState = [ordered]@{}
foreach ($port in 8188, 8189, 8190) {
    try {
        $queue = Invoke-RestMethod -Uri "http://127.0.0.1:$port/queue" -TimeoutSec 5
        $running = @($queue.queue_running).Count
        $pending = @($queue.queue_pending).Count
        $queueState[[string]$port] = [ordered]@{ running = $running; pending = $pending }
        if ($Smoke -and ($running -gt 0 -or $pending -gt 0)) {
            throw "ComfyUI queue is active at port $port."
        }
        if (-not $Smoke -and ($running -gt 0 -or $pending -gt 0)) {
            Write-Warning "Port $port is active; read-only validation will continue without modifying it."
        }
    }
    catch {
        if ($port -eq ([uri]$Server).Port -or $_.Exception.Message -match "queue is active") { throw }
        Write-Warning "Optional worker port $port could not be inspected: $($_.Exception.Message)"
    }
}

$stats = Invoke-RestMethod -Uri "$Server/system_stats" -TimeoutSec 10
$device = [string]@($stats.devices)[0].name
if ($device -notmatch "RTX 3090") { throw "Group Scene Studio requires RTX 3090; worker reports $device" }

$retiredNodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$InternalNodeName" -TimeoutSec 20
if ($retiredNodeInfo.PSObject.Properties[$InternalNodeName]) {
    throw "Live ComfyUI worker still exposes retired public Group node $InternalNodeName"
}
$expectedRequiredInputs = @("source_scene", "scene_prompt", "target_x", "target_y", "head_scale", "appearance_polish", "fast_turbo", "seed")

$visualNodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$VisualNodeName" -TimeoutSec 20
if (-not $visualNodeInfo.PSObject.Properties[$VisualNodeName]) { throw "Live ComfyUI worker is missing primary wrapper $VisualNodeName" }
$liveVisualNode = $visualNodeInfo.$VisualNodeName
Assert-ExactSequence @($liveVisualNode.input_order.required) $expectedRequiredInputs "Live primary v1.1 Group required-input contract"
Assert-ExactSequence @($liveVisualNode.input_order.optional) @("scene_preset") "Live primary v1.1 Group optional-input contract"
Assert-ExactSequence @($liveVisualNode.output_name) @("photo", "layout_guide", "effective_prompt", "output_folder", "report_json") "Live primary v1.1 Group output contract"
$liveScenePromptDefault = [string]$liveVisualNode.input.required.scene_prompt[1].default
if ($liveScenePromptDefault -cne "") { throw "Live primary v1.1 Group extra scene direction must default blank." }
$scenePresetSpec = $liveVisualNode.input.optional.scene_preset
if (-not $scenePresetSpec) { throw "Live primary v1.1 Group wrapper lacks scene_preset metadata." }
Assert-ExactSequence @($scenePresetSpec[0]) $GroupPresetLabels "Live primary v1.1 Group preset choices"
if ([string]$scenePresetSpec[1].default -cne [string]$CustomPreset.label) {
    throw "Live primary v1.1 Group wrapper scene_preset default must be $($CustomPreset.label)."
}
$expectedManifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $PresetManifestPath).Hash.ToUpperInvariant()
if ([string]$scenePresetSpec[1].manifest_sha256 -cne $expectedManifestHash) {
    throw "Live primary v1.1 Group wrapper manifest hash metadata drifted."
}
if ([double]$liveVisualNode.input.required.target_x[1].default -ne 0.50) { throw "Live primary v1.1 Group target_x default drifted." }
if ([double]$liveVisualNode.input.required.target_y[1].default -ne 0.44) { throw "Live primary v1.1 Group target_y default drifted." }
if ([double]$liveVisualNode.input.required.head_scale[1].default -ne 0.92) { throw "Live primary v1.1 Group head_scale default drifted." }
if ([bool]$liveVisualNode.input.required.appearance_polish[1].default -ne $false) { throw "Live primary v1.1 Group appearance polish must default off." }
if ([bool]$liveVisualNode.input.required.fast_turbo[1].default -ne $false) { throw "Live primary v1.1 Group Turbo must default off." }
if ([int64]$liveVisualNode.input.required.seed[1].default -ne 8675412) { throw "Live primary v1.1 Group seed default drifted." }

foreach ($requirement in @(
    @{ Class = "UNETLoader"; Field = "unet_name"; Value = "flux-2-klein-base-9b-bf16.safetensors" },
    @{ Class = "CLIPLoader"; Field = "clip_name"; Value = "qwen_3_8b_fp8mixed.safetensors" },
    @{ Class = "VAELoader"; Field = "vae_name"; Value = "flux2-vae.safetensors" },
    @{ Class = "LoraLoaderModelOnly"; Field = "lora_name"; Value = $LoraName },
    @{ Class = "LoraLoaderModelOnly"; Field = "lora_name"; Value = $StyleLoraName },
    @{ Class = "LoraLoaderModelOnly"; Field = "lora_name"; Value = $TurboLoraName }
)) {
    $loaderInfo = Invoke-RestMethod -Uri "$Server/object_info/$($requirement.Class)" -TimeoutSec 20
    $choices = @($loaderInfo.($requirement.Class).input.required.($requirement.Field)[0])
    if ($requirement.Value -notin $choices) { throw "Live RTX 3090 worker cannot select $($requirement.Value)." }
}

if (-not (Test-Path -LiteralPath $VisualWorkflowPath -PathType Leaf)) { throw "Missing primary v1.1 visual-preset workflow: $VisualWorkflowPath" }
$visualWorkflow = Get-Content -Raw -LiteralPath $VisualWorkflowPath | ConvertFrom-Json
if ([string]$visualWorkflow.id -cne "flux2-klein9b-mitch-group-scene-studio-v1-1-visual-presets") {
    throw "Primary v1.1 Group workflow id drifted."
}
if (@($visualWorkflow.nodes | Where-Object type -eq $VisualNodeName).Count -ne 1) {
    throw "Primary v1.1 Group workflow must contain exactly one $VisualNodeName node."
}
if (@($visualWorkflow.nodes | Where-Object type -eq $InternalNodeName).Count -ne 0) {
    throw "Primary v1.1 Group workflow must use the visual wrapper, not a directly serialized frozen v1 node."
}
if (@($visualWorkflow.nodes | Where-Object type -eq "LoadImage").Count -ne 1) {
    throw "Primary v1.1 Group workflow must contain exactly one custom-source LoadImage node."
}
if (@($visualWorkflow.nodes | Where-Object type -eq "PreviewImage").Count -ne 2) {
    throw "Primary v1.1 Group workflow must preview both the generated photo and structural guide."
}
$visualStudioNode = @($visualWorkflow.nodes | Where-Object type -eq $VisualNodeName)[0]
Assert-ExactSequence @($visualStudioNode.inputs.name) @(
    "source_scene", "scene_prompt", "target_x", "target_y", "head_scale", "appearance_polish", "fast_turbo", "seed", "scene_preset"
) "Primary v1.1 Group workflow input contract"
if (@($visualStudioNode.widgets_values).Count -ne 9) { throw "Primary v1.1 Group workflow must serialize exactly nine widget values." }
if ([string]$visualStudioNode.widgets_values[0] -cne "") { throw "Primary v1.1 Group workflow must leave extra scene direction blank." }
if ([double]$visualStudioNode.widgets_values[1] -ne [double]$DefaultPreset.target_x) { throw "Primary v1.1 Group saved target_x differs from its manifest preset." }
if ([double]$visualStudioNode.widgets_values[2] -ne [double]$DefaultPreset.target_y) { throw "Primary v1.1 Group saved target_y differs from its manifest preset." }
if ([double]$visualStudioNode.widgets_values[3] -ne [double]$DefaultPreset.head_scale) { throw "Primary v1.1 Group saved head_scale differs from its manifest preset." }
if ([bool]$visualStudioNode.widgets_values[4] -ne $false) { throw "Primary v1.1 Group appearance polish must open disabled." }
if ([bool]$visualStudioNode.widgets_values[5] -ne $false) { throw "Primary v1.1 Group Turbo must open disabled." }
if ([int64]$visualStudioNode.widgets_values[6] -ne 8675412) { throw "Primary v1.1 Group seed drifted." }
if ([string]$visualStudioNode.widgets_values[7] -cne "fixed") { throw "Primary v1.1 Group seed control must remain fixed." }
if ([string]$visualStudioNode.widgets_values[8] -cne [string]$DefaultPreset.label) { throw "Primary v1.1 Group workflow must open on $($DefaultPreset.label)." }
$visualLoadNode = @($visualWorkflow.nodes | Where-Object type -eq "LoadImage")[0]
if ([string]$visualLoadNode.widgets_values[0] -cne $SourceName) { throw "Primary v1.1 Group custom-source fallback drifted." }
if ($null -eq $visualStudioNode.inputs[0].link) { throw "Primary v1.1 Group workflow must retain its custom-source image link." }

$groupSourcePath = Join-Path $ProjectRoot $GroupSourceRelative.Replace("/", "\")
$groupSource = Get-Content -Raw -LiteralPath $groupSourcePath
foreach ($requiredText in @(
    "Canny edge map derived from the source photograph",
    "does not supply his identity",
    "exclusively ",
    "supplies the selected man's identity and internal facial geometry",
    "GROUP_IDENTITY_SAFE_POLISH",
    '"default": False'
)) {
    if ($groupSource -notmatch [regex]::Escape($requiredText)) {
        throw "Production Group Studio is missing the concise identity-first contract: $requiredText"
    }
}
foreach ($rejectedText in @("preserve_bone_structure=True", "Present him about three to five years younger")) {
    if ($groupSource -match [regex]::Escape($rejectedText)) {
        throw "Production Group Studio still contains rejected identity-drifting prompt text: $rejectedText"
    }
}

$visualWrapperPath = Join-Path $ProjectRoot $VisualWrapperRelative.Replace("/", "\")
if (-not (Test-Path -LiteralPath $visualWrapperPath -PathType Leaf)) { throw "Missing primary v1.1 Group wrapper: $visualWrapperPath" }
$visualWrapperSource = Get-Content -Raw -LiteralPath $visualWrapperPath
foreach ($provenanceContract in @(
    "class Flux2Klein9BMitchGroupSceneStudioVisualPresetsV11",
    "Flux2Klein9BMitchGroupSceneStudioV1",
    "PRESET_MANIFEST_SHA256",
    "verify_asset_sha256",
    'shell_name="flux2_klein9b_mitch_group_scene_studio_v1_1_visual_presets"',
    '"label": scene_preset',
    '"key": record["key"]',
    '"manifest_sha256": PRESET_MANIFEST_SHA256',
    '"source": str(source_path) if source_path else None',
    '"source_sha256": record.get("source_sha256")',
    '"target_x_input": float(target_x)',
    '"target_y_input": float(target_y)',
    '"head_scale_input": float(head_scale)',
    '"target_x_effective": resolved_x',
    '"target_y_effective": resolved_y',
    '"head_scale_effective": resolved_head_scale',
    '"scene_prompt_input": scene_prompt.strip()',
    '"scene_prompt_effective": resolved_prompt'
)) {
    if ($visualWrapperSource -notmatch [regex]::Escape($provenanceContract)) {
        throw "Primary v1.1 Group wrapper is missing provenance contract: $provenanceContract"
    }
}

$FrozenRegistryPath = Join-Path $ProjectRoot "config\frozen-baselines.json"
if (-not (Test-Path -LiteralPath $FrozenRegistryPath -PathType Leaf)) { throw "Missing frozen-baseline registry: $FrozenRegistryPath" }
$FrozenRegistry = Get-Content -Raw -LiteralPath $FrozenRegistryPath | ConvertFrom-Json
foreach ($artifact in @(
    @{ Baseline = $EngineBaselineId; Path = $GroupSourceRelative; Label = "generation-locked Group engine" },
    @{ Baseline = $VisualBaselineId; Path = $VisualWorkflowRelative; Label = "primary v1.1 Group workflow" },
    @{ Baseline = $VisualBaselineId; Path = $VisualWrapperRelative; Label = "primary v1.1 Group wrapper" },
    @{ Baseline = $VisualBaselineId; Path = $ScenePresetsRelative; Label = "canonical visual-preset resolver" },
    @{ Baseline = $VisualBaselineId; Path = $VisualSupportRelative; Label = "visual-preset provenance helper" },
    @{ Baseline = $VisualBaselineId; Path = $PresetManifestRelative; Label = "canonical visual-preset manifest" },
    @{ Baseline = $VisualBaselineId; Path = $VisualScriptRelative; Label = "visual-preset browser extension" }
)) {
    Assert-FrozenArtifactHash $FrozenRegistry $artifact.Baseline $artifact.Path $artifact.Label
}

$modelPath = Join-Path $ComfyRoot "models\diffusion_models\flux-2-klein-base-9b-bf16.safetensors"
$clipPath = Join-Path $ComfyRoot "models\text_encoders\qwen_3_8b_fp8mixed.safetensors"
$vaePath = Join-Path $ComfyRoot "models\vae\flux2-vae.safetensors"
$loraPath = Join-Path $ComfyRoot "models\loras\$LoraName"
$styleLoraPath = Join-Path $ComfyRoot "models\loras\$StyleLoraName"
$turboLoraPath = Join-Path $ComfyRoot "models\loras\$TurboLoraName"
$identityPath = Join-Path $ComfyRoot "input\$IdentityName"
$sourcePath = Join-Path $ComfyRoot "input\$SourceName"
Assert-Hash $modelPath $ModelHash "Klein Base 9B BF16 model"
Assert-Hash $clipPath $ClipHash "Qwen 3 8B text encoder"
Assert-Hash $vaePath $VaeHash "FLUX.2 VAE"
Assert-Hash $loraPath $LoraHash "protected Klein 9B step-1600 LoRA"
Assert-Hash $styleLoraPath $StyleLoraHash "Smartphone Snapshot v13 LoRA"
Assert-Hash $turboLoraPath $TurboLoraHash "rank-256 BF16 Turbo LoRA"
Assert-Hash $identityPath $IdentityHash "protected identity reference"
Assert-Hash $sourcePath $DefaultPresetSourceHash "primary Group custom-source fallback"

$validation = [ordered]@{
    status = "passed"
    workflow = $VisualWorkflowPath
    node = $VisualNodeName
    internal_engine = $GroupSourceRelative
    gpu = $device
    model_sha256 = $ModelHash
    text_encoder_sha256 = $ClipHash
    vae_sha256 = $VaeHash
    lora = $LoraName
    smartphone_style = [ordered]@{ lora = $StyleLoraName; sha256 = $StyleLoraHash; strength = 0.25; trigger = "casual snapshot" }
    turbo = [ordered]@{ lora = $TurboLoraName; sha256 = $TurboLoraHash; strength = 1.0; enabled_by_default = $false; enabled_settings = "8 Euler steps / CFG 1"; quality_fallback = "50 Euler steps / CFG 4" }
    identity_reference = $IdentityName
    visual_preset = [ordered]@{
        key = $DefaultPresetKey
        label = $DefaultPresetLabel
        manifest_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $PresetManifestPath).Hash.ToUpperInvariant()
        source = $DefaultPresetSource
        source_sha256 = $DefaultPresetSourceHash
        prompt_sha256 = $DefaultPresetPromptHash
        target_x = 0.50
        target_y = 0.44
        head_scale = 0.92
    }
    queues = $queueState
    smoke_requested = [bool]$Smoke
    smoke_node = if ($Smoke) { $VisualNodeName } else { $null }
}
if (-not $Smoke) {
    $validation | ConvertTo-Json -Depth 10
    exit 0
}

$prompt = [ordered]@{
    "1" = @{ class_type = "LoadImage"; inputs = @{ image = $SourceName } }
    "2" = @{
        class_type = $VisualNodeName
        inputs = @{
            source_scene = @("1", 0)
            scene_prompt = ""
            target_x = 0.50
            target_y = 0.44
            head_scale = 0.92
            appearance_polish = $false
            fast_turbo = $false
            seed = 8675412
            scene_preset = $DefaultPresetLabel
        }
    }
}
$body = @{ prompt = $prompt; client_id = [guid]::NewGuid().ToString() } | ConvertTo-Json -Depth 100
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id" }

$deadline = (Get-Date).AddMinutes(15)
do {
    Start-Sleep -Seconds 5
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 15
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry) {
        if ($entry.status.status_str -eq "error") {
            throw "Smoke generation failed: $($entry.status.messages | ConvertTo-Json -Depth 30)"
        }
        if ($entry.status.completed) {
            $images = @($entry.outputs."2".images)
            if ($images.Count -eq 0) { throw "Smoke generation completed without a saved photo" }
            $saved = foreach ($image in $images) {
                $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                Join-Path (Join-Path $ComfyRoot "output") $relative
            }
            $validation.smoke_prompt_id = $queued.prompt_id
            $validation.smoke_outputs = @($saved)
            $validation | ConvertTo-Json -Depth 20
            exit 0
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for Group Scene Studio smoke generation"
