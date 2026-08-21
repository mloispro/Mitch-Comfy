param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [Parameter(Mandatory = $true)][string]$Reference1,
    [string]$Reference2 = "[none]",
    [string]$Reference3 = "[none]",
    [string]$Reference4 = "[none]",
    [ValidateSet("Auto", "Front", "Left", "Right", "Full Body", "General", "Ignore")][string]$Reference4Role = "Auto",
    [ValidateSet("Single", "Dating Pack", "Instagram Pack")][string]$Mode = "Single",
    [string]$Brief = "A relaxed, approachable outdoor portrait suitable for a modern dating profile.",
    [ValidateSet("Auto Mix", "Natural Candid", "Smart Casual", "Travel", "Hobby/Active", "Pet", "Night Out", "Custom")][string]$ScenePreset = "Natural Candid",
    [ValidateSet("Authentic Phone", "Professional", "35mm Lifestyle")][string]$CameraLook = "Authentic Phone",
    [ValidateSet("Auto Mix", "Looking at camera", "Candid/action")][string]$CameraRelationship = "Looking at camera",
    [ValidateSet("Portrait 2:3", "Instagram 4:5", "Square", "Landscape 3:2")][string]$Aspect = "Portrait 2:3",
    [int]$PhotoCount = 1,
    [long]$Seed = 8675309,
    [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = "Stop"
$references = @($Reference1, $Reference2, $Reference3, $Reference4) | Where-Object { $_ -ne "[none]" }
$knownSyntheticFixture = $references | Where-Object {
    [IO.Path]::GetFileName($_) -match "^mitch(?:-workbench)?-qwen-id-(front|left|right)\.png$"
}
if ($knownSyntheticFixture) {
    throw "Generated Qwen identity fixtures cannot be used by Social Photo Studio. Pass genuine camera originals."
}

$prompt = @{
    "1" = @{
        class_type = "SocialPhotoSubjectReferences"
        inputs = @{
            reference_1 = $Reference1
            reference_1_role = "Auto"
            reference_2 = $Reference2
            reference_2_role = "Auto"
            reference_3 = $Reference3
            reference_3_role = "Auto"
            reference_4 = $Reference4
            reference_4_role = $Reference4Role
        }
    }
    "2" = @{
        class_type = "SocialPhotoSettings"
        inputs = @{
            mode = $Mode
            brief = $Brief
            scene_preset = $ScenePreset
            camera_look = $CameraLook
            camera_relationship = $CameraRelationship
            aspect = $Aspect
            photo_count = $PhotoCount
            seed = $Seed
        }
    }
    "3" = @{
        class_type = "SocialPhotoGenerate"
        inputs = @{
            subject = @("1", 0)
            settings = @("2", 0)
        }
    }
}

$body = @{ prompt = $prompt; client_id = "social-photo-smoke" } | ConvertTo-Json -Depth 12
$queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt_id."
}
Write-Host "Queued Social Photo Studio smoke test: $($queued.prompt_id)"

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.($queued.prompt_id)
    if ($entry) {
        $status = $entry.status.status_str
        if ($status -eq "success") {
            $report = $entry.outputs."3".text | Select-Object -First 1
            Write-Host "Smoke test succeeded."
            if ($report) {
                Write-Host $report
            }
            $entry | ConvertTo-Json -Depth 12
            exit 0
        }
        if ($status -eq "error") {
            $entry | ConvertTo-Json -Depth 12
            throw "Social Photo Studio smoke test failed."
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for Social Photo Studio smoke test $($queued.prompt_id)."
