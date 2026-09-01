[CmdletBinding()]
param(
    [string]$Workflow = "checkpoints\legacy-workflows\production\Krea 2 Identity Edit - Face Attention v2.json",
    [string]$ExpectedWorkflowId = "krea2-identity-edit-face-attention-v2",
    [int]$Port = 8189,
    [switch]$SkipLiveApi
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$workflowPath = [IO.Path]::GetFullPath((Join-Path $repoRoot $Workflow))
if (-not (Test-Path -LiteralPath $workflowPath -PathType Leaf)) {
    throw "Workflow does not exist: $workflowPath"
}

$graph = Get-Content -Raw -LiteralPath $workflowPath | ConvertFrom-Json
$nodes = @{}
foreach ($node in $graph.nodes) {
    if ($nodes.ContainsKey([int]$node.id)) {
        throw "Duplicate node id $($node.id)."
    }
    $nodes[[int]$node.id] = $node
}
$links = @{}
foreach ($link in $graph.links) {
    if ($links.ContainsKey([int]$link[0])) {
        throw "Duplicate link id $($link[0])."
    }
    if (-not $nodes.ContainsKey([int]$link[1]) -or -not $nodes.ContainsKey([int]$link[3])) {
        throw "Link $($link[0]) references a missing node."
    }
    $links[[int]$link[0]] = $link
}

function Assert-Equal($Actual, $Expected, [string]$Message) {
    if ($Actual -ne $Expected) {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

function Get-InputLink([int]$NodeId, [string]$Name) {
    $input = @($nodes[$NodeId].inputs | Where-Object name -eq $Name)
    if ($input.Count -ne 1) { throw "Node $NodeId does not have exactly one '$Name' input." }
    return $input[0].link
}

Assert-Equal $graph.id $ExpectedWorkflowId "Wrong workflow id."
Assert-Equal @($graph.nodes | Where-Object type -eq "Krea2ReferenceFaceAttentionMask").Count 1 "Face attention node count is wrong."
Assert-Equal @($graph.nodes | Where-Object type -eq "WholeFramePhoneFinish").Count 1 "Whole-frame phone finish node count is wrong."
Assert-Equal @($graph.nodes | Where-Object id -In @(90, 92)).Count 0 "The ambiguous optional second-reference nodes remain."
Assert-Equal (Get-InputLink 112 "image") 29 "Reference image is not connected to the face attention node."
Assert-Equal (Get-InputLink 79 "ref_boost_mask") 30 "Face attention mask is not connected to Krea2EditModelPatch."
Assert-Equal (Get-InputLink 71 "model") 28 "Identity Edit is not downstream of the smartphone LoRA."
Assert-Equal (Get-InputLink 113 "image") 31 "Decoded image is not connected to the whole-frame phone finish."
Assert-Equal (Get-InputLink 29 "images") 32 "SaveImage is not downstream of the whole-frame phone finish."
Assert-Equal $nodes[111].widgets_values[0] "krea-smartphone-photo-slider.safetensors" "Wrong camera LoRA."
Assert-Equal ([double]$nodes[111].widgets_values[1]) 0.35 "Wrong camera LoRA strength."
Assert-Equal ([double]$nodes[79].widgets_values[0]) 6.0 "Wrong masked reference boost."
Assert-Equal ([int]$nodes[84].widgets_values[1]) 512 "Wrong positive grounding resolution."
Assert-Equal ([int]$nodes[85].widgets_values[1]) 512 "Wrong negative grounding resolution."
Assert-Equal ([int]$nodes[53].widgets_values[2]) 12 "Wrong sampling step count."
Assert-Equal ([double]$nodes[53].widgets_values[3]) 1.0 "Wrong CFG."
Assert-Equal $nodes[53].widgets_values[4] "euler" "Wrong sampler."
Assert-Equal $nodes[53].widgets_values[5] "simple" "Wrong scheduler."
Assert-Equal ([double]$nodes[112].widgets_values[0]) 0.82 "Wrong face-mask width scale."
Assert-Equal ([double]$nodes[112].widgets_values[1]) 0.86 "Wrong face-mask height scale."
Assert-Equal ([double]$nodes[112].widgets_values[2]) 0.02 "Wrong face-mask vertical offset."

if (-not $SkipLiveApi) {
    $baseUrl = "http://127.0.0.1:$Port"
    $stats = Invoke-RestMethod -Uri "$baseUrl/system_stats" -TimeoutSec 10
    $device = [string](@($stats.devices)[0].name)
    if ($device -notlike "*NVIDIA GeForce RTX 4070*") {
        throw "Port $Port is serving '$device', not the isolated RTX 4070 worker."
    }
    $objectInfo = Invoke-RestMethod -Uri "$baseUrl/object_info" -TimeoutSec 45
    foreach ($nodeName in @(
        "Krea2ReferenceFaceAttentionMask",
        "WholeFramePhoneFinish",
        "Krea2EditModelPatch",
        "Krea2EditGroundedEncode"
    )) {
        if (-not $objectInfo.PSObject.Properties[$nodeName]) {
            throw "RTX 4070 ComfyUI does not expose required node '$nodeName'."
        }
    }
    $loraNames = @($objectInfo.LoraLoaderModelOnly.input.required.lora_name[0])
    foreach ($loraName in @(
        "krea2_identity_edit_v1_2.safetensors",
        "krea-smartphone-photo-slider.safetensors"
    )) {
        if ($loraNames -notcontains $loraName) {
            throw "RTX 4070 ComfyUI cannot see required LoRA '$loraName'."
        }
    }
}

Write-Host "Krea2 face-attention workflow verification passed: $workflowPath"
Write-Host "No prompt was submitted and no image was generated."
