from pathlib import Path
from importlib import import_module
from clovers.logger import logger
from clovers_sarof_core import __plugin__

for x in Path(__file__).parent.joinpath("modules").iterdir():
    name = x.stem if x.is_file() and x.name.endswith(".py") else x.name
    try:
        import_module(f"{__package__}.modules.{name}")
        logger.info(f"[{__package__}] 加载模块：{name} 成功！")
    except:
        logger.exception(f"[{__package__}] 加载模块：{name} 失败！")
