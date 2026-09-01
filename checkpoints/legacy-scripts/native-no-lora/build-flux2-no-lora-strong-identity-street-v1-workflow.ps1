[CmdletBinding()]
param(
    [string]$Destination = "checkpoints\legacy-workflows\production\FLUX.2 No-LoRA Strong Identity Street Corner v1.json",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$destinationPath = [IO.Path]::GetFullPath((Join-Path $repoRoot $Destination))
if ((Test-Path -LiteralPath $destinationPath) -and -not $Force) {
    throw "Refusing to overwrite existing workflow without -Force: $destinationPath"
}

$scenePrompt = @"
Images 1 and 2 show Mitch, the same character in every image. Mitch is a lean middle-aged white man with short brown hair, blue-gray eyes, an angular oval face, a high forehead, a narrow jaw, faint natural stubble, and natural unretouched skin. Create an unplanned vertical rear-camera smartphone snapshot of Mitch walking toward the person holding the phone through a somewhat busy downtown street corner. Frame him from mid-thigh upward with his face large enough to recognize. He wears a navy overshirt over a heather-gray T-shirt and dark jeans. Use the ordinary 1x main phone camera at about 26mm equivalent, eye-level handheld perspective, automatic exposure and white balance, restrained computational HDR, deep natural phone-camera focus, subtle edge sharpening, slight corner softness and lens distortion, faint sensor noise in shadows, gently compressed highlights, and a trace of realistic motion blur on a few moving pedestrians and hands. Show unrelated pedestrians waiting and crossing, storefronts, traffic lights, cars, crosswalk paint, concrete, signs, and resolved street depth. Every background person has a distinct face and does not resemble Mitch. It must look like a casual phone photo, not a cinematic frame or professional portrait: no studio lighting, no beauty retouching, no shallow depth of field, no creamy bokeh, no perfect global sharpness, no dramatic color grade.
"@.Trim()

$identityPrompt = @"
Image 1 is the source street photograph and defines the full composition, camera position, subject pose and clothing, pedestrian layout, cars, buildings, traffic lights, signs, crosswalk, pavement, lighting, and deep street detail. Images 2, 3, and 4 are genuine photographs of Mitch and define the exact identity of the main man in image 1. Recreate image 1 as a realistic high-resolution smartphone photograph, changing only the main man's face and identity so he is unmistakably Mitch from images 2, 3, and 4. Preserve Mitch's apparent age, facial geometry, eyes, forehead, nose, jaw, mouth, hairstyle, natural stubble, and unretouched skin. Preserve the source street background, crowd diversity, fine building texture, traffic, deep focus, full-frame lighting, subject clothing, body, pose, and placement. Every pedestrian remains a distinct unrelated person and does not resemble Mitch. Do not beautify, add a goatee, smooth skin, create portrait blur, crop, mask, or composite.
"@.Trim()

$script:nodes = [ordered]@{}
$script:links = @()
$script:linkId = 0

function Add-Node {
    param(
        [int]$Id, [string]$Type, [int[]]$Position, [int[]]$Size,
        [object[]]$Inputs = @(), [object[]]$Outputs = @(), [object[]]$Widgets = @(),
        [string]$Title = ""
    )
    $inputRows = @()
    foreach ($spec in $Inputs) {
        $row = [ordered]@{ name = [string]$spec[0]; type = [string]$spec[1]; link = $null }
        if ($spec.Count -gt 2 -and $spec[2]) { $row.widget = [ordered]@{ name = [string]$spec[2] } }
        $inputRows += ,$row
    }
    $outputRows = @()
    foreach ($spec in $Outputs) {
        $outputRows += ,[ordered]@{ name = [string]$spec[0]; type = [string]$spec[1]; links = $null }
    }
    $node = [ordered]@{
        id = $Id; type = $Type; pos = $Position; size = $Size; flags = @{}
        order = $Id - 1; mode = 0; inputs = $inputRows; outputs = $outputRows
        properties = [ordered]@{ "Node name for S&R" = $Type; cnr_id = "comfy-core" }
        widgets_values = $Widgets
    }
    if ($Title) { $node.title = $Title }
    $script:nodes[[string]$Id] = $node
}

function Add-Link {
    param([int]$From, [int]$Output, [int]$To, [int]$InputSlot, [string]$Type)
    $script:linkId++
    $id = $script:linkId
    $script:nodes[[string]$To].inputs[$InputSlot].link = $id
    $existing = @($script:nodes[[string]$From].outputs[$Output].links)
    $script:nodes[[string]$From].outputs[$Output].links = @($existing + $id)
    $script:links += ,@($id, $From, $Output, $To, $InputSlot, $Type)
}

$none = @()
Add-Node 1 "UNETLoader" @(-1200,-600) @(390,130) $none @(@("MODEL","MODEL")) @("flux-2-klein-9b-fp8.safetensors","default") "STAGE 1 — 9B detailed street"
Add-Node 2 "CLIPLoader" @(-1200,-430) @(390,150) $none @(@("CLIP","CLIP")) @("qwen_3_8b_fp8mixed.safetensors","flux2","default")
Add-Node 3 "VAELoader" @(-1200,-240) @(390,100) $none @(@("VAE","VAE")) @("flux2-vae.safetensors")
Add-Node 4 "LoadImage" @(-1200,0) @(310,360) $none @(@("IMAGE","IMAGE"),@("MASK","MASK")) @("mitch-inline-author-ref-01-face.jpg","image") "Image 1 — genuine face"
Add-Node 5 "ImageScaleToTotalPixels" @(-840,100) @(330,130) @(@("image","IMAGE")) @(@("IMAGE","IMAGE")) @("lanczos",1.0,1)
Add-Node 6 "VAEEncode" @(-460,100) @(210,100) @(@("pixels","IMAGE"),@("vae","VAE")) @(@("LATENT","LATENT")) @()
Add-Node 7 "LoadImage" @(-1200,420) @(310,360) $none @(@("IMAGE","IMAGE"),@("MASK","MASK")) @("mitch-inline-author-ref-02-angle.jpg","image") "Image 2 — genuine angle"
Add-Node 8 "ImageScaleToTotalPixels" @(-840,520) @(330,130) @(@("image","IMAGE")) @(@("IMAGE","IMAGE")) @("lanczos",1.0,1)
Add-Node 9 "VAEEncode" @(-460,520) @(210,100) @(@("pixels","IMAGE"),@("vae","VAE")) @(@("LATENT","LATENT")) @()
Add-Node 10 "CLIPTextEncode" @(-100,-590) @(430,260) @(@("clip","CLIP"),@("text","STRING","text")) @(@("CONDITIONING","CONDITIONING")) @($scenePrompt)
Add-Node 11 "ReferenceLatent" @(390,-570) @(270,100) @(@("conditioning","CONDITIONING"),@("latent","LATENT")) @(@("CONDITIONING","CONDITIONING")) @() "1 — face"
Add-Node 12 "ReferenceLatent" @(710,-570) @(270,100) @(@("conditioning","CONDITIONING"),@("latent","LATENT")) @(@("CONDITIONING","CONDITIONING")) @() "2 — angle"
Add-Node 13 "EmptyFlux2LatentImage" @(390,-350) @(260,150) $none @(@("LATENT","LATENT")) @(832,1248,1)
Add-Node 14 "KSampler" @(1040,-550) @(320,270) @(@("model","MODEL"),@("positive","CONDITIONING"),@("negative","CONDITIONING"),@("latent_image","LATENT")) @(@("LATENT","LATENT")) @(9472363,"fixed",4,1.0,"euler","simple",1.0)
Add-Node 15 "VAEDecode" @(1420,-550) @(210,100) @(@("samples","LATENT"),@("vae","VAE")) @(@("IMAGE","IMAGE")) @()
Add-Node 16 "SaveImage" @(1690,-620) @(430,420) @(@("images","IMAGE")) @() @("flux2-no-lora-strong-identity-street-v1/stage1-9b") "Stage 1 preview / saved plate"

Add-Node 17 "UNETLoader" @(-1200,920) @(390,130) $none @(@("MODEL","MODEL")) @("flux-2-klein-base-4b-fp8.safetensors","default") "STAGE 2 — 4B Base identity"
Add-Node 18 "CLIPLoader" @(-1200,1090) @(390,150) $none @(@("CLIP","CLIP")) @("qwen_3_4b_fp8_mixed.safetensors","flux2","default")
Add-Node 19 "ImageScaleToTotalPixels" @(-840,820) @(330,130) @(@("image","IMAGE")) @(@("IMAGE","IMAGE")) @("lanczos",0.5,1) "Image 1 — Stage 1 scene at 0.5 MP"
Add-Node 20 "VAEEncode" @(-460,820) @(210,100) @(@("pixels","IMAGE"),@("vae","VAE")) @(@("LATENT","LATENT")) @()
Add-Node 21 "LoadImage" @(-1200,1320) @(310,360) $none @(@("IMAGE","IMAGE"),@("MASK","MASK")) @("mitch-inline-author-ref-03-front-outdoor.jpg","image") "Image 4 — genuine front"
Add-Node 22 "ImageScaleToTotalPixels" @(-840,1420) @(330,130) @(@("image","IMAGE")) @(@("IMAGE","IMAGE")) @("lanczos",1.0,1)
Add-Node 23 "VAEEncode" @(-460,1420) @(210,100) @(@("pixels","IMAGE"),@("vae","VAE")) @(@("LATENT","LATENT")) @()
Add-Node 24 "CLIPTextEncode" @(-100,810) @(430,300) @(@("clip","CLIP"),@("text","STRING","text")) @(@("CONDITIONING","CONDITIONING")) @($identityPrompt) "Positive — scene 1, identity 2–4"
Add-Node 25 "CLIPTextEncode" @(-100,1200) @(430,180) @(@("clip","CLIP"),@("text","STRING","text")) @(@("CONDITIONING","CONDITIONING")) @("") "Negative"
foreach ($id in 26..29) { Add-Node $id "ReferenceLatent" @((390 + 320*($id-26)),820) @(270,100) @(@("conditioning","CONDITIONING"),@("latent","LATENT")) @(@("CONDITIONING","CONDITIONING")) @() ("Positive image " + ($id-25)) }
foreach ($id in 30..33) { Add-Node $id "ReferenceLatent" @((390 + 320*($id-30)),1210) @(270,100) @(@("conditioning","CONDITIONING"),@("latent","LATENT")) @(@("CONDITIONING","CONDITIONING")) @() ("Negative image " + ($id-29)) }
Add-Node 34 "CFGGuider" @(1710,960) @(270,130) @(@("model","MODEL"),@("positive","CONDITIONING"),@("negative","CONDITIONING")) @(@("GUIDER","GUIDER")) @(4.0)
Add-Node 35 "KSamplerSelect" @(1710,1130) @(270,100) $none @(@("SAMPLER","SAMPLER")) @("euler")
Add-Node 36 "Flux2Scheduler" @(1710,1270) @(270,150) $none @(@("SIGMAS","SIGMAS")) @(30,832,1248) "Fast: 30 steps | Quality: 50 steps"
Add-Node 37 "RandomNoise" @(1710,1460) @(270,100) $none @(@("NOISE","NOISE")) @(9472363,"fixed")
Add-Node 38 "EmptyFlux2LatentImage" @(1710,1600) @(270,150) $none @(@("LATENT","LATENT")) @(832,1248,1)
Add-Node 39 "SamplerCustomAdvanced" @(2050,1070) @(330,220) @(@("noise","NOISE"),@("guider","GUIDER"),@("sampler","SAMPLER"),@("sigmas","SIGMAS"),@("latent_image","LATENT")) @(@("output","LATENT"),@("denoised_output","LATENT")) @()
Add-Node 40 "VAEDecode" @(2440,1070) @(210,100) @(@("samples","LATENT"),@("vae","VAE")) @(@("IMAGE","IMAGE")) @()
Add-Node 41 "SaveImage" @(2710,980) @(430,500) @(@("images","IMAGE")) @() @("flux2-no-lora-strong-identity-street-v1/final") "FINAL — strong identity + 9B street"

Add-Link 2 0 10 0 "CLIP"
Add-Link 3 0 6 1 "VAE"; Add-Link 3 0 9 1 "VAE"; Add-Link 3 0 15 1 "VAE"
Add-Link 3 0 20 1 "VAE"; Add-Link 3 0 23 1 "VAE"; Add-Link 3 0 40 1 "VAE"
Add-Link 4 0 5 0 "IMAGE"; Add-Link 5 0 6 0 "IMAGE"
Add-Link 7 0 8 0 "IMAGE"; Add-Link 8 0 9 0 "IMAGE"
Add-Link 10 0 11 0 "CONDITIONING"; Add-Link 6 0 11 1 "LATENT"
Add-Link 11 0 12 0 "CONDITIONING"; Add-Link 9 0 12 1 "LATENT"
Add-Link 1 0 14 0 "MODEL"
Add-Link 12 0 14 1 "CONDITIONING"; Add-Link 12 0 14 2 "CONDITIONING"; Add-Link 13 0 14 3 "LATENT"
Add-Link 14 0 15 0 "LATENT"; Add-Link 15 0 16 0 "IMAGE"; Add-Link 15 0 19 0 "IMAGE"

Add-Link 17 0 34 0 "MODEL"
Add-Link 18 0 24 0 "CLIP"; Add-Link 18 0 25 0 "CLIP"
Add-Link 19 0 20 0 "IMAGE"; Add-Link 21 0 22 0 "IMAGE"; Add-Link 22 0 23 0 "IMAGE"
Add-Link 24 0 26 0 "CONDITIONING"; Add-Link 20 0 26 1 "LATENT"
Add-Link 26 0 27 0 "CONDITIONING"; Add-Link 6 0 27 1 "LATENT"
Add-Link 27 0 28 0 "CONDITIONING"; Add-Link 9 0 28 1 "LATENT"
Add-Link 28 0 29 0 "CONDITIONING"; Add-Link 23 0 29 1 "LATENT"
Add-Link 25 0 30 0 "CONDITIONING"; Add-Link 20 0 30 1 "LATENT"
Add-Link 30 0 31 0 "CONDITIONING"; Add-Link 6 0 31 1 "LATENT"
Add-Link 31 0 32 0 "CONDITIONING"; Add-Link 9 0 32 1 "LATENT"
Add-Link 32 0 33 0 "CONDITIONING"; Add-Link 23 0 33 1 "LATENT"
Add-Link 29 0 34 1 "CONDITIONING"; Add-Link 33 0 34 2 "CONDITIONING"
Add-Link 37 0 39 0 "NOISE"; Add-Link 34 0 39 1 "GUIDER"; Add-Link 35 0 39 2 "SAMPLER"
Add-Link 36 0 39 3 "SIGMAS"; Add-Link 38 0 39 4 "LATENT"; Add-Link 39 0 40 0 "LATENT"
Add-Link 40 0 41 0 "IMAGE"

$workflow = [ordered]@{
    id = "flux2-no-lora-strong-identity-street-v1"
    revision = 1
    last_node_id = 41
    last_link_id = $script:linkId
    nodes = @($script:nodes.Values)
    links = $script:links
    groups = @(
        [ordered]@{ id = 1; title = "STAGE 1 — Klein 9B owns detailed street realism"; bounding = @(-1260,-670,3440,1510); color = "#3b6f8f"; font_size = 24; flags = @{} },
        [ordered]@{ id = 2; title = "STAGE 2 — Klein 4B Base owns Mitch identity (30 fast / 50 quality)"; bounding = @(-1260,740,4480,1080); color = "#8f6c3b"; font_size = 24; flags = @{} }
    )
    config = @{}
    extra = [ordered]@{
        workflowRendererVersion = "LG"
        notes = "Tested on RTX 3090 at 832x1248. Stage 1: Klein 9B, 4 steps, CFG 1, two 1 MP genuine refs. Stage 2: Klein Base 4B, CFG 4, Stage-1 scene at 0.5 MP plus three 1 MP genuine refs. Production smartphone prompt at 30 steps: 230.048 s, centroid 0.7494, minimum 0.6204. Quality option 50 steps: 345.705 s, centroid 0.7584, minimum 0.6262. No character LoRA, PuLID, output mask, crop, face swap, or post-processing."
    }
    version = 0.4
}

$destinationDirectory = Split-Path -Parent $destinationPath
New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
$json = $workflow | ConvertTo-Json -Depth 100
[IO.File]::WriteAllText($destinationPath, $json + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
Write-Host "Built FLUX.2 no-LoRA strong-identity workflow: $destinationPath"
