[CmdletBinding()]
param(
    [string]$SourceWorkflow = "checkpoints\legacy-workflows\production\Krea 2 Identity Edit - Face Attention v2.json",
    [string]$OutputWorkflow = "checkpoints\legacy-workflows\production\Krea 2 Identity Anchor Crowd v1.json",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$sourcePath = Join-Path $repoRoot $SourceWorkflow
$outputPath = Join-Path $repoRoot $OutputWorkflow
$promptConfigPath = Join-Path $repoRoot "config\crowd-route-v1-prompts.json"
if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
    throw "Source workflow does not exist: $sourcePath"
}
if ((Test-Path -LiteralPath $outputPath) -and -not $Force) {
    throw "Refusing to overwrite existing workflow without -Force: $outputPath"
}

$workflow = Get-Content -LiteralPath $sourcePath -Raw | ConvertFrom-Json
$promptConfig = Get-Content -LiteralPath $promptConfigPath -Raw | ConvertFrom-Json
$stateFairPrompt = [string]$promptConfig.scene_prompts.'state-fair'
$workflow.id = "krea2-identity-anchor-crowd-v1"
$workflow.revision = 2
function Get-WorkflowNode([int]$Id) {
    $node = @($workflow.nodes | Where-Object id -eq $Id)
    if ($node.Count -ne 1) {
        throw "Expected exactly one workflow node with id $Id; found $($node.Count)."
    }
    return $node[0]
}

(Get-WorkflowNode 29).widgets_values = "crowd-route-v1/identity-anchor-crowd"
(Get-WorkflowNode 53).widgets_values[0] = 9472363
(Get-WorkflowNode 72).widgets_values = @("mitch-identity-anchor-walking-v1.png", "image")
(Get-WorkflowNode 84).widgets_values[0] = $stateFairPrompt
(Get-WorkflowNode 84).widgets_values[1] = 768
(Get-WorkflowNode 85).widgets_values[1] = 768
(Get-WorkflowNode 101).widgets_values = "Use the frozen user-approved identity anchor, mitch-identity-anchor-walking-v1.png. It supplies the accepted face, current hair, apparent age, lean build, and natural proportions. The state-fair proof uses native mid-torso customer framing so height is not repaired downstream. Do not replace the anchor without reopening validation."
(Get-WorkflowNode 102).widgets_values = "The mask operates only on reference-token attention inside the generated whole frame. It never masks, composites, inpaints, sharpens, or replaces output pixels. Keep width 0.82, height 0.86, vertical offset 0.02, and masked reference boost 6."
(Get-WorkflowNode 103).widgets_values = "Change only the native scene description, framing, and seed during generalization. Keep the exact identity-preservation language, anchor, model order, reference attention, sampling settings, and whole-frame finish. Establish scale in the initial generation. Never repair height or integration afterward with crop, output mask, inpaint, outpaint, swap, or compositing."
(Get-WorkflowNode 105).widgets_values = "Frozen crowd_route_v1 settings: Krea2 Turbo; Identity Edit v1.2 strength 1.0; smartphone LoRA 0.35; 12 steps; CFG 1; Euler + simple; 832 x 1248; grounding_px 768; approved native state-fair seed 9472363."
(Get-WorkflowNode 106).widgets_values = "KREA 2 IDENTITY ANCHOR CROWD v1\n\nApproved state-fair proof: one native whole-frame generation from the user-approved identity anchor, framed as a mid-torso customer activity candid. No scene plate, host replacement, ReActor, face restoration, output crop, subject mask, inpaint, outpaint, compositing, or selective sharpening. WholeFramePhoneFinish is fixed, uniform, and non-generative. Human visual identity and realism review are authoritative."
$identityGroup = @($workflow.groups | Where-Object id -eq 2)
if ($identityGroup.Count -eq 1) {
    $identityGroup[0].title = "2 · APPROVED FULL-BODY IDENTITY ANCHOR"
}

$outputDirectory = Split-Path -Parent $outputPath
[System.IO.Directory]::CreateDirectory($outputDirectory) | Out-Null
$json = $workflow | ConvertTo-Json -Depth 100
[System.IO.File]::WriteAllText($outputPath, $json, [System.Text.UTF8Encoding]::new($false))
Write-Host "Built: $outputPath"
