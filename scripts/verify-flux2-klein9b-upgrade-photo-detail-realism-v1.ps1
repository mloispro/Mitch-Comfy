[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8188",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$ForgeUrl = "http://127.0.0.1:7860",
    [switch]$Smoke,
    [switch]$Native,
    [int]$TimeoutSeconds = 1800,
    [int]$MaxIdle3090MemoryMiB = 4096,
    [int]$MaxIdle3090Utilization = 10
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WorkflowPath = Join-Path $ProjectRoot "workflows\production\FLUX.2 Klein 9B - Upgrade Photo Detail & Realism v1.1.json"
$NodePath = Join-Path $ProjectRoot "custom_nodes\ComfyUI-AIToolkit-Training\flux2_klein9b_photo_realism_upgrade.py"
$RegistryPath = Join-Path $ProjectRoot "custom_nodes\ComfyUI-AIToolkit-Training\nodes.py"
$PresetPath = Join-Path $ProjectRoot "custom_nodes\ComfyUI-AIToolkit-Training\flux2_klein9b_photo_realism_upgrade_presets.py"
$PolishPath = Join-Path $ProjectRoot "custom_nodes\ComfyUI-AIToolkit-Training\flux2_klein9b_deterministic_polish.py"
$GazePath = Join-Path $ProjectRoot "custom_nodes\ComfyUI-AIToolkit-Training\flux2_klein9b_source_gaze_lock.py"
$MaskingPath = Join-Path $ProjectRoot "custom_nodes\ComfyUI-AIToolkit-Training\flux2_klein9b_upgrade_masking.py"
$NodeName = "Flux2Klein9BPhotoRealismUpgradeV11"
$InternalNodeName = "Flux2Klein9BPhotoRealismUpgradeV1"
$SourceName = "mitch-photo2-source-aef87048.png"
$Detail = "For this included example, the man remains in the exact source three-quarter view and looks past the camera toward image-right. Preserve the exact raised-collar coat silhouette, shirt opening, building-wall diagonals, roof edge, bare-tree layout, and every foreground/background boundary. Render the same real house exterior with separate horizontal siding boards, narrow straight seams, subtle matte painted texture, and minor surface variation. Render the same leafless tree with tapered limbs, bark ridges, irregular forks, progressively thinner twigs, tiny buds, and distinct overlapping depth layers. Keep the whole environment legible with natural small-sensor depth of field; distant elements soften gradually but remain structurally readable instead of becoming portrait-mode bokeh."

function Test-LocalTcpListener([int]$Port) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync("127.0.0.1", $Port)
        return ($task.Wait(1000) -and $client.Connected)
    }
    catch { return $false }
    finally { $client.Dispose() }
}

function Assert-LocalEndpoint([string]$Endpoint, [int]$ExpectedPort, [string]$Label) {
    $uri = [Uri]$Endpoint
    if ($uri.Scheme -ne "http" -or $uri.Host -notin @("127.0.0.1", "localhost", "::1") -or $uri.Port -ne $ExpectedPort) {
        throw "$Label must be the local HTTP endpoint on port $ExpectedPort`: $Endpoint"
    }
}

function Get-WorkerSnapshot([int]$Port) {
    try {
        $base = "http://127.0.0.1:$Port"
        $stats = Invoke-RestMethod -Uri "$base/system_stats" -TimeoutSec 5
        $queue = Invoke-RestMethod -Uri "$base/queue" -TimeoutSec 5
        [ordered]@{
            port = $Port
            online = $true
            listener = $true
            device = [string]$stats.devices[0].name
            running = @($queue.queue_running).Count
            pending = @($queue.queue_pending).Count
            vram_total = [int64]$stats.devices[0].vram_total
            vram_free = [int64]$stats.devices[0].vram_free
        }
    }
    catch {
        [ordered]@{ port = $Port; online = $false; listener = (Test-LocalTcpListener $Port); device = "offline"; running = 0; pending = 0; vram_total = 0; vram_free = 0; error = $_.Exception.Message }
    }
}

