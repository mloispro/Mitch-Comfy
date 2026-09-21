$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'upgrade-whole-frame-dimensions.ps1')
foreach ($case in @(@(1024,1024,1024,1024),@(1680,1008,1360,816),@(816,1088,864,1152))) {
    $actual=Get-UpgradeWholeFrameDimensions $case[0] $case[1]
    if ($actual[0] -ne $case[2] -or $actual[1] -ne $case[3]) { throw 'Unexpected output dimensions.' }
    if ($actual[0]*$case[1] -ne $actual[1]*$case[0]) { throw 'Aspect ratio changed.' }
    if ($actual[0]%16 -or $actual[1]%16) { throw 'Dimensions not divisible by16.' }
}
foreach ($case in @(@(0,1024),@(1024,1001))) {
    $rejected=$false
    try { $null=Get-UpgradeWholeFrameDimensions $case[0] $case[1] } catch { $rejected=$true }
    if (-not $rejected) { throw 'Unsupported dimensions must fail closed.' }
}
Write-Output 'Five whole-frame dimension tests passed.'
