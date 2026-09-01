[CmdletBinding()]
param(
    [string]$Server = "http://127.0.0.1:8188",
    [string]$ComfyRoot = "C:\projects\AI-Tools\ComfyUI",
    [UInt64]$BaseSeed = 8675410,
    [string]$RunLabel = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$singleSceneRunner = Join-Path $PSScriptRoot "run-flux2-klein9b-native-multiref-no-lora.ps1"
$inputRoot = Join-Path $ComfyRoot "input"
$runStamp = if ($RunLabel) { $RunLabel } else { Get-Date -Format "yyyyMMdd-HHmmss" }
$runRoot = Join-Path $repoRoot "work\flux2-klein9b-native-nine-scenes\$runStamp"
$selectedRoot = Join-Path $runRoot "selected"
$manifestPath = Join-Path $runRoot "manifest.json"

if (Test-Path -LiteralPath $runRoot) {
    throw "Run directory already exists; refusing to overwrite it: $runRoot"
}

$references = @(
    "flux2-dev-ref-01-face-front.jpg",
    "flux2-dev-ref-02-face-angle.jpg",
    "flux2-dev-ref-03-upper-body.jpg",
    "flux2-dev-ref-04-full-body.jpg"
)
foreach ($reference in $references) {
    $path = Join-Path $inputRoot $reference
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing genuine Klein 9B identity reference: $path"
    }
}

$identityPreamble = (
    "Images 1 and 2 define Mitch's face from frontal and three-quarter views. " +
    "Image 3 defines his torso and image 4 defines his lean full-body build. " +
    "Preserve his facial geometry, short light-brown hair, apparent age, lean build, and natural skin. "
)

