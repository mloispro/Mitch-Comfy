"""Download the user-authorized, hash-pinned expression adapter; no photographs."""
import hashlib
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi, hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
NAME = 'PixelSmile-preview.safetensors'
EXPECTED = '9bb2f7981e8cd59a5d6e31c2ca08cc0961ac46c267b81af9bce7f8d542ca319a'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(8 * 1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    destination = ROOT / 'work/vendor/PixelSmile'
    installed = ROOT.parent / 'ComfyUI/models/loras/pixelsmile' / NAME
    info = HfApi(token=False).model_info('PixelSmile/PixelSmile', files_metadata=True)
    entry = next(item for item in info.siblings if item.rfilename == NAME)
    if entry.lfs.sha256 != EXPECTED or not 800_000_000 < entry.size < 950_000_000:
        raise ValueError('Published adapter differs from reviewed preview; do not substitute.')
    if shutil.disk_usage(ROOT).free < entry.size * 3:
        raise ValueError('Insufficient disk space for download and verified install.')
    if installed.exists() and sha(installed) != EXPECTED:
        raise ValueError('Existing installed file differs; preserve it.')
    print(f'Downloading {entry.size} bytes at pinned revision {info.sha}', flush=True)
    path = Path(hf_hub_download('PixelSmile/PixelSmile', filename=NAME, revision=info.sha,
                               local_dir=destination, token=False))
    if sha(path) != EXPECTED:
        raise ValueError('Downloaded adapter hash mismatch; do not install.')
    installed.parent.mkdir(parents=True, exist_ok=True)
    if not installed.exists():
        shutil.copy2(path, installed)
    if sha(installed) != EXPECTED:
        raise ValueError('Installed adapter hash mismatch.')
    report = {'repository': 'PixelSmile/PixelSmile', 'revision': info.sha,
              'filename': NAME, 'size_bytes': entry.size, 'sha256': EXPECTED,
              'download_path': str(path), 'installed_path': str(installed),
              'user_authorization': 'download whatever you want',
              'character_training': False, 'photos_uploaded': False,
              'dependencies_changed': False, 'production_workflow_changed': False}
    (destination / 'verified-download.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
