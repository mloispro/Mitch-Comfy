import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[2]/'recipe_runtime.py'
_spec = importlib.util.spec_from_file_location('mitch_recipe_group_runtime', _path)
_runtime = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_runtime)
_runtime.install()
NODE_CLASS_MAPPINGS = {}
