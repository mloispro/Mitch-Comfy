"""Pixel-aligned Qwen codec diagnostic; never a beauty acceptance test."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image, ImageDraw, ImageFont, ImageOps


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','matched-input','roundtrip','high-audit','output-dir'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--additional-high-audit',type=Path,action='append',default=[],
                        help='Optional same-recipe step-count comparison, with verified native audit.')
    parser.add_argument('--comparison-mode',choices=('steps','reference-packing'),default='steps')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(root):
        raise ValueError('Use a new project evaluation directory.')
    def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    manifest=json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    high=json.loads(args.high_audit.read_text(encoding='utf-8-sig'))
    if manifest['stage']!='qwen_vae_diagnostic' or manifest['generation_steps']!=0:
        raise ValueError('Expected zero-diffusion codec test.')
    expected={'LoadImage','ImageScale','VAELoader','VAEEncode','VAEDecode','SaveImage'}
    if {n['class_type'] for n in manifest['prompt'].values()}!=expected:
        raise ValueError('Unexpected stage in codec graph.')
    if digest(Path(manifest['reference_manifest']))!=manifest['reference_manifest_sha256']:
        raise ValueError('Parent experiment changed.')
    if not high['executed_png_graph_verified'] or high['inputs']['BASE RAW']['sha256']!=manifest['source']['sha256']:
        raise ValueError('High audit does not use this same baseline.')
    paths={'RESIZED BASE':args.matched_input,'VAE ONLY':args.roundtrip}
    comparison_graph=None;comparison_hashes=None;comparison_models=None
    if args.comparison_mode=='reference-packing' and len(args.additional_high_audit)!=1:
        raise ValueError('Packing comparison requires exactly one native parent and one aligned candidate.')
    for audit_index,audit_path in enumerate([args.high_audit,*args.additional_high_audit]):
        audited=json.loads(audit_path.read_text(encoding='utf-8-sig'))
        if (not audited['executed_png_graph_verified'] or audited['postprocess_applied']
                or audited['inputs']['BASE RAW']['sha256']!=manifest['source']['sha256']
                or audited['genuine_references']!=high['genuine_references']):
            raise ValueError('Step comparison must use the same raw and genuine scoring references, without finishing.')
        native=json.loads((root/Path(audited['manifest'])).read_text(encoding='utf-8-sig'))
        if native['stage']!='qwen_native_high_edit': raise ValueError('Expected native Qwen stage.')
        path=root/audited['inputs']['CANDIDATE HIGH']['path']
        if digest(path)!=audited['inputs']['CANDIDATE HIGH']['sha256']:
            raise ValueError('High image changed.')
        with Image.open(path) as opened:
            executed=json.loads(opened.info['prompt'])
        hashes={ref['name']:ref['sha256'].lower() for ref in native['references']}
        if comparison_hashes is not None and (hashes!=comparison_hashes or native['verified_models']!=comparison_models):
            raise ValueError('Comparison changed reference/model hashes.')
        comparison_hashes=hashes;comparison_models=native['verified_models']
        for node in executed.values():
            if node['class_type']=='LoadImage' and 'is_changed' in node:
                if node.pop('is_changed')!=[hashes[node['inputs']['image']]]:
                    raise ValueError('Executed reference hash changed.')
        if executed!=native['prompt']: raise ValueError('Executed High graph changed.')
        normalized=copy.deepcopy(executed)
        steps=normalized['169']['inputs']['steps']
        normalized['9']['inputs'].pop('filename_prefix')
        if args.comparison_mode=='reference-packing':
            from upgrade_qwen_reference_acceptance import validate_reference_layout
            layout=validate_reference_layout(native)
            packing=native.get('reference_packing','native')
            expected_packing='native' if audit_index==0 else 'author32_explicit_native_latents'
            if packing!=expected_packing: raise ValueError('Packing comparison order must be native then aligned.')
            if audit_index:
                for index in range(layout['reference_count']):
                    for node_id in range(190+4*index,194+4*index): del normalized[str(node_id)]
                for node_id in ('151','149'): normalized[node_id]['inputs']['vae']=['146',0]
                normalized['148']['inputs']['conditioning']=['151',0]
                normalized['147']['inputs']['conditioning']=['149',0]
            label=f'{steps}-STEP '+('NATIVE' if audit_index==0 else 'ALIGNED')
        else:
            normalized['169']['inputs'].pop('steps')
            label=f'{steps}-STEP HIGH'
        if comparison_graph is not None and normalized!=comparison_graph:
            raise ValueError('Comparison changed more than the declared variable and output filename.')
        comparison_graph=normalized
        if label in paths: raise ValueError('Duplicate step-count label.')
        paths[label]=path
    photos={}
    for label,path in paths.items():
        with Image.open(path) as opened:
            if label in ('RESIZED BASE','VAE ONLY'):
                graph=json.loads(opened.info['prompt'])
                for node in graph.values():
                    if node['class_type']=='LoadImage' and 'is_changed' in node:
                        if node.pop('is_changed')!=[manifest['source']['sha256']]:
                            raise ValueError('Executed source hash differs.')
                if graph!=manifest['prompt']: raise ValueError('Executed codec graph differs.')
            photos[label]=np.array(ImageOps.exif_transpose(opened).convert('RGB'))
    if len({p.shape for p in photos.values()})!=1: raise ValueError('Pixel-aligned dimensions required.')
    analyzer=FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),
                         providers=['CPUExecutionProvider'],allowed_modules=['detection','recognition'])
    analyzer.prepare(ctx_id=-1,det_size=(640,640))
    def face(rgb):
        detected=analyzer.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if len(detected)!=1: raise ValueError('Exactly one face required.')
        return detected[0]
    if len(high['genuine_references'])<2: raise ValueError('Need independent genuine scoring references.')
    embeddings=[]
    for record in high['genuine_references']:
        path=root/record['path']
        if digest(path)!=record['sha256']: raise ValueError('Genuine scoring photo changed.')
        with Image.open(path) as opened:
            embeddings.append(face(np.array(ImageOps.exif_transpose(opened).convert('RGB'))).normed_embedding)
    centroid=np.mean(embeddings,axis=0);centroid/=np.linalg.norm(centroid)
    faces={label:face(rgb) for label,rgb in photos.items()}
    delta=photos['VAE ONLY'].astype(np.float32)-photos['RESIZED BASE'].astype(np.float32)
    results={}
    for label,rgb in photos.items():
        row_step=np.abs(np.diff(rgb.astype(np.float32),axis=0)).mean(axis=(1,2))
        results[label]={'identity_centroid':float(faces[label].normed_embedding@centroid),
            'bottom_24_max_mean_row_step_8bit':float(row_step[-24:].max()),
            'bottom_24_max_step_row':int(len(row_step)-24+np.argmax(row_step[-24:]))}
    audit={'status':'diagnostic_only','executed_codec_graph_verified':True,
           'step_count_only_comparison_verified':bool(args.additional_high_audit) and args.comparison_mode=='steps',
           'reference_packing_only_comparison_verified':args.comparison_mode=='reference-packing',
           'inputs':{k:{'path':str(p),'sha256':digest(p)} for k,p in paths.items()},
           'genuine_references':high['genuine_references'],'results':results,
           'codec_mae_8bit':float(np.abs(delta).mean()),'codec_psnr_db':float(10*np.log10(255**2/max(float(np.square(delta).mean()),1e-12))),
           'limitation':'Reconstruction/row-discontinuity diagnostics, not proof of attractiveness, pore realism or the cause of a generation artifact.'}
    args.output_dir.mkdir(parents=True)
    tiles=[]
    for label,rgb in photos.items():
        box=faces[label].bbox;margin=(box[2]-box[0])*.12
        tile=Image.fromarray(rgb).crop(tuple((box+[-margin,-margin,margin,margin]).astype(int)))
        tiles.append((label,tile.resize((round(tile.width*420/tile.height),420),Image.Resampling.LANCZOS)))
    for filename,panels in (('face-comparison.jpg',tiles),('bottom-edge-comparison.jpg',[(k,Image.fromarray(v[-96:])) for k,v in photos.items()])):
        sheet=Image.new('RGB',(sum(t.width for _,t in panels),max(t.height for _,t in panels)+40),(22,22,22))
        draw=ImageDraw.Draw(sheet);font=ImageFont.load_default(size=18);left=0
        for label,tile in panels:
            sheet.paste(tile,(left,40));draw.text((left+10,10),label,font=font,fill='white');left+=tile.width
        sheet.save(args.output_dir/filename,quality=96)
    (args.output_dir/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in audit.items() if k not in ('inputs','genuine_references')},indent=2))


if __name__=='__main__': main()
