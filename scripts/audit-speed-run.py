"""Collect one completed ordinary-Comfy Speed run; never submit or retry."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent / "ComfyUI"
OUT = ROOT / "work/production-speed-rollout"
ROUTES = {"group": "Flux2Klein9BGroupLoungeFasterQuality",
          "individual": "Flux2Klein9BSpeedSampler", "upgrade": "Flux2Klein9BSpeedSampler"}


def canonical(graph):
    return {str(key): {"class_type": value["class_type"], "inputs": value["inputs"]}
            for key, value in graph.items()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--route", choices=ROUTES, required=True)
    p.add_argument("--prompt-id", required=True)
    p.add_argument("--expected-api", type=Path, required=True)
    args = p.parse_args()
    with urllib.request.urlopen("http://127.0.0.1:8188/history/" + args.prompt_id, timeout=10) as response:
        history = json.load(response)[args.prompt_id]
    if not history["status"]["completed"] or history["status"]["status_str"] != "success":
        raise RuntimeError("Prompt not successfully completed; no successful receipt")
    actual = canonical(history["prompt"][2])
    expected_data = json.loads(args.expected_api.read_text(encoding="utf-8"))
    expected = canonical(expected_data.get("prompt", expected_data))
    if actual != expected:
        raise RuntimeError("Actual browser-submitted execution graph differs from packaged API")
    if not any(v["class_type"] == ROUTES[args.route] for v in actual.values()):
        raise RuntimeError("Wrong Speed route")
    images = []
    for node_id, output in history["outputs"].items():
        for record in output.get("images", []):
            if record.get("type") == "output":
                path = (COMFY / "output" / record["subfolder"] / record["filename"]).resolve()
                if not path.is_relative_to((COMFY / "output/production-speed").resolve()):
                    raise RuntimeError("Native photo outside production-speed output scope")
                images.append((node_id, path))
    if len(images) != 1:
        raise RuntimeError(f"Expected exactly one native saved photo; got {images}")
    route_out = OUT / (args.route + "-run")
    route_out.mkdir(exist_ok=False)
    (route_out / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    (route_out / "actual-api.json").write_text(json.dumps(actual, indent=2), encoding="utf-8")
    node_id, source = images[0]
    shutil.copy2(source, route_out / "photo.png")
    from PIL import Image
    with Image.open(source) as im:
        dimensions, metadata = list(im.size), dict(im.info)
        rgb = hashlib.sha256(im.convert("RGB").tobytes()).hexdigest()
    if args.route != "group" and canonical(json.loads(metadata["prompt"])) != actual:
        raise RuntimeError("Native PNG execution graph differs from actual history")
    timestamps = {}
    for kind, event in history["status"]["messages"]:
        if kind in ("execution_start", "execution_success"):
            timestamps[kind] = event["timestamp"]
    report = {"route": args.route, "prompt_id": args.prompt_id,
              "normal_comfy_run": True, "api_graph_exact": True, "native_image": str(source),
              "local_copy": str(route_out / "photo.png"), "node_id": node_id,
              "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "rgb_sha256": rgb,
              "dimensions": dimensions, "png_metadata": metadata,
              "worker_seconds": (timestamps["execution_success"]-timestamps["execution_start"])/1000,
              "timing_scope": "single normal3090 integration run incl node execution/loading/saving; no paired speed claim",
              "visual_review": "pending", "likeness_review": "pending"}
    (route_out / "runtime.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "png_metadata"}, indent=2))


if __name__ == "__main__":
    main()
