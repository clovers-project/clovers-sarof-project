from io import BytesIO
from clovers import Result
from clovers_sarof.core.linecard import text_to_image
from typing import TypedDict
from ..action import place, Event
from ..core import Session as BaseSession
from ..tools import PokerCard, random_poker, poker_show

game = "21点"
place.info[game] = "停牌|抽牌|双倍停牌"


class SessionData(TypedDict):
    hand1: list[PokerCard]
    hand2: list[PokerCard]
    deck: list[PokerCard]


type Session = BaseSession[SessionData]


@place.create(game, ["21点", "黑杰克"])
async def _(session: Session, arg: str):
    deck = random_poker()
    session.data = {"hand1": [deck.pop(0)], "hand2": [deck.pop(0)], "deck": deck}
    return f"唰唰~，随机牌堆已生成。\n{session.create_info}"


@place.action(game, ["抽牌"], ["nickname"])
async def _(event: Event, session: Session):
    hand, pt = blackjack_hit(session)
    if pt > 21:
        result = blackjack_end(session)
        if event.is_private():
            await event.send_group_message(session.group_id, result)
            return "请返回群内查看结果"
        else:
            return result
    else:
        msg = f"你的手牌：\n{poker_show(hand,'\n')}\n合计:{pt}点"
        if event.is_private():
            await event.send_group_message(session.group_id, f"{event.nickname} 已抽牌")
            return msg
        else:
            user_id = event.user_id
            await event.send_private_message(user_id, msg)
            return [Result("at", user_id), "你的手牌已发送，请查看"]


@place.action(game, ["停牌"])
async def _(event: Event, session: Session):
    if session.round == 1:
        session.nextround()
        result = [Result("at", session.p2_uid), f"请{session.p2_nickname}{place.info[game]}"]
        if event.is_private():
            await event.send_group_message(session.group_id, result)
            return "你已停牌，请等待对方操作"
        else:
            return result
    else:
        result = blackjack_end(session)
        if event.is_private():
            await event.send_group_message(session.group_id, result)
            return "请返回群内查看结果"
        else:
            return result


@place.action(game, ["双倍停牌"])
async def _(event: Event, session: Session):
    session.double_bet()
    hand, pt = blackjack_hit(session)
    msg = f"你的手牌：\n{poker_show(hand,'\n')}\n合计:{pt}点"
    if session.round == 1:
        if pt > 21:
            result = blackjack_end(session)
            if event.is_private():
                await event.send_group_message(session.group_id, result)
                return "请返回群内查看结果"
            else:
                return result
        else:
            session.nextround()
            msg = f"你的手牌：\n{poker_show(hand,'\n')}\n合计:{pt}点"
            result = [Result("at", session.p2_uid), f"请{session.p2_nickname}{place.info[game]}"]
            if event.is_private():
                await event.send_group_message(session.group_id, result)
                return msg
            else:
                await event.send_private_message(event.user_id, msg)
                return result
    else:
        result = blackjack_end(session)
        if event.is_private():
            await event.send_group_message(session.group_id, result)
            return "请返回群内查看结果"
        else:
            return result


def blackjack_pt(hand: list[tuple[int, int]]) -> int:
    """
    返回21点牌组点数。
    """
    pts = [point if point < 10 else 10 for _, point in hand]
    pt = sum(pts)
    if 1 in pts and pt <= 11:
        pt += 10
    return pt


def blackjack_hit(session: Session):
    session.delay()
    if session.round == 1:
        hand = session.data["hand1"]
        session.win = session.p2_uid
    else:
        hand = session.data["hand2"]
        session.win = session.p1_uid
    deck = session.data["deck"]
    card = deck[0]
    session.data["deck"] = deck[1:]
    hand.append(card)
    pt = blackjack_pt(hand)
    return hand, pt


def blackjack_end(session: Session):
    hand1 = session.data["hand1"]
    pt1 = blackjack_pt(hand1)
    hand2 = session.data["hand2"]
    pt2 = blackjack_pt(hand2)
    if pt1 > 21:
        session.win = session.p2_uid
    elif pt2 > 21:
        session.win = session.p1_uid
    else:
        session.win = session.p1_uid if pt1 > pt2 else session.p2_uid
    result1 = f"玩家：{session.p1_nickname}\n手牌：{poker_show(hand1, '')}\n合计:{pt1}点"
    result2 = f"玩家：{session.p2_nickname}\n手牌：{poker_show(hand2, '')}\n合计:{pt2}点"
    text_to_image(
        f"{result1}\n----\n{result2}",
        bg_color="white",
        width=0,
    ).save(output := BytesIO(), format="png")
    return session.end(output)
