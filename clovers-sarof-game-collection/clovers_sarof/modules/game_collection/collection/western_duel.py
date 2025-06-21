from typing import TypedDict
from ..action import place, Event
from ..core import Session as BaseSession

game = "西部对战"
place.info[game] = "装弹|开枪|闪避|闪避开枪|预判开枪"


class SessionData(TypedDict):
    MAG1: int
    MAG2: int
    card: str | None


type Session = BaseSession[SessionData]


@place.create(game, ["西部对战"])
async def _(session: Session, arg: str):
    session.data = {"MAG1": 1, "MAG2": 1, "card": None}
    return f"【西部对战】游戏已创建。\n{session.create_info}"


def western_duel_action(event: Event, session: Session, card: str):
    if event.user_id == session.p1_uid:
        if not event.is_private():
            return "", "请私信发送指令。"
        session.data["card"] = card
        return "MAG1", "行动完毕"
    else:
        return "MAG2", f"双方行动: {session.data['card']} - {card}"


@place.action(game, ["装弹"])
async def _(event: Event, session: Session):
    MAG, tip = western_duel_action(event, session, "装弹")
    if not MAG:
        return tip
    session.nextround()
    session.data[MAG] += 1
    session.data[MAG] = min(session.data[MAG], 6)
    card = session.data["card"]
    if event.user_id == session.p1_uid:
        await event.send_group_message(session.group_id, f"{session.p1_nickname}已行动，请{session.p2_nickname}开始行动。")
        return tip

    if card in {"开枪", "闪枪"}:
        session.win = session.p1_uid
        result = session.end(tip)
    else:
        result = tip + "\n本轮平局。"

    if event.is_private():
        await event.send_group_message(session.group_id, result)
        return "请返回群内查看结果"
    else:
        return result


@place.action(game, ["开枪"])
async def _(event: Event, session: Session):
    MAG, tip = western_duel_action(event, session, "开枪")
    if not MAG:
        return tip
    if session.data[MAG] < 1:
        return "行动失败。你的子弹不足"
    session.nextround()
    session.data[MAG] -= 1
    card = session.data["card"]
    if event.user_id == session.p1_uid:
        await event.send_group_message(session.group_id, f"{session.p1_nickname}已行动，请{session.p2_nickname}开始行动。")
        return tip

    if card == "闪枪":
        session.win = session.p1_uid
        result = session.end(tip)
    elif card in {"装弹", "预判开枪"}:
        session.win = session.p2_uid
        result = session.end(tip)
    else:
        result = tip + "\n本轮平局。"

    if event.is_private():
        await event.send_group_message(session.group_id, result)
        return "请返回群内查看结果"
    else:
        return result


@place.action(game, ["闪避"])
async def _(event: Event, session: Session):
    MAG, tip = western_duel_action(event, session, "开枪")
    if not MAG:
        return tip
    session.nextround()
    card = session.data["card"]
    if event.user_id == session.p1_uid:
        await event.send_group_message(session.group_id, f"{session.p1_nickname}已行动，请{session.p2_nickname}开始行动。")
        return tip

    if card == "预判开枪":
        session.win = session.p1_uid
        result = session.end(tip)
    else:
        result = tip + "\n本轮平局。"

    if event.is_private():
        await event.send_group_message(session.group_id, result)
        return "请返回群内查看结果"
    else:
        return result


@place.action(game, ["闪枪"])
async def _(event: Event, session: Session):
    MAG, tip = western_duel_action(event, session, "开枪")
    if not MAG:
        return tip
    if session.data[MAG] < 1:
        return "行动失败。你的子弹不足"
    session.nextround()
    session.data[MAG] -= 1
    card = session.data["card"]
    if event.user_id == session.p1_uid:
        await event.send_group_message(session.group_id, f"{session.p1_nickname}已行动，请{session.p2_nickname}开始行动。")
        return tip

    if card == "预判开枪":
        session.win = session.p1_uid
        result = session.end(tip)
    elif card in {"装弹", "开枪"}:
        session.win = session.p2_uid
        result = session.end(tip)
    else:
        result = tip + "\n本轮平局。"

    if event.is_private():
        await event.send_group_message(session.group_id, result)
        return "请返回群内查看结果"
    else:
        return result


@place.action(game, ["预判开枪"])
async def _(event: Event, session: Session):
    MAG, tip = western_duel_action(event, session, "开枪")
    if not MAG:
        return tip
    if session.data[MAG] < 1:
        return "行动失败。你的子弹不足"
    session.nextround()
    session.data[MAG] -= 1
    card = session.data["card"]
    if not card:
        await event.send_group_message(session.group_id, f"{session.p1_nickname}已行动，请{session.p2_nickname}开始行动。")
        return tip
    if card == "开枪":
        session.win = session.p1_uid
        result = session.end(tip)
    elif card in {"闪避", "闪枪"}:
        session.win = session.p2_uid
        result = session.end(tip)
    else:
        result = tip + "\n本轮平局。"

    if event.is_private():
        await event.send_group_message(session.group_id, result)
        return "请返回群内查看结果"
    else:
        return result
