[CmdletBinding()]
param(
    [int]$Steps = 20,
    [double]$Guidance = 4.0,
    [UInt64]$Seed = 9472363,
    [string]$Server = "http://127.0.0.1:8188",
    [string]$ReferenceImage = "mitch-identity-anchor-walking-v1.png",
    [string]$OutputPrefix = "flux2-dev-native-reference-krea-comparison/state-fair-dev",
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
    "UNETLoader", "CLIPLoader", "VAELoader", "LoadImage", "GetImageSize",
    "VAEEncode", "ReferenceLatent", "CLIPTextEncode", "FluxGuidance",
    "BasicGuider", "KSamplerSelect", "Flux2Scheduler", "RandomNoise",
    "EmptyFlux2LatentImage", "SamplerCustomAdvanced", "VAEDecode", "SaveImage"
)
foreach ($nodeName in $requiredNodes) {
    $nodeInfo = Invoke-RestMethod -Uri "$Server/object_info/$nodeName"
    if (-not $nodeInfo.PSObject.Properties[$nodeName]) {
        throw "Required node is unavailable: $nodeName"
    }
}

$guidanceName = $Guidance.ToString("0.0", [Globalization.CultureInfo]::InvariantCulture)
$suffix = "${Steps}step-guidance${guidanceName}-seed${Seed}"
$prompt = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = "flux2_dev_fp8mixed.safetensors"; weight_dtype = "default" } }
    "2" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = "mistral_3_small_flux2_fp4_mixed.safetensors"; type = "flux2"; device = "default" } }
    "3" = @{ class_type = "VAELoader"; inputs = @{ vae_name = "flux2-vae.safetensors" } }
    "4" = @{ class_type = "LoadImage"; inputs = @{ image = $ReferenceImage } }
    "5" = @{ class_type = "GetImageSize"; inputs = @{ image = @("4", 0) } }
    "6" = @{ class_type = "VAEEncode"; inputs = @{ pixels = @("4", 0); vae = @("3", 0) } }
    "7" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $scenePrompt; clip = @("2", 0) } }
    "8" = @{ class_type = "FluxGuidance"; inputs = @{ conditioning = @("7", 0); guidance = $Guidance } }
    "9" = @{ class_type = "ReferenceLatent"; inputs = @{ conditioning = @("8", 0); latent = @("6", 0) } }
    "10" = @{ class_type = "BasicGuider"; inputs = @{ model = @("1", 0); conditioning = @("9", 0) } }
    "11" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    "12" = @{ class_type = "Flux2Scheduler"; inputs = @{ steps = $Steps; width = @("5", 0); height = @("5", 1) } }
    "13" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = $Seed } }
    "14" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = @("5", 0); height = @("5", 1); batch_size = 1 } }
    "15" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("13", 0); guider = @("10", 0); sampler = @("11", 0); sigmas = @("12", 0); latent_image = @("14", 0) } }
    "16" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("15", 0); vae = @("3", 0) } }
    "17" = @{ class_type = "SaveImage"; inputs = @{ images = @("16", 0); filename_prefix = "$OutputPrefix-$suffix" } }
}

$clientId = [guid]::NewGuid().ToString()
$body = @{ prompt = $prompt; client_id = $clientId } | ConvertTo-Json -Depth 100
$queued = Invoke-RestMethod -Method Post -Uri "$Server/prompt" -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) {
    throw "ComfyUI did not return a prompt id: $($queued | ConvertTo-Json -Depth 10)"
}

Write-Host "Queued prompt $($queued.prompt_id) on $Server"
$deadline = (Get-Date).AddMinutes(45)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$Server/history/$($queued.prompt_id)"
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry) {
        if ($entry.status.status_str -eq "error") {
            throw "Generation failed: $($entry.status.messages | ConvertTo-Json -Depth 20)"
        }
        if ($entry.status.completed) {
            $saved = @($entry.outputs.'17'.images)
            if ($saved.Count -eq 0) {
                throw "Generation completed without a saved image."
            }
            foreach ($image in $saved) {
                $relativePath = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
                $absolutePath = Join-Path (Join-Path $ComfyRoot "output") $relativePath
                Write-Output ([pscustomobject]@{
                    prompt_id = $queued.prompt_id
                    model = "flux2_dev_fp8mixed.safetensors"
                    text_encoder = "mistral_3_small_flux2_fp4_mixed.safetensors"
                    steps = $Steps
                    guidance = $Guidance
                    seed = $Seed
                    file = $absolutePath
                } | ConvertTo-Json -Compress)
            }
            exit 0
        }
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for prompt $($queued.prompt_id)."
