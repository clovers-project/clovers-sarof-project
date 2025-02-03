from .main import plugin as __plugin__
from pathlib import Path
from clovers.tools import load_module
from clovers.logger import logger

modules = Path(__file__).parent / "modules"

for x in modules.iterdir():
    name = x.stem if x.is_file() and x.name.endswith(".py") else x.name
    try:
        load_module(f"{__package__}.modules.{name}")
        logger.info(f"【{__package__}】加载模块：{name} 成功！")
    except Exception as err:
        logger.exception(f"【{__package__}】加载模块：{name} 失败！{err}")
