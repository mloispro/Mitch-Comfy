param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Ensure-Junction {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Target
    )

    $resolvedTarget = (Resolve-Path -LiteralPath $Target).Path
    if (Test-Path -LiteralPath $Path) {
        $item = Get-Item -LiteralPath $Path -Force
        $existingTarget = @($item.Target)[0]
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -and $existingTarget) {
            $resolvedExisting = (Resolve-Path -LiteralPath $existingTarget).Path
            if ($resolvedExisting -eq $resolvedTarget) {
                Write-Host "OK: $Path -> $resolvedTarget"
                return
            }
        }
        throw "Refusing to replace existing non-matching path: $Path"
    }

    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    New-Item -ItemType Junction -Path $Path -Target $resolvedTarget | Out-Null
    Write-Host "Linked: $Path -> $resolvedTarget"
}

Ensure-Junction -Path (Join-Path $ComfyRoot "user\default\workflows\Mitch") -Target (Join-Path $RepoRoot "workflows")
Ensure-Junction -Path (Join-Path $ComfyRoot "custom_nodes\ComfyUI-AIToolkit-Training") -Target (Join-Path $RepoRoot "custom_nodes\ComfyUI-AIToolkit-Training")
Ensure-Junction -Path (Join-Path $ComfyRoot "custom_nodes\ComfyUI-AlwaysRunImage") -Target (Join-Path $RepoRoot "custom_nodes\ComfyUI-AlwaysRunImage")

$inputAssetSource = Join-Path $RepoRoot "assets\comfy-input"
$inputAssetTarget = Join-Path $ComfyRoot "input"
foreach ($asset in Get-ChildItem -LiteralPath $inputAssetSource -File -Recurse) {
    $liveName = "mitch-workbench-$($asset.Name)"
    Copy-Item -LiteralPath $asset.FullName -Destination (Join-Path $inputAssetTarget $liveName) -Force
    Write-Host "Synced input asset: $liveName"
}

Write-Host "Links are ready. Restart ComfyUI after custom-node changes."
