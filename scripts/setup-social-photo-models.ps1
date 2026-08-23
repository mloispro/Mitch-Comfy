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

$diffusionUrl = "https://huggingface.co/Comfy-Org/z_image/resolve/main/split_files/diffusion_models/z_image_bf16.safetensors"
$textEncoderUrl = "https://huggingface.co/Comfy-Org/z_image/resolve/main/split_files/text_encoders/qwen_3_4b_fp8_mixed.safetensors"
$vaeUrl = "https://huggingface.co/Comfy-Org/z_image/resolve/main/split_files/vae/ae.safetensors"
$detectorUrl = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n.pt"
$segmenterUrl = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx"

Ensure-Download `
    -Url $diffusionUrl `
    -Destination (Join-Path $ComfyRoot "models\diffusion_models\z_image_bf16.safetensors") `
    -Sha256 "996A67D3FF666946B1C25CBC16D1B1918B6CC0AC166309E23FE3B3D830263DEE"

Ensure-Download `
    -Url $textEncoderUrl `
    -Destination (Join-Path $ComfyRoot "models\text_encoders\qwen_3_4b_fp8_mixed.safetensors") `
    -Sha256 "72450B19758172C5A7273CF7DE729D1C17E7F434A104A00167624CBA94F68F15"

Ensure-Download `
    -Url $vaeUrl `
    -Destination (Join-Path $ComfyRoot "models\vae\ae.safetensors") `
    -Sha256 "AFC8E28272CD15DB3919BACDB6918CE9C1ED22E96CB12C4D5ED0FBA823529E38"

Ensure-Download `
    -Url $detectorUrl `
    -Destination (Join-Path $ComfyRoot "models\ultralytics\bbox\yolo11n.pt") `
    -Sha256 "0EBBC80D4A7680D14987A577CD21342B65ECFD94632BD9A8DA63AE6417644EE1"

Ensure-Download `
    -Url $segmenterUrl `
    -Destination (Join-Path $ComfyRoot "models\rembg\u2net_human_seg.onnx") `
    -Sha256 "01EB6A29A5C4D8EDB30B56ADAD9BB3A2A0535338E480724A213E0ACFD2D1C73C"

$comfyPython = Join-Path $ComfyRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $comfyPython)) {
    throw "Missing ComfyUI Python runtime: $comfyPython"
}
& $comfyPython -c "import importlib.metadata as m; assert m.version('ultralytics') == '8.4.76'; assert m.version('rembg') == '2.0.69'"
if ($LASTEXITCODE -ne 0) {
    throw "ComfyUI requires ultralytics 8.4.76 and rembg 2.0.69 for v1.0.4 complex routing."
}

Write-Host "Z-Image scene, object-count, and main-subject isolation models are installed and verified. Restart ComfyUI before generating."
