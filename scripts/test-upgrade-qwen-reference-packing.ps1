$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'upgrade-qwen-reference-packing.ps1')
$cases=@(
    @{input=@(1680,1008);expected=@(1312,800)},
    @{input=@(1360,816);expected=@(1312,800)},
    @{input=@(2544,3392);expected=@(896,1184)},
    @{input=@(1024,1024);expected=@(1024,1024)}
)
foreach($case in $cases) {
    $actual=Get-UpgradeQwenAlignedDimensions $case.input[0] $case.input[1]
    if(($actual -join ',') -ne ($case.expected -join ',')) { throw 'Author32 dimensions mismatch.' }
    $latent=@(($actual[0]/8),($actual[1]/8))
    if($latent.Count -ne 2 -or $latent[0]%2 -or $latent[1]%2) { throw 'Unexpected wrapped latent edge.' }
}
$rejected=$false
try { Get-UpgradeQwenAlignedDimensions 0 816 } catch { $rejected=$true }
if(-not $rejected) { throw 'Invalid dimensions were accepted.' }
'Five author32 dimension checks passed.'
