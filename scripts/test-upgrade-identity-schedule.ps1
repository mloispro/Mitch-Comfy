$ErrorActionPreference='Stop'
. "$PSScriptRoot/upgrade-identity-schedule.ps1"
function New-TestGraph {
    return [ordered]@{
        '1'=@{class_type='UNETLoader';inputs=@{}}
        '2'=@{class_type='LoraLoaderModelOnly';inputs=@{lora_name='identity';strength_model=0.9}}
        '3'=@{class_type='LoraLoaderModelOnly';inputs=@{lora_name='phone';strength_model=0.25}}
        '21'=@{class_type='CFGGuider';inputs=@{positive=@('133',0);negative=@('134',0);cfg=4}}
        '22'=@{class_type='KSamplerSelect';inputs=@{sampler_name='euler'}}
        '23'=@{class_type='Flux2Scheduler';inputs=@{steps=50}}
        '25'=@{class_type='SamplerCustomAdvanced';inputs=@{sigmas=@('23',0);noise=@('20',0);latent_image=@('24',0)}}
        '26'=@{class_type='VAEDecode';inputs=@{samples=@('25',0)}}
    }
}
foreach ($Late in 0.0,0.9) {
    $Graph=New-TestGraph
    $Report=Add-UpgradeIdentitySchedule -Graph $Graph -SplitStep 35 -LateStrength $Late
    if ($Graph['35'].inputs.latent_image[0] -ne '25' -or $Graph['35'].inputs.latent_image[1] -ne 0 -or
        $Graph['34'].class_type -ne 'DisableNoise' -or $Graph['35'].inputs.noise[0] -ne '34' -or
        $Graph['25'].inputs.sigmas[0] -ne '30' -or $Graph['25'].inputs.sigmas[1] -ne 0 -or
        $Graph['35'].inputs.sigmas[0] -ne '30' -or $Graph['35'].inputs.sigmas[1] -ne 1 -or
        $Graph['33'].inputs.positive[0] -ne '133' -or $Graph['33'].inputs.negative[0] -ne '134' -or
        $Graph['31'].inputs.strength_model -ne $Late -or $Graph['32'].inputs.strength_model -ne 0.25 -or
        $Report.constant_strength_control -ne ($Late -eq 0.9)) { throw 'Schedule topology/control failed.' }
}
foreach ($Case in @(@(0,0.0),@(50,0.0),@(35,-0.1),@(35,[double]::NaN),@(35,1.6))) {
    $Rejected=$false
    try { $null=Add-UpgradeIdentitySchedule -Graph (New-TestGraph) -SplitStep $Case[0] -LateStrength $Case[1] } catch { $Rejected=$true }
    if (-not $Rejected) { throw 'Invalid schedule accepted.' }
}
$Graph=New-TestGraph
$Graph['22'].inputs.sampler_name='dpmpp_2m'
$Rejected=$false
try { $null=Add-UpgradeIdentitySchedule -Graph $Graph -SplitStep 35 -LateStrength 0 } catch { $Rejected=$true }
if (-not $Rejected) { throw 'Stateful sampler accepted.' }
Write-Output 'PASS: constant/change topology, residual-noise output, unchanged conditioning/phone, bounds and Euler-only guard.'
