"""Read-only Speed publication, preservation and live-node surface checks."""
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def get(port, route):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/{route}", timeout=15) as response:
        return json.load(response)


def main():
    published = list((ROOT / "workflows/production-speed").iterdir())
    assert len(published) == 3 and all(p.suffix == ".json" for p in published), "Exactly three workflow files required"
    expected = [ROOT / "work/production-speed-rollout/group-api.json",
                ROOT / "work/production-speed-rollout/packaged-api/individual-cocktail.json",
                ROOT / "work/production-speed-rollout/packaged-api/upgrade-source-preserve.json"]
    info = get(8188, "object_info")
    checked = []
    adapters = {"Flux2Klein9BSpeedUNETLoader": "UNETLoader",
                "Flux2Klein9BSpeedCLIPLoader": "CLIPLoader",
                "Flux2Klein9BSpeedVAELoader": "VAELoader",
                "Flux2Klein9BSpeedSampler": "SamplerCustomAdvanced"}
    for path in expected:
        document = json.loads(path.read_text(encoding="utf-8"))
        graph = document.get("prompt", document)
        for key, node in graph.items():
            kind = node["class_type"]
            assert kind in info, f"Missing live node {kind}"
            schema = info[adapters.get(kind, kind)]["input"]
            fields = {**schema.get("required", {}), **schema.get("optional", {})}
            for name, value in node["inputs"].items():
                if isinstance(value, list):
                    assert value[0] in graph, f"Broken API link {value}"
                elif name in fields and isinstance(fields[name][0], list):
                    assert value in fields[name][0], f"Missing model/input/choice {kind}.{name}: {value}"
            checked.append(kind)
    for name, klass, field in (("flux-2-klein-base-9b-bf16.safetensors", "UNETLoader", "unet_name"),
                               ("qwen_3_8b_fp8mixed.safetensors", "CLIPLoader", "clip_name"),
                               ("flux2-vae.safetensors", "VAELoader", "vae_name")):
        assert name in info[klass]["input"]["required"][field][0], name
    other_info = get(8189, "object_info")
    for kind in adapters.keys() | {"Flux2Klein9BGroupLoungeFasterQuality"}:
        assert kind in other_info, f"4070 UI cannot recognize guarded node {kind}"
    print(json.dumps({"passed": True, "files": [p.name for p in published],
                      "execution_nodes_checked": len(checked), "unique_node_types": sorted(set(checked)),
                      "queues": {str(p): get(p, "queue") for p in (8188, 8189)}}))


if __name__ == "__main__":
    main()