function Get-ForgeSnapshot {
    try {
        $progress = Invoke-RestMethod -Uri "$ForgeUrl/sdapi/v1/progress?skip_current_image=true" -TimeoutSec 5
        $job = [string]$progress.state.job
        $jobCount = if ($null -ne $progress.state.PSObject.Properties["job_count"]) { [int]$progress.state.job_count } else { 0 }
        [ordered]@{
            online = $true
            listener = $true
            active = ([double]$progress.progress -gt 0 -or $jobCount -gt 0 -or -not [string]::IsNullOrWhiteSpace($job))
            progress = [double]$progress.progress
            job_count = $jobCount
        }
    }
    catch {
        [ordered]@{ online = $false; listener = (Test-LocalTcpListener ([Uri]$ForgeUrl).Port); active = $false; progress = 0.0; job_count = 0; error = $_.Exception.Message }
    }
}

function Assert-Shared3090Idle([object[]]$Workers, [object]$Forge, [string]$Phase) {
    $targetWorker = @($Workers | Where-Object port -eq 8188)[0]
    if (-not $targetWorker.online -or $targetWorker.device -notmatch "RTX 3090") {
        throw "Port 8188 is not the RTX 3090 worker during $Phase."
    }
    if ($targetWorker.running -gt 0 -or $targetWorker.pending -gt 0) {
        throw "RTX 3090 queue at port 8188 is active during $Phase."
    }

    $sharedWorker = @($Workers | Where-Object port -eq 8190)[0]
    if ($sharedWorker.online) {
        if ($sharedWorker.device -notmatch "RTX 3090") { throw "Port 8190 is not the shared RTX 3090 worker during $Phase." }
        if ($sharedWorker.running -gt 0 -or $sharedWorker.pending -gt 0) {
            throw "Shared RTX 3090 queue at port 8190 is active during $Phase."
        }
    }
    elseif ($sharedWorker.listener) {
        throw "Port 8190 is listening but its shared RTX 3090 queue could not be verified during $Phase."
    }

    if ($Forge.online -and $Forge.active) { throw "Forge has active RTX 3090 work during $Phase." }
    if (-not $Forge.online -and $Forge.listener) {
        throw "Forge is listening but its RTX 3090 activity could not be verified during $Phase."
    }
}

function Get-GpuHardwareSnapshots {
    $rows = @(& nvidia-smi --query-gpu=index,name,memory.used,memory.free,utilization.gpu,pstate --format=csv,noheader,nounits)
    if ($LASTEXITCODE -ne 0 -or $rows.Count -eq 0) { throw "Could not inspect GPU hardware state." }
    return @($rows | ForEach-Object {
        $parts = @($_ -split ",\s*", 6)
        if ($parts.Count -ne 6) { throw "Unexpected nvidia-smi row: $_" }
        [ordered]@{
            index = [int]$parts[0]
            name = [string]$parts[1]
            memory_used_mib = [int]$parts[2]
            memory_free_mib = [int]$parts[3]
            utilization_percent = [int]$parts[4]
            pstate = [string]$parts[5]
        }
    })
}

function Assert-Hardware3090Idle([object[]]$Snapshots, [string]$Phase) {
    $gpu = @($Snapshots | Where-Object name -match "RTX 3090")
    if ($gpu.Count -ne 1) { throw "Expected exactly one RTX 3090 hardware row during $Phase." }
    if ($gpu[0].utilization_percent -gt $MaxIdle3090Utilization) {
        throw "RTX 3090 utilization is $($gpu[0].utilization_percent)% during $Phase."
    }
    if ($gpu[0].memory_used_mib -gt $MaxIdle3090MemoryMiB) {
        throw "RTX 3090 uses $($gpu[0].memory_used_mib) MiB during $Phase."
    }
}

