"""Fetch only official human core weights, pinned and SHA256-verified; no photo input."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download


def main():
    root=Path(__file__).resolve().parents[1]
    destination=root/'work/vendor/LivePortrait-code/pretrained_weights'
    names=[f'liveportrait/base_models/{name}.pth' for name in (
        'appearance_feature_extractor','motion_extractor','warping_module','spade_generator')]
    names.append('liveportrait/retargeting_models/stitching_retargeting_module.pth')
    api=HfApi(token=False)
    info=api.model_info('KlingTeam/LivePortrait',files_metadata=True)
    records={item.rfilename:item for item in info.siblings}
    manifest={'repository':'KlingTeam/LivePortrait','revision':info.sha,'files':[],'photos_uploaded':False}
    for name in names:
        item=records[name]
        expected=item.lfs.sha256
        print(f'Downloading verified human model: {name} ({item.size} bytes)',flush=True)
        path=Path(hf_hub_download('KlingTeam/LivePortrait',filename=name,revision=info.sha,
                                  local_dir=destination,token=False))
        with path.open('rb') as handle:
            digest=hashlib.sha256()
            for block in iter(lambda:handle.read(4*1024*1024),b''):
                digest.update(block)
            actual=digest.hexdigest()
        if actual!=expected:
            raise RuntimeError(f'Checkpoint hash mismatch: {name}')
        manifest['files'].append({'name':name,'path':str(path),'sha256':actual,'size':item.size})
    (destination/'verified-human-control.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    main()
