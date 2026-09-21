# Curated ComfyUI exposure. Source workflows remain at their original paths.
# Dot-source this helper; importing it does not create or replace any paths.

function Get-ComfyWorkflowLibraryPath {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    return [IO.Path]::GetFullPath((Join-Path $RepoRoot 'local\comfy-workflow-library'))
}

function Get-ComfyWorkflowLibrarySources {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    return [ordered]@{
        'production' = [IO.Path]::GetFullPath((Join-Path $RepoRoot 'workflows\production'))
        'production-speed' = [IO.Path]::GetFullPath((Join-Path $RepoRoot 'workflows\production-speed'))
    }
}

function Assert-WorkflowPlainDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Expected an ordinary directory, not a file/link: $Path"
    }
}

function Get-WorkflowJunctionTarget {
    param([Parameter(Mandatory = $true)][string]$Path)
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($item.LinkType -ne 'Junction' -or -not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Refusing to replace a real directory, file, or non-junction link: $Path"
    }
    $targets = @($item.Target)
    if ($targets.Count -ne 1 -or -not $targets[0]) { throw "Junction has no single target: $Path" }
    return (Resolve-Path -LiteralPath $targets[0] -ErrorAction Stop).Path.TrimEnd('\')
}

function Assert-ComfyWorkflowLibrarySources {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    Assert-WorkflowPlainDirectory -Path $RepoRoot
    Assert-WorkflowPlainDirectory -Path (Join-Path $RepoRoot 'workflows')
    foreach ($source in (Get-ComfyWorkflowLibrarySources -RepoRoot $RepoRoot).Values) {
        Assert-WorkflowPlainDirectory -Path $source
        # Do not expose an unexpected nested junction to experiments or elsewhere.
        $nestedLinks = @(Get-ChildItem -LiteralPath $source -Force -Recurse |
            Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint })
        if ($nestedLinks.Count) { throw "Curated source contains an unexpected nested link: $($nestedLinks[0].FullName)" }
    }
}

function Assert-ComfyWorkflowLibrary {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    Assert-ComfyWorkflowLibrarySources -RepoRoot $RepoRoot
    $library = Get-ComfyWorkflowLibraryPath -RepoRoot $RepoRoot
    Assert-WorkflowPlainDirectory -Path (Join-Path $RepoRoot 'local')
    Assert-WorkflowPlainDirectory -Path $library
    $sources = Get-ComfyWorkflowLibrarySources -RepoRoot $RepoRoot
    $children = @(Get-ChildItem -LiteralPath $library -Force)
    if ($children.Count -ne $sources.Count -or @($children | Where-Object { $_.Name -notin $sources.Keys }).Count) {
        throw "Curated library must contain only production and production-speed; unknown content is preserved: $library"
    }
    foreach ($name in $sources.Keys) {
        $target = Get-WorkflowJunctionTarget -Path (Join-Path $library $name)
        if ($target -ne (Resolve-Path -LiteralPath $sources[$name]).Path.TrimEnd('\')) {
            throw "Wrong curated workflow target: $name -> $target"
        }
    }
}

function Initialize-ComfyWorkflowLibrary {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    Assert-ComfyWorkflowLibrarySources -RepoRoot $RepoRoot
    $library = Get-ComfyWorkflowLibraryPath -RepoRoot $RepoRoot
    $localRoot = Join-Path $RepoRoot 'local'
    $sources = Get-ComfyWorkflowLibrarySources -RepoRoot $RepoRoot
    if (Test-Path -LiteralPath $localRoot) { Assert-WorkflowPlainDirectory -Path $localRoot }
    if (Test-Path -LiteralPath $library) {
        Assert-WorkflowPlainDirectory -Path $library
        foreach ($item in @(Get-ChildItem -LiteralPath $library -Force)) {
            if ($item.Name -notin $sources.Keys) { throw "Unknown library content preserved; review manually: $($item.FullName)" }
            $target = Get-WorkflowJunctionTarget -Path $item.FullName
            if ($target -ne (Resolve-Path -LiteralPath $sources[$item.Name]).Path.TrimEnd('\')) {
                throw "Non-matching library link preserved: $($item.FullName) -> $target"
            }
        }
    }
    # Only create missing paths. Never remove, overwrite, or synchronize user files.
    New-Item -ItemType Directory -Path $library -Force | Out-Null
    foreach ($name in $sources.Keys) {
        $entry = Join-Path $library $name
        if (-not (Test-Path -LiteralPath $entry)) {
            New-Item -ItemType Junction -Path $entry -Target $sources[$name] | Out-Null
        }
    }
    Assert-ComfyWorkflowLibrary -RepoRoot $RepoRoot
    return $library
}

function Ensure-ComfyWorkflowEntry {
    param([Parameter(Mandatory = $true)][string]$Path,
          [Parameter(Mandatory = $true)][string]$LibraryRoot)
    $expected = (Resolve-Path -LiteralPath $LibraryRoot -ErrorAction Stop).Path.TrimEnd('\')
    if (Test-Path -LiteralPath $Path) {
        $actual = Get-WorkflowJunctionTarget -Path $Path
        if ($actual -ne $expected) {
            throw "Workflow junction still points to '$actual'. Run scripts/set-comfy-workflow-visibility.ps1 -Apply explicitly; no existing paths were replaced."
        }
    } else {
        New-Item -ItemType Directory -Path (Split-Path -Parent $Path) -Force | Out-Null
        New-Item -ItemType Junction -Path $Path -Target $expected | Out-Null
    }
}
