[CmdletBinding()]
param(
    [ValidateSet(20, 50)]
    [int]$Steps = 20,
    [UInt64]$Seed = 9472363,
    [string]$Server = "http://127.0.0.1:8188",
    [string]$ReferenceImage = "mitch-identity-anchor-walking-v1.png",
    [string]$OutputPrefix = "flux2-native-reference-krea-comparison/state-fair-base4b",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$promptConfigPath = Join-Path $repoRoot "config\crowd-route-v1-prompts.json"
$promptConfig = Get-Content -LiteralPath $promptConfigPath -Raw | ConvertFrom-Json
$scenePrompt = [string]$promptConfig.scene_prompts.'state-fair'

$queue = Invoke-RestMethod -Uri "$Server/queue"
if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
    throw "ComfyUI queue is not idle at $Server. Refusing to disturb active GPU work."
}

$requiredNodes = @(
    "UNETLoader", "CLIPLoader", "VAELoader", "LoadImage",
    "ImageScaleToTotalPixels", "GetImageSize", "VAEEncode", "ReferenceLatent",
    "CLIPTextEncode", "CFGGuider", "KSamplerSelect", "Flux2Scheduler",
    "RandomNoise", "EmptyFlux2LatentImage", "SamplerCustomAdvanced",
    "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$nodeName"
    if (-not $nodeInfo.PSObject.Properties[$nodeName]) {
        throw "Required node is unavailable: $nodeName"
    }
}

$suffix = "${Steps}step-cfg5-seed${Seed}"
$prompt = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = "flux-2-klein-base-4b-fp8.safetensors"; weight_dtype = "default" } }
    "2" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = "qwen_3_4b_fp8_mixed.safetensors"; type = "flux2"; device = "default" } }
    "3" = @{ class_type = "VAELoader"; inputs = @{ vae_name = "flux2-vae.safetensors" } }
    "4" = @{ class_type = "LoadImage"; inputs = @{ image = $ReferenceImage } }
    "5" = @{ class_type = "ImageScaleToTotalPixels"; inputs = @{ image = @("4", 0); upscale_method = "nearest-exact"; megapixels = 1.0; resolution_steps = 1 } }
    "6" = @{ class_type = "GetImageSize"; inputs = @{ image = @("5", 0) } }
    "7" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("5", 0); vae = @("3", 0) } }
    "8" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $scenePrompt; clip = @("2", 0) } }
    "9" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = ""; clip = @("2", 0) } }
    "10" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("8", 0); latent = @("7", 0) } }
    "11" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("9", 0); latent = @("7", 0) } }
    "12" = @{ class_type = "CFGGuider"; inputs = @{ model = @("1", 0); positive = @("10", 0); negative = @("11", 0); cfg = 5.0 } }
    "13" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    "14" = @{ class_type = "Flux2Scheduler"; inputs = @{ steps = $Steps; width = @("6", 0); height = @("6", 1) } }
    "15" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Seed } }
    "16" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = @("6", 0); height = @("6", 1); batch_size = 1 } }
    "17" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("15", 0); guider = @("12", 0); sampler = @("13", 0); sigmas = @("14", 0); latent_image = @("16", 0) } }
    "18" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("17", 0); vae = @("3", 0) } }
    "19" = @{ class_type = "SaveImage"; inputs = @{ images = @("18", 0); filename_prefix = "$OutputPrefix-$suffix" } }
}

$clientId = [guid]::NewGuid().ToString()
$body = @{ prompt = $prompt; client_id = $clientId } | ConvertTo-Json -Depth 100
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt id: $($queued | ConvertTo-Json -Depth 10)"
}

Write-Host "Queued prompt $($queued.prompt_id) on $Server"
$deadline = (Get-Date).AddMinutes(30)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)"
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry) {
        if ($entry.status.status_str -eq "error") {
            throw "Generation failed: $($entry.status.messages | ConvertTo-Json -Depth 20)"
        }
        if ($entry.status.completed) {
            $saved = @($entry.outputs.'19'.images)
            if ($saved.Count -eq 0) {
                throw "Generation completed without a saved image."
            }
            foreach ($image in $saved) {
                $relativePath = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                $absolutePath = Join-Path (Join-Path $ComfyRoot "output") $relativePath
                Write-Output ([pscustomobject]@{
                    prompt_id = $queued.prompt_id
                    steps = $Steps
                    seed = $Seed
                    file = $absolutePath
                } | ConvertTo-Json -Compress)
            }
            exit 0
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for prompt $($queued.prompt_id)."
