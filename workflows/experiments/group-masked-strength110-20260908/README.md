# One controlled Group strength refinement

CPU-prepared experiment only. The old failed-quality pilot remains intact. The only graph changes are node50 character-hook strength0.90→1.10 and the new save prefix; no identity success is predicted as proven. See RESEARCH-AND-ACCEPTANCE.md.

One consolidated run_recipe.ps1 facade and recipe_runtime.py bind the pinned native guard, final heartbeat observer and existing lifecycle helpers directly. No new wrapper chain or production installation. wddm_admission.py and wddm-lifetimes.ps1 retain exact22 desktop lifetime checks against frozen evidence, but require a fresh capture and approval. Every actual graph check uses the new payload; historical masks, source, schedule and score references stay at their immutable original paths.

Fixed3090 UUID GPU-c2ca4516-2c9f-e87b-3a20-f459947ddb17, port8191, new worker/user/database/output. LegacyFP8/cache-none/MaxSpeed/reserve5.2 unchanged. Admission41GiB host+commit, nativeUNET40/40, sampler30/28, initial/effective20GiB targetfree, watch12/10 and5-second freshness remain unchanged. Cooperative monitoring cannot guarantee prevention of every allocation race. No auto-retry, free, threshold relaxation or foreign-job action.

CPU commands (from this folder):
```powershell
.\run_recipe.ps1 -Action verify
.\test-recipe.ps1
$env:CUDA_VISIBLE_DEVICES=''
$env:HF_HUB_OFFLINE='1'
$env:TORCH_COMPILE_DISABLE='1'
& 'C:/projects/AI-Tools/ComfyUI/.venv/Scripts/python.exe' -X utf8 -B -m unittest -v test_recipe.py test_wddm.py
```

Root-only execution after review and fresh resource checks:
1. Run `run_recipe.ps1 -Action capture`; inspect new wddm-candidate-v2.json. Fill a new wddm-root-approval-v2.json using the separate false template. No old approval is reusable.
2. Fill root-approval.json using the false template: current issued/expires, both prepared fields equal this prepared.json SHA, recipeSHA and exact worker path. Set approved only after review.
3. Run `run_recipe.ps1 -Action start -ExclusiveWindowAccepted`.
4. Bind actual worker/owned.json SHA in the root approval before `run_recipe.ps1 -Action run -ExclusiveWindowAccepted`.
5. Preserve all output/failure evidence. After terminal, `run_recipe.ps1 -Action stop -ExclusiveWindowAccepted` stops only this exact owned lifetime. An interrupted run is not permission to submit another.
6. Root and independent native/thumbnail visual reviews precede explicit CPU scoring. The separate evaluator manifest owns evaluate_recipe.py; runtime preparation deliberately excludes evaluator files to avoid a circular freeze.

Internal case and run stay `pilot`/`runs/ready-amber-hook-pilot` only within this NEW package. Expected native image is worker/output/group-masked-strength110-20260908/group-amber-hook-s110-seed8675412_00001_.png. The graph prefix is not an extra treatment. No worker, capture, live approval, run or image is created by preparation.
