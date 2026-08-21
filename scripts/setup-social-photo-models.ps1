param(
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"

function Ensure-Download {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Destination,
        [Parameter(Mandatory = $true)][string]$Sha256
    )

    $destinationPath = [IO.Path]::GetFullPath($Destination)
    $expectedRoot = [IO.Path]::GetFullPath((Join-Path $ComfyRoot "models"))
    if (-not $destinationPath.StartsWith($expectedRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to write a model outside $expectedRoot"
    }
    $parent = Split-Path -Parent $destinationPath
    New-Item -ItemType Directory -Path $parent -Force | Out-Null

    if (Test-Path -LiteralPath $destinationPath) {
        $existingHash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash
        if ($existingHash -eq $Sha256) {
            Write-Host "OK: $destinationPath"
            return
        }
        throw "Existing model has the wrong SHA256 and was not replaced: $destinationPath"
    }

    $partialPath = "$destinationPath.partial"
    Write-Host "Downloading $Url"
    & curl.exe --location --fail --retry 5 --continue-at - --output $partialPath $Url
    if ($LASTEXITCODE -ne 0) {
        throw "Download failed with curl exit code $LASTEXITCODE"
    }
    $downloadedHash = (Get-FileHash -LiteralPath $partialPath -Algorithm SHA256).Hash
    if ($downloadedHash -ne $Sha256) {
        throw "Downloaded model failed SHA256 verification: $partialPath"
    }
    Move-Item -LiteralPath $partialPath -Destination $destinationPath
    Write-Host "Installed: $destinationPath"
}

$diffusionUrl = "https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-kv-fp8/resolve/main/flux-2-klein-9b-kv-fp8.safetensors"
$textEncoderUrl = "https://huggingface.co/Comfy-Org/flux2-klein-9B/resolve/main/split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors"
$vaeUrl = "https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors"

Ensure-Download `
    -Url $diffusionUrl `
    -Destination (Join-Path $ComfyRoot "models\diffusion_models\flux-2-klein-9b-kv-fp8.safetensors") `
    -Sha256 "33F7DA5625A00798349A719742999D3C7DD20C1A7EDA14663922C363640728F1"

Ensure-Download `
    -Url $textEncoderUrl `
    -Destination (Join-Path $ComfyRoot "models\text_encoders\qwen_3_8b_fp8mixed.safetensors") `
    -Sha256 "ABAD16806E0CBABC54E0325D6565847443FE396D5F0BE38BB3CD3FE75A1201D6"

Ensure-Download `
    -Url $vaeUrl `
    -Destination (Join-Path $ComfyRoot "models\vae\flux2-vae.safetensors") `
    -Sha256 "D64F3A68E1CC4F9F4E29B6E0DA38A0204FE9A49F2D4053F0EC1FA1CA02F9C4B5"

Write-Host "FLUX.2 Klein 9B KV Social Photo Studio models are installed and verified. Restart ComfyUI before generating."
