"""Read-only A/B presentation from evaluated seed or weight-dtype probes."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont,ImageOps
from upgrade_seed_probe import changed_inputs

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control-audit',type=Path,required=True)
    parser.add_argument('--probe-audit',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'work'):raise ValueError('Use a new work directory.')
    control,probe=read(args.control_audit),read(args.probe_audit)
    for audit in (control,probe):
        if not audit['executed_png_graph_verified'] or audit['postprocess_applied']:
            raise ValueError('Expected evaluated native pixels.')
        for record in list(audit['inputs'].values())+audit['genuine_references']:
            if sha(ROOT/record['path'])!=record['sha256'].lower():raise ValueError('Audited pixels changed.')
    if control['genuine_references']!=probe['genuine_references']:
        raise ValueError('Scoring references differ.')
    for key in ('SOURCE','BASE RAW','LOW'):
        if control['inputs'][key]['sha256']!=probe['inputs'][key]['sha256']:
            raise ValueError('Comparison inputs differ: '+key)
    original_manifest=ROOT/control['manifest'];candidate_manifest=ROOT/probe['manifest']
    original,test=read(original_manifest),read(candidate_manifest)
    if sha(original_manifest)!=test['control_manifest_sha256'] or sha(args.control_audit)!=test['control_audit_sha256']:
        raise ValueError('Probe control provenance differs.')
    changes=changed_inputs(original['prompt'],test['prompt'])
    if test.get('probe_kind','seed')=='seed':
        if changes!=['20.noise_seed','27.filename_prefix'] or test['seed']!=original['seed']+1:
            raise ValueError('Not the frozen next-seed probe.')
        labels=('NATIVE HIGH - SEED '+str(original['seed']),'NATIVE HIGH - SEED '+str(test['seed']))
    elif test['probe_kind']=='weight-dtype':
        if (changes!=['1.weight_dtype','27.filename_prefix'] or test['seed']!=original['seed']
            or original['prompt']['1']['inputs']['weight_dtype']!='fp8_e4m3fn'
            or test['prompt']['1']['inputs']['weight_dtype']!='default'):
            raise ValueError('Not the frozen weight-dtype probe.')
        labels=('NATIVE HIGH - FP8 WEIGHTS','NATIVE HIGH - DEFAULT DTYPE')
    else:raise ValueError('Unknown bounded probe kind.')
    entries=[('SOURCE',control,'SOURCE'),('PRODUCTION LOW',control,'LOW'),
             (labels[0],control,'CANDIDATE HIGH'),(labels[1],probe,'CANDIDATE HIGH')]
    out.mkdir(parents=True)
    for kind in ('face','thumbnail'):
        tiles=[]
        for label,audit,key in entries:
            with Image.open(ROOT/audit['inputs'][key]['path']) as im:
                tile=ImageOps.exif_transpose(im).convert('RGB')
            if kind=='face':
                x0,y0,x1,y1=audit['results'][key]['bbox_xyxy'];margin=(x1-x0)*.12
                tile=tile.crop((max(0,int(x0-margin)),max(0,int(y0-margin)),min(tile.width,int(x1+margin)),min(tile.height,int(y1+margin))))
                tile=tile.resize((round(tile.width*480/tile.height),480),Image.Resampling.LANCZOS)
            else:tile.thumbnail((390,500),Image.Resampling.LANCZOS)
            tiles.append((label,tile))
        sheet=Image.new('RGB',(sum(im.width for _,im in tiles),max(im.height for _,im in tiles)+58),(20,20,20))
        draw=ImageDraw.Draw(sheet);font=ImageFont.load_default(size=15);x=0
        for label,tile in tiles:
            sheet.paste(tile,(x,58));draw.text((x+8,8),label,fill='white',font=font)
            if label.startswith('NATIVE'):draw.text((x+8,29),'EXPERIMENT / NOT PROMOTED',fill=(190,190,190),font=font)
            x+=tile.width
        sheet.save(out/f'source-low-control-probe-{kind}.jpg',quality=96)
    report={'status':'comparison_only_not_acceptance','control_audit':str(args.control_audit),
            'control_audit_sha256':sha(args.control_audit),'probe_audit':str(args.probe_audit),
            'probe_audit_sha256':sha(args.probe_audit),'graph_changed_inputs':changes,
            'same_source_raw_low_and_genuine_references':True,
            'control':{'results':control['results']['CANDIDATE HIGH'],'diagnostics':control['diagnostics']},
            'probe':{'results':probe['results']['CANDIDATE HIGH'],'diagnostics':probe['diagnostics']},
            'image_edits_applied':False,'presentation':'Individual face bounds resized to 480px height; full-frame thumbnails. Original image pixels remain unchanged.',
            'visual_review_required':True}
    (out/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'control_identity':report['control']['results']['identity_centroid'],
                      'probe_identity':report['probe']['results']['identity_centroid'],
                      'graph_changed_inputs':changes,'output_dir':str(out)},indent=2))


if __name__=='__main__':main()
