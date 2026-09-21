"""Read-only protected-latent diagnostic, independent of the global VAE decoder."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from safetensors import safe_open
import torch
import torch.nn.functional as F

from upgrade_background_detail import validate_graph

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run','source-latent','sampled-latent','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or not args.output.resolve().is_relative_to(ROOT/'work'):
        raise ValueError('Use a fresh project audit file.')
    manifest=json.loads((args.run/'experiment.json').read_text(encoding='utf-8-sig'))
    validate_graph(manifest)
    if len(manifest['references'])!=4:
        raise ValueError('This diagnostic requires the refinement with explicit latent outputs.')
    refs={r['name']:r for r in manifest['references']}
    for ref in refs.values():
        if sha(ref['path'])!=ref['sha256']:raise ValueError('Recorded reference changed.')
    tensors=[];dtypes=[]
    for path in (args.source_latent,args.sampled_latent):
        with safe_open(str(path),framework='pt',device='cpu') as file:
            if set(file.keys())!={'latent_tensor','latent_format_version_0'}:
                raise ValueError('Unexpected saved latent representation.')
            graph=json.loads(file.metadata()['prompt'])
            for node in graph.values():
                if node['class_type']=='LoadImage':
                    if node.pop('is_changed',None)!=[refs[node['inputs']['image']]['sha256']]:
                        raise ValueError('Latent executed image hash differs.')
            if graph!=manifest['prompt']:raise ValueError('Latent graph differs from the frozen run.')
            value=file.get_tensor('latent_tensor');dtypes.append(str(value.dtype));tensors.append(value.float())
    source,sampled=tensors
    if source.shape!=sampled.shape or source.ndim!=4 or source.shape[0]!=1:
        raise ValueError('Expected matching full-frame, single-image latents.')
    if not torch.isfinite(source).all() or not torch.isfinite(sampled).all():
        raise ValueError('Nonfinite latent values.')
    with Image.open(manifest['references'][2]['path']) as image:
        mask=np.asarray(image.convert('L')).copy()
    # Match installed comfy.utils.reshape_mask for this2D, batch1 case.
    mapped=F.interpolate(torch.from_numpy(mask.astype(np.float32)/255)[None,None],
                         size=source.shape[-2:],mode='bilinear')[0,0]
    distance=cv2.distanceTransform((mask==0).astype(np.uint8),cv2.DIST_L2,5)
    core=F.interpolate(torch.from_numpy((distance>64).astype(np.float32))[None,None],
                       size=source.shape[-2:],mode='bilinear')[0,0]==1
    error=(sampled-source).abs()[0].permute(1,2,0)
    def stats(where):
        values=error[where]
        if values.numel()==0:raise ValueError('Empty latent diagnostic region.')
        return {'spatial_cells':int(where.sum()),'mean_abs_error':float(values.mean()),
                'max_abs_error':float(values.max()),'p99_abs_error':float(torch.quantile(values.flatten(),.99)),
                'exact_channel_vector_fraction':float((values==0).all(dim=-1).float().mean()),
                'channel_vector_within_1e_5_fraction':float((values<=1e-5).all(dim=-1).float().mean())}
    report={'status':'measured_not_a_pixel_preservation_guarantee','manifest_sha256':sha(args.run/'experiment.json'),
            'source_latent_sha256':sha(args.source_latent),'sampled_latent_sha256':sha(args.sampled_latent),
            'executed_graphs_verified':True,'shape':list(source.shape),'saved_dtypes':dtypes,
            'mask_resize':'installed2D bilinear interpolation, align_corners default false; repeated channels',
            'all_black_mask_cells':stats(mapped==0),'person_core_64px':stats(core & (mapped==0)),
            'fully_editable_background_cells':stats(mapped==1),
            'interpretation':'Small protected latent differences can be solver/format rounding. Compare with the independent codec/RGB audit. Preserved latent values do not imply invariant RGB after spatially coupled VAE decoding.'}
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
