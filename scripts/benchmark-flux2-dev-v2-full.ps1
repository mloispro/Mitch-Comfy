param(
    [Parameter(Mandatory = $true)]
    [ValidateCount(1, 3)]
    [int[]]$CandidateSteps,
    [ValidateSet("1.0", "0.8")]
    [string]$Strength = "1.0",
    [string]$ComfyUrl = "http://127.0.0.1:8188"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$trainingDirectory = "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit\output\m1tch-flux2-dev-identity-v2"
$comfyLoraDirectory = "C:\projects\AI-Tools\ComfyUI\models\loras\flux2-dev-identity-v2-candidates"
$results = [System.Collections.Generic.List[object]]::new()
$numericStrength = [double]::Parse($Strength, [Globalization.CultureInfo]::InvariantCulture)
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source

foreach ($step in $CandidateSteps) {
    if ($step -notin @(250, 300, 350, 400, 450, 500)) {
        throw "Full evaluation accepts only screened steps 250/300/350/400/450/500; received $step."
    }
    $tag = "s$($step.ToString('0000'))"
    $source = if ($step -eq 500) {
        Join-Path $trainingDirectory "m1tch-flux2-dev-identity-v2.safetensors"
    } else {
        Join-Path $trainingDirectory "m1tch-flux2-dev-identity-v2_$($step.ToString('000000000')).safetensors"
    }
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Checkpoint is missing: $source" }
    New-Item -ItemType Directory -Path $comfyLoraDirectory -Force | Out-Null
    $filename = "m1tch-flux2-dev-identity-v2-$tag.safetensors"
    $destination = Join-Path $comfyLoraDirectory $filename
    Copy-Item -LiteralPath $source -Destination $destination -Force
    $relativeName = "flux2-dev-identity-v2-candidates\$filename"

    & $pwsh -NoProfile -File (Join-Path $repoRoot "scripts\benchmark-flux2-dev-lora-only.ps1") `
        -ComfyUrl $ComfyUrl `
        -LoraName $relativeName `
        -LoraStrength $numericStrength `
        -Steps 28 `
        -Guidance 4.0 `
        -BaseSeed 8675310 `
        -Width 832 `
        -Height 1248 `
        -Campaign "flux2-dev-identity-v2" `
        -OutputPrefix "identity-eval/flux2-dev-v2/full"
    $diagnosticExitCode = $LASTEXITCODE
    $latestReport = Get-ChildItem -LiteralPath (Join-Path $repoRoot "work\flux2-dev-identity-v2\benchmarks") -Filter "*$tag*.json" -File | Sort-Object LastWriteTime | Select-Object -Last 1
    $results.Add([pscustomobject]@{
        step = $step
        strength = $numericStrength
        checkpoint = $source
        checkpoint_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant()
        diagnostic_exit_code = $diagnosticExitCode
        report = if ($latestReport) { $latestReport.FullName } else { $null }
        manual_review_required = $true
        promotion_eligible = $false
    })
}

$indexPath = Join-Path $repoRoot "work\flux2-dev-identity-v2\comparisons\full-evaluation-index-s$($Strength.Replace('.', ''))-$(Get-Date -Format 'yyyyMMdd-HHmmss').json"
New-Item -ItemType Directory -Path (Split-Path -Parent $indexPath) -Force | Out-Null
[ordered]@{
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    candidates = $results
    scenes = @("portrait", "waist-up-social", "near-profile-candid", "full-body-walking", "friends-crowd-stress")
    policy = "InsightFace is diagnostic only. Manual full-size and thumbnail identity review and crowd-leakage review control acceptance."
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $indexPath -Encoding utf8
Write-Host "Full-evaluation index: $indexPath"
