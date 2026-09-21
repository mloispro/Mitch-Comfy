"""Prepare/review an author-style full Canny control on CPU; no GPU work or upload."""
import argparse
import json
from pathlib import Path

from PIL import Image
from upgrade_refcontrol_high import ROOT, COMFY, digest, read_json, read_rgb, source_edges, image_name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-audit', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / 'work'):
        raise ValueError('Use a new project work directory.')
    audit = read_json(args.source_audit)
    if not audit['executed_png_graph_verified'] or audit['postprocess_applied']:
        raise ValueError('Require a verified native audit.')
    source = (ROOT / audit['inputs']['SOURCE']['path']).resolve(strict=True)
    if digest(source) != audit['inputs']['SOURCE']['sha256']:
        raise ValueError('Original source changed.')
    rgb = read_rgb(source)
    edges = source_edges(rgb)
    out.mkdir(parents=True)
    control = out / 'source-full-canny.png'
    Image.fromarray(edges).save(control)
    sha = digest(control)
    staged = COMFY / 'input' / ('mitch-upgrade-refcontrol-canny-' + sha[:12] + '.png')
    if staged.exists():
        if digest(staged) != sha: raise ValueError('Staging filename collision; never overwrite.')
    else:
        with staged.open('xb') as f: f.write(control.read_bytes())
    result = {'source_audit':str(args.source_audit.resolve()),'source_audit_sha256':digest(args.source_audit),
              'source':{'path':str(source),'sha256':digest(source)},
              'control':{'path':str(staged),'name':image_name(staged),'sha256':sha,
                         'role':'original full source Canny geometry, including facial features; not an identity photo'},
              'settings':{'short_edge':512,'low_threshold':100,'high_threshold':200,'padding_multiple':64,
                          'downsample':'area','upsample':'cubic','clear_face_interior':False},
              'source_dimensions':[rgb.shape[1],rgb.shape[0]],'control_dimensions':[edges.shape[1],edges.shape[0]],
              'gpu_work':False,'uploads':False,'photo_rgb_changed':False,'visual_review_required_before_generation':True}
    (out / 'preparation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__ == '__main__': main()
