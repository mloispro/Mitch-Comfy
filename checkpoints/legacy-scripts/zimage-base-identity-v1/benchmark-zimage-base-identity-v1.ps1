[CmdletBinding()]
param(
    [ValidateSet("Validate", "Screen", "NineScenes", "Publish")]
    [string]$Mode = "Validate",
    [string]$CandidatePath = "",
    [double]$CandidateStrength = 0.0,
    [string]$ResumeCoarseResults = "",
    [switch]$MitchApproved,
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ComfyRoot = "C:\projects\AI-Tools\ComfyUI"
$ComfyPython = Join-Path $ComfyRoot ".venv\Scripts\python.exe"
$ToolkitPython = "C:\projects\AI-Tools\ai-toolkit\python_embeded\python.exe"
$RunRoot = Join-Path $RepoRoot "work\zimage-base-identity-v1"
$TrainingOutput = Join-Path $RunRoot "train\ai-toolkit-output\m1tch-zimage-base-identity-v1"
$CandidateStageRoot = Join-Path $ComfyRoot "models\loras\aitk\_zimage_identity_v1_eval"
$ValidationRoot = "C:\projects\AI-Tools\Mitch photos\mitch-identity-stills-v3\validation"
$OriginalRawRoot = Join-Path $ComfyRoot "output\zimg-social-pack\finals\curated-20260819"
$NegativePrompt = "low resolution, blurry, soft focus, CGI, illustration, painting, plastic skin, waxy skin, overprocessed face, beauty filter, deformed anatomy, bad hands, extra fingers, missing fingers, extra limbs, duplicate main subject, two identical men, cloned face, malformed cat, distorted golf club, text, caption, watermark, logo, screenshot, interface, playback controls, white border, blank margin, picture frame, letterboxing"
$GlobalStyle = "photorealistic candid lifestyle photography, authentic skin texture, natural anatomy, believable smartphone or 35mm camera detail, no text or watermark"
$LoraValidator = Join-Path $RepoRoot "scripts\validate-zimage-lora.py"
$IdentityEvaluator = Join-Path $RepoRoot "scripts\evaluate-flux2-dev-identity.py"
$SceneExtractor = Join-Path $RepoRoot "scripts\extract-zimage-scene-metadata.py"
$SheetBuilder = Join-Path $RepoRoot "scripts\build-zimage-identity-comparison-sheet.py"

function Assert-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required file is missing: $Path" }
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Assert-ComfyReady {
    $queue = Invoke-RestMethod -Uri "$ComfyUrl/queue" -TimeoutSec 10
    if (@($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
        throw "RTX 3090 ComfyUI has active work; no benchmark was submitted."
    }
    $stats = Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 10
    if ([string]$stats.devices[0].name -notmatch "RTX 3090") { throw "$ComfyUrl is not the RTX 3090 worker." }
    $classes = @("AIToolkitSocialPackSettings", "AIToolkitSocialScene", "AIToolkitSocialPackFinals")
    foreach ($class in $classes) {
        $info = Invoke-RestMethod -Uri "$ComfyUrl/object_info/$class" -TimeoutSec 20
        if (-not $info.$class) { throw "Required ComfyUI node is unavailable: $class" }
    }
    return [ordered]@{ device = [string]$stats.devices[0].name; port = 8188; queue_running = 0; queue_pending = 0 }
}

function Stage-Candidate([string]$Path) {
    Assert-File $Path
    & $ToolkitPython $LoraValidator $Path --expected-modules 240 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Candidate is not a valid 240-module Z-Image LoRA: $Path" }
    $hash = Get-Sha256 $Path
    $match = [regex]::Match((Split-Path -Leaf $Path), "_(\d{9})\.safetensors$")
    $stepLabel = if ($match.Success) { [int]$match.Groups[1].Value } else { "final" }
    $name = "m1tch-zimage-base-v1-step-$stepLabel-$($hash.Substring(0,8).ToLowerInvariant()).safetensors"
    New-Item -ItemType Directory -Path $CandidateStageRoot -Force | Out-Null
    $destination = Join-Path $CandidateStageRoot $name
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        if ((Get-Sha256 $destination) -ne $hash) { throw "Staged candidate hash collision: $destination" }
    } else {
        Copy-Item -LiteralPath $Path -Destination $destination
        if ((Get-Sha256 $destination) -ne $hash) { throw "Staged candidate copy hash mismatch: $destination" }
    }
    return [ordered]@{
        source = (Resolve-Path $Path).Path
        source_sha256 = $hash
        staged = $destination
        lora_name = "aitk\_zimage_identity_v1_eval\$name"
        step = $stepLabel
    }
}

function New-SceneNode([string]$Prompt, [long]$Seed, [string]$Preset, [double]$ControlStrength, [bool]$Enabled) {
    return [ordered]@{
        class_type = "AIToolkitSocialScene"
        inputs = [ordered]@{
            scene_name = "Evaluation"
            prompt = $Prompt
            negative_additions = ""
            seed = $Seed
            reference_preset = $Preset
            control_strength = $ControlStrength
            enabled = $Enabled
        }
    }
}

function New-SocialWorkflow(
    [string]$LoraName,
    [double]$Strength,
    [int]$Steps,
    [string]$OutputPrefix,
    [object[]]$Scenes
) {
    if ($Scenes.Count -gt 9) { throw "The social renderer accepts at most nine scenes." }
    $workflow = [ordered]@{}
    $workflow["1"] = [ordered]@{
        class_type = "AIToolkitSocialPackSettings"
        inputs = [ordered]@{
            lora_name = $LoraName
            trigger_word = "m1tch_person"
            global_style = $GlobalStyle
            negative_prompt = $NegativePrompt
            lora_strength = $Strength
            cfg = 4.0
            model_shift = 3.0
            draft_width = 576
            draft_height = 832
            draft_steps = 10
            final_width = 832
            final_height = 1216
            final_steps = $Steps
            output_prefix = $OutputPrefix
        }
    }
    for ($index = 0; $index -lt 9; $index++) {
        $nodeId = [string]($index + 2)
        if ($index -lt $Scenes.Count) {
            $scene = $Scenes[$index]
            $workflow[$nodeId] = New-SceneNode $scene.prompt ([long]$scene.seed) $scene.reference_preset ([double]$scene.control_strength) ([bool]$scene.enabled)
            $workflow[$nodeId].inputs.scene_name = [string]$scene.label
        } else {
            $workflow[$nodeId] = New-SceneNode "m1tch_person, disabled placeholder" (99000 + $index) "None (prompt only)" 0.7 $false
        }
    }
    $finalInputs = [ordered]@{
        render_final = $true
        final_scope = "All enabled scenes"
        settings = @("1", 0)
    }
    for ($index = 1; $index -le 9; $index++) { $finalInputs["scene_$index"] = @([string]($index + 1), 0) }
    $workflow["11"] = [ordered]@{ class_type = "AIToolkitSocialPackFinals"; inputs = $finalInputs }
    return $workflow
}

function Invoke-ComfyWorkflow([System.Collections.IDictionary]$Workflow, [int]$ExpectedImages, [string]$ClientId) {
    Assert-ComfyReady | Out-Null
    $body = @{ prompt = $Workflow; client_id = $ClientId } | ConvertTo-Json -Depth 30
    $queued = Invoke-RestMethod -Uri "$ComfyUrl/prompt" -Method Post -ContentType "application/json" -Body $body
    if (-not $queued.prompt_id) { throw "ComfyUI did not return a prompt id." }
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds * [math]::Max($ExpectedImages, 1))
    do {
        Start-Sleep -Seconds 3
        $history = Invoke-RestMethod -Uri "$ComfyUrl/history/$($queued.prompt_id)" -TimeoutSec 20
        $entry = $history.($queued.prompt_id)
        if ($entry -and $entry.status.status_str -eq "error") {
            $entry | ConvertTo-Json -Depth 20
            throw "ComfyUI benchmark generation failed."
        }
    } while ((-not $entry -or $entry.status.status_str -ne "success") -and (Get-Date) -lt $deadline)
    if (-not $entry -or $entry.status.status_str -ne "success") { throw "Timed out waiting for benchmark generation." }
    $images = @($entry.outputs."11".images)
    if ($images.Count -ne $ExpectedImages) { throw "Expected $ExpectedImages outputs, got $($images.Count)." }
    return @($images | ForEach-Object {
        $relative = if ($_.subfolder) { Join-Path $_.subfolder $_.filename } else { $_.filename }
        Join-Path (Join-Path $ComfyRoot "output") $relative
    })
}

