function Add-UpgradeIdentitySchedule {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][System.Collections.IDictionary]$Graph,
        [Parameter(Mandatory)][int]$SplitStep,
        [Parameter(Mandatory)][double]$LateStrength
    )
    # Continue the SAME Euler trajectory. Output0 carries residual noise;
    # output1 is a denoised preview and must never initialize the continuation.
    if ($SplitStep -lt 1 -or $SplitStep -ge 50 -or
        [double]::IsNaN($LateStrength) -or [double]::IsInfinity($LateStrength) -or
        $LateStrength -lt 0 -or $LateStrength -gt 1.5) { throw 'Invalid identity schedule.' }
    if ($Graph['23'].inputs.steps -ne 50 -or $Graph['22'].inputs.sampler_name -ne 'euler' -or
        $Graph['21'].inputs.cfg -ne 4 -or $Graph['25'].class_type -ne 'SamplerCustomAdvanced' -or
        $Graph['2'].class_type -ne 'LoraLoaderModelOnly' -or $Graph['3'].class_type -ne 'LoraLoaderModelOnly') {
        throw 'Identity scheduling requires the validated 50-step Euler/CFG4 Klein graph.'
    }
    foreach ($Id in '30','31','32','33','34','35') {
        if ($Graph.Contains($Id)) { throw "Schedule node collision: $Id" }
    }
    $Graph['30']=@{class_type='SplitSigmas';inputs=@{sigmas=@('23',0);step=$SplitStep}}
    $Graph['31']=@{class_type='LoraLoaderModelOnly';inputs=@{model=@('1',0);lora_name=$Graph['2'].inputs.lora_name;strength_model=$LateStrength}}
    $Graph['32']=@{class_type='LoraLoaderModelOnly';inputs=@{model=@('31',0);lora_name=$Graph['3'].inputs.lora_name;strength_model=$Graph['3'].inputs.strength_model}}
    $Graph['33']=@{class_type='CFGGuider';inputs=@{model=@('32',0);positive=$Graph['21'].inputs.positive.Clone();negative=$Graph['21'].inputs.negative.Clone();cfg=$Graph['21'].inputs.cfg}}
    $Graph['34']=@{class_type='DisableNoise';inputs=@{}}
    $Graph['35']=@{class_type='SamplerCustomAdvanced';inputs=@{noise=@('34',0);guider=@('33',0);sampler=@('22',0);sigmas=@('30',1);latent_image=@('25',0)}}
    $Graph['25'].inputs.sigmas=@('30',0)
    $Graph['26'].inputs.samples=@('35',0)
    return [ordered]@{
        mechanism='single Euler trajectory; full noisy latent continuation, no new noise or intermediate VAE'
        split_step=$SplitStep
        total_steps=50
        early_identity_strength=$Graph['2'].inputs.strength_model
        late_identity_strength=$LateStrength
        phone_strength_both_segments=$Graph['3'].inputs.strength_model
        reference_and_text_conditioning='identical in both segments'
        constant_strength_control=($LateStrength -eq $Graph['2'].inputs.strength_model)
    }
}
