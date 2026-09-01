[CmdletBinding()]
param(
    [string]$SceneSlug = "state-fair",
    [string]$Prompt = "",
    [uint64]$Seed = 9472363,
    [int]$Port = 8188,
    [string]$ExpectedGpuName = "",
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$promptConfigPath = Join-Path $repoRoot "config\crowd-route-v1-prompts.json"
$anchorName = "mitch-identity-anchor-walking-v1.png"
$anchorPath = "C:\projects\AI-Tools\ComfyUI\input\$anchorName"

if (-not (Test-Path -LiteralPath $anchorPath -PathType Leaf)) {
    throw "The frozen identity anchor is missing: $anchorPath"
}
if ([string]::IsNullOrWhiteSpace($Prompt)) {
    $promptConfig = Get-Content -LiteralPath $promptConfigPath -Raw | ConvertFrom-Json
    $sceneProperty = $promptConfig.scene_prompts.PSObject.Properties[$SceneSlug]
    if (-not $sceneProperty) {
        throw "No frozen prompt exists for scene '$SceneSlug'. Pass -Prompt explicitly."
    }
    $Prompt = [string]$sceneProperty.Value
}
if ([string]::IsNullOrWhiteSpace($ExpectedGpuName)) {
    $ExpectedGpuName = switch ($Port) {
        8188 { "NVIDIA GeForce RTX 3090" }
        8189 { "NVIDIA GeForce RTX 4070" }
        default { throw "Pass -ExpectedGpuName when using ComfyUI port $Port." }
    }
}

$runner = Join-Path $PSScriptRoot "smoke-krea2-identity-edit.ps1"
$run = @{
    Reference = $anchorName
    Prompt = $Prompt
    Seed = $Seed
    Width = 832
    Height = 1248
    Steps = 12
    RefBoost = 6.0
    SmartphoneLoraStrength = 0.35
    GroundingPixels = 768
    FaceAttentionMask = $true
    ApplyPhoneFinish = $true
    OutputPrefix = "crowd-route-v1/$SceneSlug/seed-$Seed"
    Port = $Port
    ExpectedGpuName = $ExpectedGpuName
    TimeoutSeconds = $TimeoutSeconds
}
& $runner @run
