[CmdletBinding()]
param(
    [string]$ComfyRoot = 'C:\projects\AI-Tools\ComfyUI',
    [string]$BaselineReport = 'C:\projects\AI-Tools\ComfyUI\output\flux2-klein9b-upgrade-photo-detail-realism-v1\20260903-005704-305944\report.json',
    [string]$OutputDirectory = 'work\flux2-klein9b-attractiveness-20260903\generation-high-v1',
    [switch]$SourceExpressionRefinement
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Server = 'http://127.0.0.1:8188'
$SourceName = 'mitch-canyon-source-edit-05333f6f.png'
$Baseline = Get-Content -Raw -LiteralPath $BaselineReport | ConvertFrom-Json
if (-not $Baseline.phone_camera_style -or $Baseline.turbo -or $Baseline.steps -ne 50 -or $Baseline.seed -ne 8675412) {
    throw 'The comparison baseline must be the accepted 50-step phone-on, non-Turbo, seed-8675412 canyon run.'
}
$Workers = foreach ($Port in 8188,8189,8190) {
    try {
        $Stats = Invoke-RestMethod "http://127.0.0.1:$Port/system_stats" -TimeoutSec 3
        $Queue = Invoke-RestMethod "http://127.0.0.1:$Port/queue" -TimeoutSec 3
        [pscustomobject]@{port=$Port; online=$true; device=$Stats.devices[0].name; running=@($Queue.queue_running).Count; pending=@($Queue.queue_pending).Count}
    } catch {
        $Socket = [Net.Sockets.TcpClient]::new()
        try { $Listening = $Socket.ConnectAsync('127.0.0.1',$Port).Wait(500) -and $Socket.Connected } catch { $Listening=$false } finally { $Socket.Dispose() }
        if ($Listening) { throw "Cannot inspect listening worker $Port." }
        [pscustomobject]@{port=$Port; online=$false; device='offline'; running=0; pending=0}
    }
}
$Target = @($Workers | Where-Object port -eq 8188)[0]
if (-not $Target.online -or $Target.device -notmatch 'RTX 3090' -or $Target.running -or $Target.pending) { throw 'Required 3090 worker is unavailable or busy.' }
if (@($Workers | Where-Object { $_.device -match '3090' -and ($_.running -or $_.pending) }).Count) { throw 'Shared 3090 work is active.' }
$Hardware = @(& nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader,nounits)
$Gpu3090 = @($Hardware | Where-Object { $_ -match 'RTX 3090' })
if ($Gpu3090.Count -ne 1) { throw '3090 hardware identity unavailable.' }
$GpuFields = $Gpu3090[0] -split ',\s*'
if ([int]$GpuFields[2] -gt 4096 -or [int]$GpuFields[3] -gt 10) { throw '3090 hardware is not idle.' }
$Info = Invoke-RestMethod "$Server/object_info/Flux2Klein9BPhotoRealismUpgradeV11" -TimeoutSec 10
if (-not $Info.Flux2Klein9BPhotoRealismUpgradeV11) { throw 'Upgrade v1.1 node is unavailable.' }
if (-not (Test-Path -LiteralPath (Join-Path $ComfyRoot "input\$SourceName"))) { throw 'Source image missing.' }
$HighInstruction = 'Facial expression and cheek refinement: keep m1tch_person recognizable, with naturally lean cheek planes and a clean cheek-to-jaw taper rather than rounded, inflated cheek apples. Closely preserve Picture 1''s lip-line curvature, mouth proportions, and relaxed expression. When the source smiles, reproduce its restrained asymmetric closed-lip smile: one corner gently raised, the opposite corner relaxed, with naturally coordinated cheek tension. Do not replace it with uniformly lifted mouth corners, a forced grin, pursed lips, swollen cheeks, or a generic beauty face. Keep teeth hidden. Retain the exact source head angle, gaze, eye shape, forehead height, and hairline; keep real skin texture and natural facial shading.'
if ($SourceExpressionRefinement) {
    $HighInstruction = 'Stronger flattering facial treatment for m1tch_person: retain his recognizable features and adult age, with lean lower cheeks, clearly defined cheekbone-to-jaw taper, and relaxed facial muscles. The expression comes from Picture 1, not from the identity portrait. Match Picture 1''s appealing relaxed asymmetric half-smile, its exact curved lip seam, and the gentle smiling narrowing of the eyelids. The lips softly meet along their full length, concealing all teeth; one mouth corner is gently raised and the opposite corner stays relaxed. Keep the cheek crease naturally connected to that restrained half-smile. Give the existing eyes and eyebrows a noticeably rested, confident appearance, with cleaner brow definition and less forehead frown tension and under-eye creasing. Preserve the iris position within each eye, exact head angle, forehead height, hairline, and facial proportions. Skin remains clear and even with fine irregular pores and light natural stubble; preserve real facial shading and do not add cheek volume.'
}
$Detail = "$($Baseline.detail_instructions) $HighInstruction"
$Prompt = [ordered]@{
    '1' = @{class_type='LoadImage';inputs=@{image=$SourceName}}
    '2' = @{class_type='Flux2Klein9BPhotoRealismUpgradeV11';inputs=@{source_photo=@('1',0);detail_instructions=$Detail;appearance_polish='off';phone_camera_style=$true;seed=[UInt64]8675412}}
}
$Destination = Join-Path $ProjectRoot $OutputDirectory
if (Test-Path -LiteralPath (Join-Path $Destination 'submission.json')) { throw 'This experiment has already been submitted. Use its saved prompt ID.' }
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$Manifest = [ordered]@{status='prepared';purpose='single-variable generation-prompt experiment, not a production promotion';baseline_report=$BaselineReport;source=$SourceName;high_instruction=$HighInstruction;detail_instructions=$Detail;seed=8675412;steps=50;phone_camera_style=$true;turbo=$false;appearance='off to save raw; accepted polish is replayed separately';workers=$Workers;hardware=$Hardware;prompt=$Prompt}
$Manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $Destination 'experiment.json') -Encoding utf8
$Body = @{prompt=$Prompt;client_id="upgrade-expression-$([guid]::NewGuid().ToString('N'))"} | ConvertTo-Json -Depth 20
$Submission = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType 'application/json' -Body $Body -TimeoutSec 30
$Submission | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $Destination 'submission.json') -Encoding utf8
$Submission | ConvertTo-Json -Depth 20
