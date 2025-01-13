from .main import plugin as __plugin__
from pathlib import Path
from clovers.tools import list_modules, load_module

for package in list_modules(Path(__file__).parent / "modules"):
    load_module(package)
