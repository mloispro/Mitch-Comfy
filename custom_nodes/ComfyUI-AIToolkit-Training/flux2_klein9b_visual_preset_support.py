from __future__ import annotations

import hashlib
import json
from pathlib import Path


_VERIFIED_SIGNATURES: dict[str, tuple[str, int, int]] = {}


def verify_asset_sha256(path: Path, expected: str, label: str) -> Path:
    """Verify a visual-shell asset without depending on a frozen engine module."""
    path = Path(path)
    if not path.is_file():
        raise RuntimeError(f"Missing {label}: {path}")
    signature = (str(path.resolve()), int(path.stat().st_size), int(path.stat().st_mtime_ns))
    cache_key = f"{label}:{path.resolve()}"
    if _VERIFIED_SIGNATURES.get(cache_key) != signature:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                digest.update(block)
        actual = digest.hexdigest().upper()
        if actual != expected.upper():
            raise RuntimeError(f"{label} hash mismatch. Expected {expected}, found {actual}.")
        _VERIFIED_SIGNATURES[cache_key] = signature
    return path


def augment_visual_preset_report(
    response: dict,
    *,
    output_directory: str | Path,
    shell_name: str,
    preset: dict,
) -> dict:
    """Extend a frozen engine's sidecar report without changing its embedded PNG report."""
    result = list(response["result"])
    if len(result) < 2:
        raise RuntimeError("Visual preset engine returned an invalid result tuple.")
    output_folder = result[-2]
    report = json.loads(result[-1])
    report["visual_preset_shell"] = {
        "name": shell_name,
        **preset,
    }
    report["provenance_scope"] = {
        "png_embedded_report": "hash-frozen v1 generation engine",
        "report_json": "v1 engine report plus visual-preset shell selection",
    }
    updated_report_json = json.dumps(report, indent=2)
    report_path = Path(output_directory) / output_folder / "report.json"
    report_path.write_text(updated_report_json, encoding="utf-8")
    result[-1] = updated_report_json
    response["result"] = tuple(result)
    return response
