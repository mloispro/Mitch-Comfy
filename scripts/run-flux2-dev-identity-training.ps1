param(
    [string]$ConfigPath = "C:\projects\AI-Tools\Mitch-Comfy\config\flux2-dev-identity-v1.yaml",
    [string]$LogPath = "C:\projects\AI-Tools\Mitch-Comfy\work\flux2-dev-identity-v1\training.log"
)

$ErrorActionPreference = "Stop"
$toolkitRoot = "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit"
$python = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$runPy = Join-Path $toolkitRoot "run.py"
$flux2Loader = Join-Path $toolkitRoot "extensions_built_in\diffusion_models\flux2\flux2_model.py"
$memoryManager = Join-Path $toolkitRoot "toolkit\memory_management\manager_modules.py"

foreach ($path in @($ConfigPath, $python, $runPy, $flux2Loader, $memoryManager)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required local file is missing: $path"
    }
}
if (-not (Select-String -LiteralPath $flux2Loader -Quiet -SimpleMatch 'Keep the 24B encoder on CPU until it has been quantized')) {
    throw "The required FLUX.2 Dev Mistral load-order patch is not installed. See patches\ai-toolkit-flux2-dev-win64gb.patch."
}
if (-not (Select-String -LiteralPath $memoryManager -Quiet -SimpleMatch 'AI_TOOLKIT_PIN_QUANTIZED_OFFLOAD')) {
    throw "The required quantized-offload memory compatibility patch is not installed. See patches\ai-toolkit-flux2-dev-win64gb.patch."
}

$queue = Invoke-RestMethod -Uri "http://127.0.0.1:8189/queue" -TimeoutSec 10
if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
    throw "The RTX 4070 worker queue is active; refusing to start training without a clean state record."
}

$logDirectory = Split-Path -Parent $LogPath
if (-not (Test-Path -LiteralPath $logDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}

$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:PYTHONUNBUFFERED = "1"
$env:CUDA_VISIBLE_DEVICES = "0"
$env:AI_TOOLKIT_PIN_QUANTIZED_OFFLOAD = "0"

Push-Location $toolkitRoot
try {
    & $python $runPy $ConfigPath -l $LogPath
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
