[CmdletBinding()]
param(
    [string]$Source = "checkpoints\legacy-workflows\production\Krea 2 Identity Edit - Face Attention v2.json",
    [string]$Destination = "checkpoints\legacy-workflows\production\Krea 2 No Character LoRA Street Corner v1.json",
    [string]$Reference = "20260815_165446.jpg",
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

$scenePrompt = @"
Restage this exact same man in a new candid vertical smartphone photograph at a somewhat busy downtown street corner. Preserve his exact recognizable facial identity, face shape, forehead lines, eye shape and spacing, nose, mouth, ears, short light-brown hairstyle, hairline, apparent age, natural skin texture, and lean build. He walks naturally toward the camera with the camera directly seeing his face and front torso, framed about knees-up and slightly off center, wearing a plain fitted navy crew-neck T-shirt and dark casual pants. Unrelated pedestrians cross and walk behind him at varied depths and in both directions; nearby people have independent clothing colors and natural actions. Clearly resolve storefront windows, traffic lights, cars, street signs, curb, crosswalk paint, pavement texture, and building detail extending into the distance. Use ordinary soft late-afternoon daylight, natural recent-smartphone exposure, restrained phone HDR, realistic skin pores, subtle sensor texture, and normal small-sensor depth with coherent exposure, sharpness, noise, and edge softness across the subject and scene. Make the result look like one genuine unedited rear-phone-camera photograph captured in a single moment.
"@.Trim()

$workflow = Get-Content -Raw -LiteralPath $sourcePath | ConvertFrom-Json -AsHashtable
$workflow.id = "krea2-no-character-lora-street-corner-v1"
$workflow.revision = [int]$workflow.revision + 1
$nodes = @{}
foreach ($node in $workflow.nodes) {
    $nodes[[int]$node.id] = $node
}

$nodes[72].widgets_values[0] = $Reference
$nodes[84].widgets_values[0] = $scenePrompt
$nodes[84].widgets_values[1] = 512
$nodes[29].widgets_values[0] = "krea2-identity-edit/no-character-lora-street-corner-v1"
$nodes[106].widgets_values[0] = @"
KREA 2 IDENTITY EDIT — NO CHARACTER LoRA STREET CORNER v1

This is the tested fallback after native FLUX.2 and PuLID-Flux2 failed Mitch identity. One genuine photograph enters both trained Krea2 Identity Edit paths. The internal face mask controls reference attention only; it never masks, inpaints, or composites output pixels.

Locked settings: Identity Edit v1.2 strength 1.0, masked ref boost 6, grounding 512, camera-appearance LoRA 0.35, 832x1248, 12 Euler/simple steps, CFG 1, seed 9472103. The camera LoRA is not a character LoRA.

Tested street-corner candidate: 0.7459 against five held-out genuine photographs (calibrated strong match). Visual approval remains authoritative.
"@.Trim()

$destinationDirectory = Split-Path -Parent $destinationPath
New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
$json = $workflow | ConvertTo-Json -Depth 100
[IO.File]::WriteAllText($destinationPath, $json + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
Write-Host "Built no-character-LoRA street-corner workflow: $destinationPath"
