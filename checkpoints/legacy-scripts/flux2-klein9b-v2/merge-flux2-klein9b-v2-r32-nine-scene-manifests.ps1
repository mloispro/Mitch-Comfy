[CmdletBinding()]
param(
    [string]$TargetedManifest = "work\flux2-klein9b-identity-v2-r32\nine-scenes\v2-step1200-s1.10-targeted\manifest.json",
    [string]$CompletionManifest = "work\flux2-klein9b-identity-v2-r32\nine-scenes\v2-step1200-s1.10-completion-scenes-3-8\manifest.json",
    [string]$OutputDirectory = "work\flux2-klein9b-identity-v2-r32\nine-scenes\v2-step1200-s1.10-complete-nine-rescore"
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

function Resolve-RepoPath([string]$Path) {
    if ([IO.Path]::IsPathRooted($Path)) { return $Path }
    return Join-Path $repoRoot $Path
}

$targetedPath = Resolve-RepoPath $TargetedManifest
$completionPath = Resolve-RepoPath $CompletionManifest
$outputRoot = Resolve-RepoPath $OutputDirectory
foreach ($path in @($targetedPath, $completionPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing source manifest: $path" }
}
if (Test-Path -LiteralPath $outputRoot) { throw "Refusing to overwrite existing output: $outputRoot" }

$targeted = Get-Content -Raw -LiteralPath $targetedPath | ConvertFrom-Json
$completion = Get-Content -Raw -LiteralPath $completionPath | ConvertFrom-Json
foreach ($field in @('model','text_encoder','vae','lora','lora_strength','trigger','source_scene_conditioning','reference_conditioning','identity_pass','face_swap','restoration')) {
    if ([string]$targeted.$field -cne [string]$completion.$field) {
        throw "Manifest invariant '$field' differs: '$($targeted.$field)' versus '$($completion.$field)'"
    }
}
$targetedSettings = $targeted.settings | ConvertTo-Json -Compress
$completionSettings = $completion.settings | ConvertTo-Json -Compress
if ($targetedSettings -cne $completionSettings) { throw 'Generation settings differ between source manifests.' }

$scenes = @($targeted.scenes) + @($completion.scenes) | Sort-Object { [int]$_.scene }
$sceneNumbers = @($scenes | ForEach-Object { [int]$_.scene })
if (($sceneNumbers -join ',') -cne '1,2,3,4,5,6,7,8,9') {
    throw "Merged manifests must contain scenes 1-9 exactly once; found $($sceneNumbers -join ',')."
}
foreach ($scene in $scenes) {
    $selectedPath = [string]$scene.selected_output
    if (-not (Test-Path -LiteralPath $selectedPath -PathType Leaf)) { throw "Missing selected output: $selectedPath" }
    $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $selectedPath).Hash.ToUpperInvariant()
    if ($scene.PSObject.Properties.Name -contains 'selected_output_sha256' -and [string]$scene.selected_output_sha256) {
        if ([string]$scene.selected_output_sha256 -cne $actualHash) { throw "Selected output hash mismatch: $selectedPath" }
    } else {
        $scene | Add-Member -NotePropertyName selected_output_sha256 -NotePropertyValue $actualHash
    }
}

$targetedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $targetedPath).Hash.ToUpperInvariant()
$completionHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $completionPath).Hash.ToUpperInvariant()
$record = [ordered]@{}
foreach ($property in $completion.PSObject.Properties) { $record[$property.Name] = $property.Value }
$record.created_utc = (Get-Date).ToUniversalTime().ToString('o')
$record.method = 'FLUX.2 Klein Base 9B LoRA-only text-to-image; merged preserved evaluation outputs; source scenes shown only for comparison'
$record.prompt_variant = 'Scenes 1-2 use the earlier targeted wording, scenes 3-8 use the locked default wording, and scene 9 uses the earlier identity-first wording. This is a practical adapter review, not a single-prompt-variable experiment.'
$record.scenes = $scenes
$record['combined_manifest_sources'] = @(
    [ordered]@{ path = $targetedPath; sha256 = $targetedHash; scenes = @(1,2,9) },
    [ordered]@{ path = $completionPath; sha256 = $completionHash; scenes = @(3,4,5,6,7,8) }
)
$record['evaluation_scene_numbers'] = 1..9
$record['published'] = $false

New-Item -ItemType Directory -Path $outputRoot | Out-Null
$manifestPath = Join-Path $outputRoot 'manifest.json'
$record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $manifestPath -Encoding utf8
$manifestPath
