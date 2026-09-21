"""Download and atomically install the exact official Comfy FLUX CLIP-L export.

No generation, GPU operations, photo transfer, dependency changes or replacement
of any existing model. The existing extracted clip_l_fp16 file remains intact.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import urllib.request
import uuid

from huggingface_hub import HfApi, hf_hub_download


ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / "ComfyUI"
WORK = ROOT / "work/upgrade-high-20260907/models/official-clip"
REPO = "comfyanonymous/flux_text_encoders"
REVISION = "6af2a98e3f615bdfa612fbd85da93d1ed5f69ef5"
FILENAME = "clip_l.safetensors"
SIZE = 246144152
SHA256 = "660c6f5b1abae9dc498ac2d21e1347d2abdb0cf6c0c0c8576cd796491d9a6cdd"
DESTINATION = COMFY / "models/text_encoders" / FILENAME


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(path):
    if path.stat().st_size != SIZE or sha(path) != SHA256:
        raise ValueError("Preserve file with unexpected size/hash: " + str(path))


def visible():
    with urllib.request.urlopen("http://127.0.0.1:8188/object_info/DualCLIPLoader", timeout=30) as response:
        data = json.load(response)
    names = data["DualCLIPLoader"]["input"]["required"]["clip_name1"][0]
    return {"port": 8188, "loader": "DualCLIPLoader", "clip_l_visible": FILENAME in names,
        "existing_extracted_clip_visible": "clip_l_fp16.safetensors" in names}


def main():
    if os.name != "nt":
        raise RuntimeError("This scoped installer relies on Windows non-overwriting atomic rename.")
    receipt_path = WORK / "verified-download.json"
    if receipt_path.exists():
        verify(DESTINATION)
        print(json.dumps({"status": "already_verified", "receipt": str(receipt_path), "visibility": visible()}, indent=2))
        return
    original = DESTINATION.with_name("clip_l_fp16.safetensors")
    original_hash = sha(original) if original.exists() else None
    before = visible()
    info = HfApi(token=False).model_info(REPO, revision=REVISION, files_metadata=True)
    entry = next(item for item in info.siblings if item.rfilename == FILENAME)
    if info.sha != REVISION or entry.size != SIZE or not entry.lfs or entry.lfs.sha256 != SHA256:
        raise ValueError("Pinned official CLIP-L repository metadata changed.")
    if shutil.disk_usage(ROOT).free < SIZE * 3:
        raise ValueError("Insufficient space for verified download and atomic install.")
    WORK.mkdir(parents=True, exist_ok=True)
    reused = DESTINATION.exists()
    if reused:
        verify(DESTINATION)
        downloaded = None
    else:
        downloaded = Path(hf_hub_download(REPO, FILENAME, revision=REVISION, token=False, local_dir=WORK))
        verify(downloaded)
        DESTINATION.parent.mkdir(parents=True, exist_ok=True)
        temporary = DESTINATION.with_name("." + FILENAME + "." + uuid.uuid4().hex + ".installing")
        if temporary.parent.resolve() != (COMFY / "models/text_encoders").resolve():
            raise ValueError("Temporary installation path escapes intended model directory.")
        with downloaded.open("rb") as source, temporary.open("xb") as target:
            shutil.copyfileobj(source, target, 8 * 1024**2)
            target.flush()
            os.fsync(target.fileno())
        verify(temporary)
        # On Windows this fails if DESTINATION appeared concurrently. It never
        # replaces an existing file and exposes only a fully verified model.
        os.rename(temporary, DESTINATION)
        verify(DESTINATION)
    if original_hash is not None and sha(original) != original_hash:
        raise RuntimeError("Existing extracted CLIP-L changed concurrently; inspect before using this receipt.")
    after = visible()
    receipt = {"status": "verified_installed", "repo": REPO, "revision": REVISION,
        "filename": FILENAME, "size": SIZE, "sha256": SHA256,
        "download_path": str(downloaded) if downloaded else None, "installed_path": str(DESTINATION),
        "reused_existing_verified_file": reused, "atomic_install": "Windows same-directory rename with no overwrite",
        "existing_extracted_clip": {"path": str(original), "sha256": original_hash, "unchanged": True},
        "visibility_before": before, "visibility_after": after,
        "authorization": "User: download whatever you want; get it done",
        "dependencies_changed": False, "photos_uploaded": False, "gpu_operations": False,
        "generation_queued": False, "production_changed": False}
    with receipt_path.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
