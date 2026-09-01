param(
    [Parameter(Mandatory = $true)]
    [string]$CheckpointPath,
    [ValidateSet("1.0", "0.8")]
    [string]$Strength = "1.0"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$workRoot = Join-Path $repoRoot "work\flux2-dev-identity-v2"
$toolkitRoot = "C:\projects\AI-Tools\ai-toolkit\AI-Toolkit"
$python = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$runPy = Join-Path $toolkitRoot "run.py"
$validator = Join-Path $repoRoot "scripts\validate-flux2-dev-v2-checkpoint.py"
$checkpoint = (Resolve-Path -LiteralPath $CheckpointPath).Path
$checkpointHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $checkpoint).Hash.ToLowerInvariant()

$metadataCommand = "import json; from safetensors import safe_open; f=safe_open(r'''$checkpoint''',framework='pt',device='cpu'); print(json.loads((f.metadata() or {}).get('training_info','{}')).get('step',''))"
$step = [int](& $python -c $metadataCommand)
if ($LASTEXITCODE -ne 0 -or $step -notin @(250, 300, 350, 400, 450, 500)) {
    throw "Native final validation accepts a screened v2 checkpoint at step 250/300/350/400/450/500."
}
$precheck = Join-Path $workRoot "checkpoint-validation\native-precheck-s$step.json"
& $python $validator $checkpoint --expected-step $step --expected-modules 128 --json-output $precheck
if ($LASTEXITCODE -ne 0) { throw "Checkpoint pre-validation failed: $precheck" }

foreach ($port in 8188, 8189) {
    $queue = Invoke-RestMethod -Uri "http://127.0.0.1:$port/queue" -TimeoutSec 10
    if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
        throw "Comfy queue at port $port is active."
    }
}
Invoke-RestMethod -Uri "http://127.0.0.1:8188/free" -Method Post -ContentType "application/json" -Body '{"unload_models":true,"free_memory":true}' -TimeoutSec 30 | Out-Null

$hashTag = $checkpointHash.Substring(0, 8)
$runName = "native-s$step-$hashTag-s$($Strength.Replace('.', ''))"
$runDirectory = Join-Path $workRoot "native-final\$runName"
$configPath = Join-Path $runDirectory "config.yaml"
$logPath = Join-Path $runDirectory "native-training.log"
New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null
$config = @"
---
job: extension
config:
  name: $runName
  process:
    - type: diffusion_trainer
      training_folder: $runDirectory
      device: cuda:0
      trigger_word: m1tch_person
      performance_log_every: 0
      network:
        type: lora
        linear: 16
        linear_alpha: 16
        pretrained_lora_path: $checkpoint
        network_kwargs:
          only_if_contains:
            - ".img_attn."
            - ".txt_attn."
            - ".single_blocks."
      save:
        dtype: bf16
        save_every: 0
        max_step_saves_to_keep: 1
        save_format: safetensors
        push_to_hub: false
      datasets:
        - folder_path: $repoRoot\datasets\mitch-identity-stills-v3\dataset
          caption_ext: txt
          caption_dropout_rate: 0.0
          token_dropout_rate: 0.0
          shuffle_tokens: false
          cache_latents_to_disk: true
          cache_text_embeddings: true
          resolution: 1024
          num_repeats: 1
          flip_x: false
          flip_y: false
      train:
        batch_size: 1
        steps: $step
        start_step: $step
        gradient_accumulation: 4
        train_unet: true
        train_text_encoder: false
        gradient_checkpointing: true
        noise_scheduler: flowmatch
        timestep_type: linear
        content_or_style: balanced
        optimizer: adamw8bit
        optimizer_params:
          weight_decay: 0.0001
        lr: 0.00008
        lr_scheduler: constant
        max_grad_norm: 1.0
        unload_text_encoder: true
        cache_text_embeddings: true
        skip_first_sample: true
        force_first_sample: true
        disable_sampling: false
        dtype: bf16
        loss_type: mse
        ema_config:
          use_ema: false
          ema_decay: 0.99
      model:
        name_or_path: black-forest-labs/FLUX.2-dev
        arch: flux2
        dtype: bf16
        quantize: true
        qtype: qfloat8
        quantize_te: true
        qtype_te: qfloat8
        low_vram: true
        layer_offloading: true
        layer_offloading_transformer_percent: 1.0
        layer_offloading_text_encoder_percent: 1.0
        model_kwargs:
          match_target_res: false
      sample:
        sampler: flowmatch
        sample_every: 0
        sample_start_step: 0
        width: 832
        height: 1248
        prompts:
          - An ordinary unedited smartphone portrait of m1tch_person, an adult man, seated at a neighborhood cafe in soft open shade, head and shoulders, navy crew-neck T-shirt, relaxed natural half-smile, looking at the camera, realistic pores and fine facial detail, believable phone-camera exposure, no beauty filter.
        neg: ""
        seed: 8675310
        walk_seed: false
        guidance_scale: 4.0
        sample_steps: 50
        network_multiplier: $Strength
        format: png
meta:
  purpose: Native AI-Toolkit 50-step final compatibility validation; no optimizer updates are executed.
  source_checkpoint_sha256: $checkpointHash
  optimizer_steps_executed: 0
  promotion_eligible: false
"@
$config | Set-Content -LiteralPath $configPath -Encoding utf8

$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:PYTHONUNBUFFERED = "1"
$env:CUDA_VISIBLE_DEVICES = "0"
$env:AI_TOOLKIT_PIN_QUANTIZED_OFFLOAD = "0"
Push-Location $toolkitRoot
try {
    & $python $runPy $configPath -l $logPath
    if ($LASTEXITCODE -ne 0) { throw "Native AI-Toolkit validation failed with exit code $LASTEXITCODE." }
} finally {
    Pop-Location
}
$sample = Get-ChildItem -LiteralPath $runDirectory -Filter "*.png" -File -Recurse | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $sample) { throw "Native validation completed without a PNG sample." }
[ordered]@{
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    checkpoint = $checkpoint
    checkpoint_sha256 = $checkpointHash
    checkpoint_step = $step
    strength = [double]$Strength
    native_steps = 50
    guidance = 4.0
    seed = 8675310
    width = 832
    height = 1248
    sample = $sample.FullName
    config = $configPath
    log = $logPath
    optimizer_updates_executed = 0
    manual_review = "pending"
    promotion_eligible = $false
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $runDirectory "RESULT.json") -Encoding utf8
Write-Host "Native 50-step validation sample: $($sample.FullName)"
