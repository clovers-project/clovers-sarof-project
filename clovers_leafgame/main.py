from clovers import Plugin
from .core.clovers import Event, build_result
from .manager import Manager
from clovers.config import config as clovers_config
from .config import Config

config_key = __package__
config_data = Config.model_validate(clovers_config.get(config_key, {}))
"""主配置类"""
clovers_config[config_key] = config_data.model_dump()

plugin = Plugin(build_event=lambda event: Event(event), build_result=build_result)
"""主插件实例"""

manager = Manager(config_data.main_path)
"""小游戏管理器实例"""
