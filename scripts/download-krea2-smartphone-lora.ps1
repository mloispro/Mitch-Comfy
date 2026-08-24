[CmdletBinding()]
param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"

$hfPath = Join-Path $ComfyRoot ".venv\Scripts\hf.exe"
$destination = Join-Path $ComfyRoot "models\loras\krea-smartphone-photo-slider.safetensors"
$repository = "reverentelusarca/elusarcas-krea2-smartphone-photography-lora"
$filename = "krea-smartphone-photo-slider.safetensors"
$expectedSha256 = "6468A57747EE8953036AEDC28EBA2034AD6355789151F4F85EF63260ED3FA2CE"

if (-not (Test-Path -LiteralPath $hfPath -PathType Leaf)) {
    throw "Hugging Face CLI was not found: $hfPath"
}

if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) {
    $downloadRoot = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null
    & $hfPath download $repository $filename --local-dir $downloadRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Hugging Face download failed with exit code $LASTEXITCODE."
    }
}

$actualSha256 = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
if ($actualSha256 -ne $expectedSha256) {
    throw "SHA256 mismatch for $destination. Expected $expectedSha256, got $actualSha256."
}

Write-Host "Verified: $destination"
Write-Host "SHA256: $actualSha256"
