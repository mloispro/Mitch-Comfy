"""Prepare an expression-only reference crop; no generation, upload or final composite."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image, ImageOps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-audit', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(root):
        raise ValueError('Use a new project-local directory.')
    native = json.loads(args.native_audit.read_text(encoding='utf-8-sig'))
    record = native['inputs']['SOURCE']
    source = Path(record['path'])
    if hashlib.sha256(source.read_bytes()).hexdigest() != record['sha256']:
        raise ValueError('Source no longer matches its audit.')
    with Image.open(source) as handle:
        image = ImageOps.exif_transpose(handle).convert('RGB')
    analyzer = FaceAnalysis(name='antelopev2', root=str(Path.home()/'.insightface'),
                            providers=['CPUExecutionProvider'], allowed_modules=['detection'])
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    faces = analyzer.get(cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR))
    if len(faces) != 1:
        raise ValueError('Exactly one source face required.')
    x0, y0, x1, y1 = faces[0].bbox
    side = min(image.width, image.height, round(max(x1-x0, y1-y0)*1.25))
    left = max(0, min(image.width-side, round((x0+x1-side)/2)))
    top = max(0, min(image.height-side, round((y0+y1-side)/2)))
    box = (left, top, left+side, top+side)
    args.output_dir.mkdir(parents=True)
    crop_path = args.output_dir/'original-expression-crop.png'
    image.crop(box).save(crop_path)
    crop_hash = hashlib.sha256(crop_path.read_bytes()).hexdigest()
    staged = root.parent/'ComfyUI/input'/f'mitch-source-expression-{crop_hash[:12]}.png'
    if staged.exists():
        if hashlib.sha256(staged.read_bytes()).hexdigest() != crop_hash:
            raise ValueError('Staging path collision; no overwrite.')
    else:
        with crop_path.open('rb') as source_handle, staged.open('xb') as destination:
            shutil.copyfileobj(source_handle, destination)
    report = {'source': record, 'crop_box': box, 'crop_context_factor': 1.25,
              'rotation_or_warp': False, 'crop': str(crop_path.resolve()), 'sha256': crop_hash,
              'staged': str(staged.resolve()), 'reference_role': 'source expression/eye/brow/lip geometry, not genuine identity anchor',
              'scoring_reference': False, 'native_audit': str(args.native_audit.resolve())}
    (args.output_dir/'provenance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
