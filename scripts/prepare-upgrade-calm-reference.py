"""Verify a genuine alternate identity reference and create only a viewing preview."""
import hashlib
import json
from pathlib import Path
from PIL import Image,ImageOps

root=Path(__file__).resolve().parents[1]
source=root/'datasets/mitch-identity-stills-v3/dataset/07_sweater_front_neutral.jpg'
expected='0e9f30d584646b3455674fa88e03c3c8b5a534d0fcbc2083088032ecb35da93a'
actual=hashlib.sha256(source.read_bytes()).hexdigest()
if actual!=expected: raise RuntimeError('Genuine photograph hash changed.')
output=root/'work/upgrade-source-faithful-20260903/calm-reference-prepared'
if output.exists(): raise FileExistsError('Preserve previous preparation.')
output.mkdir(parents=True)
with Image.open(source) as image:
    preview=ImageOps.exif_transpose(image).convert('RGB')
    original_size=preview.size
    preview.thumbnail((1200,1200),Image.Resampling.LANCZOS)
    preview.save(output/'viewing-preview.jpg',quality=95)
report={'status':'verified_not_staged_or_generated','reference_source':str(source),'sha256':actual,
        'genuine':True,'provenance':'datasets/mitch-identity-stills-v3/manifest.json, camera_still, train07',
        'reference_pixels_changed':False,'preview_only_operations':['EXIF orientation','whole-frame downsize'],
        'original_oriented_size':original_size,'preview_used_for_generation':False,
        'purpose':'Potential four-reference native edit ablation; replace only the tense frontal identity portrait.'}
(output/'provenance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
