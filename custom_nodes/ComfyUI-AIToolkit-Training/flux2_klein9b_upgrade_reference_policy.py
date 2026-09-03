"""Reference-resolution policy for the Klein 9B existing-photo upgrade."""

QUALITY_IDENTITY_REFERENCE_MEGAPIXELS = 0.50
TURBO_IDENTITY_REFERENCE_MEGAPIXELS = 1.00


def identity_reference_megapixels(fast_turbo: bool) -> float:
    """Use more native identity evidence in the compressed eight-step Turbo path."""

    return (
        TURBO_IDENTITY_REFERENCE_MEGAPIXELS
        if fast_turbo
        else QUALITY_IDENTITY_REFERENCE_MEGAPIXELS
    )