$scenes = @(
    [ordered]@{
        Number = 1; Slug = "night-out-a"; Label = "night out A"; Source = "mitch-workbench-dating-01-night-out-a.png"
        Prompt = "Create a vertical candid phone photograph in a warm amber lounge. Exactly four adults are visible. Mitch is the foreground man seated diagonally on a caramel curved leather sofa in a dark navy suit and open-collar white shirt, with his left arm draped along the sofa back, right hand near his pocket, and extended crossed legs. Behind him are three unrelated friends: a woman at far left holding a red drink, a man behind her in black, and a woman at rear right in a sleeveless black dress. Every friend has a clearly different face and none resembles Mitch."
    },
    [ordered]@{
        Number = 2; Slug = "night-out-b"; Label = "night out B"; Source = "mitch-workbench-dating-02-night-out-b.png"
        Prompt = "Create a vertical candid group phone photograph in an amber lounge. Exactly five adult faces are visible, including a partial person at the far left edge. Mitch is the central seated man in a dark suit and open-collar white shirt, leaning forward with hands near his knees and looking naturally toward the camera. Preserve an unrelated woman in a black one-shoulder dress on his left, an unrelated woman in a brown dress on his right, an unrelated man leaning in at far right, and the partial far-left person. Only the central man is Mitch; never duplicate his identity."
    },
    [ordered]@{
        Number = 3; Slug = "ragdoll-cat"; Label = "Ragdoll cat"; Source = "mitch-workbench-dating-03-cat-ragdoll.png"
        Prompt = "Create a vertical quiet apartment portrait. Mitch stands centered in a black zip hoodie and black shirt, cradling a very large fluffy white-and-gray Ragdoll cat horizontally across both forearms. His head tilts down toward image-right and he smiles affectionately at the cat with no eye contact. The cat's head and blue eyes are at image-right, its hind legs and fluffy tail at image-left, and both hands support it naturally. Sheer curtains and a beige leather sofa fill the softly lit background."
    },
    [ordered]@{
        Number = 4; Slug = "tabby-cat"; Label = "tabby cat"; Source = "mitch-workbench-dating-04-cat-tabby.png"
        Prompt = "Create a vertical bright apartment portrait. Mitch wears a plain black pullover hoodie and cradles a gray-brown tabby-and-white cat close to his chest with both hands. His head is bowed down toward image-right, looking at the cat rather than the camera, while the cat looks up at him. The cat's horizontal body and tail extend toward image-left. Include a pale sofa, white wall, beige curtain, soft window light, and a close three-quarter crop."
    },
    [ordered]@{
        Number = 5; Slug = "golfer"; Label = "golfer"; Source = "mitch-workbench-dating-05-golfer-safe.png"
        Prompt = "Create a vertical full-body walking golf portrait. Mitch walks directly toward the camera in the center of a tropical fairway, wearing an unbranded black long-sleeve golf polo, tailored gray trousers, and black golf shoes. He has a white glove on his left hand at image-right and holds one golf club down in his right hand at image-left. Keep his entire lean body and both feet in frame, with symmetrical palms, distant bunkers, clear morning light, and generous sky."
    },
    [ordered]@{
        Number = 6; Slug = "amalfi"; Label = "Amalfi"; Source = "mitch-workbench-dating-06-amalfi.png"
        Prompt = "Create a vertical close travel portrait at an Amalfi Coast overlook. Mitch stands left-of-center in a relaxed white short-sleeve linen shirt with an open collar, smiling naturally toward the camera. His torso is angled and one hand rests on a dark railing at image-right, with a wristwatch visible. Use late-afternoon sunlight, Positano hillside and church dome at image-left, open blue sea at image-right, and waist-up smartphone framing."
    },
    [ordered]@{
        Number = 7; Slug = "lake-boat"; Label = "lake boat"; Source = "mitch-workbench-dating-07-lake-boat.png"
        Prompt = "Create a vertical Italian lake boat portrait. Mitch sits centered on the cream bow seat of a polished classic wooden motorboat, wearing an open-collar white linen shirt with rolled sleeves, white shorts, and dark sunglasses. He sits with knees apart and both arms extended, hands resting on the wooden side rails. Include glossy wood in the foreground, rippling lake, villas at image-left, steep green mountains, and three-quarter framing."
    },
    [ordered]@{
        Number = 8; Slug = "restaurant"; Label = "restaurant"; Source = "mitch-workbench-dating-08-restaurant.png"
        Prompt = "Create a vertical elegant restaurant portrait containing one person only. Mitch sits centered at a white table in a light-gray double-breasted blazer over a black shirt. His right hand lightly supports his chin and he makes direct calm eye contact. Include a small glowing table lamp in the left foreground, warm arched mirror light behind him, dark reflective walls, palm leaves, a chair, and chest-to-waist framing."
    },
    [ordered]@{
        Number = 9; Slug = "night-rooftop"; Label = "night rooftop"; Source = "mitch-workbench-dating-09-night-city.png"
        Prompt = "Create a vertical night rooftop portrait. Mitch stands centered at a glass high-rise railing in a fitted black short-sleeve open-collar button shirt, dark trousers, and a watch on his left wrist at image-right. Both extended arms and both hands rest on the railing. His head tilts downward and turns toward image-left, and his eyes look down-left away from the camera with absolutely no eye contact. Use wide three-quarter-body framing, a large dark teal sky, and dense city lights far below. Do not turn his head toward image-right or the viewer."
    }
)

foreach ($scene in $scenes) {
    $sourcePath = Join-Path $inputRoot $scene.Source
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Missing comparison source: $sourcePath"
    }
}

$queue3090 = Invoke-RestMethod -Uri "$Server/queue" -TimeoutSec 10
if (@($queue3090.queue_running).Count -gt 0 -or @($queue3090.queue_pending).Count -gt 0) {
    throw "RTX 3090 ComfyUI queue is not idle."
}
$queue4070 = Invoke-RestMethod -Uri "http://127.0.0.1:8189/queue" -TimeoutSec 10
$otherWorkerRunningAtStart = @($queue4070.queue_running).Count
$otherWorkerPendingAtStart = @($queue4070.queue_pending).Count
if ($otherWorkerRunningAtStart -gt 0 -or $otherWorkerPendingAtStart -gt 0) {
    Write-Warning "RTX 4070 worker is active and will be left untouched while the independent RTX 3090 runs."
}
$stats = Invoke-RestMethod -Uri "$Server/system_stats" -TimeoutSec 10
if ([string]$stats.devices[0].name -notmatch "RTX 3090") {
    throw "The selected Klein 9B worker is not the RTX 3090: $($stats.devices[0].name)"
}

