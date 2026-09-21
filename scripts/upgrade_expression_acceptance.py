"""Small, model-independent checks for the Upgrade closed-lip requirement."""
from __future__ import annotations

import math


def identity_retention_check(source: float, baseline: float, candidate: float, role: str) -> dict:
    """Conservative diagnostic; visual identity and attractiveness remain separate."""
    if role not in ('high-edit','source-fidelity'):
        raise ValueError('Unknown candidate role.')
    if any(not math.isfinite(value) or not -1 <= value <= 1 for value in (source,baseline,candidate)):
        raise ValueError('Expected finite cosine similarities.')
    reference=source if role=='source-fidelity' else baseline
    return {'reference':'source' if role=='source-fidelity' else 'base raw',
            'reference_similarity':reference,'candidate_similarity':candidate,
            'delta':candidate-reference,'minimum_similarity':.70,'maximum_drop':.03,
            'passed':candidate>=.70 and candidate-reference>=-.03,
            'note':'Diagnostic only; not proof of likeness, attractiveness or a final identity lock.'}


def closed_lip_check(source_opening: float, candidate_opening: float) -> dict:
    """Do not normalize a new result against an already-broken generated baseline.

    Landmark opening is a diagnostic, not a teeth detector. Visual review is still
    required even when this check passes. The user requests closed lips regardless
    of whether a previous generated image happened to have an open mouth.
    """
    values = (source_opening, candidate_opening)
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("Mouth opening ratios must be finite and nonnegative.")
    limit = 0.035
    return {
        "source_opening_ratio": round(source_opening, 6),
        "candidate_opening_ratio": round(candidate_opening, 6),
        "maximum_closed_lip_ratio": limit,
        "passed": candidate_opening <= limit,
        "reference": "user closed-lip requirement, not previous generated mouth",
        "visual_teeth_review_required": True,
    }
