[CmdletBinding()]
param(
    [string]$Source = "templates\krea2-workflows\Krea 2 Identity Edit - Local Reference Restage.source.json",
    [string]$Destination = "workflows\production\Krea 2 Identity Edit - Face Attention v2.json",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$sourcePath = [IO.Path]::GetFullPath((Join-Path $repoRoot $Source))
$destinationPath = [IO.Path]::GetFullPath((Join-Path $repoRoot $Destination))

if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
    throw "Source workflow does not exist: $sourcePath"
}
if ((Test-Path -LiteralPath $destinationPath) -and -not $Force) {
    throw "Refusing to overwrite existing workflow without -Force: $destinationPath"
}

$workflow = Get-Content -Raw -LiteralPath $sourcePath | ConvertFrom-Json -AsHashtable
$workflow.id = "krea2-identity-edit-face-attention-v2"
$workflow.revision = 1
$workflow.last_node_id = 113
$workflow.last_link_id = 32

# This version is intentionally single-reference. The trained two-reference order has different
# semantics, so leaving a bypassed second portrait in the graph makes the face mask ambiguous.
$workflow.nodes = @($workflow.nodes | Where-Object { [int]$_.id -notin @(90, 92) })
$workflow.links = @(
    $workflow.links | Where-Object {
        [int]$_[1] -notin @(90, 92) -and [int]$_[3] -notin @(90, 92)
    }
)

$nodes = @{}
foreach ($node in $workflow.nodes) {
    $nodes[[int]$node.id] = $node
}

function Get-NodeInput {
    param([hashtable]$Node, [string]$Name)
    return @($Node.inputs | Where-Object { $_.name -eq $Name })[0]
}

$smartphoneNode = [ordered]@{
    id = 111
    type = "LoraLoaderModelOnly"
    pos = @(60, 370)
    size = @(480, 120)
    flags = @{}
    order = 14
    mode = 0
    inputs = @(
        [ordered]@{ name = "model"; type = "MODEL"; link = 1 }
    )
    outputs = @(
        [ordered]@{ name = "MODEL"; type = "MODEL"; links = @(28) }
    )
    properties = [ordered]@{
        cnr_id = "comfy-core"
        ver = "0.26.0"
        "Node name for S&R" = "LoraLoaderModelOnly"
    }
    widgets_values = @("krea-smartphone-photo-slider.safetensors", 0.35)
}

$faceMaskNode = [ordered]@{
    id = 112
    type = "Krea2ReferenceFaceAttentionMask"
    pos = @(640, 310)
    size = @(520, 180)
    flags = @{}
    order = 15
    mode = 0
    inputs = @(
        [ordered]@{ name = "image"; type = "IMAGE"; link = 29 },
        [ordered]@{ name = "width_scale"; type = "FLOAT"; widget = [ordered]@{ name = "width_scale" }; link = $null },
        [ordered]@{ name = "height_scale"; type = "FLOAT"; widget = [ordered]@{ name = "height_scale" }; link = $null },
        [ordered]@{ name = "vertical_offset"; type = "FLOAT"; widget = [ordered]@{ name = "vertical_offset" }; link = $null }
    )
    outputs = @(
        [ordered]@{ name = "reference_attention_mask"; type = "MASK"; links = @(30); slot_index = 0 }
    )
    properties = [ordered]@{
        cnr_id = "ComfyUI-AIToolkit-Training"
        "Node name for S&R" = "Krea2ReferenceFaceAttentionMask"
    }
    widgets_values = @(0.82, 0.86, 0.02)
    color = "#174d52"
    bgcolor = "#20666d"
}

$workflow.nodes += $smartphoneNode
$workflow.nodes += $faceMaskNode
$nodes[111] = $smartphoneNode
$nodes[112] = $faceMaskNode

$phoneFinishNode = [ordered]@{
    id = 113
    type = "WholeFramePhoneFinish"
    pos = @(3160, 390)
    size = @(440, 90)
    flags = @{}
    order = 16
    mode = 0
    inputs = @(
        [ordered]@{ name = "image"; type = "IMAGE"; link = 31 }
    )
    outputs = @(
        [ordered]@{ name = "finished_image"; type = "IMAGE"; links = @(32); slot_index = 0 }
    )
    properties = [ordered]@{
        cnr_id = "ComfyUI-AIToolkit-Training"
        "Node name for S&R" = "WholeFramePhoneFinish"
    }
    widgets_values = @()
    color = "#423514"
    bgcolor = "#66521f"
}
$workflow.nodes += $phoneFinishNode
$nodes[113] = $phoneFinishNode

# Apply the selected subtle response to every decoded pixel before saving. This is a deterministic
# CPU image transform, not another model pass, and has no subject or face selection.
$workflow.links = @($workflow.links | Where-Object { [int]$_[0] -ne 26 })
$nodes[54].outputs[0].links = @(31)
(Get-NodeInput $nodes[29] "images").link = 32
$nodes[29].pos = @(3640, -160)
$workflow.links += ,@(31, 54, 0, 113, 0, "IMAGE")
$workflow.links += ,@(32, 113, 0, 29, 0, "IMAGE")

# Chain camera appearance before Identity Edit, exactly as in the accepted local experiment.
$linkOne = @($workflow.links | Where-Object { [int]$_[0] -eq 1 })[0]
$linkOne[3] = 111
$nodes[55].outputs[0].links = @(1)
(Get-NodeInput $nodes[71] "model").link = 28
$nodes[71].pos = @(60, 520)
$nodes[100].pos = @(60, 680)
$workflow.links += ,@(28, 111, 0, 71, 0, "MODEL")

