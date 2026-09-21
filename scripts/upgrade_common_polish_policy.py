"""Process-local experimental overrides; never modify production module bytes."""
from contextlib import contextmanager


@contextmanager
def common_polish_policy(module, *, native_high_skip_smoothing=False):
    overrides={'MOUTH_CORNER_LIFT_FACE_HEIGHT':0.0,'CHEEK_HIGHLIGHT_GAIN':0.0}
    if native_high_skip_smoothing:
        overrides.update(SKIN_TEXTURE_BLEND=0.0,FOREHEAD_WRINKLE_BLEND=0.0,
                         UNDER_EYE_TEXTURE_BLEND=0.0)
    previous={name:getattr(module,name) for name in overrides}
    try:
        for name,value in overrides.items(): setattr(module,name,value)
        yield dict(overrides)
    finally:
        for name,value in previous.items(): setattr(module,name,value)
