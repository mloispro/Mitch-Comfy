[CmdletBinding()]
param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [string]$OtherComfyUrl = "http://127.0.0.1:8189",
    [string]$SharedGpuComfyUrl = "http://127.0.0.1:8190",
    [string]$ForgeUrl = "http://127.0.0.1:7860",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string[]]$SceneSlugs = @(),
    [int]$CandidatesPerScene = 2,
    [bool]$FastTurbo = $true,
    [UInt64]$BaseSeed = 8676200,
    [int]$TimeoutSeconds = 1200,
    [int]$MaxIdle3090MemoryMiB = 4096,
    [int]$MaxIdle3090Utilization = 10,
    [switch]$PreflightOnly,
    [string]$RunLabel = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runStamp = if ($RunLabel) { $RunLabel } else { Get-Date -Format "yyyyMMdd-HHmmss" }
$runRoot = Join-Path $repoRoot "work\flux2-klein9b-visual-presets\candidates\$runStamp"
$runManifestPath = Join-Path $runRoot "manifest.json"
$presetManifestPath = Join-Path $repoRoot "custom_nodes\ComfyUI-AIToolkit-Training\web\assets\scene-presets\manifest.json"
$nodeType = "Flux2Klein9BMitchIdentityStudioVisualPresetsV11"

function Test-LocalTcpListener([int]$Port) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync("127.0.0.1", $Port)
        return ($task.Wait(1000) -and $client.Connected)
    }
    catch { return $false }
    finally { $client.Dispose() }
}

function Assert-LocalEndpoint([string]$Endpoint, [int]$ExpectedPort, [string]$Label) {
    $uri = [Uri]$Endpoint
    if ($uri.Scheme -ne "http" -or $uri.Host -notin @("127.0.0.1", "localhost", "::1") -or $uri.Port -ne $ExpectedPort) {
        throw "$Label must be the local HTTP endpoint on port $ExpectedPort`: $Endpoint"
    }
}

function Get-ComfyWorkerSnapshot([string]$Endpoint) {
    $port = ([Uri]$Endpoint).Port
    try {
        $stats = Invoke-RestMethod -Uri "$Endpoint/system_stats" -TimeoutSec 10
        $queue = Invoke-RestMethod -Uri "$Endpoint/queue" -TimeoutSec 10
        return [pscustomobject][ordered]@{
            endpoint = $Endpoint
            port = $port
            online = $true
            listener = $true
            gpu = [string]$stats.devices[0].name
            running = @($queue.queue_running).Count
            pending = @($queue.queue_pending).Count
        }
    }
    catch {
        return [pscustomobject][ordered]@{
            endpoint = $Endpoint
            port = $port
            online = $false
            listener = (Test-LocalTcpListener $port)
            gpu = "offline"
            running = 0
            pending = 0
            error = $_.Exception.Message
        }
    }
}

function Get-ForgeSnapshot {
    $port = ([Uri]$ForgeUrl).Port
    try {
        $progress = Invoke-RestMethod -Uri "$ForgeUrl/sdapi/v1/progress?skip_current_image=true" -TimeoutSec 10
        $job = [string]$progress.state.job
        $jobCount = if ($null -ne $progress.state.PSObject.Properties["job_count"]) { [int]$progress.state.job_count } else { 0 }
        return [pscustomobject][ordered]@{
            online = $true
            listener = $true
            active = ([double]$progress.progress -gt 0 -or $jobCount -gt 0 -or -not [string]::IsNullOrWhiteSpace($job))
            progress = [double]$progress.progress
            job_count = $jobCount
        }
    }
    catch {
        return [pscustomobject][ordered]@{
            online = $false
            listener = (Test-LocalTcpListener $port)
            active = $false
            progress = 0.0
            job_count = 0
            error = $_.Exception.Message
        }
    }
}

function Assert-GenerationServicesIdle([object[]]$Snapshots, [object]$Forge, [string]$Phase) {
    $target = @($Snapshots | Where-Object endpoint -eq $ComfyUrl)[0]
    if (-not $target.online -or $target.gpu -notmatch "RTX 3090") {
        throw "Target endpoint is not the RTX 3090 worker during $Phase`: $($target.gpu)"
    }
    if ($target.running -or $target.pending) {
        throw "RTX 3090 queue at $ComfyUrl is active during $Phase."
    }

    $shared = @($Snapshots | Where-Object endpoint -eq $SharedGpuComfyUrl)[0]
    if ($shared.online) {
        if ($shared.gpu -notmatch "RTX 3090") { throw "Shared endpoint is not an RTX 3090 worker during $Phase`: $($shared.gpu)" }
        if ($shared.running -or $shared.pending) { throw "Shared RTX 3090 queue is active during $Phase." }
    }
    elseif ($shared.listener) {
        throw "Shared RTX 3090 endpoint is listening but could not be verified during $Phase."
    }

    if ($Forge.online -and $Forge.active) { throw "Forge reports active RTX 3090 work during $Phase." }
    if (-not $Forge.online -and $Forge.listener) {
        throw "Forge is listening but its RTX 3090 activity could not be verified during $Phase."
    }
}

