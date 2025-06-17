from ._clovers import create_plugin, Event, Rule
from ._manager import Manager
from ._config import __config__
import httpx

__plugin__ = create_plugin()
"""主插件实例"""
manager = Manager(__config__.path)
"""小游戏管理器实例"""


GOLD = manager.items_library["金币"]
STD_GOLD = manager.items_library["标准金币"]
REVOLUTION_MARKING = manager.items_library["路灯挂件"] = manager.items_library["路灯挂件标记"]

DEBUG_MARKING = manager.items_library["Debug奖章"]

client = httpx.AsyncClient()
__plugin__.shutdown(client.aclose)

__all__ = [
    "Event",
    "Rule",
    "__plugin__",
    "manager",
    "client",
    "GOLD",
    "STD_GOLD",
    "REVOLUTION_MARKING",
    "DEBUG_MARKING",
]
