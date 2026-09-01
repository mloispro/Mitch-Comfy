[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceImage,
    [string]$FilenamePrefix = "crowd-proof/identity-anchor-statefair/final-phone-finish",
    [int]$Port = 8188,
    [string]$ExpectedGpuName = "NVIDIA GeForce RTX 3090",
    [int]$TimeoutSeconds = 300
)

$ErrorActionPreference = "Stop"
$baseUrl = "http://127.0.0.1:$Port"
$resolvedSource = [System.IO.Path]::GetFullPath($SourceImage)
if (-not (Test-Path -LiteralPath $resolvedSource -PathType Leaf)) {
    throw "Source image does not exist: $resolvedSource"
}

$stats = Invoke-RestMethod -Uri "$baseUrl/system_stats" -TimeoutSec 10
$deviceName = [string](@($stats.devices)[0].name)
if ($deviceName -notlike "*$ExpectedGpuName*") {
    throw "Port $Port is serving '$deviceName', not '$ExpectedGpuName'."
}
$queue = Invoke-RestMethod -Uri "$baseUrl/queue" -TimeoutSec 10
if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
    throw "Port $Port already has queued work. Nothing was submitted."
}
$objectInfo = Invoke-RestMethod -Uri "$baseUrl/object_info" -TimeoutSec 45
foreach ($nodeName in @("Image Load", "WholeFramePhoneFinish", "SaveImage")) {
    if (-not $objectInfo.PSObject.Properties[$nodeName]) {
        throw "Required node is unavailable: $nodeName"
    }
}

$workflow = @{
    "1" = @{
        class_type = "Image Load"
        inputs = @{
            image_path = $resolvedSource
            RGBA = "false"
        }
    }
    "2" = @{
        class_type = "WholeFramePhoneFinish"
        inputs = @{ image = @("1", 0) }
    }
    "3" = @{
        class_type = "SaveImage"
        inputs = @{
            images = @("2", 0)
            filename_prefix = $FilenamePrefix
        }
    }
}
$clientId = "whole-frame-phone-finish-$(New-Guid)"
$body = @{
    prompt = $workflow
    client_id = $clientId
} | ConvertTo-Json -Depth 16
$queued = Invoke-RestMethod -Method Post -Uri "$baseUrl/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt id."
}

$started = Get-Date
$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
while ([DateTime]::UtcNow -lt $deadline) {
    Start-Sleep -Seconds 1
    $history = Invoke-RestMethod -Uri "$baseUrl/history/$($queued.prompt_id)" -TimeoutSec 20
    $record = $history.PSObject.Properties[[string]$queued.prompt_id].Value
    if (-not $record) {
        continue
    }
    if ($record.status.status_str -eq "error") {
        throw "Whole-frame phone finish failed: $($record.status.messages | ConvertTo-Json -Depth 20 -Compress)"
    }
    if ($record.status.completed -or $record.status.status_str -eq "success") {
        $images = @()
        foreach ($output in $record.outputs.PSObject.Properties.Value) {
            foreach ($image in @($output.images)) {
                if ($image.filename) {
                    $relative = if ($image.subfolder) {
                        Join-Path $image.subfolder $image.filename
                    }
                    else {
                        $image.filename
                    }
                    $outputRoot = if ($Port -eq 8189) {
                        "C:\projects\AI-Tools\ComfyUI\output\gpu-4070"
                    }
                    else {
                        "C:\projects\AI-Tools\ComfyUI\output"
                    }
                    $images += Join-Path $outputRoot $relative
                }
            }
        }
        [ordered]@{
            prompt_id = [string]$queued.prompt_id
            source_image = $resolvedSource
            gpu = $ExpectedGpuName
            finish = "fixed whole-frame phone response"
            generative = $false
            masked = $false
            selective_face_processing = $false
            elapsed_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
            images = $images
        } | ConvertTo-Json -Depth 8
        exit 0
    }
}

throw "Timed out waiting for whole-frame phone finish $($queued.prompt_id)."
