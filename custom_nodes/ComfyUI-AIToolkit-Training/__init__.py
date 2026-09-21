from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from . import status_server as _status_server
from .pixelsmile_experiment import NODE_CLASS_MAPPINGS as _pixelsmile_nodes
from .pixelsmile_experiment import NODE_DISPLAY_NAME_MAPPINGS as _pixelsmile_names
from .flux2_klein9b_group_speed import Flux2Klein9BGroupLoungeFasterQuality
from .flux2_klein9b_speed_guard import (
    SPEED_NODE_CLASS_MAPPINGS,
    SPEED_NODE_DISPLAY_NAME_MAPPINGS,
)

NODE_CLASS_MAPPINGS.update(_pixelsmile_nodes)
NODE_DISPLAY_NAME_MAPPINGS.update(_pixelsmile_names)
NODE_CLASS_MAPPINGS.update(SPEED_NODE_CLASS_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(SPEED_NODE_DISPLAY_NAME_MAPPINGS)
NODE_CLASS_MAPPINGS["Flux2Klein9BGroupLoungeFasterQuality"] = Flux2Klein9BGroupLoungeFasterQuality
NODE_DISPLAY_NAME_MAPPINGS["Flux2Klein9BGroupLoungeFasterQuality"] = "Speed - Group Lounge Faster Quality (RTX 3090)"

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
