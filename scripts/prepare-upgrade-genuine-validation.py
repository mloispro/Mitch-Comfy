"""Prepare a held-out genuine source locally; no face edits, uploads or inference."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / 'datasets/mitch-identity-stills-v3/validation/val_03_navy_upper_body.jpg'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    expected = 'fef084d60982754250ab76a7320d71228c96255b2d5244b7461f77b67ce929cf'
    if digest != expected:
        raise RuntimeError('The genuine held-out photograph changed.')
    output = root / 'work/upgrade-source-faithful-20260903/third-source'
    output.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        photo = ImageOps.exif_transpose(image).convert('RGB')
        original_size = photo.size
        scale = min(1.0, (1024*1024/(photo.width*photo.height))**0.5)
        size = (round(photo.width*scale/16)*16, round(photo.height*scale/16)*16)
        if photo.size != size:
            photo = photo.resize(size, Image.Resampling.LANCZOS)
        path = output / 'mitch-upgrade-third-genuine-fef084d6.png'
        if path.exists():
            with Image.open(path) as existing:
                if existing.convert('RGB').tobytes() != photo.tobytes():
                    raise RuntimeError('Refusing to overwrite a different prepared image.')
        else:
            photo.save(path)
    manifest = {'source': str(source), 'source_sha256': digest, 'genuine': True,
                'held_out': True, 'exclude_from_identity_scoring': str(source),
                'output': str(path), 'output_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'original_exif_oriented_size': original_size, 'prepared_size': size,
                'operations': ['EXIF orientation', 'RGB conversion', 'whole-frame aspect-preserving size rounding'],
                'face_edits': False, 'local_only': True}
    (output / 'provenance.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
