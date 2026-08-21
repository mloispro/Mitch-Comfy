param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [Parameter(Mandatory = $true)][string]$Reference1,
    [string]$Reference2 = "[none]",
    [string]$Reference3 = "[none]",
    [string]$Reference4 = "[none]",
    [string]$Prompt = "Create a new realistic smartphone portrait of the same adult man shown in Picture 1. Preserve his identity exactly: face shape, eyes, nose, mouth, ears, hairline, apparent age, and natural skin texture. He is wearing a fitted dark navy crew-neck T-shirt, standing on a shaded city sidewalk in soft afternoon daylight, waist-up, relaxed posture, slight natural smile, looking at the camera. Ordinary recent phone photo, subtle sensor noise, realistic skin, no beauty filter, no studio retouching. Do not copy the reference background or clothing.",
    [int]$Width = 768,
    [int]$Height = 1024,
    [long]$Seed = 8675309,
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
$references = @($Reference1, $Reference2, $Reference3, $Reference4) | Where-Object { $_ -ne "[none]" }
if (-not $references) {
    throw "Pass at least one genuine reference photo."
}
$knownSyntheticFixture = $references | Where-Object {
    [IO.Path]::GetFileName($_) -match "^mitch(?:-workbench)?-qwen-id-(front|left|right)\.png$"
}
if ($knownSyntheticFixture) {
    throw "Generated Qwen identity fixtures cannot be used by the 9B KV identity proof. Pass genuine camera originals."
}

$workflow = @{
    "1" = @{
        class_type = "Klein9BKVIdentityProof"
        inputs = @{
            reference_1 = $Reference1
            reference_2 = $Reference2
            reference_3 = $Reference3
            reference_4 = $Reference4
            prompt = $Prompt
            width = $Width
            height = $Height
            seed = $Seed
        }
    }
}

$body = @{ prompt = $workflow; client_id = "klein9b-kv-identity-proof" } | ConvertTo-Json -Depth 12
$queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt_id."
}
Write-Host "Queued native FLUX.2 Klein 9B KV identity proof: $($queued.prompt_id)"

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 10
    $entry = $history.($queued.prompt_id)
    if ($entry) {
        $status = $entry.status.status_str
        if ($status -eq "success") {
            $summary = $entry.outputs."1".text | Select-Object -First 1
            Write-Host "9B KV identity proof succeeded."
            if ($summary) {
                Write-Host $summary
            }
            $entry | ConvertTo-Json -Depth 12
            exit 0
        }
        if ($status -eq "error") {
            $entry | ConvertTo-Json -Depth 12
            throw "9B KV identity proof failed."
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for 9B KV identity proof $($queued.prompt_id)."