function Get-HeldoutReferences {
    $references = @(Get-ChildItem -LiteralPath $ValidationRoot -Filter "*.jpg" -File | Sort-Object Name)
    if ($references.Count -ne 6) { throw "Expected six held-out validation photographs." }
    return $references
}

function Get-ScreenScenes([long]$SeedBase) {
    return @(
        [ordered]@{ label = "portrait"; prompt = "A realistic close portrait photograph of m1tch_person, an adult man, facing the camera in soft window daylight, relaxed neutral expression, plain navy crew-neck shirt, natural skin and hair texture, head and shoulders fully visible."; seed = $SeedBase + 1; reference_preset = "None (prompt only)"; control_strength = 0.7; enabled = $true },
        [ordered]@{ label = "waist-up-social"; prompt = "A candid waist-up smartphone photograph of m1tch_person, an adult man, seated at an outdoor cafe in soft afternoon daylight, relaxed posture and a restrained natural smile while looking just past the camera, believable phone-camera texture."; seed = $SeedBase + 2; reference_preset = "None (prompt only)"; control_strength = 0.7; enabled = $true },
        [ordered]@{ label = "near-profile-candid"; prompt = "A realistic nighttime rooftop photograph of m1tch_person at a glass railing. His head is tilted downward and turned toward image-left, and his eyes look clearly down-left away from the camera with absolutely no eye contact. Three-quarter profile, natural skin, dark open-collar shirt, city lights far below."; seed = $SeedBase + 3; reference_preset = "None (prompt only)"; control_strength = 0.7; enabled = $true },
        [ordered]@{ label = "full-body-walking"; prompt = "A realistic full-body vertical lifestyle photograph of m1tch_person walking naturally toward the camera on a tropical golf course, fitted plain black golf shirt, tailored charcoal trousers, white glove, carrying one iron at his side, entire body and both feet visible, ordinary slim-to-average proportions."; seed = $SeedBase + 4; reference_preset = "Golf course pose"; control_strength = 0.7; enabled = $true },
        [ordered]@{ label = "multiperson-lounge"; prompt = "A photorealistic candid lounge group photo with exactly four adults. m1tch_person is the single central man on a caramel leather sofa in a dark navy suit. The other three friends are unrelated people with clearly different faces, hairlines, skin tones, builds, and clothing. Exactly one person matches m1tch_person; never clone or duplicate his face."; seed = $SeedBase + 5; reference_preset = "None (prompt only)"; control_strength = 0.7; enabled = $true }
    )
}

