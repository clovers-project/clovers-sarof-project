import asyncio
from clovers_sarof.core import __plugin__ as plugin, Event, Rule
from clovers_sarof.core import manager, client
from clovers_sarof.core.account import AccountBank, UserBank, Session, User, Account, col
from clovers_sarof.core.tools import download_url
from .image import draw_rank


def ranklist(title: str, user_ids: list[int], limit: int = 20):
    """总排名"""

    def _get_user_extra(key: str, user_ids: list[int], limit: int):
        query = (
            User.select()
            .where(col(User.extra).contains({key: None}), col(User.id).in_(user_ids))
            .order_by(col(User.extra[key]).desc())
            .limit(limit)
        )

        def func(user: User):
            avatar_url = user.avatar_url
            name = user.name
            value: int = user.extra[key]
            return avatar_url, name, value

        with manager.db.session as session:
            return [func(data) for data in session.exec(query).all()]

    def _get_user_bank(item_id: str, user_ids: list[int], limit: int):
        query = (
            UserBank.select()
            .where(UserBank.item_id == item_id, col(UserBank.id).in_(user_ids))
            .order_by(col(UserBank.n).desc())
            .limit(limit)
        )

        def func(bank: UserBank):
            avatar_url = bank.user.avatar_url
            name = bank.user.name
            value = bank.n
            return avatar_url, name, value

        with manager.db.session as session:
            return [func(data) for data in session.exec(query).all()]

    def _get_account_bank(item_id: str, user_ids: list[int], limit: int):
        query = (
            AccountBank.select()
            .join(Account)
            .where(AccountBank.item_id == item_id, col(Account.user_id).in_(user_ids))
            .order_by(col(AccountBank.n).desc())
            .limit(limit)
        )

        def func(bank: AccountBank):
            avatar_url = bank.account.user.avatar_url
            name = bank.account.nickname
            value = bank.n
            return avatar_url, name, value

        with manager.db.session as session:
            return [func(data) for data in session.exec(query).all()]

    if (item := manager.items_library.get(title)) is not None:
        if item.domain == 2:
            return _get_user_bank(item.id, user_ids, limit)
        elif item.domain == 1:
            return _get_account_bank(item.id, user_ids, limit)
    else:
        match title:
            case "胜场":
                return _get_user_extra("win", user_ids, limit)
            case "败场":
                return _get_user_extra("lose", user_ids, limit)
            case "连胜":
                return _get_user_extra("win_streak", user_ids, limit)
            case "连败":
                return _get_user_extra("lose_streak", user_ids, limit)


@plugin.handle(r"^(.+)排行(.*)", ["user_id", "group_id"])
async def _(event: Event):
    title = event.args[0]
    if title.endswith("总"):
        ranklist = all_ranklist(title[:-1])
    else:
        group_name = event.args[1] or event.group_id or manager.data.user(event.user_id).connect
        group = manager.group_library.get(group_name)
        group_id = group.id if group else None
        if not group_id:
            return
        ranklist = group_ranklist(title, group_id)
    if not ranklist:
        return f"无数据，无法进行{title}排行" if event.to_me else None
    ranklist = heapq.nlargest(20, ranklist, key=lambda x: x[1])
    nickname_data = []
    rank_data = []
    task_list = []
    for nickname, v, avatar_url in ranklist[:20]:
        nickname_data.append(nickname)
        rank_data.append(v)
        task_list.append(download_url(avatar_url))
    avatar_data = await asyncio.gather(*task_list)
    return manager.info_card([draw_rank(list(zip(nickname_data, rank_data, avatar_data)))], event.user_id)
