import asyncio
from clovers_sarof.core import __plugin__ as plugin, Event
from clovers_sarof.core import manager, client
from clovers_sarof.core import REVOLUTION_MARKING
from clovers_sarof.core.tools import download_url
from .image import draw_rank
from .rankdata import rank_account_bank, rank_user_bank, rank_user_extra


user_extra = {
    "胜场": "win",
    "败场": "lose",
    "连胜": "win_streak",
    "连败": "lose_streak",
    "最大连胜": "win_streak_max",
    "最大连败": "lose_streak_max",
}


def ranklist(title: str, group_id: str | None = None, limit: int = 20):
    if title in ("路灯挂件", "重置"):
        key = REVOLUTION_MARKING.id
        func = rank_account_bank
    elif (item := manager.items_library.get(title)) is not None:
        if item.domain == 2:
            key = item.id
            func = rank_user_bank
        elif item.domain == 1:
            key = item.id
            func = rank_account_bank
        else:
            return
    else:
        key = user_extra.get(title)
        if key is None:
            return
        func = rank_user_extra
    with manager.db.session as session:
        return func(key, group_id, limit, session)


@plugin.handle(r"^(.+)排行(.*)", ["user_id", "group_id", "to_me"])
async def _(event: Event):
    title = event.args[0]
    if title.endswith("总"):
        group_id = None
        title = title[:-1]
    else:
        group_id = event.group_id
    data = ranklist(title, group_id)
    if not data:
        return f"无数据，无法进行{title}排行" if event.to_me else None
    avatar_urls, nicknames, values = zip(*data)
    avatar_data = await asyncio.gather(*(download_url(url, client) for url in avatar_urls))
    return manager.info_card([draw_rank(list(zip(avatar_data, nicknames, values)))], event.user_id)