function Invoke-IdentityEvaluation([string[]]$Images, [string]$OutputPath) {
    if ($Images.Count -ne 5) { throw "Identity evaluation requires five generated images." }
    $args = [System.Collections.Generic.List[string]]::new()
    $args.Add($IdentityEvaluator)
    foreach ($reference in Get-HeldoutReferences) { $args.Add("--reference"); $args.Add($reference.FullName) }
    foreach ($item in @(
        "portrait=$($Images[0])",
        "waist-up-social=$($Images[1])",
        "near-profile-candid=$($Images[2])",
        "full-body-walking=$($Images[3])"
    )) { $args.Add("--scene"); $args.Add($item) }
    $args.Add("--crowd"); $args.Add($Images[4])
    $args.Add("--json-output"); $args.Add($OutputPath)
    $args.Add("--insightface-root"); $args.Add("C:\Users\Mitch\.insightface")
    & $ComfyPython @args | Out-Null
    $evaluationExit = $LASTEXITCODE
    if ($evaluationExit -notin @(0, 2) -or -not (Test-Path -LiteralPath $OutputPath -PathType Leaf)) {
        throw "Local AntelopeV2 evaluation failed with exit code $evaluationExit."
    }
    return Get-Content -Raw -LiteralPath $OutputPath | ConvertFrom-Json
}