function Get-GpuHardwareSnapshots {
    $rows = @(& nvidia-smi --query-gpu=index,name,memory.used,memory.free,utilization.gpu,pstate --format=csv,noheader,nounits)
    if ($LASTEXITCODE -ne 0 -or $rows.Count -eq 0) { throw "Could not inspect GPU hardware state." }
    return @($rows | ForEach-Object {
        $parts = @($_ -split ",\s*", 6)
        if ($parts.Count -ne 6) { throw "Unexpected nvidia-smi row: $_" }
        [pscustomobject][ordered]@{
            index = [int]$parts[0]
            name = [string]$parts[1]
            memory_used_mib = [int]$parts[2]
            memory_free_mib = [int]$parts[3]
            utilization_percent = [int]$parts[4]
            pstate = [string]$parts[5]
        }
    })
}

function Assert-Hardware3090Idle([object[]]$Snapshots, [string]$Phase) {
    $gpu = @($Snapshots | Where-Object name -match "RTX 3090")
    if ($gpu.Count -ne 1) { throw "Expected exactly one RTX 3090 hardware row during $Phase." }
    if ($gpu[0].utilization_percent -gt $MaxIdle3090Utilization) {
        throw "RTX 3090 utilization is $($gpu[0].utilization_percent)% during $Phase; no work was queued."
    }
    if ($gpu[0].memory_used_mib -gt $MaxIdle3090MemoryMiB) {
        throw "RTX 3090 uses $($gpu[0].memory_used_mib) MiB during $Phase; no work was queued."
    }
}

function Assert-LiveManifestHash([string]$ExpectedHash, [string]$Phase) {
    $currentHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $presetManifestPath).Hash.ToUpperInvariant()
    if ($currentHash -cne $ExpectedHash) {
        throw "Local visual-preset manifest changed during $Phase."
    }
    $liveInfo = Invoke-RestMethod -Uri "$ComfyUrl/object_info/$nodeType" -TimeoutSec 30
    $liveHash = [string]$liveInfo.$nodeType.input.optional.scene_preset[1].manifest_sha256
    if ($liveHash -cne $ExpectedHash) {
        throw "Live Identity wrapper manifest hash differs from the local manifest during $Phase; restart the worker."
    }
}

Assert-LocalEndpoint $ComfyUrl 8188 "ComfyUrl"
Assert-LocalEndpoint $OtherComfyUrl 8189 "OtherComfyUrl"
Assert-LocalEndpoint $SharedGpuComfyUrl 8190 "SharedGpuComfyUrl"
Assert-LocalEndpoint $ForgeUrl 7860 "ForgeUrl"
if ($RunLabel -and $RunLabel -cnotmatch "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$") {
    throw "RunLabel must be one safe filename component using letters, digits, underscore, or hyphen."
}
if ($TimeoutSeconds -le 0) { throw "TimeoutSeconds must be greater than zero before any work is queued." }
if ($MaxIdle3090MemoryMiB -lt 1024 -or $MaxIdle3090Utilization -lt 0 -or $MaxIdle3090Utilization -gt 100) {
    throw "GPU idle thresholds are outside their supported range."
}
$candidateRoot = Join-Path $repoRoot "work\flux2-klein9b-visual-presets\candidates"
$resolvedCandidateRoot = [IO.Path]::GetFullPath($candidateRoot).TrimEnd("\", "/") + [IO.Path]::DirectorySeparatorChar
$resolvedRunRoot = [IO.Path]::GetFullPath($runRoot)
if (-not ($resolvedRunRoot + [IO.Path]::DirectorySeparatorChar).StartsWith($resolvedCandidateRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Candidate run directory escapes its approved root: $resolvedRunRoot"
}
if (Test-Path -LiteralPath $runRoot) {
    throw "Candidate run directory already exists; choose a unique RunLabel: $runRoot"
}

$sceneRequests = @(
    [ordered]@{ Key = "canyon-river-overlook"; SeedOffset = 100 },
    [ordered]@{ Key = "golden-shepherd-puppy"; SeedOffset = 200 },
    [ordered]@{ Key = "downtown-menswear"; SeedOffset = 300 }
)

if (-not (Test-Path -LiteralPath $presetManifestPath -PathType Leaf)) {
    throw "Missing canonical scene-preset manifest: $presetManifestPath"
}
$presetManifestHashBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $presetManifestPath).Hash.ToUpperInvariant()
$presetManifest = Get-Content -Raw -LiteralPath $presetManifestPath | ConvertFrom-Json
$presetManifestSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $presetManifestPath).Hash.ToUpperInvariant()
if ($presetManifestHashBefore -cne $presetManifestSha256) {
    throw "Canonical scene-preset manifest changed while it was being read."
}
$scenes = foreach ($request in $sceneRequests) {
    $record = @($presetManifest.identity | Where-Object key -eq $request.Key)
    if ($record.Count -ne 1) {
        throw "Expected exactly one identity preset with key $($request.Key); found $($record.Count)."
    }
    [ordered]@{
        Slug = [string]$record[0].key
        Preset = [string]$record[0].label
        Profile = [string]$record[0].profile
        SeedOffset = [int]$request.SeedOffset
    }
}

