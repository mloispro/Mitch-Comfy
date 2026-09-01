param(
    [Parameter(Mandatory = $true)]
    [string]$CheckpointPath,
    [ValidateSet("1.0", "0.8")]
    [string]$Strength = "1.0",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$workRoot = Join-Path $repoRoot "work\flux2-dev-identity-v2"
$approvalPath = Join-Path $workRoot "approvals\final-publication-approved.json"
if (-not (Test-Path -LiteralPath $approvalPath -PathType Leaf)) {
    throw "Final publication is locked until Mitch's explicit final-publication approval record exists."
}
$checkpoint = (Resolve-Path -LiteralPath $CheckpointPath).Path
$checkpointHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $checkpoint).Hash.ToLowerInvariant()
$approval = Get-Content -Raw -LiteralPath $approvalPath | ConvertFrom-Json
if ($approval.decision -ne "approved" -or $approval.checkpoint_sha256 -ne $checkpointHash -or [string]$approval.strength -ne $Strength) {
    throw "Approval is not bound to this exact checkpoint hash and strength."
}
foreach ($evidencePath in @([string]$approval.comfy_evaluation, [string]$approval.native_evaluation)) {
    if (-not $evidencePath -or -not (Test-Path -LiteralPath $evidencePath -PathType Leaf)) {
        throw "The approval record must reference existing Comfy and native evaluation evidence."
    }
}
$destination = Join-Path $ComfyRoot "models\loras\m1tch-flux2-dev-identity-v2-best.safetensors"
if (Test-Path -LiteralPath $destination -PathType Leaf) {
    $existingHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash.ToLowerInvariant()
    if ($existingHash -ne $checkpointHash) { throw "A different published v2-best file already exists; refusing to overwrite it." }
} else {
    Copy-Item -LiteralPath $checkpoint -Destination $destination
}
$workers = [System.Collections.Generic.List[object]]::new()
foreach ($port in 8188, 8189) {
    $queue = Invoke-RestMethod -Uri "http://127.0.0.1:$port/queue" -TimeoutSec 10
    $stats = Invoke-RestMethod -Uri "http://127.0.0.1:$port/system_stats" -TimeoutSec 10
    $workers.Add([pscustomobject]@{ port = $port; device = [string]$stats.devices[0].name; queue_running = @($queue.queue_running).Count; queue_pending = @($queue.queue_pending).Count })
}
if (($workers | Where-Object port -eq 8188).device -notmatch "RTX 3090" -or ($workers | Where-Object port -eq 8189).device -notmatch "RTX 4070") {
    throw "Both expected Comfy workers were not verified after publication."
}
$record = [ordered]@{
    published_utc = (Get-Date).ToUniversalTime().ToString("o")
    published_file = $destination
    sha256 = $checkpointHash
    source_checkpoint = $checkpoint
    strength = [double]$Strength
    approval = $approvalPath
    workers = $workers
    limitations = @("Portrait and half-body identity only", "Full-body identity and face scale are reported separately", "No distant-face locking claim")
}
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $workRoot "publication-record.json") -Encoding utf8
Write-Host "Published approved checkpoint: $destination"
