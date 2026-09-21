[CmdletBinding()]
param(
    [string]$ComfyRoot = 'C:\projects\AI-Tools\ComfyUI',
    [ValidateSet('Curated', 'Legacy')][string]$Mode = 'Curated',
    [switch]$Apply,
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'comfy-workflow-library.ps1')
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path.TrimEnd('\')
$ComfyRoot = (Resolve-Path -LiteralPath $ComfyRoot).Path.TrimEnd('\')
Assert-WorkflowPlainDirectory -Path $RepoRoot
Assert-WorkflowPlainDirectory -Path $ComfyRoot
$legacy = (Resolve-Path -LiteralPath (Join-Path $RepoRoot 'workflows')).Path.TrimEnd('\')
$curated = Get-ComfyWorkflowLibraryPath -RepoRoot $RepoRoot
if ($Mode -eq 'Curated') { Assert-ComfyWorkflowLibrarySources -RepoRoot $RepoRoot }
$requestedTarget = if ($Mode -eq 'Curated') { $curated } else { $legacy }

# Exact two-entry allowlist. Parent links are rejected so a redirected user root
# cannot move or expose unrelated data. This script never touches .index.json,
# browser/unsaved-tab state, source workflow files, or Comfy processes/queues.
$entries = @(
    @{ Label = 'primary'; Relative = 'user\default\workflows\Mitch' },
    @{ Label = 'secondary'; Relative = 'user-4070\default\workflows\Mitch' }
)
$plan = @()
foreach ($entry in $entries) {
    $parent = $ComfyRoot
    foreach ($segment in @($entry.Relative.Split('\') | Select-Object -SkipLast 1)) {
        $parent = Join-Path $parent $segment
        Assert-WorkflowPlainDirectory -Path $parent
    }
    $path = [IO.Path]::GetFullPath((Join-Path $ComfyRoot $entry.Relative))
    $actual = Get-WorkflowJunctionTarget -Path $path
    if ($actual -notin @($legacy, $curated)) {
        throw "Refusing a junction outside the exact legacy/curated target allowlist: $path -> $actual"
    }
    $plan += [ordered]@{ label = $entry.Label; path = $path; old_target = $actual;
                         new_target = $requestedTarget; change_required = ($actual -ne $requestedTarget) }
}
$result = [ordered]@{ mode = $Mode; apply = [bool]$Apply; repo_root = $RepoRoot; comfy_root = $ComfyRoot;
                     entries = $plan; preserved = @('all source workflows', 'experiments at original paths',
                     '.index.json and other user files', 'unsaved/browser state', 'running processes and queues') }
if (-not $Apply) {
    $result.status = 'read_only_plan_no_changes'
    $result | ConvertTo-Json -Depth 8
    return
}
if ($Mode -eq 'Curated') { $null = Initialize-ComfyWorkflowLibrary -RepoRoot $RepoRoot }
if (-not @($plan | Where-Object { $_.change_required }).Count) {
    $result.status = 'already_configured_no_live_changes'
    $result | ConvertTo-Json -Depth 8
    return
}
$transactionParent = Join-Path $RepoRoot 'local\workflow-visibility-transactions'
if (Test-Path -LiteralPath (Join-Path $RepoRoot 'local')) { Assert-WorkflowPlainDirectory -Path (Join-Path $RepoRoot 'local') }
if (Test-Path -LiteralPath $transactionParent) { Assert-WorkflowPlainDirectory -Path $transactionParent }
$transaction = Join-Path $transactionParent ((Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $transaction | Out-Null
$result.transaction_directory = $transaction
$result.status = 'prepared'
$manifest = Join-Path $transaction 'transaction.json'
function Save-VisibilityTransaction {
    [IO.File]::WriteAllText($manifest, ($result | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
}
Save-VisibilityTransaction
$moved = [System.Collections.Generic.List[object]]::new()
try {
    foreach ($entry in $plan) {
        if (-not $entry.change_required) { continue }
        # Revalidate immediately before moving the junction object. No recursive
        # move/delete is used; both absolute locations are explicit and validated.
        if ((Get-WorkflowJunctionTarget -Path $entry.path) -ne $entry.old_target) {
            throw "Live junction changed after preflight: $($entry.path)"
        }
        $backup = Join-Path $transaction ($entry.label + '-Mitch.original-junction')
        $entry.backup_junction = $backup
        Move-Item -LiteralPath $entry.path -Destination $backup -ErrorAction Stop
        $moved.Add($entry)
        Save-VisibilityTransaction
        New-Item -ItemType Junction -Path $entry.path -Target $entry.new_target -ErrorAction Stop | Out-Null
        if ((Get-WorkflowJunctionTarget -Path $entry.path) -ne $entry.new_target) { throw 'New junction verification failed.' }
        $entry.completed = $true
        Save-VisibilityTransaction
    }
    $result.status = 'applied_original_junctions_preserved'
    $result.rollback = "Run this script with -Mode $(if ($Mode -eq 'Curated') { 'Legacy' } else { 'Curated' }) -Apply using the same RepoRoot and ComfyRoot. Exact original junctions also remain in the transaction directory."
    Save-VisibilityTransaction
} catch {
    $originalFailure = $_.Exception.Message
    $rollbackErrors = [System.Collections.Generic.List[string]]::new()
    for ($index = $moved.Count - 1; $index -ge 0; $index--) {
        $entry = $moved[$index]
        try {
            if (Test-Path -LiteralPath $entry.path) {
                if ((Get-WorkflowJunctionTarget -Path $entry.path) -ne $entry.new_target) {
                    throw "Refuse to disturb concurrently changed path: $($entry.path)"
                }
                Move-Item -LiteralPath $entry.path -Destination (Join-Path $transaction ($entry.label + '-failed-new-junction')) -ErrorAction Stop
            }
            if ((Get-WorkflowJunctionTarget -Path $entry.backup_junction) -ne $entry.old_target) { throw 'Original junction backup changed.' }
            Move-Item -LiteralPath $entry.backup_junction -Destination $entry.path -ErrorAction Stop
            if ((Get-WorkflowJunctionTarget -Path $entry.path) -ne $entry.old_target) { throw 'Rollback target verification failed.' }
        } catch { $rollbackErrors.Add($_.Exception.Message) }
    }
    $result.status = if ($rollbackErrors.Count) { 'failed_rollback_needs_manual_attention' } else { 'failed_original_junctions_restored' }
    $result.error = $originalFailure
    $result.rollback_errors = @($rollbackErrors)
    Save-VisibilityTransaction
    throw "$originalFailure; transaction status: $($result.status); manifest: $manifest"
}
$result | ConvertTo-Json -Depth 10
