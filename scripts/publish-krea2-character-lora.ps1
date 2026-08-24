[CmdletBinding()]
param(
    [string]$InlineStudioUrl = "http://127.0.0.1:8848",
    [string]$InlineStudioRoot = "C:\projects\AI-Tools\Inline-Studio",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [string]$RunId = "36d539e7-e05d-48ed-a74e-ddb1db3ab684",
    [string]$ExpectedTrigger = "m1tch_person",
    [int]$ExpectedDatasetItems = 22
)

$ErrorActionPreference = "Stop"

function Invoke-InlineStudioRpc {
    param(
        [Parameter(Mandatory)][string]$Channel,
        [Parameter(Mandatory)][object[]]$Arguments
    )

    $body = @{ channel = $Channel; args = $Arguments } | ConvertTo-Json -Depth 10
    $response = Invoke-RestMethod `
        -Uri "$($InlineStudioUrl.TrimEnd('/'))/rpc" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body `
        -TimeoutSec 15
    if (-not $response.ok) {
        throw "Inline Studio RPC '$Channel' failed: $($response.error)"
    }
    return $response.value
}

function Get-SafetensorsTensorCount {
    param([Parameter(Mandatory)][string]$Path)

    $stream = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        $reader = [IO.BinaryReader]::new($stream, [Text.Encoding]::UTF8, $true)
        $headerLength = $reader.ReadInt64()
        if ($headerLength -lt 2 -or $headerLength -gt 134217728) {
            throw "Invalid safetensors header length $headerLength in $Path"
        }
        $headerBytes = $reader.ReadBytes([int]$headerLength)
        if ($headerBytes.Length -ne $headerLength) {
            throw "Truncated safetensors header in $Path"
        }
        $header = [Text.Encoding]::UTF8.GetString($headerBytes) | ConvertFrom-Json -AsHashtable
        return @($header.Keys | Where-Object { $_ -ne "__metadata__" }).Count
    }
    finally {
        $stream.Dispose()
    }
}

$run = Invoke-InlineStudioRpc -Channel "training:status" -Arguments @($RunId)
if ($run.status -ne "done") {
    throw "Training run $RunId is '$($run.status)' at step $($run.step)/$($run.totalSteps). Nothing was copied."
}
if ($run.step -ne $run.totalSteps -or $run.totalSteps -ne 500) {
    throw "Completed run has unexpected progress $($run.step)/$($run.totalSteps); expected 500/500."
}
if ($run.hyperparams.arch -ne "krea2") {
    throw "Refusing run architecture '$($run.hyperparams.arch)'; expected 'krea2'."
}
if ($run.hyperparams.baseMode -ne "turbo_adapter") {
    throw "Refusing Krea2 base mode '$($run.hyperparams.baseMode)'; expected 'turbo_adapter'."
}
if (-not $run.outputLoraPath) {
    throw "Completed run has no outputLoraPath."
}

$items = @(Invoke-InlineStudioRpc -Channel "training:listItems" -Arguments @([string]$run.datasetId))
if ($items.Count -ne $ExpectedDatasetItems) {
    throw "Dataset contains $($items.Count) items; expected $ExpectedDatasetItems."
}
$badCaptions = @($items | Where-Object { [string]$_.caption -notmatch "^$([regex]::Escape($ExpectedTrigger))(?=,|\s|$)" })
if ($badCaptions.Count -gt 0) {
    throw "$($badCaptions.Count) dataset caption(s) do not begin with trigger '$ExpectedTrigger'."
}

$relativeOutput = ([string]$run.outputLoraPath).Replace("/", "\")
$candidatePaths = [System.Collections.Generic.List[string]]::new()
if ([IO.Path]::IsPathRooted($relativeOutput)) {
    $candidatePaths.Add($relativeOutput)
}
else {
    $candidatePaths.Add((Join-Path $ComfyRoot "models\$relativeOutput"))
    $candidatePaths.Add((Join-Path $InlineStudioRoot "core\models\loras\$relativeOutput"))
    $candidatePaths.Add((Join-Path $InlineStudioRoot "core\models\$relativeOutput"))
    $candidatePaths.Add((Join-Path $InlineStudioRoot $relativeOutput))
}
$sourceMatches = @($candidatePaths | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -Unique)
if ($sourceMatches.Count -ne 1) {
    throw "Could not resolve exactly one output LoRA from '$($run.outputLoraPath)'. Checked: $($candidatePaths -join '; ')"
}
$sourcePath = [IO.Path]::GetFullPath($sourceMatches[0])

$tensorCount = Get-SafetensorsTensorCount -Path $sourcePath
if ($tensorCount -lt 16) {
    throw "The output has only $tensorCount tensor entries and does not look like a usable LoRA: $sourcePath"
}

$loraRoot = [IO.Path]::GetFullPath((Join-Path $ComfyRoot "models\loras"))
$destinationDirectory = Join-Path $loraRoot "aitk"
$destinationPath = [IO.Path]::GetFullPath((Join-Path $destinationDirectory "mitch-krea2-identity-v1.safetensors"))
$requiredPrefix = $loraRoot.TrimEnd('\') + '\'
if (-not $destinationPath.StartsWith($requiredPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Resolved destination escaped the ComfyUI LoRA root: $destinationPath"
}

$sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
if (Test-Path -LiteralPath $destinationPath -PathType Leaf) {
    $destinationHash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash
    if ($destinationHash -eq $sourceHash) {
        Write-Host "Canonical Mitch Krea2 LoRA is already published and identical: $destinationPath"
        Write-Host "SHA256: $sourceHash | tensors: $tensorCount"
        exit 0
    }
    throw "A different file already exists at $destinationPath. It was not overwritten."
}

New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
$temporaryPath = Join-Path $destinationDirectory ".mitch-krea2-identity-v1.$PID.partial"
try {
    Copy-Item -LiteralPath $sourcePath -Destination $temporaryPath
    $temporaryHash = (Get-FileHash -LiteralPath $temporaryPath -Algorithm SHA256).Hash
    if ($temporaryHash -ne $sourceHash) {
        throw "Copied LoRA hash mismatch. Source $sourceHash, copy $temporaryHash."
    }
    Move-Item -LiteralPath $temporaryPath -Destination $destinationPath
}
finally {
    if (Test-Path -LiteralPath $temporaryPath) {
        Remove-Item -LiteralPath $temporaryPath -Force
    }
}

Write-Host "Published verified Mitch Krea2 LoRA: $destinationPath"
Write-Host "Run: $RunId | dataset: $($run.datasetId) | items: $($items.Count) | trigger: $ExpectedTrigger"
Write-Host "SHA256: $sourceHash | tensors: $tensorCount"
