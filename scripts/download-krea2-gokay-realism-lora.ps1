[CmdletBinding()]
param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"

$hfPath = Join-Path $ComfyRoot ".venv\Scripts\hf.exe"
$destination = Join-Path $ComfyRoot "models\loras\krea2_realism_lora.safetensors"
$comfyDestination = Join-Path $ComfyRoot "models\loras\krea2_realism_lora_comfy.safetensors"
$repository = "gokaygokay/Krea-2-Realism-LoRA"
$filename = "krea2_realism_lora.safetensors"
$expectedSha256 = "6C38A7934C54A56E0F67753660A4500A094D6DCE28A0EE4A0D1DC9F4975D32D2"
$expectedComfySha256 = "C85612BAC3392C28A1B7D2FFDC74E23FEB3C783A596EC8839C67ED8A2D24237C"

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

if (-not (Test-Path -LiteralPath $comfyDestination -PathType Leaf)) {
    $pythonPath = Join-Path $ComfyRoot ".venv\Scripts\python.exe"
    $converterPath = Join-Path $PSScriptRoot "convert-krea2-fal-lora-for-comfy.py"
    & $pythonPath $converterPath $destination $comfyDestination
    if ($LASTEXITCODE -ne 0) {
        throw "Krea2 LoRA key conversion failed with exit code $LASTEXITCODE."
    }
}

$actualComfySha256 = (Get-FileHash -LiteralPath $comfyDestination -Algorithm SHA256).Hash
if ($actualComfySha256 -ne $expectedComfySha256) {
    throw "SHA256 mismatch for $comfyDestination. Expected $expectedComfySha256, got $actualComfySha256."
}

Write-Host "ComfyUI-compatible copy: $comfyDestination"
Write-Host "Converted SHA256: $actualComfySha256"
