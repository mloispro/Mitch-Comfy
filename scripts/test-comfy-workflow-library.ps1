# Safe offline tests: all fake Comfy/user trees remain under repo/local.
# No live junctions, APIs, processes, queues, or source workflows are touched.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'comfy-workflow-library.ps1')
$projectRoot = Split-Path -Parent $PSScriptRoot
$testRoot = Join-Path $projectRoot ('local\workflow-visibility-tests\' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$switchScript = Join-Path $PSScriptRoot 'set-comfy-workflow-visibility.ps1'
$script:checks = 0

function Assert-Test {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
    $script:checks++
}

function New-TestFixture {
    param([string]$Name, [switch]$SecondaryRealFolder, [switch]$SecondaryForeignTarget)
    $base = Join-Path $testRoot $Name
    $repo = Join-Path $base 'repo'
    $comfy = Join-Path $base 'comfy'
    foreach ($relative in @('workflows\production', 'workflows\production-speed', 'workflows\experiments')) {
        New-Item -ItemType Directory -Path (Join-Path $repo $relative) -Force | Out-Null
    }
    foreach ($pair in @(@('production', 'prod.json'), @('production-speed', 'speed.json'), @('experiments', 'unfinished.json'))) {
        [IO.File]::WriteAllText((Join-Path $repo ('workflows\' + $pair[0] + '\' + $pair[1])), '{"nodes":[]}')
    }
    $sentinels = @((Join-Path $repo 'workflows\experiments\unfinished.json'))
    foreach ($relative in @('user\default\workflows', 'user-4070\default\workflows')) {
        $parent = Join-Path $comfy $relative
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
        foreach ($filename in @('.index.json', 'unsaved-user-copy.json')) {
            $path = Join-Path $parent $filename
            [IO.File]::WriteAllText($path, '{"preserve":"user content"}')
            $sentinels += $path
        }
        $entry = Join-Path $parent 'Mitch'
        if ($relative.StartsWith('user-4070') -and $SecondaryRealFolder) {
            New-Item -ItemType Directory -Path $entry | Out-Null
            $path = Join-Path $entry 'unique-user-workflow.json'
            [IO.File]::WriteAllText($path, '{"preserve":"real folder"}')
            $sentinels += $path
        } elseif ($relative.StartsWith('user-4070') -and $SecondaryForeignTarget) {
            $foreign = Join-Path $base 'foreign-workflows'
            New-Item -ItemType Directory -Path $foreign | Out-Null
            New-Item -ItemType Junction -Path $entry -Target $foreign | Out-Null
        } else {
            New-Item -ItemType Junction -Path $entry -Target (Join-Path $repo 'workflows') | Out-Null
        }
    }
    $hashes = @{}
    foreach ($path in $sentinels) { $hashes[$path] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash }
    return @{ Repo = $repo; Comfy = $comfy; Hashes = $hashes }
}

function Assert-SentinelsUnchanged {
    param($Fixture)
    foreach ($path in $Fixture.Hashes.Keys) {
        Assert-Test ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -eq $Fixture.Hashes[$path]) "User/experiment file changed: $path"
    }
}

$fixture = New-TestFixture -Name 'round-trip'
$plan = (& $switchScript -RepoRoot $fixture.Repo -ComfyRoot $fixture.Comfy | ConvertFrom-Json)
Assert-Test ($plan.status -eq 'read_only_plan_no_changes') 'Default must be read-only.'
Assert-Test (-not (Test-Path -LiteralPath (Join-Path $fixture.Repo 'local'))) 'Read-only plan wrote local state.'
$applied = (& $switchScript -RepoRoot $fixture.Repo -ComfyRoot $fixture.Comfy -Apply | ConvertFrom-Json)
Assert-Test ($applied.status -eq 'applied_original_junctions_preserved') 'Apply failed.'
Assert-ComfyWorkflowLibrary -RepoRoot $fixture.Repo
foreach ($entry in $applied.entries) {
    Assert-Test ((Get-WorkflowJunctionTarget -Path $entry.path) -eq (Get-ComfyWorkflowLibraryPath -RepoRoot $fixture.Repo)) 'Live fixture did not switch to curated.'
    Assert-Test ((Get-WorkflowJunctionTarget -Path $entry.backup_junction) -eq (Join-Path $fixture.Repo 'workflows')) 'Original junction backup not preserved.'
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $entry.path 'experiments'))) 'Experiments remain exposed.'
    Assert-Test (Test-Path -LiteralPath (Join-Path $entry.path 'production\prod.json')) 'Production source disappeared.'
    Assert-Test (Test-Path -LiteralPath (Join-Path $entry.path 'production-speed\speed.json')) 'Production Speed source disappeared.'
}
Assert-SentinelsUnchanged -Fixture $fixture
$again = (& $switchScript -RepoRoot $fixture.Repo -ComfyRoot $fixture.Comfy -Apply | ConvertFrom-Json)
Assert-Test ($again.status -eq 'already_configured_no_live_changes') 'Apply must be idempotent.'
$reversed = (& $switchScript -RepoRoot $fixture.Repo -ComfyRoot $fixture.Comfy -Mode Legacy -Apply | ConvertFrom-Json)
Assert-Test ($reversed.status -eq 'applied_original_junctions_preserved') 'Explicit rollback failed.'
foreach ($entry in $reversed.entries) {
    Assert-Test ((Get-WorkflowJunctionTarget -Path $entry.path) -eq (Join-Path $fixture.Repo 'workflows')) 'Rollback did not restore legacy target.'
}
Assert-SentinelsUnchanged -Fixture $fixture

foreach ($case in @('real-folder', 'foreign-junction')) {
    $bad = if ($case -eq 'real-folder') { New-TestFixture -Name $case -SecondaryRealFolder } else { New-TestFixture -Name $case -SecondaryForeignTarget }
    $rejected = $false
    try { $null = & $switchScript -RepoRoot $bad.Repo -ComfyRoot $bad.Comfy -Apply } catch { $rejected = $true }
    Assert-Test $rejected "Unsafe $case must be rejected."
    Assert-Test ((Get-WorkflowJunctionTarget -Path (Join-Path $bad.Comfy 'user\default\workflows\Mitch')) -eq (Join-Path $bad.Repo 'workflows')) 'Preflight failure changed the first junction.'
    Assert-SentinelsUnchanged -Fixture $bad
}
$unknown = New-TestFixture -Name 'unknown-library-content'
$library = Initialize-ComfyWorkflowLibrary -RepoRoot $unknown.Repo
$unrelated = Join-Path $library 'user-file.json'
[IO.File]::WriteAllText($unrelated, '{"preserve":true}')
$rejected = $false
try { $null = Initialize-ComfyWorkflowLibrary -RepoRoot $unknown.Repo } catch { $rejected = $true }
Assert-Test $rejected 'Unknown library content must not be silently removed.'
Assert-Test (Test-Path -LiteralPath $unrelated) 'Unknown library content was removed.'

foreach ($name in @('comfy-workflow-library.ps1', 'set-comfy-workflow-visibility.ps1', 'setup-links.ps1',
                     'verify.ps1', 'start-comfy-4070.ps1', 'start-dual-comfy.ps1', 'test-comfy-workflow-library.ps1')) {
    $parseErrors = $null; $tokens = $null
    $null = [Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name), [ref]$tokens, [ref]$parseErrors)
    Assert-Test (@($parseErrors).Count -eq 0) "PowerShell syntax error in $name"
}
Write-Output "$script:checks workflow visibility checks passed. Preserved offline fixtures: $testRoot"