# The genuine reference still reaches both trained Identity Edit paths. The new mask only limits
# the extra target->reference boost to the detected internal face.
$nodes[72].outputs[0].links = @(11, 12, 13, 14, 29)
$nodes[57].outputs[0].links = @($nodes[57].outputs[0].links | Where-Object { [int]$_ -ne 8 })
(Get-NodeInput $nodes[79] "source_latent_b").link = $null
(Get-NodeInput $nodes[79] "source_image_b").link = $null
(Get-NodeInput $nodes[79] "ref_boost_mask").link = 30
(Get-NodeInput $nodes[84] "image_b").link = $null
(Get-NodeInput $nodes[85] "image_b").link = $null
$workflow.links += ,@(29, 72, 0, 112, 0, "IMAGE")
$workflow.links += ,@(30, 112, 0, 79, 3, "MASK")

$nodes[79].widgets_values = @(6, 1, "fit")
$nodes[84].widgets_values[0] = "Restage this exact same man in a completely new candid vertical smartphone photograph, walking naturally toward the camera on a genuinely busy downtown sidewalk. Preserve his exact recognizable facial identity, face shape, forehead lines, eye shape and spacing, nose, mouth, ears, short light-brown hairstyle, hairline, apparent age, natural skin texture, and lean build. The camera is about three and a half meters away using an ordinary 1x rear phone camera. Show him approximately full body, slightly off center, mid-stride, occupying about sixty to sixty-five percent of the frame height, wearing a plain fitted navy crew-neck T-shirt and dark casual pants. He is clearly the subject but is not posing. Unrelated pedestrians move in both directions at varied depths with overlapping bodies and different natural actions; nobody is grouped with him. Use ordinary soft open-shade afternoon daylight, natural recent-smartphone exposure, restrained phone HDR, realistic skin pores, and subtle sensor texture. Use natural deep smartphone focus across the complete photograph: the subject, nearby pedestrians, storefront masonry, windows, sidewalk joints, street furniture, signs, clothing, and separate people remain resolved with coherent local detail throughout the foreground and middle distance, with only a gentle gradual falloff at the far end of the block. The entire scene shares one consistent camera response, exposure, sharpness progression, and texture. No flash, studio lighting, beauty filter, cinematic grade, copied source background, collage, face swap, pasted head boundary, selectively sharpened face, text, or watermark. Make the result look like one ordinary phone photograph captured in a single moment."
$nodes[84].widgets_values[1] = 512
$nodes[85].widgets_values[1] = 512
$nodes[53].widgets_values[0] = 9472103
$nodes[53].widgets_values[1] = "fixed"
$nodes[53].widgets_values[2] = 12
$nodes[53].widgets_values[3] = 1
$nodes[29].widgets_values[0] = "krea2-identity-edit/face-attention-v2"

$nodes[101].title = "Identity reference"
$nodes[101].pos = @(640, 510)
$nodes[101].widgets_values[0] = "Use one genuine reference with a clearly visible face. The image enters through both training-matched paths: VAE appearance tokens and image-aware Qwen3-VL grounding. It is not used as a style reference or pasted into the output."
$nodes[102].title = "Face attention — reference only"
$nodes[102].pos = @(640, 690)
$nodes[102].size = @(520, 230)
$nodes[102].mode = 0
$nodes[102].widgets_values[0] = "The CPU-only node detects the largest reference face and boosts only an internal oval. It excludes the hair/head silhouette, ears, neck, clothing, body, and source background. This MASK controls reference attention inside Krea2EditModelPatch; it never masks, composites, inpaints, or sharpens output pixels. Defaults reproduce the accepted no-Mitch-LoRA test."
$nodes[104].widgets_values[0] = "FACE-ONLY FIDELITY\n\nref_boost 6 is restricted by the connected reference attention mask. Unmasked reference tokens remain available at neutral strength through the native Identity Edit paths. Do not disconnect the mask and increase global boost: that recreates the sharp subject/background separation this version fixes.\n\nfit mode is training-matched and should remain enabled."
$nodes[105].widgets_values[0] = "Validated local settings:\n  Krea2 Turbo\n  12 steps, CFG 1\n  Euler + simple\n  832 x 1248 (2:3, about 1 MP)\n  grounding_px 512\n\nThe fixed seed reproduces the accepted calibration. Change it only after confirming the graph works."
$nodes[106].widgets_values[0] = "KREA 2 IDENTITY EDIT — FACE ATTENTION v2\n\nPurpose: create a new coherent photograph from one genuine identity reference without a Mitch LoRA, face swap, head mask, or output compositing.\n\nThe internal-face MASK is reference-space attention guidance only. The model still generates every output pixel together.\n\nSelected deep-focus result: 0.7822 strong identity match. The deterministic whole-frame phone finish raised the measured result to 0.7884 while preserving background detail. It uses no face selection or generative processing."

$workflow.groups = @($workflow.groups | Where-Object { [int]$_.id -ne 3 })
$groupById = @{}
foreach ($group in $workflow.groups) { $groupById[[int]$group.id] = $group }
$groupById[1].bounding = @(40, -240, 540, 1140)
$groupById[2].title = "2 · GENUINE IDENTITY REFERENCE + FACE ATTENTION"
$groupById[2].bounding = @(620, -240, 580, 1190)
$groupById[4].title = "3 · INSTRUCTION"
$groupById[5].title = "4 · IDENTITY FIDELITY"
$groupById[6].title = "5 · GENERATE"

$workflow.extra.ds.scale = 0.72
$workflow.extra.ds.offset = @(55, 360)

$destinationDirectory = Split-Path -Parent $destinationPath
New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
$json = $workflow | ConvertTo-Json -Depth 100
[IO.File]::WriteAllText($destinationPath, $json + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
Write-Host "Built versioned Krea2 face-attention workflow: $destinationPath"