Assert-LocalEndpoint $Server 8188 "Server"
Assert-LocalEndpoint $ForgeUrl 7860 "ForgeUrl"
if ($TimeoutSeconds -le 0) { throw "TimeoutSeconds must be greater than zero before any smoke work is queued." }
if ($MaxIdle3090MemoryMiB -lt 1024 -or $MaxIdle3090Utilization -lt 0 -or $MaxIdle3090Utilization -gt 100) {
    throw "GPU idle thresholds are outside their supported range."
}

function Assert-Hash([string]$Path, [string]$Expected, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing $Label`: $Path" }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
    if ($actual -ne $Expected) { throw "$Label SHA-256 mismatch. Expected $Expected, found $actual." }
}

if (-not (Test-Path -LiteralPath $WorkflowPath -PathType Leaf)) { throw "Missing production workflow: $WorkflowPath" }
if (-not (Test-Path -LiteralPath $NodePath -PathType Leaf)) { throw "Missing Upgrade production node: $NodePath" }
if (-not (Test-Path -LiteralPath $RegistryPath -PathType Leaf)) { throw "Missing public node registry: $RegistryPath" }
if (-not (Test-Path -LiteralPath $PresetPath -PathType Leaf)) { throw "Missing Upgrade prompt preset: $PresetPath" }
if (-not (Test-Path -LiteralPath $PolishPath -PathType Leaf)) { throw "Missing deterministic appearance-polish implementation: $PolishPath" }
if (-not (Test-Path -LiteralPath $GazePath -PathType Leaf)) { throw "Missing source-gaze-lock implementation: $GazePath" }
if (-not (Test-Path -LiteralPath $MaskingPath -PathType Leaf)) { throw "Missing natural-lens background implementation: $MaskingPath" }
$workflow = Get-Content -Raw -LiteralPath $WorkflowPath | ConvertFrom-Json
if ($workflow.nodes.Count -ne 5) { throw "Production sheet must contain exactly five visible nodes." }
foreach ($required in @("MarkdownNote", "LoadImage", $NodeName, "PreviewImage")) {
    if ($required -notin @($workflow.nodes.type)) { throw "Production sheet is missing $required." }
}
$upgradeNode = @($workflow.nodes | Where-Object type -eq $NodeName)[0]
if (@($upgradeNode.inputs).Count -ne 5) { throw "Upgrade node must expose only source_photo, detail_instructions, appearance_polish, phone_camera_style, and seed." }
if ([bool]$upgradeNode.widgets_values[1] -ne $true) { throw "Production sheet must open with Subtle handsome polish enabled." }
if ([bool]$upgradeNode.widgets_values[2] -ne $true) { throw "Production sheet must open in the accepted phone-camera mode." }
if ([UInt64]$upgradeNode.widgets_values[3] -ne 8675416) { throw "Production sheet no longer opens at approved seed 8675416." }

$registrySource = Get-Content -Raw -LiteralPath $RegistryPath
if ($registrySource -notmatch [regex]::Escape('"Flux2Klein9BPhotoRealismUpgradeV11": Flux2Klein9BPhotoRealismUpgradeV1,')) {
    throw "Upgrade v1.1 must be a direct public alias to the exact validated internal engine."
}
if ($registrySource -match [regex]::Escape('"Flux2Klein9BPhotoRealismUpgradeV1": Flux2Klein9BPhotoRealismUpgradeV1,')) {
    throw "Retired Upgrade v1 remains exposed in the public node registry."
}

$nodeSource = Get-Content -Raw -LiteralPath $NodePath
$presetSource = Get-Content -Raw -LiteralPath $PresetPath
$polishSource = Get-Content -Raw -LiteralPath $PolishPath
$gazeSource = Get-Content -Raw -LiteralPath $GazePath
$maskingSource = Get-Content -Raw -LiteralPath $MaskingPath
foreach ($requiredMechanism in @(
    '"schema_version": 2',
    'build_face_free_guide\(source\)',
    'SOURCE_REFERENCE_MEGAPIXELS, "bicubic"',
    'GUIDE_REFERENCE_MEGAPIXELS, "nearest-exact"',
    'IDENTITY_REFERENCE_MEGAPIXELS, "nearest-exact"',
    'HAIR_REFERENCE_MEGAPIXELS, "bicubic"',
    'EmptyFlux2LatentImage\.execute',
    'SamplerCustomAdvanced\.execute',
    '"source_latent_initialization": False',
    '"second_model_pass": False',
    'apply_deterministic_face_polish',
    'build_semantic_hair_mask',
    'apply_source_gaze_lock',
    'SOURCE_GAZE_LOCK_PROFILE',
    'apply_smartphone_style_trigger',
    'SMARTPHONE_STYLE_LORA_STRENGTH',
    'UPGRADE_PHONE_STYLE_TEST_BASIS',
    'phone-off additionally applies an edge-safe background-only natural-lens finish',
    'if not phone_camera_style:',
    'human_foreground_mask',
    'apply_natural_lens_background_blur',
    'NATURAL_LENS_BLUR_PROFILE',
    '"appearance_generation_prompt_changed": False',
    '"background_generation_prompt_changed": True',
    '"background_generation_prompt_changed_scope": \(',
    '"phone_style_generation_prompt_changed": bool\(phone_camera_style\)',
    '"revalidation_generation_prompt_changed_by_report_hardening": False',
    '"generation_spatial_mask": False',
    '"appearance_postprocess_mask": bool\(appearance_polish\)',
    '"background_postprocess_mask": not bool\(phone_camera_style\)',
    '"camera_finish_second_model_pass": False',
    'MILESTONE_COMMIT = "d58732a"',
    'MILESTONE_TAG = "milestone-good-identity-workflows-2026-09-01"',
    'REVALIDATION_COMMIT = "b32ecb9"',
    'REVALIDATION_TAG = "milestone-klein9b-production-revalidated-2026-09-03"',
    '"milestone_sampling_path_preserved": False',
    '"milestone_sampling_path_status": \(',
    'unpreserved_phone_on_prompt_and_smartphone_lora_drift',
    'unpreserved_phone_off_prompt_drift',
    '"milestone_generation_prompt_changed": True',
    '"milestone_smartphone_lora_changed": bool\(phone_camera_style\)',
    'phone-on differs from d58732a through prompt drift',
    'phone-off differs from d58732a through prompt drift',
    '"revalidation_sampling_path_preserved": True',
    'Compared with b32ecb9, this report-only hardening changes reporting semantics',
    '"source_used_as_identity": None',
    '"source_used_as_identity_scope": \(',
    '"source_intended_as_identity_reference": False',
    '"source_identity_influence_status": "unisolated_not_proven_absent"',
    'identity contribution has not been isolated and cannot',
    'explicit identity mechanism:',
    'not part of that exact shipped-default generation run',
    'appearance polish is disabled; no face, iris, or hair-local polish runs',
    'appearance polish is disabled, so no face, iris, or hair-local appearance postprocess runs'
)) {
    if ($nodeSource -notmatch $requiredMechanism) { throw "Upgrade node is missing a milestone mechanism: $requiredMechanism" }
}
foreach ($incorrectReportClaim in @(
    '"milestone_sampling_path_preserved": True',
    '"milestone_sampling_path_preserved": not bool\(phone_camera_style\)',
    '"source_used_as_identity": False',
    'after the unchanged generation',
    '"background_generation_prompt_changed": False',
    'phone-off preserves the milestone core sampling path',
    'phone-off recipe retains that core sampling path'
)) {
    if ($nodeSource -match $incorrectReportClaim) { throw "Upgrade report retains an overclaim: $incorrectReportClaim" }
}
foreach ($requiredGazeMechanism in @(
    'SOURCE_GAZE_LOCK_PROFILE = "mediapipe_refined_iris_source_lock_v1"',
    'refine_landmarks=True',
    'MAX_SHIFT_EYE_WIDTH = 0.18',
    'MIN_VERTICAL_COORDINATE_DELTA = 0.03',
    'source_pixels_copied": False',
    'eyelid_boundary_pixels_protected": True',
    'background_face_hair_and_eye_shape_protected": True',
    'output\[selected\] = warped\[selected\]'
)) {
    if ($gazeSource -notmatch $requiredGazeMechanism) { throw "Source gaze lock is missing its tested safety mechanism: $requiredGazeMechanism" }
}
foreach ($forbiddenMechanism in @(
    'TURBO_LORA',
    'source_latent = comfy_nodes\.VAEEncode',
    'noise_mask',
    'compose_edit_masks'
)) {
    if ($nodeSource -match $forbiddenMechanism) { throw "Upgrade node reintroduced rejected mechanism: $forbiddenMechanism" }
}
foreach ($requiredBackgroundMechanism in @(
    'NATURAL_LENS_BLUR_PROFILE = "u2net_human_edge_safe_depth_ramp_v1"',
    'HUMAN_SEGMENTATION_SHA256 = "01EB6A29A5C4D8EDB30B56ADAD9BB3A2A0535338E480724A213E0ACFD2D1C73C"',
    'BACKGROUND_SUBJECT_THRESHOLD = 0.12',
    'BACKGROUND_NEAR_SIGMA_FRACTION = 0.0022',
    'BACKGROUND_FAR_SIGMA_FRACTION = 0.0055',
    'BACKGROUND_DEPTH_RAMP_FRACTION = 0.18',
    'rgb \* weights\[\.\.\., None\]',
    'numerator / np\.maximum\(denominator\[\.\.\., None\], 1e-5\)',
    'protected_subject = cv2\.dilate',
    'output\[protected_subject > 0\] = source\[protected_subject > 0\]',
    '"subject_colors_excluded_from_background_blur": True',
    '"phone_on_path_unchanged": True'
)) {
    if ($maskingSource -notmatch $requiredBackgroundMechanism) { throw "Natural-lens finish is missing its tested safety mechanism: $requiredBackgroundMechanism" }
}
foreach ($requiredPolishMechanism in @(
    'POLISH_PROFILE = "deterministic_face_and_hair_local_v4"',
    'MOUTH_CORNER_LIFT_FACE_HEIGHT = 0.009',
    'FOREHEAD_WRINKLE_BLEND = 0.25',
    'EYE_DETAIL_GAIN = 0.18',
    'STUBBLE_DETAIL_GAIN = 0.12',
    'FRECKLE_RESPONSE_THRESHOLD = 0.0105',
    'FRECKLE_COMPONENT_MAX_AREA = 72',
    'FRECKLE_LOCAL_MEDIAN_DIAMETER = 7',
    'HAIR_PARSER_MODEL = "facedetection/parsing_parsenet.pth"',
    'HAIR_MID_FREQUENCY_GAIN = 0.42',
    'HAIR_HIGHLIGHT_LUMA_GAIN = 4.0',
    'highlights_follow_existing_hair_luminance',
    'hairline_and_silhouette_protected_pixels',
    'unselected_skin_texture_untouched_by_freckle_operation',
    'rgb\[active_mask == 0.0\] = original\[active_mask == 0.0\]',
    '"protected_pixel_max_error_0_to_255"',
    '"background_and_head_outline_are_source_pixels": True'
)) {
    if ($polishSource -notmatch $requiredPolishMechanism) { throw "Appearance polish is missing its tested safety mechanism: $requiredPolishMechanism" }
}
foreach ($requiredApprovedPromptLock in @(
    'APPROVED_INCLUDED_EXAMPLE_PROMPT',
    'exact landscape edit target',
    'three-quarter view',
    'materially detailed background',
    'return APPROVED_INCLUDED_EXAMPLE_PROMPT'
)) {
    if ($presetSource -notmatch [regex]::Escape($requiredApprovedPromptLock)) { throw "Included-example milestone prompt lock is missing: $requiredApprovedPromptLock" }
}
foreach ($unsafePrompt in @(
    'three to five years younger',
    'stronger natural jaw',
    'higher and more defined cheekbones',
    'noticeable light bronze sun tan',
    'very slight confident closed-mouth smile',
    'about twenty percent',
    'sun-kissed warmth'
)) {
    if ($presetSource -match [regex]::Escape($unsafePrompt)) { throw "Appearance prompt reintroduced rejected wording: $unsafePrompt" }
}

$workers = @(@(8188, 8189, 8190) | ForEach-Object { Get-WorkerSnapshot $_ })
$forge = Get-ForgeSnapshot
Assert-Shared3090Idle $workers $forge "preflight"
$hardware = Get-GpuHardwareSnapshots
if ($Smoke) { Assert-Hardware3090Idle $hardware "preflight" }

$nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$NodeName" -TimeoutSec 30
if (-not $nodeInfo.$NodeName) { throw "Live RTX 3090 worker does not expose $NodeName; restart the worker after installing the workflow." }
$retiredNodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$InternalNodeName" -TimeoutSec 30
if ($retiredNodeInfo.PSObject.Properties[$InternalNodeName]) { throw "Live RTX 3090 worker still exposes retired Upgrade node $InternalNodeName." }
$requiredInputs = @($nodeInfo.$NodeName.input_order.required)
if (($requiredInputs -join ",") -ne "source_photo,detail_instructions,appearance_polish,phone_camera_style,seed") {
    throw "Live node input contract drifted: $($requiredInputs -join ', ')"
}
$livePhoneDefault = [bool]$nodeInfo.$NodeName.input.required.phone_camera_style[1].default
if (-not $livePhoneDefault) { throw "Live RTX 3090 node still defaults Phone-camera realism off; reload the worker." }

$hashes = [ordered]@{
    workflow = (Get-FileHash -Algorithm SHA256 -LiteralPath $WorkflowPath).Hash.ToUpperInvariant()
    upgrade_engine = "3A712E7BBD53E0AF070CD5D986830C1EC7B1F87B0456032A065944E52A8C3412"
    model = "4A54FAD7F5F741B99EEE217198DAAC20B8D8E515E2A1F5B064FD51CF074F95BD"
    text_encoder = "ABAD16806E0CBABC54E0325D6565847443FE396D5F0BE38BB3CD3FE75A1201D6"
    vae = "D64F3A68E1CC4F9F4E29B6E0DA38A0204FE9A49F2D4053F0EC1FA1CA02F9C4B5"
    lora = "D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC"
    identity = "28DF2AE0D717A788370CC825F7BB24CF38DB9C7CDA3F66BAEFAB58BE86D8AF33"
    hair = "3B7C223BFB6390AED6981EB3C3549CC767BDC967B887D170153EFA6BE7DDB201"
    hair_parser = "3D558D8D0E42C20224F13CF5A29C79EBA2D59913419F945545D8CF7B72920DE2"
    smartphone_style = "1E0B419B1448F77CF7AEF430625325E46B16D1515CBF6C5C7E8C14D938CF1A90"
    deterministic_polish = "D970934CE4CF0B640A4BD24ABD7DA3BFA16A67F23842CBC81B14B4323793977B"
    source_gaze_lock = "3C68D54C4E94DFF8A2CD4D308C282F441A98916717D6DF4DC57F81889AF50275"
    natural_lens_masking = "7AB8ABA5053EC73646F28C7EAF7E0195A69699246F662F070D828DA08ECD5BF3"
    human_segmentation = "01EB6A29A5C4D8EDB30B56ADAD9BB3A2A0535338E480724A213E0ACFD2D1C73C"
    smoke_source = "AEF8704873C40C92EC365C091EA142998E72B3D80D22B45F55275309165BA5B4"
}
Assert-Hash $NodePath $hashes.upgrade_engine "generation-locked Upgrade engine"
Assert-Hash (Join-Path $ComfyRoot "models\diffusion_models\flux-2-klein-base-9b-bf16.safetensors") $hashes.model "Klein Base 9B model"
Assert-Hash (Join-Path $ComfyRoot "models\text_encoders\qwen_3_8b_fp8mixed.safetensors") $hashes.text_encoder "Qwen 3 8B text encoder"
Assert-Hash (Join-Path $ComfyRoot "models\vae\flux2-vae.safetensors") $hashes.vae "FLUX.2 VAE"
Assert-Hash (Join-Path $ComfyRoot "models\loras\m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors") $hashes.lora "protected step-1600 LoRA"
Assert-Hash (Join-Path $ComfyRoot "input\mitch-klein9b-ref-front-neutral-v2.jpg") $hashes.identity "genuine identity reference"
Assert-Hash (Join-Path $ComfyRoot "input\mitch-natural-hair-only-val05-isolated.png") $hashes.hair "isolated hair reference"
Assert-Hash (Join-Path $ComfyRoot "models\facedetection\parsing_parsenet.pth") $hashes.hair_parser "semantic hair ParseNet model"
Assert-Hash (Join-Path $ComfyRoot "models\loras\smartphone-snapshot\FLUX.2-klein-base-9B_SmartphoneSnapshotPhotoReality_v13.safetensors") $hashes.smartphone_style "optional Smartphone Snapshot v13 LoRA"
Assert-Hash $PolishPath $hashes.deterministic_polish "deterministic handsome-polish implementation"
Assert-Hash $GazePath $hashes.source_gaze_lock "source-gaze-lock implementation"
Assert-Hash $MaskingPath $hashes.natural_lens_masking "natural-lens background implementation"
Assert-Hash (Join-Path $ComfyRoot "models\rembg\u2net_human_seg.onnx") $hashes.human_segmentation "U2Net human segmentation model"

$validation = [ordered]@{
    schema_version = 1
    status = "validated"
    public_version = "v1.1"
    workflow = $WorkflowPath
    node = $NodeName
    workers = $workers
    forge = $forge
    nvidia_smi = $hardware
    hashes = $hashes
    milestone = [ordered]@{ commit = "d58732a"; tag = "milestone-good-identity-workflows-2026-09-01"; sampling_path_preserved = $false; phone_off_delta = "prompt drift"; phone_on_delta = "prompt drift plus Smartphone Snapshot v13 LoRA"; included_example_base_prompt_matches_approved_png = $true; current_effective_prompt_matches_milestone = $false; included_example_guide_pixels_match_approved_guide = $true }
    revalidation = [ordered]@{ commit = "b32ecb9"; tag = "milestone-klein9b-production-revalidated-2026-09-03"; report_only_hardening = $true; sampling_path_preserved = $true; generation_prompt_changed = $false; model_or_lora_selection_changed = $false; reference_order_changed = $false; postprocessing_changed = $false }
    appearance = [ordered]@{ default = $true; profile = "deterministic_face_and_hair_local_v4+mediapipe_refined_iris_source_lock_v1"; mechanism = "deterministic face-local, source-relative iris-interior, and eroded semantic-hair-interior postprocess after sampling; this appearance stage does not resample"; appearance_stage_changes_generation_prompt = $false; protected_pixels_exact = $true; dark_dots_and_freckles_reduced = $true; existing_hair_highlights_enhanced = $true; hairline_unchanged = $true; eyelids_unchanged = $true; source_gaze_lock = $true }
    phone_camera_style = [ordered]@{ available = $true; default = $true; strength = 0.25; trigger = "casual snapshot"; rendering = "deep_focus"; background_blur_skipped = $true; decision = "visually accepted by Mitch" }
    phone_off_camera_finish = [ordered]@{ available = $true; default = $false; profile = "u2net_human_edge_safe_depth_ramp_v1"; mechanism = "local U2Net human matte plus subject-excluding normalized near/far Gaussian depth ramp"; protected_subject_pixels_exact = $true; subject_colors_excluded = $true; second_model_pass = $false }
    locked_settings = [ordered]@{ model_dtype = "fp8_e4m3fn"; lora_strength = 0.90; steps = 50; cfg = 4.0; sampler = "euler"; scheduler = "Flux2Scheduler"; references = 4 }
    forbidden_stages = [ordered]@{ turbo = $false; source_latent_init = $false; generation_mask = $false; face_swap = $false; restoration = $false; generation_sharpening = $false; upscaling = $false; second_model_pass = $false }
    appearance_postprocess = [ordered]@{ local_soft_mask = $true; face_iris_and_hair_interiors_only = $true; outside_pixels_exact_before_camera_finish = $true; local_texture_and_detail_contrast = $true }
}

if (-not $Smoke) {
    $validation | ConvertTo-Json -Depth 20
    exit 0
}

$sourcePath = Join-Path $ComfyRoot "input\$SourceName"
Assert-Hash $sourcePath $hashes.smoke_source "smoke source"
$workersAtSubmit = @(@(8188, 8189, 8190) | ForEach-Object { Get-WorkerSnapshot $_ })
$forgeAtSubmit = Get-ForgeSnapshot
Assert-Shared3090Idle $workersAtSubmit $forgeAtSubmit "smoke submission"
$hardwareAtSubmit = Get-GpuHardwareSnapshots
Assert-Hardware3090Idle $hardwareAtSubmit "smoke submission"
$validation.workers_at_submit = $workersAtSubmit
$validation.forge_at_submit = $forgeAtSubmit
$validation.nvidia_smi_at_submit = $hardwareAtSubmit
$prompt = [ordered]@{ "1" = @{ class_type = "LoadImage"; inputs = @{ image = $SourceName } } }
if ($Native) {
    $outputNodeId = "2"
    $prompt[$outputNodeId] = @{ class_type = $NodeName; inputs = @{ source_photo = @("1", 0); detail_instructions = $Detail; appearance_polish = $true; phone_camera_style = $true; seed = [UInt64]8675416 } }
    $validation.test_resolution = "source native"
}
else {
    $prompt["2"] = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("1", 0); upscale_method = "bicubic"; megapixels = 1.0; resolution_steps = 1 } }
    $outputNodeId = "3"
    $prompt[$outputNodeId] = @{ class_type = $NodeName; inputs = @{ source_photo = @("2", 0); detail_instructions = $Detail; appearance_polish = $true; phone_camera_style = $true; seed = [UInt64]8675416 } }
    $validation.test_resolution = "approximately 1 MP preview; use -Native only for final confirmation"
}
$body = @{ prompt = $prompt; client_id = "verify-upgrade-photo-$([guid]::NewGuid().ToString('N'))" } | ConvertTo-Json -Depth 30
$started = Get-Date
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body -TimeoutSec 60
if (-not $queued.prompt_id) { throw "ComfyUI did not return a smoke prompt ID." }
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 5
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)" -TimeoutSec 15
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry -and $entry.status.status_str -eq "error") { throw "Smoke generation failed: $($entry.status.messages | ConvertTo-Json -Depth 30)" }
    if ($entry -and ($entry.status.completed -or $entry.status.status_str -eq "success")) {
        $images = @($entry.outputs.$outputNodeId.images)
        if ($images.Count -eq 0) { throw "Smoke generation completed without a saved photo." }
        $validation.status = "smoke_generated_pending_visual_and_identity_review"
        $validation.smoke_prompt_id = [string]$queued.prompt_id
        $validation.smoke_runtime_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
        $validation.smoke_outputs = @($images | ForEach-Object {
            $relative = if ($_.subfolder) { Join-Path $_.subfolder $_.filename } else { $_.filename }
            Join-Path (Join-Path $ComfyRoot "output") $relative
        })
        $validation | ConvertTo-Json -Depth 20
        exit 0
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for Upgrade Photo Detail & Realism smoke generation."
