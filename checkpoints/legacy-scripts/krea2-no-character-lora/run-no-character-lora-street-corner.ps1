[CmdletBinding()]
param(
    [string]$Reference = "20260815_165446.jpg",
    [uint64]$Seed = 9472103,
    [int]$Port = 8189,
    [string]$ExpectedGpuName = "NVIDIA GeForce RTX 4070",
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"

foreach ($workerPort in 8188, 8189) {
    $queue = Invoke-RestMethod -Uri "http://127.0.0.1:$workerPort/queue" -TimeoutSec 10
    if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
        throw "ComfyUI queue $workerPort is not idle. Refusing to disturb active GPU work."
    }
}

$scenePrompt = @"
Restage this exact same man in a new candid vertical smartphone photograph at a somewhat busy downtown street corner. Preserve his exact recognizable facial identity, face shape, forehead lines, eye shape and spacing, nose, mouth, ears, short light-brown hairstyle, hairline, apparent age, natural skin texture, and lean build. He walks naturally toward the camera with the camera directly seeing his face and front torso, framed about knees-up and slightly off center, wearing a plain fitted navy crew-neck T-shirt and dark casual pants. Unrelated pedestrians cross and walk behind him at varied depths and in both directions; nearby people have independent clothing colors and natural actions. Clearly resolve storefront windows, traffic lights, cars, street signs, curb, crosswalk paint, pavement texture, and building detail extending into the distance. Use ordinary soft late-afternoon daylight, natural recent-smartphone exposure, restrained phone HDR, realistic skin pores, subtle sensor texture, and normal small-sensor depth with coherent exposure, sharpness, noise, and edge softness across the subject and scene. Make the result look like one genuine unedited rear-phone-camera photograph captured in a single moment.
"@.Trim()

$runner = Join-Path $PSScriptRoot "smoke-krea2-identity-edit.ps1"
& $runner `
    -Reference $Reference `
    -Prompt $scenePrompt `
    -Seed $Seed `
    -Width 832 `
    -Height 1248 `
    -Steps 12 `
    -RefBoost 6.0 `
    -SmartphoneLoraStrength 0.35 `
    -GroundingPixels 512 `
    -FaceAttentionMask `
    -ApplyPhoneFinish `
    -OutputPrefix "krea2-identity-edit/no-character-lora-street-corner-v1" `
    -Port $Port `
    -ExpectedGpuName $ExpectedGpuName `
    -TimeoutSeconds $TimeoutSeconds
