param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [string]$FaceReference = "20260815_165446.jpg",
    [Parameter(Mandatory = $true)][string]$LoraName,
    [double]$LoraStrength = 0.8,
    [int]$Steps = 50,
    [double]$GuidanceScale = 4.0,
    [string]$ScenePrompt = "A casual waist-up smartphone photo on a shaded city sidewalk in soft afternoon daylight, wearing a fitted navy crew-neck T-shirt, relaxed posture, small natural smile, looking at the camera.",
    [long]$Seed = 8675310,
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
$workflow = @{
    "1" = @{
        class_type = "Flux2IdentityLoraExperiment"
        inputs = @{
            face_reference = $FaceReference
            scene_prompt = $ScenePrompt
            lora_name = $LoraName
            lora_strength = $LoraStrength
            steps = $Steps
            guidance_scale = $GuidanceScale
            seed = $Seed
        }
    }
}
$body = @{ prompt = $workflow; client_id = "flux2-identity-lora" } | ConvertTo-Json -Depth 10
$queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt_id."
}
Write-Host "Queued identity LoRA '$LoraName' at strength $LoraStrength`: $($queued.prompt_id)"

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.($queued.prompt_id)
    if ($entry) {
        if ($entry.status.status_str -eq "success") {
            $image = @($entry.outputs."1".images)[0]
            [pscustomobject]@{
                lora_name = $LoraName
                lora_strength = $LoraStrength
                steps = $Steps
                guidance_scale = $GuidanceScale
                filename = $image.filename
                subfolder = $image.subfolder
                type = $image.type
            } | ConvertTo-Json -Compress
            exit 0
        }
        if ($entry.status.status_str -eq "error") {
            $entry | ConvertTo-Json -Depth 12
            throw "Identity LoRA experiment failed."
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for identity LoRA experiment $($queued.prompt_id)."
