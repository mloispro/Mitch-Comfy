param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [string]$FaceReference = "20260815_165446.jpg",
    [Parameter(Mandatory = $true)][string]$LoraName,
    [double]$LoraStrength = 0.8,
    [int]$Steps = 50,
    [double]$GuidanceScale = 4.0,
    [ValidateSet("Action", "Quick", "Full")][string]$Profile = "Quick",
    [long]$Seed = 8675310,
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
$benchmarkStarted = Get-Date
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
$professionalScene = @{
        name = "professional"
        prompt = "A natural professional waist-up portrait in a modern loft beside a large window, wearing a charcoal blazer over an open-collar pale blue shirt, relaxed confident expression looking at the camera, realistic 50mm camera photograph, restrained retouching and natural skin."
    }
$actionScene = @{
        name = "action-profile"
        prompt = "A candid smartphone action photo walking along a lakeside path at golden hour, wearing a fitted forest green henley, three-quarter profile looking ahead and not at the camera, waist-up to mid-thigh, photographed by a friend, natural stride, slight believable motion and real skin texture."
    }
$scenes = if ($Profile -eq "Action") { @($actionScene) } else { @($professionalScene, $actionScene) }
if ($Profile -eq "Full") {
    $scenes += @{
        name = "phone-candid"
        prompt = "A casual waist-up smartphone photo sitting at an outdoor cafe in soft afternoon daylight, wearing a fitted navy crew-neck T-shirt, relaxed posture, small natural smile, looking just past the camera, believable phone-camera texture."
    }
}

$candidates = [System.Collections.Generic.List[string]]::new()
$candidateLabels = [System.Collections.Generic.List[string]]::new()
foreach ($scene in $scenes) {
    $workflow = @{
        "1" = @{
            class_type = "Flux2IdentityLoraExperiment"
            inputs = @{
                face_reference = $FaceReference
                scene_prompt = $scene.prompt
                lora_name = $LoraName
                lora_strength = $LoraStrength
                steps = $Steps
                guidance_scale = $GuidanceScale
                seed = $Seed
            }
        }
    }
    $body = @{ prompt = $workflow; client_id = "flux2-identity-lora-benchmark" } | ConvertTo-Json -Depth 10
    $queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
    if (-not $queued.prompt_id) {
        throw "ComfyUI did not return a prompt_id for $($scene.name)."
    }
    Write-Host "Queued $($scene.name): $($queued.prompt_id)"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        Start-Sleep -Seconds 2
        $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 10
        $entry = $history.($queued.prompt_id)
        if ($entry -and $entry.status.status_str -eq "error") {
            $entry | ConvertTo-Json -Depth 12
            throw "LoRA benchmark failed for $($scene.name)."
        }
        if ($entry -and $entry.status.status_str -eq "success") {
            $image = @($entry.outputs."1".images)[0]
            $candidates.Add((Join-Path $ComfyRoot ("output\" + $image.subfolder + "\" + $image.filename)))
            $candidateLabels.Add($scene.name)
            break
        }
    } while ((Get-Date) -lt $deadline)
    if (-not $entry -or $entry.status.status_str -ne "success") {
        throw "Timed out waiting for $($scene.name)."
    }
}

$safeName = ($LoraName -replace '[^A-Za-z0-9._-]', '-')
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportPath = Join-Path $RepoRoot ("work\identity-evals\" + $safeName + "-s" + $LoraStrength + "-n" + $Steps + "-g" + $GuidanceScale + "-" + $stamp + ".json")
$evalArgs = [System.Collections.Generic.List[string]]::new()
$evalArgs.Add((Join-Path $RepoRoot "scripts\evaluate-face-likeness.py"))
foreach ($reference in @(
    "20260815_165446.jpg",
    "20260815_165449.jpg",
    "20260818_173106.jpg",
    "20260508_123156.jpg"
)) {
    $evalArgs.Add("--reference")
    $evalArgs.Add((Join-Path $ComfyRoot ("input\" + $reference)))
}
for ($index = 0; $index -lt $candidates.Count; $index++) {
    $evalArgs.Add("--candidate")
    $evalArgs.Add($candidates[$index])
    $evalArgs.Add("--candidate-label")
    $evalArgs.Add($candidateLabels[$index])
}
$evalArgs.Add("--json-output")
$evalArgs.Add($reportPath)

& "C:\projects\AI-Tools\ComfyUI\.venv\Scripts\python.exe" @evalArgs
if ($LASTEXITCODE -ne 0) {
    throw "Local identity evaluation failed."
}
$report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
$report | Add-Member -NotePropertyName benchmark -NotePropertyValue ([pscustomobject]@{
    lora_name = $LoraName
    lora_strength = $LoraStrength
    steps = $Steps
    guidance_scale = $GuidanceScale
    profile = $Profile
    seed = $Seed
    duration_seconds = [math]::Round(((Get-Date) - $benchmarkStarted).TotalSeconds, 3)
})
foreach ($candidate in $report.candidates) {
    $generationReportPath = Join-Path (Split-Path -Parent $candidate.path) "report.json"
    if (Test-Path -LiteralPath $generationReportPath) {
        $candidate | Add-Member -NotePropertyName generation -NotePropertyValue (
            Get-Content -Raw -LiteralPath $generationReportPath | ConvertFrom-Json
        )
    }
}
$report | ConvertTo-Json -Depth 24 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Host "Saved benchmark report: $reportPath"
