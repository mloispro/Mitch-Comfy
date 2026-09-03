from __future__ import annotations

import hashlib
import json
from pathlib import Path


def verify_asset_sha256(path: Path, expected: str, label: str) -> Path:
    """Verify a visual-shell asset without depending on a frozen engine module."""
    path = Path(path).resolve()
    if not path.is_file():
        raise RuntimeError(f"Missing {label}: {path}")
    normalized_expected = expected.upper()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    actual = digest.hexdigest().upper()
    if actual != normalized_expected:
        raise RuntimeError(f"{label} hash mismatch. Expected {expected}, found {actual}.")
    return path


def augment_visual_preset_report(
    response: dict,
    *,
    output_directory: str | Path,
    shell_name: str,
    preset: dict,
) -> dict:
    """Extend the internal engine's sidecar report without changing its embedded PNG report."""
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
        "png_embedded_report": "generation-locked internal engine",
        "report_json": "internal engine report plus v1.1 visual-preset selection",
    }
    updated_report_json = json.dumps(report, indent=2)
    report_path = Path(output_directory) / output_folder / "report.json"
    report_path.write_text(updated_report_json, encoding="utf-8")
    result[-1] = updated_report_json
    response["result"] = tuple(result)
    return response
