$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$workRoot = Join-Path $repoRoot "work\flux2-dev-identity-v2"
$chainPid = 28280
$step1100Record = Join-Path $workRoot "approvals\step-1100-evaluation.json"
$runner = Join-Path $repoRoot "scripts\run-flux2-dev-identity-v2-gated.ps1"
$benchmark = Join-Path $repoRoot "scripts\benchmark-flux2-dev-v2-gate.ps1"
$validator = Join-Path $repoRoot "scripts\validate-flux2-dev-v2-checkpoint.py"
$python = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$optimizer = "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit\output\m1tch-flux2-dev-identity-v2\optimizer.pt"
$checkpoint1100 = Join-Path $workRoot "checkpoint-archives\m1tch-flux2-dev-identity-v2-step-1100.safetensors"
$validation1100 = Join-Path $workRoot "checkpoint-validation\pre-resume-step-1100.json"
$finalRecord = Join-Path $workRoot "approvals\step-1200-evaluation.json"
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source

while ($true) {
    if (Test-Path -LiteralPath $step1100Record -PathType Leaf) {
        $state = Get-Content -Raw -LiteralPath $step1100Record | ConvertFrom-Json
        if ($state.status -eq "complete") { break }
    }
    if (-not (Get-Process -Id $chainPid -ErrorAction SilentlyContinue)) {
        throw "The To1100 chain exited before its evaluation completed."
    }
    Start-Sleep -Seconds 30
}
while (Get-Process -Id $chainPid -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 5 }

& $python $validator $checkpoint1100 --expected-step 1100 --expected-modules 128 --optimizer $optimizer --json-output $validation1100
if ($LASTEXITCODE -ne 0) { throw "Step-1100 checkpoint or optimizer validation failed; refusing to continue." }

& $pwsh -NoProfile -ExecutionPolicy Bypass -File $runner -Phase To1200
if ($LASTEXITCODE -ne 0) { throw "To1200 gated runner failed with exit code $LASTEXITCODE." }

$releaseDeadline = (Get-Date).AddMinutes(3)
do {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:8188/free" -Method Post -ContentType "application/json" -Body '{"unload_models":true,"free_memory":true}' -TimeoutSec 30 | Out-Null
    } catch {
        Write-Warning "Could not request a 3090 Comfy memory release: $($_.Exception.Message)"
    }
    $usedMemory = [int](((& nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | Select-Object -First 1).Trim()))
    if ($usedMemory -le 4096) { break }
    Start-Sleep -Seconds 5
} while ((Get-Date) -lt $releaseDeadline)
if ($usedMemory -gt 4096) { throw "RTX 3090 memory did not release after To1200." }

[ordered]@{
    status = "running"
    started_utc = (Get-Date).ToUniversalTime().ToString("o")
    training_paused_at_step = 1200
    comparison = "steps 1000, 1100, and 1200"
    publication_approved = $false
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $finalRecord -Encoding utf8

& $pwsh -NoProfile -ExecutionPolicy Bypass -File $benchmark -Mode Gate1200
if ($LASTEXITCODE -ne 0) { throw "Gate1200 benchmark failed with exit code $LASTEXITCODE." }

$manifest = Join-Path $workRoot "comparisons\gate-1200\gate-1200-manifest.json"
$sheet = Join-Path $workRoot "comparisons\gate-1200\gate-1200-review-thumbnails.jpg"
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf) -or -not (Test-Path -LiteralPath $sheet -PathType Leaf)) {
    throw "Gate1200 benchmark did not create its manifest and contact sheet."
}
[ordered]@{
    status = "complete"
    completed_utc = (Get-Date).ToUniversalTime().ToString("o")
    training_paused_at_step = 1200
    resume_requires_mitch_approval = $true
    publication_approved = $false
    manifest = $manifest
    contact_sheet = $sheet
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $finalRecord -Encoding utf8

Write-Host "To1200 training and Gate1200 evaluation completed; nothing was published."
