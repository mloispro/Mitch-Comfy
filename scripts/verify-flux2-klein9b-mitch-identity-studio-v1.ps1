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

$workflowPath = Join-Path $repoRoot "workflows\production\FLUX.2 Klein 9B Mitch Identity Studio v1.json"
if (-not (Test-Path -LiteralPath $workflowPath -PathType Leaf)) {
    $errors.Add("Missing winning Production workflow: $workflowPath")
} else {
    try {
        $workflow = Get-Content -Raw -LiteralPath $workflowPath | ConvertFrom-Json
        if (@($workflow.nodes).Count -ne 3) { $errors.Add("Winning workflow must contain exactly three visible nodes.") }
        foreach ($nodeType in "MarkdownNote", "Flux2Klein9BMitchIdentityStudioV1", "PreviewImage") {
            if ($nodeType -notin @($workflow.nodes.type)) { $errors.Add("Winning workflow is missing node: $nodeType") }
        }
        $studioNode = @($workflow.nodes | Where-Object type -eq "Flux2Klein9BMitchIdentityStudioV1")[0]
        if ($studioNode) {
            if (@($studioNode.inputs).Count -ne 3) { $errors.Add("Winning workflow must expose only reference_profile, scene_prompt, and seed.") }
            if ([string]$studioNode.widgets_values[0] -notmatch "^GROUP") { $errors.Add("Winning workflow must open in the one-reference group-safe profile.") }
            if ([string]$studioNode.widgets_values[1] -notmatch "(?i)(Only the foreground man is m1tch_person|m1tch_person is the one foreground man)") { $errors.Add("Winning workflow default must explicitly scope Mitch to the main group subject.") }
        }
    } catch {
        $errors.Add("Winning workflow JSON is invalid: $($_.Exception.Message)")
    }
}

$nodeSourcePath = Join-Path $repoRoot "custom_nodes\ComfyUI-AIToolkit-Training\flux2_klein9b_mitch_identity_studio.py"
if (-not (Test-Path -LiteralPath $nodeSourcePath -PathType Leaf)) {
    $errors.Add("Missing Klein 9B Studio implementation: $nodeSourcePath")
} else {
    $source = Get-Content -Raw -LiteralPath $nodeSourcePath
    foreach ($lockedText in @(
        'MODEL_NAME = "flux-2-klein-base-9b-bf16.safetensors"',
        'LORA_NAME = "m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors"',
        'LORA_STRENGTH = 0.90', 'WIDTH = 832', 'HEIGHT = 1216', 'STEPS = 50', 'GUIDANCE = 4.0',
        'KSamplerSelect.execute("euler")', 'Flux2Scheduler.execute(STEPS, WIDTH, HEIGHT)', '"RTX 3090" not in device_name'
    )) {
        if ($source -notmatch [regex]::Escape($lockedText)) { $errors.Add("Klein 9B Studio is missing locked setting: $lockedText") }
    }
}

Assert-FileHash (Join-Path $ComfyRoot "models\loras\m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors") "D24907A84B8644A70C07611016A9D2FF8FAD2D2C761A8F97B213AE1D36088EEC" "protected Klein 9B step-1600 LoRA"

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
    $nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/Flux2Klein9BMitchIdentityStudioV1" -TimeoutSec 30
    if (-not $nodeInfo.Flux2Klein9BMitchIdentityStudioV1) { $errors.Add("Live RTX 3090 worker does not expose Flux2Klein9BMitchIdentityStudioV1.") }
    foreach ($requirement in @(
        @{ Class = "UNETLoader"; Field = "unet_name"; Value = "flux-2-klein-base-9b-bf16.safetensors" },
        @{ Class = "LoraLoaderModelOnly"; Field = "lora_name"; Value = "m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors" },
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

Write-Host "Verified the Klein 9B winner, protected files, live RTX 3090 node/models, and all eleven hidden archives."
