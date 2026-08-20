param(
    [Parameter(Mandatory = $true)][string]$Message,
    [string]$Tag = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

& (Join-Path $PSScriptRoot "verify.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "Verification failed; checkpoint was not created."
}

git -C $RepoRoot add --all
git -C $RepoRoot diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "No changes to checkpoint."
    exit 0
}

git -C $RepoRoot commit -m $Message
if ($LASTEXITCODE -ne 0) {
    throw "Git commit failed."
}

if ($Tag) {
    git -C $RepoRoot tag -a $Tag -m $Message
    if ($LASTEXITCODE -ne 0) {
        throw "Git tag failed."
    }
}

git -C $RepoRoot status --short