New-Item -ItemType Directory -Path $selectedRoot -Force | Out-Null
$records = [System.Collections.Generic.List[object]]::new()
$firstScene = $true
foreach ($scene in $scenes) {
    $seed = [UInt64]($BaseSeed + [UInt64]$scene.Number)
    $outputPrefix = "flux2-klein9b-native-nine-scenes/$runStamp/$($scene.Number.ToString('00'))-$($scene.Slug)"
    $arguments = @{
        Steps = 4
        Cfg = 1.0
        Seed = $seed
        Width = 832
        Height = 1248
        ReferenceMegapixels = 0.40
        ReferenceCount = 4
        Server = $Server
        OutputPrefix = $outputPrefix
        ComfyRoot = $ComfyRoot
        ScenePrompt = "$identityPreamble$($scene.Prompt)"
        AllowOtherWorkerBusy = $true
    }
    if (-not $firstScene) {
        $arguments["SkipModelHashValidation"] = $true
    }
    $runnerOutput = @(& $singleSceneRunner @arguments)
    $jsonLine = @($runnerOutput | Where-Object { $_ -is [string] -and $_.TrimStart().StartsWith("{") } | Select-Object -Last 1)
    if ($jsonLine.Count -ne 1) {
        throw "The Klein 9B runner did not return one result for scene $($scene.Number)."
    }
    $result = $jsonLine[0] | ConvertFrom-Json
    $selectedPath = Join-Path $selectedRoot "$($scene.Number.ToString('00'))-$($scene.Slug).png"
    Copy-Item -LiteralPath $result.file -Destination $selectedPath
    $records.Add([ordered]@{
        scene = [int]$scene.Number
        label = [string]$scene.Label
        source = (Join-Path $inputRoot $scene.Source)
        source_used_as_conditioning = $false
        selected_output = $selectedPath
        raw_output = [string]$result.file
        seed = $seed
        seconds = [double]$result.seconds
        prompt = [string]$result.prompt
    })
    $firstScene = $false
}

$manifest = [ordered]@{
    schema_version = 1
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    method = "FLUX.2 Klein 9B native four-reference generation; source scenes are comparison targets only"
    gpu = [string]$stats.devices[0].name
    model = "flux-2-klein-9b-fp8.safetensors"
    model_sha256 = "865BA09F5B4C3CBD3468A4BD3ACB9FCB2F8740C54317482F0BCD4ED1D3655CEE"
    text_encoder = "qwen_3_8b_fp8mixed.safetensors"
    vae = "flux2-vae.safetensors"
    identity_mechanism = "four genuine Mitch photographs VAE-encoded and appended as native ReferenceLatent conditioning"
    identity_references = $references
    source_scene_conditioning = $false
    other_worker_activity_at_start = [ordered]@{
        port = 8189
        running = $otherWorkerRunningAtStart
        pending = $otherWorkerPendingAtStart
        action_taken = "none"
    }
    character_lora = $null
    identity_adapter = $null
    face_swap = $false
    mask = $false
    restoration = $false
    settings = [ordered]@{
        width = 832
        height = 1248
        steps = 4
        cfg = 1.0
        sampler = "euler"
        scheduler = "simple"
        reference_megapixels_each = 0.40
    }
    scenes = @($records)
}
$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Host "Manifest: $manifestPath"
Write-Host "Selected outputs: $selectedRoot"
Write-Output $manifestPath
