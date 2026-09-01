[CmdletBinding()]
param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [long[]]$Seeds = @(8675421, 8675422, 8675423, 8675424),
    [int]$TimeoutSeconds = 1200,
    [string]$ManifestRoot = "C:\projects\AI-Tools\Mitch-Comfy\output\crowd-proof-campaign"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $PSScriptRoot "run-klein9b-scene-plates.ps1"
$prompt = @"
An ordinary candid vertical rear-camera smartphone photograph at a genuinely busy Midwestern state fair in clear late-afternoon open daylight. One plausible adult man in his early-to-mid forties with a lean average build and short light-brown hair is naturally embedded among the foreground pedestrians, slightly off center, captured mid-stride rather than planted or posing. His complete head, ears, neck, hands, legs, shoes, and contact shadow are coherent. His unobstructed face is specifically 112 to 128 pixels tall, turned only slightly toward the camera while his eyes look past it, suitable for later identity replacement. His visible body is naturally proportioned: the head is roughly one eighth of his visible height and his shoulders are at least two and a half head widths, with no oversized head. He wears a plain fitted muted navy crew-neck T-shirt and dark casual pants. He is not isolated, enlarged, spotlighted, selectively sharp, or given an empty hero lane; nearby pedestrians overlap his space naturally.

The crowd is dense and irregular at foreground, middle, and far depth. Nearby people overlap the host naturally without covering his face; other pedestrians move laterally, diagonally, toward, and away from the camera with mostly side and rear views. People perform independent fair activities and have different ages, builds, hair, poses, and clothing. Clothing spans muted red, rust, green, denim blue, tan, mustard, gray, patterned fabric, black, and white with no coordinated wardrobe and no dominant black/white/navy shirts. Preserve coherent food stalls, colorful umbrellas, railings, pavement clutter, ride structures, and one correctly formed Ferris wheel in the middle distance. Maintain resolved phone-camera detail through the middle distance with gentle far falloff, restrained phone HDR, natural edge softness, mild sensor texture, and plausible motion only on moving people.

This must look like one unedited phone capture of one instant: no flash, portrait blur, beauty filter, cinematic grading, parade row, mirrored layout, synchronized stride, duplicated faces, repeated props, fused people, malformed limbs, floating objects, legible brand text, logo, or watermark.
"@

$started = Get-Date
$result = & $runner `
    -ComfyUrl $ComfyUrl `
    -ExpectedGpuName "NVIDIA GeForce RTX 3090" `
    -Prompt $prompt `
    -Width 896 `
    -Height 1344 `
    -Seeds $Seeds `
    -TimeoutSeconds $TimeoutSeconds

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$manifestDirectory = Join-Path $ManifestRoot $stamp
New-Item -ItemType Directory -Path $manifestDirectory -Force | Out-Null
$manifestPath = Join-Path $manifestDirectory "replacement-plates.json"
$manifest = [ordered]@{
    schema_version = 1
    purpose = "state_fair_replacement_plate_campaign"
    backend = "FLUX.2 Klein 9B KV FP8"
    gpu = "NVIDIA GeForce RTX 3090"
    width = 896
    height = 1344
    steps = 4
    seeds = $Seeds
    prompt = $prompt.Trim()
    elapsed_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
    runner_output = @($result)
}
$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding utf8
$manifest["manifest_path"] = $manifestPath
$manifest | ConvertTo-Json -Depth 20
