from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


TARGETS = (
    ("01-night-out-a", "mitch-workbench-dating-01-night-out-a.png"),
    ("02-night-out-b", "mitch-workbench-dating-02-night-out-b.png"),
    ("03-ragdoll-cat", "mitch-workbench-dating-03-cat-ragdoll.png"),
    ("04-tabby-cat", "mitch-workbench-dating-04-cat-tabby.png"),
    ("05-golfer", "mitch-workbench-dating-05-golfer-safe.png"),
    ("06-amalfi", "mitch-workbench-dating-06-amalfi.png"),
    ("07-lake-boat", "mitch-workbench-dating-07-lake-boat.png"),
    ("08-restaurant", "mitch-workbench-dating-08-restaurant.png"),
    ("09-night-rooftop", "mitch-workbench-dating-09-night-city.png"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lock the original nine Z-Image scene settings from PNG metadata.")
    parser.add_argument("raw_directory", type=Path)
    parser.add_argument("comfy_input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    raw_files = sorted(args.raw_directory.glob("*.png"))
    if len(raw_files) != 9:
        raise RuntimeError(f"Expected nine original Z-Image PNGs, got {len(raw_files)}")

    scenes = []
    common = None
    for index, (raw, (slug, target_name)) in enumerate(zip(raw_files, TARGETS), start=1):
        with Image.open(raw) as opened:
            info = opened.info
        social = json.loads(info["social_workbench"])
        prompt_graph = json.loads(info["prompt"])
        settings = next(
            node["inputs"]
            for node in prompt_graph.values()
            if node.get("class_type") == "AIToolkitSocialPackSettings"
        )
        if common is None:
            common = {
                "width": int(settings["final_width"]),
                "height": int(settings["final_height"]),
                "steps": int(settings["final_steps"]),
                "cfg": float(settings["cfg"]),
                "shift": float(settings["model_shift"]),
                "negative_prompt": settings["negative_prompt"],
                "global_style": settings["global_style"],
                "sampler": "res_multistep",
                "scheduler": "simple",
            }
        prompt = social["scene"]["prompt"].replace("zimg_person", "m1tch_person")
        if index == 9:
            prompt = (
                "m1tch_person, highly realistic vertical nighttime phone photograph of the same adult man "
                "standing centered at a glass high-rise balcony railing, both arms extended naturally along the rail, "
                "fitted black short-sleeve button shirt open at the upper chest, dark trousers and understated wristwatch. "
                "His head is tilted downward and turned toward image-left; his eyes look clearly down-left away from the "
                "camera with absolutely no eye contact. Vast sparkling city skyline far below, direct camera flash on the "
                "subject, deep teal-black sky, tasteful film grain, candid social-media nightlife portrait, correct hands "
                "and body proportions. Do not turn his head toward image-right or toward the viewer."
            )
        target = (args.comfy_input / target_name).resolve()
        if not target.is_file():
            raise RuntimeError(f"Final scene target is missing: {target}")
        scenes.append(
            {
                "number": index,
                "slug": slug,
                "label": social["scene"]["name"],
                "prompt": prompt,
                "seed": int(social["scene"]["seed"]),
                "reference_preset": social["scene"]["reference_preset"],
                "control_strength": float(social["scene"]["control_strength"]),
                "original_raw": str(raw.resolve()),
                "final_target": str(target),
            }
        )

    output = {"common": common, "scenes": scenes}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