if ($SceneSlugs.Count) {
    $unknownSceneSlugs = @($SceneSlugs | Where-Object { $_ -notin @($scenes.Slug) })
    if ($unknownSceneSlugs.Count) {
        throw "Unknown scene slug(s): $($unknownSceneSlugs -join ', ')"
    }
    $scenes = @($scenes | Where-Object { $_.Slug -in $SceneSlugs })
}

if ($CandidatesPerScene -lt 1 -or $CandidatesPerScene -gt 4) {
    throw "CandidatesPerScene must be between 1 and 4."
}

$workers = [System.Collections.Generic.List[object]]::new()
foreach ($endpoint in @($ComfyUrl, $OtherComfyUrl, $SharedGpuComfyUrl)) {
    $workers.Add((Get-ComfyWorkerSnapshot $endpoint))
}

$targetWorker = @($workers | Where-Object endpoint -eq $ComfyUrl)[0]
$otherWorker = @($workers | Where-Object endpoint -eq $OtherComfyUrl)[0]
$sharedGpuWorker = @($workers | Where-Object endpoint -eq $SharedGpuComfyUrl)[0]
$gpuName = [string]$targetWorker.gpu
if (-not $otherWorker.online -or [string]$otherWorker.gpu -notmatch "RTX 4070") {
    throw "The second GPU could not be verified as the RTX 4070 worker: $($otherWorker.gpu)"
}
$forge = Get-ForgeSnapshot
Assert-GenerationServicesIdle @($workers) $forge "preflight"
$nvidiaSmi = Get-GpuHardwareSnapshots
Assert-Hardware3090Idle $nvidiaSmi "preflight"

$otherGpuName = [string]$otherWorker.gpu
$nodeInfoResponse = Invoke-RestMethod -Uri "$ComfyUrl/object_info/$nodeType" -TimeoutSec 30
$nodeInfo = $nodeInfoResponse.$nodeType
if (-not $nodeInfo) {
    throw "$nodeType is unavailable on the RTX 3090 worker."
}
Assert-LiveManifestHash $presetManifestSha256 "preflight"
$presetChoices = @($nodeInfo.input.optional.scene_preset[0])
$profileChoices = @($nodeInfo.input.required.reference_profile[0])
foreach ($scene in $scenes) {
    if ($presetChoices -notcontains $scene.Preset) {
        throw "Preset is not live on the RTX 3090 worker: $($scene.Preset)"
    }
    if ($profileChoices -notcontains $scene.Profile) {
        throw "Reference profile is not live on the RTX 3090 worker: $($scene.Profile)"
    }
}

if ($PreflightOnly) {
    [ordered]@{
        status = "preflight_passed"
        node = $nodeType
        manifest_sha256 = $presetManifestSha256
        workers = @($workers)
        forge = $forge
        hardware = $nvidiaSmi
        selected_scenes = @($scenes.Slug)
    } | ConvertTo-Json -Depth 20
    return
}

New-Item -ItemType Directory -Path $runRoot | Out-Null
$results = [System.Collections.Generic.List[object]]::new()

