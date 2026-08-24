[CmdletBinding()]
param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"

$hfPath = Join-Path $ComfyRoot ".venv\Scripts\hf.exe"
$modelRoot = Join-Path $ComfyRoot "models"
$repository = "Comfy-Org/Krea-2"
$files = @(
    [pscustomobject]@{
        RelativePath = "diffusion_models/krea2_turbo_fp8_scaled.safetensors"
        Sha256 = "EB4DD8C612CFD10F64F25B057E6E6BBCB5737C94A7372177E456DBF7579502F1"
    },
    [pscustomobject]@{
        RelativePath = "text_encoders/qwen3vl_4b_fp8_scaled.safetensors"
        Sha256 = "54BD5144DF0BBC25DD6CCADFCB826B521445A1B06AE5A42570BDD2974CA87094"
    },
    [pscustomobject]@{
        RelativePath = "vae/qwen_image_vae.safetensors"
        Sha256 = "A70580F0213E67967EE9C95F05BB400E8FB08307E017A924BF3441223E023D1F"
    }
)

if (-not (Test-Path -LiteralPath $hfPath -PathType Leaf)) {
    throw "Hugging Face CLI was not found: $hfPath"
}

$missing = [System.Collections.Generic.List[string]]::new()
foreach ($file in $files) {
    $localPath = Join-Path $modelRoot ($file.RelativePath.Replace("/", "\"))
    if (-not (Test-Path -LiteralPath $localPath -PathType Leaf)) {
        $missing.Add($file.RelativePath)
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Downloading $($missing.Count) missing official Krea2 file(s) from $repository ..."
    $previousDisableXet = $env:HF_HUB_DISABLE_XET
    try {
        $env:HF_HUB_DISABLE_XET = "1"
        & $hfPath download $repository @($missing) --local-dir $modelRoot
        if ($LASTEXITCODE -ne 0) {
            throw "Hugging Face download failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        if ($null -eq $previousDisableXet) {
            Remove-Item Env:HF_HUB_DISABLE_XET -ErrorAction SilentlyContinue
        }
        else {
            $env:HF_HUB_DISABLE_XET = $previousDisableXet
        }
    }
}
else {
    Write-Host "All required Krea2 files are already present."
}

foreach ($file in $files) {
    $localPath = Join-Path $modelRoot ($file.RelativePath.Replace("/", "\"))
    if (-not (Test-Path -LiteralPath $localPath -PathType Leaf)) {
        throw "Required model is still missing: $localPath"
    }
    $actualHash = (Get-FileHash -LiteralPath $localPath -Algorithm SHA256).Hash
    if ($actualHash -ne $file.Sha256) {
        throw "SHA256 mismatch for $localPath. Expected $($file.Sha256), got $actualHash."
    }
    Write-Host "Verified $($file.RelativePath) [$actualHash]"
}

Write-Host "Krea2 model download and integrity verification complete. No workflow was run."
