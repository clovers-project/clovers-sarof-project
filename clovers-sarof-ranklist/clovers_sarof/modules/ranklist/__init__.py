import asyncio
from clovers_sarof.core import __plugin__ as plugin, Event
from clovers_sarof.core import manager, client
from clovers_sarof.core import REVOLUTION_MARKING
from clovers_sarof.core.tools import download_url
from .image import draw_rank
from .rankdata import rank_account_bank, rank_user_bank, rank_user_extra


def ranklist(title: str, group_id: str | None = None, limit: int = 20):

    if (item := manager.items_library.get(title)) is not None:
        if item.domain == 2:
            query, func = rank_user_bank(item.id, group_id, limit)
        elif item.domain == 1:
            query, func = rank_account_bank(item.id, group_id, limit)
        else:
            return
    else:
        match title:
            case "胜场":
                query, func = rank_user_extra("win", group_id, limit)
            case "败场":
                query, func = rank_user_extra("lose", group_id, limit)
            case "连胜":
                query, func = rank_user_extra("win_streak", group_id, limit)
            case "连败":
                query, func = rank_user_extra("lose_streak", group_id, limit)
            case "路灯挂件", "重置":
                query, func = rank_account_bank(REVOLUTION_MARKING.id, None, limit)
            case _:
                return

    with manager.db.session as session:
        return [func(data) for data in session.exec(query).all()]  # type: ignore # 生成的 query, func 一定是对应的


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
