[CmdletBinding()]
param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [string]$OtherComfyUrl = "http://127.0.0.1:8189",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string[]]$SceneSlugs = @(),
    [int]$CandidatesPerScene = 2,
    [bool]$FastTurbo = $true,
    [UInt64]$BaseSeed = 8676200,
    [int]$TimeoutSeconds = 1200,
    [string]$RunLabel = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runStamp = if ($RunLabel) { $RunLabel } else { Get-Date -Format "yyyyMMdd-HHmmss" }
$runRoot = Join-Path $repoRoot "work\flux2-klein9b-visual-presets\candidates\$runStamp"
$runManifestPath = Join-Path $runRoot "manifest.json"
$presetManifestPath = Join-Path $repoRoot "custom_nodes\ComfyUI-AIToolkit-Training\web\assets\scene-presets\manifest.json"
$nodeType = "Flux2Klein9BMitchIdentityStudioVisualPresetsV11"

$sceneRequests = @(
    [ordered]@{ Key = "canyon-river-overlook"; SeedOffset = 100 },
    [ordered]@{ Key = "golden-shepherd-puppy"; SeedOffset = 200 },
    [ordered]@{ Key = "downtown-menswear"; SeedOffset = 300 }
)

if (-not (Test-Path -LiteralPath $presetManifestPath -PathType Leaf)) {
    throw "Missing canonical scene-preset manifest: $presetManifestPath"
}
$presetManifest = Get-Content -Raw -LiteralPath $presetManifestPath | ConvertFrom-Json
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

foreach ($endpoint in @($ComfyUrl, $OtherComfyUrl)) {
    $queue = Invoke-RestMethod -Uri "$endpoint/queue" -TimeoutSec 10
    if (@($queue.queue_running).Count -or @($queue.queue_pending).Count) {
        throw "ComfyUI queue at $endpoint is not idle. No work was queued."
    }
}

$stats = Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 10
$gpuName = [string]$stats.devices[0].name
if ($gpuName -notmatch "RTX 3090") {
    throw "Port 8188 is not the RTX 3090 worker: $gpuName"
}

$otherStats = Invoke-RestMethod -Uri "$OtherComfyUrl/system_stats" -TimeoutSec 10
$otherGpuName = [string]$otherStats.devices[0].name
$nodeInfoResponse = Invoke-RestMethod -Uri "$ComfyUrl/object_info/$nodeType" -TimeoutSec 30
$nodeInfo = $nodeInfoResponse.$nodeType
if (-not $nodeInfo) {
    throw "$nodeType is unavailable on the RTX 3090 worker."
}
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

New-Item -ItemType Directory -Path $runRoot -Force | Out-Null
$results = [System.Collections.Generic.List[object]]::new()

foreach ($scene in $scenes) {
    for ($candidateNumber = 1; $candidateNumber -le $CandidatesPerScene; $candidateNumber++) {
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
        Copy-Item -LiteralPath $generatedPath -Destination $candidatePath

        $reportPath = Join-Path (Split-Path -Parent $generatedPath) "report.json"
        $report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
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
