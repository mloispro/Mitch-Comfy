"""Experimental generation-level High role; not imported by production.

Replace the identity presentation instruction, not the scene/gaze contract.
This makes the edit request explicit without appending it underneath an exact
current-age/skin instruction. Likeness and quality must still be tested.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HIGH_IDENTITY_ROLE = (
    "Picture 3 supplies the stable facial identity of m1tch_person, not his expression or tiredness. "
    "Make a visibly more handsome, well-rested best-day portrait of this same adult man. "
    "Keep his distinctive nose, facial asymmetry, eye color, recognizable bone structure and face width. "
    "His cheeks look naturally lean, with a clear cheekbone-to-jaw transition, not rounded or swollen; "
    "do not hollow them or widen the jaw. His eyes have an attractive relaxed, confident shape with "
    "cleaner upper-eyelid definition, subtly stronger well-groomed eyebrows and less under-eye fatigue. "
    "Preserve Picture 1's exact iris focus and appealing expression: the same gently curved closed lip "
    "seam and unequal smile corners, not a stronger grin. Keep the lips softly touching with no teeth. "
    "His skin looks several years more rested and youthful, clear of freckles and dark speckles, with "
    "greatly softened forehead frown creases and a healthy light tan, while retaining fine real pores "
    "and soft, neatly groomed stubble. Keep his original forehead height, hairline, head angle and "
    "natural facial shading. The improvement should be clearly visible, but still look like the same "
    "man in a candid photograph, not a new face, heavy makeup or a beauty filter. "
)


def make_high_prompt(prompt: str) -> str:
    prefix = r"Picture 3 (?:is a protected genuine photograph|exclusively supplies the identity)"
    pattern = prefix + r".*?(?=Picture 4 is)"
    if len(re.findall(pattern, prompt, flags=re.DOTALL)) != 1:
        raise ValueError('Expected exactly one verified four-reference identity paragraph.')
    result = re.sub(pattern, HIGH_IDENTITY_ROLE, prompt, flags=re.DOTALL)
    before = re.split(prefix, prompt, maxsplit=1)[0]
    after = prompt.split('Picture 4 is', 1)[1]
    assert result.startswith(before)
    assert result.split('Picture 4 is', 1)[1] == after
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--input', type=Path)
    inputs.add_argument('--baseline-report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve earlier experiment prompts.')
    prompt = (args.input.read_text(encoding='utf-8-sig') if args.input else
              json.loads(args.baseline_report.read_text(encoding='utf-8-sig'))['effective_prompt'])
    args.output.write_text(make_high_prompt(prompt), encoding='utf-8')


if __name__ == '__main__':
    main()
