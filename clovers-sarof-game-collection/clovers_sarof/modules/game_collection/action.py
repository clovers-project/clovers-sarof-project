import asyncio
from clovers_sarof.core import __plugin__, manager
from clovers_sarof.core import Event, Rule
from .core import Manager

place = Manager(__plugin__)


@place.plugin.handle(["接受挑战"], ["user_id", "group_id", "nickname"], rule=Rule.group)
async def _(event: Event):
    group_id: str = event.group_id  # type: ignore
    session = place.session(group_id)
    if not session:
        return
    user_id = event.user_id
    if session.p2_uid or session.p1_uid == user_id:
        return
    if session.at and session.at != user_id:
        return f"现在是 {session.p1_nickname} 发起的对决，请等待比赛结束后再开始下一轮..."
    with manager.db.session as sql_session:
        account = manager.db.account(user_id, group_id, sql_session)
        account.user.connect = group_id
        bet = session.bet
        if bet:
            item, n = bet
            if (bn := item.bank(account, sql_session).n) < n:
                return f"你的无法接受这场对决！\n——你还有{bn}个{item.name}。"
            tip = f"对战金额为 {n} {item.name}\n"
        else:
            tip = ""
        sql_session.commit()
    session.join(user_id, account.name)
    session.next = session.p1_uid
    game = session.game
    tip = f"{session.p2_nickname}接受了对决！\n本场对决为【{game}】\n{tip}请{session.p1_nickname}发送指令\n{place.info[game]}"

    if session.start_tips:

        async def result():
            yield tip
            await asyncio.sleep(1)
            yield session.start_tips

        return result()
    return tip


@place.plugin.handle(["拒绝挑战"], ["user_id", "group_id"], rule=Rule.group)
async def _(event: Event):
    group_id: str = event.group_id  # type: ignore
    session = place.session(group_id)
    if session and (at := session.at) and at == event.user_id:
        if session.p2_uid:
            return "对决已开始，拒绝失败。"
        return "拒绝成功，对决已结束。"


@place.plugin.handle(["超时结算"], ["user_id", "group_id"], rule=Rule.group)
async def _(event: Event):
    group_id: str = event.group_id  # type: ignore
    session = place.session(group_id)
    if (session := place.place.get(group_id)) and session.timeout() < 0:
        session.win = session.p2_uid if session.next == session.p1_uid else session.p1_uid
        return session.end()


@place.plugin.handle(["认输"], ["user_id", "group_id"], rule=Rule.group)
async def _(event: Event):
    group_id: str = event.group_id  # type: ignore
    session = place.place.get(group_id)
    if not session or session.p2_uid is None:
        return
    user_id = event.user_id
    if user_id == session.p1_uid:
        session.win = session.p2_uid
    elif user_id == session.p2_uid:
        session.win = session.p1_uid
    else:
        return
    return session.end()


@place.plugin.handle(["游戏重置", "清除对战"], ["user_id", "group_id", "permission"], rule=Rule.group)
async def _(event: Event):
    group_id: str = event.group_id  # type: ignore
    session = place.place.get(group_id)
    if not session:
        return
    if session.timeout() > 0 and event.permission < 1:
        return f"当前游戏未超时。"
    del place.place[group_id]
    return "游戏已重置。"
