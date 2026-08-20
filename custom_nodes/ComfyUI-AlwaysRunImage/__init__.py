class AlwaysRunImage:
    """Pass an image through while invalidating only downstream execution cache."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": ("IMAGE",)}}

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "passthrough"
    CATEGORY = "image/cache"

    def passthrough(self, image):
        return (image,)


NODE_CLASS_MAPPINGS = {
    "AlwaysRunImage": AlwaysRunImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AlwaysRunImage": "Always Run Image (Cache-Safe Save)",
}
