import random
from clovers_leafgame.main import plugin, manager
from clovers_leafgame.clovers import Event
from ..core import Session, Game
from ..action import place


def dice_pt(dice_array: list):
    pt = 0
    for i in range(1, 7):
        n = dice_array.count(i)
        if n <= 1:
            pt += i * dice_array.count(i)
        elif n == 2:
            pt += (100 + i) * (10**n)
        else:
            pt += i * (10 ** (2 + n))
    return pt


def pt_analyse(pt: int):
    array_type = []
    if (n := int(pt / 10000000)) > 0:
        pt -= n * 10000000
        array_type.append(f"满{n}")
    if (n := int(pt / 1000000)) > 0:
        pt -= n * 1000000
        array_type.append(f"串{n}")
    if (n := int(pt / 100000)) > 0:
        pt -= n * 100000
        array_type.append(f"条{n}")
    if (n := int(pt / 10000)) > 0:
        if n == 1:
            pt -= 10000
            n = int(pt / 100)
            array_type.append(f"对{n}")
        else:
            pt -= 20000
            n = int(pt / 100)
            array_type.append(f"两对{n}")
        pt -= n * 100
    if pt > 0:
        array_type.append(f"散{pt}")
    return " ".join(array_type)


dice = Game("掷骰子", "开数")


@plugin.handle(["摇色子", "摇骰子", "掷色子", "掷骰子"], ["user_id", "group_id", "at"], priority=1)
@dice.create(place)
async def _(session: Session, arg: str):

    dice_array1 = [random.randint(1, 6) for _ in range(5)]
    session.data["dice_array1"] = dice_array1
    pt1 = dice_pt(dice_array1)
    session.data["pt1"] = pt1
    session.data["array_name1"] = pt_analyse(pt1)

    dice_array2 = [random.randint(1, 6) for _ in range(5)]
    session.data["dice_array2"] = dice_array2
    pt2 = dice_pt(dice_array2)
    session.data["pt2"] = pt2
    session.data["array_name2"] = pt_analyse(pt2)

    if session.bet:
        prop, n = session.bet
        n1 = prop.N(*manager.locate_account(session.p1_uid, session.group_id))
        n2 = prop.N(*manager.locate_account(session.p2_uid, session.group_id))
        session.data["bet_limit"] = min(n1, n2)
        session.data["bet"] = n
        tip = f"\n本场下注：{n}{prop.name}/次"
    else:
        tip = ""
    return f"哗啦哗啦~，骰子准备完毕{tip}\n{session.create_info()}"


@plugin.handle(["开数"], ["user_id", "group_id"])
@dice.action(place)
async def _(event: Event, session: Session):
    user_id = event.user_id
    if user_id == session.p1_uid:
        nickname = session.p1_nickname
        dice_array = session.data["dice_array1"]
        array_name = session.data["array_name1"]
    else:
        nickname = session.p2_nickname
        dice_array = session.data["dice_array2"]
        array_name = session.data["array_name2"]

    result = f"玩家：{nickname}\n组合：{' '.join(str(x) for x in dice_array)}\n点数：{array_name}"
    if session.round == 2:
        session.double_bet()
        session.win = session.p1_uid if session.data["pt1"] > session.data["pt2"] else session.p2_uid
        return session.end(result)
    session.nextround()
    return result + f"\n下一回合{session.p2_nickname}"
