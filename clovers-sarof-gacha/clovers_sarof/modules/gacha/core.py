import json
import random
from pathlib import Path
from typing import Any
from collections.abc import Callable, Iterable
from clovers_sarof.core import __plugin__ as plugin, Event
from clovers_sarof.core import manager
from clovers_sarof.core.account import Item, Account, Session


for k, v in json.loads(Path(__file__).parent.joinpath("props_library.json").read_text(encoding="utf_8")).items():
    item = Item(f"item:{k}", **v)
    manager.items_library.set_library(item.id, [item.name], item)

AIR = manager.items_library["空气"]
AIR_PACK = manager.items_library["空气礼包"]
RED_PACKET = manager.items_library["随机红包"]
DIAMOND = manager.items_library["钻石"]


class CardPool:
    def __init__(self):
        self.pool: dict[int, list[Item]] = {}
        self.prob = (0.3, 0.1, 0.1, 0.02)
        self.min_rare = 3

    def gacha(self):
        """随机获取道具"""
        rand = random.uniform(0.0, 1.0)
        rare = self.min_rare
        for prob in self.prob:
            rand -= prob
            if rand <= 0:
                break
            rare += 1
        return random.choice(pool) if (pool := self.pool.get(rare)) else AIR

    def append(self, item: Item):
        """添加道具"""
        self.pool.setdefault(item.rare, []).append(item)

    def extend(self, items: Iterable[Item]):
        """添加道具池"""
        for item in items:
            self.append(item)

    def remove(self, item: Item):
        """弹出道具"""
        return self.pool[item.rare].remove(item)


pool_names = [
    "优质空气",
    "四叶草标记",
    "初级元素",
    "高级空气",
    "钻石会员卡",
    "特级空气",
    "进口空气",
    "幸运硬币",
    "纯净空气",
    "钻石",
    "道具兑换券",
    "重开券",
]

pool = CardPool()
pool.extend(manager.items_library[name] for name in pool_names)


type ItemUsage = Callable[[Account, Session, Item, int, str], Any]

usage_lib: dict[str, tuple[ItemUsage, int | None]] = {}


@plugin.handle(r"使用(道具)?\s*(\S+)\s*(\d*)(.*)", ["user_id", "group_id", "nickname"])
async def _(event: Event):
    _, item_name, count, extra = event.args
    if (use := usage_lib.get(item_name)) is None:
        return
    count = int(count) if count else 1
    if count < 1:
        return "请输入正确的数量。"
    use, cost = use
    with manager.db.session as session:
        account = manager.account(event, session)
        if account is None:
            return "无法在当前会话创建账户。"
        if cost != 0:
            cost = cost or count
            item = manager.items_library[item_name]
            if (tn := item.deal(account, -cost, session)) is not None:
                return f"使用失败，你还有{tn}个{item.name}。"
        return use(account, session, item, count, extra)


def usage(item_name: str, cost: int | None = None):
    def decorator(use: ItemUsage):
        item = manager.items_library.get(item_name)
        if item is None:
            raise ValueError(f"不存在道具{item_name}，无法注册使用方法。")
        usage_lib[item_name] = use, cost

    return decorator
