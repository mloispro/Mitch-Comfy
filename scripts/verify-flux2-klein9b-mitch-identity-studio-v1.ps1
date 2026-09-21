[CmdletBinding()]
param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$Server = "http://127.0.0.1:8188"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$errors = [System.Collections.Generic.List[string]]::new()

function Assert-FileHash {
    param([string]$Path, [string]$Expected, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        $errors.Add("Missing $Label`: $Path")
        return
    }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
    if ($actual -cne $Expected.ToUpperInvariant()) {
        $errors.Add("$Label SHA-256 mismatch: $actual")
    }
}

function Assert-FrozenArtifactHash {
    param(
        [object]$Registry,
        [string]$BaselineId,
        [string]$RelativePath,
        [string]$Label
    )
    $baselines = @($Registry.baselines | Where-Object id -eq $BaselineId)
    if ($baselines.Count -ne 1) {
        $errors.Add("Frozen-baseline registry must contain exactly one $BaselineId entry.")
        return
    }
    $artifacts = @($baselines[0].artifacts | Where-Object path -eq $RelativePath)
    if ($artifacts.Count -ne 1 -or -not $artifacts[0].sha256) {
        $errors.Add("Frozen baseline $BaselineId is missing one SHA-256 entry for $RelativePath.")
        return
    }
    Assert-FileHash (
        Join-Path $repoRoot $RelativePath.Replace("/", "\")
    ) ([string]$artifacts[0].sha256) $Label
}

function Assert-ExactSequence {
    param([object[]]$Actual, [object[]]$Expected, [string]$Label)
    $actualText = @($Actual) -join "`n"
    $expectedText = @($Expected) -join "`n"
    if ($actualText -cne $expectedText) {
        $errors.Add("$Label drifted. Expected [$(@($Expected) -join ', ')], found [$(@($Actual) -join ', ')].")
    }
}

$visualWorkflowRelative = "workflows/production/FLUX.2 Klein 9B Mitch Identity Studio v1.1 - Visual Presets.json"
$visualWrapperRelative = "custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_mitch_identity_studio_visual_presets.py"
$scenePresetsRelative = "custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_scene_presets.py"
$visualSupportRelative = "custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_visual_preset_support.py"
$presetManifestRelative = "custom_nodes/ComfyUI-AIToolkit-Training/web/assets/scene-presets/manifest.json"
$visualScriptRelative = "custom_nodes/ComfyUI-AIToolkit-Training/web/visual_scene_presets.js"
$visualWorkflowPath = Join-Path $repoRoot $visualWorkflowRelative.Replace("/", "\")
$visualWrapperPath = Join-Path $repoRoot $visualWrapperRelative.Replace("/", "\")
$presetManifestPath = Join-Path $repoRoot $presetManifestRelative.Replace("/", "\")
$internalNodeName = "Flux2Klein9BMitchIdentityStudioV1"
$visualNodeName = "Flux2Klein9BMitchIdentityStudioVisualPresetsV11"
$defaultPresetKey = "rooftop-cocktail-city-lights"

$presetManifest = $null
$defaultPreset = $null
$customPreset = $null
$identityPresetLabels = @()
if (-not (Test-Path -LiteralPath $presetManifestPath -PathType Leaf)) {
    $errors.Add("Missing canonical visual-preset manifest: $presetManifestPath")
} else {
    try {
        $presetManifest = Get-Content -Raw -LiteralPath $presetManifestPath | ConvertFrom-Json
        if ([int]$presetManifest.schema_version -ne 1) { $errors.Add("Unsupported visual-preset manifest schema.") }
        $identityPresetLabels = @($presetManifest.identity | ForEach-Object { [string]$_.label })
        $customPresets = @($presetManifest.identity | Where-Object key -eq "custom")
        if ($customPresets.Count -ne 1) {
            $errors.Add("Visual-preset manifest must contain exactly one custom Identity preset.")
        } else {
            $customPreset = $customPresets[0]
        }
        $defaultPresets = @($presetManifest.identity | Where-Object key -eq $defaultPresetKey)
        if ($defaultPresets.Count -ne 1) {
            $errors.Add("Visual-preset manifest must contain exactly one Identity preset keyed $defaultPresetKey.")
        } else {
            $defaultPreset = $defaultPresets[0]
            if (-not [string]$defaultPreset.prompt) { $errors.Add("Primary Identity visual preset must include its complete tested prompt.") }
        }
    } catch {
        $errors.Add("Visual-preset manifest is invalid: $($_.Exception.Message)")
    }
}

if (-not (Test-Path -LiteralPath $visualWorkflowPath -PathType Leaf)) {
    $errors.Add("Missing primary v1.1 visual-preset workflow: $visualWorkflowPath")
} else {
    try {
        $visualWorkflow = Get-Content -Raw -LiteralPath $visualWorkflowPath | ConvertFrom-Json
        if (@($visualWorkflow.nodes).Count -ne 3) { $errors.Add("Primary v1.1 workflow must contain exactly three visible nodes.") }
        foreach ($nodeType in "MarkdownNote", $visualNodeName, "PreviewImage") {
            if ($nodeType -notin @($visualWorkflow.nodes.type)) { $errors.Add("Primary v1.1 workflow is missing node: $nodeType") }
        }
        $visualNode = @($visualWorkflow.nodes | Where-Object type -eq $visualNodeName)[0]
        if ($visualNode) {
            Assert-ExactSequence -Actual @($visualNode.inputs.name) -Expected @(
                "reference_profile", "scene_prompt", "appearance_polish", "fast_turbo", "seed", "scene_preset"
            ) -Label "Primary v1.1 Identity input contract"
            if (@($visualNode.widgets_values).Count -lt 7) { $errors.Add("Primary v1.1 Identity workflow is missing saved preset widgets.") }
            if ($defaultPreset) {
                if ([string]$visualNode.widgets_values[6] -cne [string]$defaultPreset.label) { $errors.Add("Primary v1.1 Identity workflow must open on $($defaultPreset.label).") }
                if ([string]$visualNode.widgets_values[0] -cne [string]$defaultPreset.profile) { $errors.Add("Primary v1.1 Identity workflow reference profile must match the saved preset profile.") }
            }
            if ([string]$visualNode.widgets_values[1] -cne "") { $errors.Add("Primary v1.1 Identity workflow must leave extra scene direction blank by default.") }
            if ([bool]$visualNode.widgets_values[2] -ne $true) { $errors.Add("Primary v1.1 Identity workflow must open with appearance polish enabled.") }
            if ([bool]$visualNode.widgets_values[3] -ne $true) { $errors.Add("Primary v1.1 Identity workflow must open in validated Turbo mode.") }
            if ([int64]$visualNode.widgets_values[4] -ne 8675411) { $errors.Add("Primary v1.1 Identity workflow seed drifted.") }
        }
    } catch {
        $errors.Add("Primary v1.1 Identity workflow JSON is invalid: $($_.Exception.Message)")
    }
}

if (-not (Test-Path -LiteralPath $visualWrapperPath -PathType Leaf)) {
    $errors.Add("Missing primary v1.1 Identity visual-preset wrapper: $visualWrapperPath")
} else {
    $visualWrapperSource = Get-Content -Raw -LiteralPath $visualWrapperPath
    foreach ($provenanceContract in @(
        "class Flux2Klein9BMitchIdentityStudioVisualPresetsV11",
        "Flux2Klein9BMitchIdentityStudioV1",
        "PRESET_MANIFEST_SHA256",
        'shell_name="flux2_klein9b_mitch_identity_studio_v1_1_visual_presets"',
        '"label": scene_preset',
        '"key": record["key"]',
        '"manifest_sha256": PRESET_MANIFEST_SHA256',
        '"reference_profile_input": reference_profile',
        '"reference_profile_effective": resolved_profile',
        '"scene_prompt_input": scene_prompt.strip()',
        '"scene_prompt_effective": resolved_prompt'
    )) {
        if ($visualWrapperSource -notmatch [regex]::Escape($provenanceContract)) {
            $errors.Add("Primary v1.1 Identity wrapper is missing provenance contract: $provenanceContract")
        }
    }
}

$frozenRegistryPath = Join-Path $repoRoot "config\frozen-baselines.json"
if (-not (Test-Path -LiteralPath $frozenRegistryPath -PathType Leaf)) {
    $errors.Add("Missing frozen-baseline registry: $frozenRegistryPath")
} else {
    try {
        $frozenRegistry = Get-Content -Raw -LiteralPath $frozenRegistryPath | ConvertFrom-Json
        foreach ($artifact in @(
            @{ Baseline = "flux2-klein9b-mitch-identity-engine-v1"; Path = "custom_nodes/ComfyUI-AIToolkit-Training/flux2_klein9b_mitch_identity_studio.py"; Label = "generation-locked Identity engine" },
            @{ Baseline = "flux2-klein9b-production-gallery-st-barts-20260920"; Path = $visualWorkflowRelative; Label = "primary v1.1 Identity workflow" },
            @{ Baseline = "flux2-klein9b-production-gallery-st-barts-20260920"; Path = $visualWrapperRelative; Label = "primary v1.1 Identity wrapper" },
            @{ Baseline = "flux2-klein9b-production-gallery-st-barts-20260920"; Path = $scenePresetsRelative; Label = "canonical visual-preset resolver" },
            @{ Baseline = "flux2-klein9b-production-gallery-st-barts-20260920"; Path = $visualSupportRelative; Label = "visual-preset provenance helper" },
            @{ Baseline = "flux2-klein9b-production-gallery-st-barts-20260920"; Path = $presetManifestRelative; Label = "canonical visual-preset manifest" },
            @{ Baseline = "flux2-klein9b-production-gallery-st-barts-20260920"; Path = $visualScriptRelative; Label = "visual-preset browser extension" }
        )) {
            Assert-FrozenArtifactHash -Registry $frozenRegistry -BaselineId $artifact.Baseline -RelativePath $artifact.Path -Label $artifact.Label
        }
    } catch {
        $errors.Add("Frozen-baseline registry is invalid: $($_.Exception.Message)")
    }
}

$nodeSourcePath = Join-Path $repoRoot "custom_nodes\ComfyUI-AIToolkit-Training\flux2_klein9b_mitch_identity_studio.py"
$styleSourcePath = Join-Path $repoRoot "custom_nodes\ComfyUI-AIToolkit-Training\flux2_klein9b_smartphone_style.py"
$turboSourcePath = Join-Path $repoRoot "custom_nodes\ComfyUI-AIToolkit-Training\flux2_klein9b_turbo.py"
if (-not (Test-Path -LiteralPath $nodeSourcePath -PathType Leaf)) {
    $errors.Add("Missing Klein 9B Studio implementation: $nodeSourcePath")
} else {
    $source = Get-Content -Raw -LiteralPath $nodeSourcePath
    foreach ($lockedText in @(
        'MODEL_NAME = "flux-2-klein-base-9b-bf16.safetensors"',
        'LORA_NAME = "m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors"',
        'LORA_STRENGTH = 0.90', 'WIDTH = 832', 'HEIGHT = 1216', 'STEPS = 50', 'GUIDANCE = 4.0',
        '"appearance_polish": (', '"fast_turbo": (', '"default": True',
        'sampling_settings(fast_turbo, STEPS, GUIDANCE)',
        'KSamplerSelect.execute("euler")', 'Flux2Scheduler.execute(steps, WIDTH, HEIGHT)', '"RTX 3090" not in device_name'
    )) {
        if ($source -notmatch [regex]::Escape($lockedText)) { $errors.Add("Klein 9B Studio is missing locked setting: $lockedText") }
    }
}
if (-not (Test-Path -LiteralPath $turboSourcePath -PathType Leaf)) {
    $errors.Add("Missing locked Klein 9B Turbo contract: $turboSourcePath")
} else {
    $turboSource = Get-Content -Raw -LiteralPath $turboSourcePath
    foreach ($lockedText in @(
        'TURBO_LORA_BYTES = 1_386_477_008',
        'TURBO_LORA_STRENGTH = 1.0',
        'TURBO_STEPS = 8',
        'TURBO_GUIDANCE = 1.0'
    )) {
        if ($turboSource -notmatch [regex]::Escape($lockedText)) { $errors.Add("Turbo contract is missing locked setting: $lockedText") }
    }
}
if (-not (Test-Path -LiteralPath $styleSourcePath -PathType Leaf)) {
    $errors.Add("Missing locked Smartphone Snapshot style contract: $styleSourcePath")
} else {
    $styleSource = Get-Content -Raw -LiteralPath $styleSourcePath
    foreach ($lockedText in @(
        'SMARTPHONE_STYLE_LORA_STRENGTH = 0.25',
        'SMARTPHONE_STYLE_TRIGGER = "casual snapshot"',
        'SMARTPHONE_STYLE_BASE_MODEL = "flux2_klein_9b"',
        'SMARTPHONE_STYLE_CIVITAI_VERSION_ID = 2916530'
    )) {
        if ($styleSource -notmatch [regex]::Escape($lockedText)) { $errors.Add("Smartphone style contract is missing locked setting: $lockedText") }
    }
}

Assert-FileHash (Join-Path $ComfyRoot "models\diffusion_models\flux-2-klein-base-9b-bf16.safetensors") "4A54FAD7F5F741B99EEE217198DAAC20B8D8E515E2A1F5B064FD51CF074F95BD" "Klein Base 9B BF16 model"
Assert-FileHash (Join-Path $ComfyRoot "models\text_encoders\qwen_3_8b_fp8mixed.safetensors") "ABAD16806E0CBABC54E0325D6565847443FE396D5F0BE38BB3CD3FE75A1201D6" "Qwen 3 8B text encoder"
Assert-FileHash (Join-Path $ComfyRoot "models\vae\flux2-vae.safetensors") "D64F3A68E1CC4F9F4E29B6E0DA38A0204FE9A49F2D4053F0EC1FA1CA02F9C4B5" "FLUX.2 VAE"
Assert-FileHash (Join-Path $ComfyRoot "models\loras\m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors") "D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC" "protected Klein 9B step-1600 LoRA"
Assert-FileHash (Join-Path $ComfyRoot "models\loras\smartphone-snapshot\FLUX.2-klein-base-9B_SmartphoneSnapshotPhotoReality_v13.safetensors") "1E0B419B1448F77CF7AEF430625325E46B16D1515CBF6C5C7E8C14D938CF1A90" "locked Smartphone Snapshot v13 LoRA"
Assert-FileHash (Join-Path $ComfyRoot "models\loras\flux2-klein9b-turbo\Flux_Klein_9b_Turbo_lora_rank_256_bf16_standard.safetensors") "A3BFA40E936AF059C2D0814DE8E9E5531FA0EB135087ADD22C27510685585600" "locked rank-256 BF16 Turbo LoRA"

foreach ($reference in @(
    @{ File = "mitch-klein9b-ref-front-neutral-v2.jpg"; Hash = "28DF2AE0D717A788370CC825F7BB24CF38DB9C7CDA3F66BAEFAB58BE86D8AF33" },
    @{ File = "mitch-klein9b-ref-left-3q-v2.jpg"; Hash = "1DBEDEE1F712222F4E183D0B7648AA4739510CD86DB8B097697D2CB2C4ECEB08" },
    @{ File = "mitch-klein9b-ref-right-3q-v2.jpg"; Hash = "2F502B5233950BB01808FC3168540D54B8CC3A09894E2895D003C10A69EAA3BA" },
    @{ File = "flux2-dev-ref-04-full-body.jpg"; Hash = "C5F57CC155075071F8F761356E3AD1153AA0BCE55825A52226B2A4E8A19365FC" }
)) {
    Assert-FileHash (Join-Path $ComfyRoot ("input\" + $reference.File)) $reference.Hash ("genuine reference " + $reference.File)
}

foreach ($protected in @(
    "scripts\run-flux2-klein9b-v3-lora-native-ref-nine-scenes-3090.ps1",
    "work\flux2-klein9b-identity-v3-r32-dop\lora-native-reference-nine-scenes\full-nine-s090-ref025\manifest.json",
    "work\flux2-klein9b-identity-v3-r32-dop\lora-native-reference-nine-scenes\full-nine-s090-ref025\RESULTS.md"
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $protected) -PathType Leaf)) { $errors.Add("Missing protected winner artifact: $protected") }
}

$archivePairs = @(
    @{ Source = "workflows\production\FLUX.2 Dev Mitch Scene Studio v1.json"; Destination = "checkpoints\legacy-workflows\production\FLUX.2 Dev Mitch Scene Studio v1.json" },
    @{ Source = "workflows\production\FLUX.2 Easy Social Photos v1.0.4 - Auto Scene Routing.json"; Destination = "checkpoints\legacy-workflows\production\FLUX.2 Easy Social Photos v1.0.4 - Auto Scene Routing.json" },
    @{ Source = "workflows\production\FLUX.2 No-LoRA Strong Identity Street Corner v1.json"; Destination = "checkpoints\legacy-workflows\production\FLUX.2 No-LoRA Strong Identity Street Corner v1.json" },
    @{ Source = "workflows\production\Krea 2 Identity Anchor Crowd v1.json"; Destination = "checkpoints\legacy-workflows\production\Krea 2 Identity Anchor Crowd v1.json" },
    @{ Source = "workflows\production\Krea 2 Identity Edit - Face Attention v2.json"; Destination = "checkpoints\legacy-workflows\production\Krea 2 Identity Edit - Face Attention v2.json" },
    @{ Source = "workflows\production\Krea 2 No Character LoRA Street Corner v1.json"; Destination = "checkpoints\legacy-workflows\production\Krea 2 No Character LoRA Street Corner v1.json" },
    @{ Source = "workflows\production\ReActor Multi-Person Identity Finish - Sharper Face.json"; Destination = "checkpoints\legacy-workflows\production\ReActor Multi-Person Identity Finish - Sharper Face.json" },
    @{ Source = "workflows\experiments\HiDream-O1 Dev Native 2-Reference Dating Identity - Test.json"; Destination = "checkpoints\legacy-workflows\experiments\HiDream-O1 Dev Native 2-Reference Dating Identity - Test.json" },
    @{ Source = "workflows\experiments\HiDream-O1 Dev Native 3-Reference Dating Identity - Seed Screen.json"; Destination = "checkpoints\legacy-workflows\experiments\HiDream-O1 Dev Native 3-Reference Dating Identity - Seed Screen.json" },
    @{ Source = "workflows\experiments\HiDream-O1 Full Native 2-Reference Dating Identity - Test.json"; Destination = "checkpoints\legacy-workflows\experiments\HiDream-O1 Full Native 2-Reference Dating Identity - Test.json" },
    @{ Source = "workflows\experiments\InfiniteYou FLUX.1 Dev One Reference - Tested Rejected.json"; Destination = "checkpoints\legacy-workflows\experiments\InfiniteYou FLUX.1 Dev One Reference - Tested Rejected.json" }
)
foreach ($pair in $archivePairs) {
    if (Test-Path -LiteralPath (Join-Path $repoRoot $pair.Source)) { $errors.Add("Obsolete workflow is still visible: $($pair.Source)") }
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $pair.Destination) -PathType Leaf)) { $errors.Add("Archived workflow is missing: $($pair.Destination)") }
}

try {
    $stats = Invoke-RestMethod -Uri "$Server/system_stats" -TimeoutSec 10
    $device = [string]$stats.devices[0].name
    if ($device -notmatch "RTX 3090") { $errors.Add("Selected live worker is not the RTX 3090: $device") }
    $queue = Invoke-RestMethod -Uri "$Server/queue" -TimeoutSec 10
    if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) { $errors.Add("RTX 3090 queue is not idle.") }
    $retiredNodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$internalNodeName" -TimeoutSec 30
    if ($retiredNodeInfo.PSObject.Properties[$internalNodeName]) {
        $errors.Add("Live RTX 3090 worker still exposes retired public Identity node $internalNodeName.")
    }

    $visualNodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$visualNodeName" -TimeoutSec 30
    if (-not $visualNodeInfo.PSObject.Properties[$visualNodeName]) {
        $errors.Add("Live RTX 3090 worker does not expose primary wrapper $visualNodeName.")
    } else {
        $liveVisualNode = $visualNodeInfo.$visualNodeName
        Assert-ExactSequence -Actual @($liveVisualNode.input_order.required) -Expected @(
            "reference_profile", "scene_prompt", "appearance_polish", "fast_turbo", "seed"
        ) -Label "Live primary v1.1 Identity required-input contract"
        Assert-ExactSequence -Actual @($liveVisualNode.input_order.optional) -Expected @("scene_preset") -Label "Live primary v1.1 Identity optional-input contract"

        $scenePresetSpec = $liveVisualNode.input.optional.scene_preset
        if (-not $scenePresetSpec) {
            $errors.Add("Live primary v1.1 Identity wrapper does not expose scene_preset metadata.")
        } else {
            Assert-ExactSequence -Actual @($scenePresetSpec[0]) -Expected $identityPresetLabels -Label "Live primary v1.1 Identity preset choices"
            if ($customPreset -and [string]$scenePresetSpec[1].default -cne [string]$customPreset.label) {
                $errors.Add("Live primary v1.1 Identity wrapper scene_preset default must be $($customPreset.label).")
            }
            $expectedManifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $presetManifestPath).Hash.ToUpperInvariant()
            if ([string]$scenePresetSpec[1].manifest_sha256 -cne $expectedManifestHash) {
                $errors.Add("Live primary v1.1 Identity wrapper manifest hash metadata drifted.")
            }
        }

        if ($presetManifest) {
            $expectedProfiles = @(
                [string]$presetManifest.reference_profiles.group,
                [string]$presetManifest.reference_profiles.solo_left,
                [string]$presetManifest.reference_profiles.solo_right,
                [string]$presetManifest.reference_profiles.full_body
            )
            $referenceProfileSpec = $liveVisualNode.input.required.reference_profile
            Assert-ExactSequence -Actual @($referenceProfileSpec[0]) -Expected $expectedProfiles -Label "Live primary v1.1 Identity reference-profile choices"
            if ([string]$referenceProfileSpec[1].default -cne [string]$presetManifest.reference_profiles.group) {
                $errors.Add("Live primary v1.1 Identity reference_profile default drifted from the frozen engine.")
            }
        }
        if ([string]$liveVisualNode.input.required.scene_prompt[1].default -cne "") { $errors.Add("Live primary v1.1 Identity extra scene direction must default blank.") }
        if ([bool]$liveVisualNode.input.required.appearance_polish[1].default -ne $true) { $errors.Add("Live primary v1.1 Identity appearance polish must default on.") }
        if ([bool]$liveVisualNode.input.required.fast_turbo[1].default -ne $true) { $errors.Add("Live primary v1.1 Identity Turbo must default on.") }
        if ([int64]$liveVisualNode.input.required.seed[1].default -ne 8675411) { $errors.Add("Live primary v1.1 Identity seed default drifted.") }
    }
    foreach ($requirement in @(
        @{ Class = "UNETLoader"; Field = "unet_name"; Value = "flux-2-klein-base-9b-bf16.safetensors" },
        @{ Class = "LoraLoaderModelOnly"; Field = "lora_name"; Value = "m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors" },
        @{ Class = "LoraLoaderModelOnly"; Field = "lora_name"; Value = "smartphone-snapshot\FLUX.2-klein-base-9B_SmartphoneSnapshotPhotoReality_v13.safetensors" },
        @{ Class = "LoraLoaderModelOnly"; Field = "lora_name"; Value = "flux2-klein9b-turbo\Flux_Klein_9b_Turbo_lora_rank_256_bf16_standard.safetensors" },
        @{ Class = "CLIPLoader"; Field = "clip_name"; Value = "qwen_3_8b_fp8mixed.safetensors" },
        @{ Class = "VAELoader"; Field = "vae_name"; Value = "flux2-vae.safetensors" }
    )) {
        $info = Invoke-RestMethod -Uri "$Server/object_info/$($requirement.Class)" -TimeoutSec 30
        $choices = @($info.($requirement.Class).input.required.($requirement.Field)[0])
        if ($requirement.Value -notin $choices) { $errors.Add("Live RTX 3090 worker cannot select $($requirement.Value).") }
    }
} catch {
    $errors.Add("Could not verify the live RTX 3090 worker: $($_.Exception.Message)")
}

if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Host "Verified the public Identity v1.1 workflow, protected internal engine, live RTX 3090 surface/models, and all eleven hidden archives."