function Get-CoreMedian($Evaluation) {
    $values = @($Evaluation.scenes | Where-Object label -In @("portrait", "waist-up-social", "near-profile-candid") | ForEach-Object centroid_similarity | Where-Object { $null -ne $_ } | Sort-Object)
    if ($values.Count -ne 3) { return -1.0 }
    return [double]$values[1]
}

function Invoke-CandidateEvaluation($Candidate, [double]$Strength, [long]$SeedBase, [string]$Root, [string]$Label) {
    $safeStrength = ([string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0:0.0}", $Strength)).Replace(".", "p")
    $outputPrefix = "zimage-identity-v1/$Label/step-$($Candidate.step)-strength-$safeStrength-seed-$SeedBase"
    $workflow = New-SocialWorkflow $Candidate.lora_name $Strength 30 $outputPrefix (Get-ScreenScenes $SeedBase)
    $started = Get-Date
    $images = Invoke-ComfyWorkflow $workflow 5 "zimage-identity-v1-$Label"
    $reportPath = Join-Path $Root "step-$($Candidate.step)-strength-$safeStrength-seed-$SeedBase.json"
    $evaluation = Invoke-IdentityEvaluation $images $reportPath
    $result = [ordered]@{
        step = $Candidate.step
        strength = $Strength
        seed_base = $SeedBase
        candidate = $Candidate
        images = $images
        evaluation_report = $reportPath
        automatic_gates_passed = [bool]$evaluation.acceptance.automatic_gates_passed
        core_median = Get-CoreMedian $evaluation
        core_strong_count = [int]$evaluation.acceptance.core_strong_match_count
        crowd_leakage_failures = @($evaluation.acceptance.crowd_leakage_failures)
        runtime_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
        manual_rooftop_down_left_required = $true
        manual_full_body_proportion_required = $true
    }
    return $result
}

function Find-Checkpoint([int]$Step) {
    $name = "m1tch-zimage-base-identity-v1_$($Step.ToString('000000000')).safetensors"
    $path = Join-Path $TrainingOutput $name
    Assert-File $path
    return $path
}

function Select-BestGroup([object[]]$Groups) {
    $passing = @($Groups | Where-Object automatic_gates_passed)
    if ($passing.Count -eq 0) { return $null }
    $ordered = @($passing | Sort-Object @{ Expression = "mean_core_median"; Descending = $true }, @{ Expression = "tie_break"; Descending = $false })
    $leader = $ordered[0]
    $ties = @($ordered | Where-Object { [math]::Abs([double]$_.mean_core_median - [double]$leader.mean_core_median) -le 0.02 })
    return @($ties | Sort-Object tie_break)[0]
}

function Invoke-NineScenes($Candidate, [double]$Strength, [string]$BenchmarkRoot) {
    $sceneLock = Join-Path $BenchmarkRoot "nine-scene-lock.json"
    & $ToolkitPython $SceneExtractor $OriginalRawRoot (Join-Path $ComfyRoot "input") $sceneLock | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Could not extract the original Z-Image scene metadata." }
    $locked = Get-Content -Raw -LiteralPath $sceneLock | ConvertFrom-Json
    $scenes = @($locked.scenes | ForEach-Object {
        [ordered]@{
            label = $_.label
            prompt = $_.prompt
            seed = [long]$_.seed
            reference_preset = $_.reference_preset
            control_strength = [double]$_.control_strength
            enabled = $true
        }
    })
    $workflow = New-SocialWorkflow $Candidate.lora_name $Strength 25 "zimage-identity-v1/nine-scenes/step-$($Candidate.step)" $scenes
    $images = Invoke-ComfyWorkflow $workflow 9 "zimage-identity-v1-nine-scenes"
    $manifestScenes = [System.Collections.Generic.List[object]]::new()
    for ($index = 0; $index -lt 9; $index++) {
        $source = $locked.scenes[$index]
        $manifestScenes.Add([ordered]@{
            number = $index + 1
            slug = $source.slug
            label = $source.label
            prompt = $source.prompt
            seed = $source.seed
            reference_preset = $source.reference_preset
            control_strength = $source.control_strength
            identity_conditioning = "LoRA only"
            composition_conditioning = if ($source.reference_preset -eq "None (prompt only)") { "prompt only" } else { "Canny Z-Image Fun ControlNet 2.1 at strength 0.7" }
            original_raw = $source.original_raw
            final_target = $source.final_target
            new_image = $images[$index]
        })
    }
    $manifest = [ordered]@{
        generated_utc = (Get-Date).ToUniversalTime().ToString("o")
        candidate = $Candidate
        strength = $Strength
        width = 832
        height = 1216
        steps = 25
        cfg = 4.0
        shift = 3.0
        sampler = "res_multistep"
        scheduler = "simple"
        no_face_swap_or_identity_edit = $true
        scenes = $manifestScenes
        manual_requirements = @("rooftop head and eyes down-left", "exactly one Mitch in group scenes", "full-body golfer proportions", "full-size and thumbnail review")
    }
    $manifestPath = Join-Path $BenchmarkRoot "nine-scenes.json"
    $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding utf8
    $sheet = Join-Path $BenchmarkRoot "nine-scenes-overview.jpg"
    & $ToolkitPython $SheetBuilder $manifestPath $sheet
    if ($LASTEXITCODE -ne 0) { throw "Nine-scene comparison sheet creation failed." }
    return [ordered]@{ manifest = $manifestPath; overview = $sheet; images = $images }
}

function Invoke-FullScreen {
    $validation = Join-Path $RunRoot "train\training-validation.json"
    Assert-File $validation
    $training = Get-Content -Raw -LiteralPath $validation | ConvertFrom-Json
    if (-not $training.valid -or -not $training.zero_ooms) { throw "The production training validation has not passed." }
    Assert-ComfyReady | Out-Null
    if ($ResumeCoarseResults) {
        Assert-File $ResumeCoarseResults
        $coarsePath = (Resolve-Path $ResumeCoarseResults).Path
        $benchmarkRoot = Split-Path -Parent $coarsePath
        $coarse = @(Get-Content -Raw -LiteralPath $coarsePath | ConvertFrom-Json)
        $expectedCoarseSteps = @(600, 800, 1000, 1200, 1400, 1600, 1800, 2000)
        if ($coarse.Count -ne $expectedCoarseSteps.Count) { throw "Resumed coarse results do not contain eight candidates." }
        foreach ($step in $expectedCoarseSteps) {
            $entry = @($coarse | Where-Object step -eq $step)
            if ($entry.Count -ne 1 -or [double]$entry[0].strength -ne 0.9 -or [int]$entry[0].seed_base -ne 22000) {
                throw "Resumed coarse results are missing the locked step/strength/seed entry for step $step."
            }
            Assert-File $entry[0].evaluation_report
            if ((Get-Sha256 $entry[0].candidate.source) -ne [string]$entry[0].candidate.source_sha256) {
                throw "Resumed coarse candidate hash changed at step $step."
            }
            foreach ($image in @($entry[0].images)) { Assert-File $image }
        }
        Write-Host "Resuming explicit preserved coarse results: $coarsePath"
    } else {
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $benchmarkRoot = Join-Path $RunRoot "benchmarks\screen-$stamp"
        New-Item -ItemType Directory -Path $benchmarkRoot -Force | Out-Null
        $coarseList = [System.Collections.Generic.List[object]]::new()
        foreach ($step in @(600, 800, 1000, 1200, 1400, 1600, 1800, 2000)) {
            $candidate = Stage-Candidate (Find-Checkpoint $step)
            $coarseList.Add((Invoke-CandidateEvaluation $candidate 0.9 22000 $benchmarkRoot "coarse"))
        }
        $coarse = @($coarseList)
        $coarsePath = Join-Path $benchmarkRoot "coarse-results.json"
        $coarse | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $coarsePath -Encoding utf8
    }

    # Coarse screening ranks candidates; the strict pass/fail decision is made after
    # the two leaders and their adjacent checkpoints have each run three fixed seeds.
    $coarseLeaders = @($coarse | Sort-Object core_median -Descending | Select-Object -First 2)
    if ($coarseLeaders.Count -ne 2) { throw "Coarse screening did not produce two leaders." }
    $topSteps = @($coarseLeaders | Select-Object -ExpandProperty step)
    $finalistSteps = @($topSteps | ForEach-Object { $_ - 100; $_; $_ + 100 } | Where-Object { $_ -ge 100 -and $_ -le 2000 } | Sort-Object -Unique)
    $finalistGroups = [System.Collections.Generic.List[object]]::new()
    foreach ($step in $finalistSteps) {
        $candidate = Stage-Candidate (Find-Checkpoint $step)
        $runs = [System.Collections.Generic.List[object]]::new()
        foreach ($seedBase in @(22000, 32000, 42000)) { $runs.Add((Invoke-CandidateEvaluation $candidate 0.9 $seedBase $benchmarkRoot "finalist")) }
        $passes = @($runs | Where-Object automatic_gates_passed).Count
        $finalistGroups.Add([ordered]@{
            step = $step
            candidate = $candidate
            runs = $runs
            automatic_gates_passed = $passes -eq 3
            passing_runs = $passes
            mean_core_median = [double](($runs | ForEach-Object { [double]$_.core_median } | Measure-Object -Average).Average)
            tie_break = [int]$step
        })
    }
    $finalistPath = Join-Path $benchmarkRoot "finalist-results.json"
    $finalistGroups | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $finalistPath -Encoding utf8
    $bestCheckpoint = Select-BestGroup @($finalistGroups)
    if ($null -eq $bestCheckpoint) {
        $failurePath = Join-Path $benchmarkRoot "failure.json"
        $failure = [ordered]@{
            status = "rejected"
            failed_stage = "three-seed-finalist"
            reason = "No finalist passed all three fixed-seed automatic identity and leakage gates."
            recorded_utc = (Get-Date).ToUniversalTime().ToString("o")
            coarse_results = $coarsePath
            finalist_results = $finalistPath
            finalist_summaries = @($finalistGroups | ForEach-Object {
                [ordered]@{
                    step = $_.step
                    passing_runs = $_.passing_runs
                    automatic_gates_passed = $_.automatic_gates_passed
                    mean_core_median = $_.mean_core_median
                }
            })
            strength_sweep_run = $false
            nine_scenes_run = $false
            publication_allowed = $false
        }
        $failure | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $failurePath -Encoding utf8
        throw "No finalist passed all three fixed-seed automatic gates. Failure record: $failurePath"
    }

    $strengthGroups = [System.Collections.Generic.List[object]]::new()
    foreach ($strength in @(0.7, 0.9, 1.1)) {
        $runs = [System.Collections.Generic.List[object]]::new()
        foreach ($seedBase in @(22000, 32000, 42000)) { $runs.Add((Invoke-CandidateEvaluation $bestCheckpoint.candidate $strength $seedBase $benchmarkRoot "strength")) }
        $passes = @($runs | Where-Object automatic_gates_passed).Count
        $strengthGroups.Add([ordered]@{
            strength = $strength
            candidate = $bestCheckpoint.candidate
            runs = $runs
            automatic_gates_passed = $passes -eq 3
            passing_runs = $passes
            mean_core_median = [double](($runs | ForEach-Object { [double]$_.core_median } | Measure-Object -Average).Average)
            tie_break = [double]$strength
        })
    }
    $strengthPath = Join-Path $benchmarkRoot "strength-results.json"
    $strengthGroups | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $strengthPath -Encoding utf8
    $bestStrength = Select-BestGroup @($strengthGroups)
    if ($null -eq $bestStrength) { throw "No LoRA strength passed all three fixed-seed automatic gates." }

    $nineScenes = Invoke-NineScenes $bestCheckpoint.candidate ([double]$bestStrength.strength) $benchmarkRoot
    $winner = [ordered]@{
        automatic_gates_passed = $true
        selected_utc = (Get-Date).ToUniversalTime().ToString("o")
        checkpoint = $bestCheckpoint.candidate.source
        checkpoint_sha256 = $bestCheckpoint.candidate.source_sha256
        step = $bestCheckpoint.step
        strength = $bestStrength.strength
        mean_core_median = $bestStrength.mean_core_median
        coarse_results = $coarsePath
        finalist_results = $finalistPath
        strength_results = $strengthPath
        nine_scene_manifest = $nineScenes.manifest
        nine_scene_overview = $nineScenes.overview
        manual_visual_approval_required = $true
        published = $false
    }
    $winnerPath = Join-Path $benchmarkRoot "winner.json"
    $winner | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $winnerPath -Encoding utf8
    $latest = Join-Path $RunRoot "benchmarks\latest-winner.json"
    $winner | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $latest -Encoding utf8
    Write-Host "Automatic screen complete. Visual approval required: $($nineScenes.overview)"
    Write-Host "Winner record: $winnerPath"
}

function Invoke-NineSceneOnly([string]$Path, [double]$Strength) {
    if (-not $Path) { throw "NineScenes requires -CandidatePath." }
    if ($Strength -le 0) { throw "NineScenes requires -CandidateStrength." }
    $candidate = Stage-Candidate $Path
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $root = Join-Path $RunRoot "benchmarks\nine-scenes-$stamp"
    New-Item -ItemType Directory -Path $root -Force | Out-Null
    Invoke-NineScenes $candidate $Strength $root | ConvertTo-Json -Depth 8
}

function Publish-Winner([string]$Path) {
    if (-not $MitchApproved) { throw "Publication requires -MitchApproved after full-size visual review." }
    Assert-File $Path
    $latest = Join-Path $RunRoot "benchmarks\latest-winner.json"
    Assert-File $latest
    $winner = Get-Content -Raw -LiteralPath $latest | ConvertFrom-Json
    $sourceHash = Get-Sha256 $Path
    if (-not $winner.automatic_gates_passed -or $sourceHash -ne [string]$winner.checkpoint_sha256) {
        throw "Candidate is not the automatically passing checkpoint recorded in latest-winner.json."
    }
    & $ToolkitPython $LoraValidator $Path --expected-modules 240 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Publication candidate failed safetensors validation." }
    $destination = Join-Path $ComfyRoot "models\loras\aitk\m1tch-zimage-base-identity-v1.safetensors"
    if (Test-Path -LiteralPath $destination) { throw "Publication destination already exists; refusing to overwrite: $destination" }
    $temporary = "$destination.tmp"
    if (Test-Path -LiteralPath $temporary) { throw "Publication temporary path already exists: $temporary" }
    Copy-Item -LiteralPath $Path -Destination $temporary
    if ((Get-Sha256 $temporary) -ne $sourceHash) { throw "Publication copy hash mismatch." }
    Move-Item -LiteralPath $temporary -Destination $destination
    $record = [ordered]@{
        published_utc = (Get-Date).ToUniversalTime().ToString("o")
        source = (Resolve-Path $Path).Path
        destination = $destination
        sha256 = $sourceHash
        step = $winner.step
        strength = $winner.strength
        automatic_gates_passed = $true
        mitch_visual_approval = $true
        previous_loras_overwritten = $false
    }
    $recordPath = Join-Path $RunRoot "publication.json"
    $record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $recordPath -Encoding utf8
    Write-Host "Published guarded Z-Image Base identity LoRA: $destination"
}

foreach ($path in @($ToolkitPython, $ComfyPython, $LoraValidator, $IdentityEvaluator, $SceneExtractor, $SheetBuilder)) { Assert-File $path }

switch ($Mode) {
    "Validate" {
        $comfy = Assert-ComfyReady
        $references = Get-HeldoutReferences
        $checkpoints = @(@(600, 800, 1000, 1200, 1400, 1600, 1800, 2000) | ForEach-Object { Find-Checkpoint $_ })
        [ordered]@{
            valid = $true
            comfy = $comfy
            heldout_references = @($references.FullName)
            coarse_checkpoints = $checkpoints
            no_face_swap_or_identity_edit = $true
            publish_requires_automatic_gates_and_mitch_approval = $true
        } | ConvertTo-Json -Depth 8
    }
    "Screen" { Invoke-FullScreen }
    "NineScenes" { Invoke-NineSceneOnly $CandidatePath $CandidateStrength }
    "Publish" {
        if (-not $CandidatePath) { throw "Publish requires -CandidatePath." }
        Publish-Winner $CandidatePath
    }
}