foreach ($scene in $scenes) {
    for ($candidateNumber = 1; $candidateNumber -le $CandidatesPerScene; $candidateNumber++) {
        $workersAtSubmit = @(
            Get-ComfyWorkerSnapshot $ComfyUrl
            Get-ComfyWorkerSnapshot $SharedGpuComfyUrl
        )
        $forgeAtSubmit = Get-ForgeSnapshot
        Assert-GenerationServicesIdle $workersAtSubmit $forgeAtSubmit "candidate submission"
        $hardwareAtSubmit = Get-GpuHardwareSnapshots
        Assert-Hardware3090Idle $hardwareAtSubmit "candidate submission"
        Assert-LiveManifestHash $presetManifestSha256 "candidate submission"
        $seed = [UInt64]($BaseSeed + [UInt64]$scene.SeedOffset + [UInt64]$candidateNumber)
        $workflow = [ordered]@{
            "1" = @{
                class_type = $nodeType
                inputs = [ordered]@{
                    reference_profile = $scene.Profile
                    scene_prompt = ""
                    appearance_polish = $true
                    fast_turbo = $FastTurbo
                    seed = $seed
                    scene_preset = $scene.Preset
                }
            }
        }
        $body = @{ prompt = $workflow; client_id = "klein9b-preset-preview-3090" } | ConvertTo-Json -Depth 30
        $queuedAt = Get-Date
        $queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 30
        if (-not $queued.prompt_id) {
            throw "ComfyUI rejected $($scene.Slug) candidate $candidateNumber`: $($queued | ConvertTo-Json -Depth 20)"
        }
        Write-Host "Queued $($scene.Slug) candidate $candidateNumber on RTX 3090: $($queued.prompt_id)"

        $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
        $entry = $null
        do {
            Start-Sleep -Seconds 3
            $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 20
            $entry = $history.PSObject.Properties[$queued.prompt_id].Value
            if ($entry -and $entry.status.status_str -eq "error") {
                throw "$($scene.Slug) candidate $candidateNumber failed: $($entry.status.messages | ConvertTo-Json -Depth 30)"
            }
        } while ((-not $entry -or -not $entry.status.completed) -and (Get-Date) -lt $deadline)
        if (-not $entry -or -not $entry.status.completed) {
            throw "Timed out generating $($scene.Slug) candidate $candidateNumber."
        }

        $image = @($entry.outputs."1".images)[0]
        if (-not $image) {
            throw "$($scene.Slug) candidate $candidateNumber completed without a saved image."
        }
        $relativeOutput = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
        $generatedPath = Join-Path (Join-Path $ComfyRoot "output") $relativeOutput
        if (-not (Test-Path -LiteralPath $generatedPath -PathType Leaf)) {
            throw "Generated file was not found: $generatedPath"
        }
        $candidatePath = Join-Path $runRoot ("{0}-candidate-{1}.png" -f $scene.Slug, $candidateNumber)
        $reportPath = Join-Path (Split-Path -Parent $generatedPath) "report.json"
        $report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
        if ([string]$report.visual_preset_shell.manifest_sha256 -cne $presetManifestSha256) {
            throw "Generated report manifest hash differs from the candidate manifest; refusing to copy a mislabeled result."
        }
        Copy-Item -LiteralPath $generatedPath -Destination $candidatePath
        $results.Add([pscustomobject][ordered]@{
            slug = $scene.Slug
            candidate = $candidateNumber
            preset = $scene.Preset
            reference_profile = $scene.Profile
            selected_output = $candidatePath
            comfy_output = $generatedPath
            report = $reportPath
            prompt_id = [string]$queued.prompt_id
            seed = $seed
            generation_seconds = [double]$report.seconds
            wall_seconds = [math]::Round(((Get-Date) - $queuedAt).TotalSeconds, 3)
            worker_snapshots_at_submit = $workersAtSubmit
            forge_at_submit = $forgeAtSubmit
            hardware_at_submit = $hardwareAtSubmit
        })
        Write-Host "Completed $($scene.Slug) candidate $candidateNumber in $($report.seconds)s: $candidatePath"
    }
}

$manifest = [ordered]@{
    schema_version = 1
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    purpose = "Candidate photographs for the unfinished Klein 9B visual preset cards."
    gpu = $gpuName
    other_worker = $otherGpuName
    worker_snapshots = @($workers)
    forge_snapshot_at_preflight = $forge
    nvidia_smi_at_preflight = $nvidiaSmi
    preset_manifest_sha256 = $presetManifestSha256
    comfy_url = $ComfyUrl
    workflow_node = $nodeType
    width = 832
    height = 1216
    fast_turbo = $FastTurbo
    appearance_polish = $true
    candidates = @($results)
}
$manifest | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $runManifestPath -Encoding utf8
Write-Host "Manifest: $runManifestPath"
