param(
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [int]$TimeoutSeconds = 2700
)

$ErrorActionPreference = "Stop"
$queue = Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 10
if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
    throw "The RTX 3090 ComfyUI queue is not idle."
}
$stats = Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 10
if ([string]$stats.devices[0].name -notmatch "RTX 3090") {
    throw "This diagnostic must run on the RTX 3090 worker at port 8188."
}

$prompt = "An ordinary candid waist-up smartphone photo of one clearly featured person: m1tch_person, an adult man, standing alone in the foreground at a casual backyard gathering in late-afternoon daylight. He is the only foreground subject, wearing a pale blue open-collar shirt and looking directly toward the camera with a relaxed neutral expression. Any other guests are distant, small, softly blurred background figures; no foreground friend, no occlusion, no second prominent face. Natural skin texture, ordinary phone-camera depth and exposure."
$lora = "flux2-dev-identity-v2-candidates\m1tch-flux2-dev-identity-v2-s0200.safetensors"
$workflow = [ordered]@{
    "1" = @{ class_type = "UNETLoader"; inputs = @{ unet_name = "flux2_dev_fp8mixed.safetensors"; weight_dtype = "default" } }
    "2" = @{ class_type = "LoraLoaderModelOnly"; inputs = @{ model = @("1", 0); lora_name = $lora; strength_model = 1.0 } }
    "3" = @{ class_type = "CLIPLoader"; inputs = @{ clip_name = "mistral_3_small_flux2_fp4_mixed.safetensors"; type = "flux2"; device = "default" } }
    "4" = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $prompt; clip = @("3", 0) } }
    "5" = @{ class_type = "FluxGuidance"; inputs = @{ conditioning = @("4", 0); guidance = 4.0 } }
    "6" = @{ class_type = "BasicGuider"; inputs = @{ model = @("2", 0); conditioning = @("5", 0) } }
    "7" = @{ class_type = "KSamplerSelect"; inputs = @{ sampler_name = "euler" } }
    "8" = @{ class_type = "Flux2Scheduler"; inputs = @{ width = 832; height = 1248; steps = 28 } }
    "9" = @{ class_type = "RandomNoise"; inputs = @{ noise_seed = [UInt64]8675311 } }
    "10" = @{ class_type = "EmptyFlux2LatentImage"; inputs = @{ width = 832; height = 1248; batch_size = 1 } }
    "11" = @{ class_type = "SamplerCustomAdvanced"; inputs = @{ noise = @("9", 0); guider = @("6", 0); sampler = @("7", 0); sigmas = @("8", 0); latent_image = @("10", 0) } }
    "12" = @{ class_type = "VAELoader"; inputs = @{ vae_name = "flux2-vae.safetensors" } }
    "13" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("11", 0); vae = @("12", 0) } }
    "14" = @{ class_type = "SaveImage"; inputs = @{ images = @("13", 0); filename_prefix = "identity-eval/flux2-dev-v2/gate-200-s0200-waist-up-social-unambiguous" } }
}

$body = @{ prompt = $workflow; client_id = "flux2-dev-v2-social-retry" } | ConvertTo-Json -Depth 30
$queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id." }
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 2
    $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 15
    $entry = $history.PSObject.Properties[$queued.prompt_id].Value
    if ($entry -and $entry.status.status_str -eq "error") {
        throw "Generation failed: $($entry.status.messages | ConvertTo-Json -Depth 15)"
    }
    if ($entry -and $entry.status.completed) {
        $image = @($entry.outputs."14".images)[0]
        $relative = if ($image.subfolder) { Join-Path $image.subfolder $image.filename } else { $image.filename }
        $result = [ordered]@{
            created_utc = (Get-Date).ToUniversalTime().ToString("o")
            purpose = "One-variable step-200 diagnostic: remove multi-person subject ambiguity from the waist-up social prompt."
            changed_variable = "prompt only"
            checkpoint = $lora
            checkpoint_step = 200
            strength = 1.0
            sampler = "euler"
            steps = 28
            guidance = 4.0
            seed = 8675311
            width = 832
            height = 1248
            prompt = $prompt
            output = Join-Path "C:\projects\AI-Tools\ComfyUI\output" $relative
            promotion_eligible = $false
            manual_review = "pending"
        }
        $report = "C:\projects\AI-Tools\Mitch-Comfy\work\flux2-dev-identity-v2\comparisons\gate-200\step-200-social-unambiguous.json"
        $result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $report -Encoding utf8
        $result | ConvertTo-Json -Depth 10
        exit 0
    }
} while ((Get-Date) -lt $deadline)
throw "Timed out waiting for the social retry."
