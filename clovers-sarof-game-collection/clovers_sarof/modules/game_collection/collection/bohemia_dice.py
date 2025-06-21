import random
from typing import TypedDict
from ..action import place, Event
from ..core import Session as BaseSession

game = "天国骰子"
place.info[game] = "123456 继续|结束"


class SessionData(TypedDict):
    pt1: int
    pt1_table: int
    array1: list[int]
    alive1: int
    pt2: int
    pt2_table: int
    array2: list[int]
    alive2: int
    last_round: bool


type Session = BaseSession[SessionData]


@place.create(game, ["天国骰子"])
async def _(session: Session, arg: str):
    array = first_random_dice()
    session.data = {
        "pt1": 0,
        "pt1_table": 0,
        "array1": array,
        "alive1": 6,
        "pt2": 0,
        "pt2_table": 0,
        "array2": [],
        "alive2": 6,
        "last_round": False,
    }
    session.start_tips = f"桌面：\n{bohemia_show_array(array)}"
    return f"【天国骰子】游戏已创建。\n{session.create_info}"


@place.action(game, r"([1-6]+) ?(继续|结束)")
async def _(event: Event, session: Session):
    user_id = event.user_id
    if user_id == session.p1_uid:
        next_user = session.p2_nickname
        pt_self = "pt1"
        pt_table_self = "pt1_table"
        alive_self = "alive1"
        array_self = "array1"
        pt_others = "pt2"
        array_others = "array2"
        alive_others = "alive2"
    else:
        next_user = session.p1_nickname
        pt_self = "pt2"
        pt_table_self = "pt2_table"
        array_self = "array2"
        alive_self = "alive2"
        pt_others = "pt1"
        array_others = "array1"
        alive_others = "alive1"
    choise, cmd = event.args
    try:
        choise_array: list[int] = [session.data[array_self][i - 1] for i in map(int, set(choise))]
    except IndexError:
        return
    pt, actN = bohemia_dice_pt(choise_array)
    if pt == 0:
        return
    last_pt = session.data[pt_table_self]
    session.data[pt_table_self] = last_pt + pt
    if cmd == "继续":
        tip = (
            f"你选择了：\n{bohemia_show_array(choise_array)}\n"
            "目标分数：4000\n"
            f"对方分数：{session.data[pt_others]}\n"
            f"自己分数：{session.data[pt_self]}(+{session.data[pt_table_self]})\n"
            f"本轮分数：{last_pt} + {pt}\n"
            "继续..."
        )
        if session.data[alive_self] == actN:
            session.data[alive_self] = 6
        else:
            session.data[alive_self] -= actN
        next_array = session.data[array_self] = [random.randint(1, 6) for _ in range(session.data[alive_self])]
        if bohemia_dice_pt(next_array)[0] == 0:
            session.data[pt_table_self] = 0
            session.data[alive_others] = 6
            session.data[array_others] = next2_array = first_random_dice()
            session.nextround()
            return (
                f"{tip}\n"
                f"桌面：\n{bohemia_show_array(next_array)}\n"
                "本轮失败！\n"
                f"下一个玩家：{next_user}\n"
                f"桌面：\n{bohemia_show_array(next2_array)}"
            )
        else:
            session.delay()
            return f"{tip}\n桌面：\n{bohemia_show_array(next_array)}"
    else:
        session.data[pt_self] += session.data[pt_table_self]
        tip = (
            f"你选择了：\n{bohemia_show_array(choise_array)}\n"
            "目标分数 4000\n"
            f"对方分数 {session.data[pt_others]}\n"
            f"自己分数 {session.data[pt_self]}\n"
            f"本轮分数 {last_pt} + {pt}\n"
            "结束..."
        )
        session.data[pt_table_self] = 0
        if session.data["last_round"]:
            session.win = session.p1_uid if session.data["pt1"] > session.data["pt2"] else session.p2_uid
            return session.end(tip)
        if session.data[pt_self] >= 4000:
            if user_id == session.p2_uid:
                session.win = user_id
                return session.end(tip)
            else:
                session.data["last_round"] = True
                tip += "\n先手已超分，本轮为最后一轮！"
        session.data[alive_others] = 6
        session.data[array_others] = next_array = first_random_dice()
        session.nextround()
        return f"{tip}\n下一个玩家：{next_user}\n桌面：\n{bohemia_show_array(next_array)}"


dice_charlist = [" ", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]


def bohemia_show_array(array: list[int]):
    output = [f"{i} [{dice_charlist[d]}] " for i, d in enumerate(array, start=1)]
    if len(array) > 3:
        output.insert(3, "\n")
    return "".join(output)


def bohemia_dice_pt(array: list[int]):
    """array长度1-6"""
    array_set = set(array)

    def straight_rest(array: list[int]):
        if array.count(1) == 2:
            return 100
        elif array.count(5) == 2:
            return 50
        else:
            return 0

    match len(array_set):
        case 6:
            return 1500, 6
        case 5:
            if 6 not in array_set:
                pt = 500 + straight_rest(array)
                return pt, 5 + int(pt != 500)
            elif 1 not in array_set:
                pt = 750 + straight_rest(array)
                return pt, 5 + int(pt != 750)
            else:
                x = array.count(1)
                y = array.count(5)
                return x * 100 + y * 50, x + y
    actN = 0
    pt = 0
    n = array.count(1)
    if n > 2:
        actN += n
        pt += 1000 * (2 ** (n - 3))
    elif n > 0:
        actN += n
        pt += 100 * n
    n = array.count(5)
    if n > 2:
        actN += n
        pt += 500 * (2 ** (n - 3))
    elif n > 0:
        actN += n
        pt += 50 * n
    for i in [2, 3, 4, 6]:
        n = array.count(i)
        if n > 2:
            actN += n
            pt += i * 100 * (2 ** (n - 3))
    return pt, actN


def first_random_dice():
    while bohemia_dice_pt(array := [random.randint(1, 6) for _ in range(6)])[0] == 0:
        pass
    return array
