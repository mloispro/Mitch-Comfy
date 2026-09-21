"""Read-only photo analysis views; no scoring, restoration or image replacement."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--image', required=True, type=Path)
parser.add_argument('--sha', required=True)
args = parser.parse_args()
assert args.image.resolve().parent == (HERE / 'runs/ready-amber-hook-pilot').resolve()
assert hashlib.sha256(args.image.read_bytes()).hexdigest().upper() == args.sha
with Image.open(args.image) as source:
    assert source.size == (832, 1216)
    image = source.convert('RGB')
output = HERE / 'pre-score-visual-review'
output.mkdir(exist_ok=False)
thumbnail = image.copy()
thumbnail.thumbnail((312, 456), Image.Resampling.LANCZOS)
thumbnail.save(output / 'whole-frame-thumbnail.png')
image.crop((220, 440, 730, 690)).save(output / 'heads-native.png')
image.crop((250, 680, 750, 1120)).save(output / 'hands-body-native.png')
(output / 'provenance.json').write_text(json.dumps({
    'source': str(args.image.resolve()), 'source_sha256': args.sha,
    'scope': 'Analysis views only; original PNG unchanged. Crops preserve native pixels; thumbnail is downsampled. No scores, enhancement or restoration.',
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
}, indent=2), encoding='utf-8')
print(output)
