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

Ensure-Download `
    -Url "https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4b-fp8/resolve/main/flux-2-klein-base-4b-fp8.safetensors" `
    -Destination (Join-Path $ComfyRoot "models\diffusion_models\flux-2-klein-base-4b-fp8.safetensors") `
    -Sha256 "44BAB3A86FE98B85D21DD2A4729EBDC3AE51FB8A39F76E457E18C724219E6840"

Ensure-Download `
    -Url "https://huggingface.co/Comfy-Org/z_image/resolve/main/split_files/text_encoders/qwen_3_4b_fp8_mixed.safetensors" `
    -Destination (Join-Path $ComfyRoot "models\text_encoders\qwen_3_4b_fp8_mixed.safetensors") `
    -Sha256 "72450B19758172C5A7273CF7DE729D1C17E7F434A104A00167624CBA94F68F15"

Ensure-Download `
    -Url "https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors" `
    -Destination (Join-Path $ComfyRoot "models\vae\flux2-vae.safetensors") `
    -Sha256 "D64F3A68E1CC4F9F4E29B6E0DA38A0204FE9A49F2D4053F0EC1FA1CA02F9C4B5"

$loraPath = Join-Path $ComfyRoot "models\loras\aitk\m1tch-flux2-klein-4b-identity-v1-best.safetensors"
if (-not (Test-Path -LiteralPath $loraPath)) {
    throw "Missing the private trained identity LoRA: $loraPath. Restore it from backup or rerun the documented local training job."
}
$loraHash = (Get-FileHash -LiteralPath $loraPath -Algorithm SHA256).Hash
if ($loraHash -ne "8A7D1477914D0A5262BF219F71F303418130449841CF220226B4E979D7232F87") {
    throw "The private production identity LoRA has an unexpected SHA256: $loraPath"
}

Write-Host "FLUX.2 One Reference Photo dependencies are installed and verified. Restart ComfyUI before generating."
