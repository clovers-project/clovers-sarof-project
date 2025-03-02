import random
from clovers_leafgame.main import plugin
from clovers_leafgame.core.clovers import Event
from ..core import Session, Game
from .action import place


def bohemia_show_array(array: list[int]):
    return " | ".join(f"{i}.【{d}】" for i, d in enumerate(array, start=1))


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
                pt = 750
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


bohemia_dice = Game("天国骰子", "123456 继续|结束")


@plugin.handle(["天国骰子"], ["user_id", "group_id", "at"], priority=1)
@bohemia_dice.create(place)
async def _(session: Session, arg: str):
    session.data["pt1"] = 0
    session.data["pt1_table"] = 0
    array = first_random_dice()
    session.data["array1"] = array
    session.data["alive1"] = 6
    session.data["pt2"] = 500
    session.data["pt2_table"] = 0
    session.data["array2"] = None
    session.data["alive2"] = 6
    if session.bet:
        prop, n = session.bet
        tip = f"\n本场下注：{n}{prop.name}/轮"
    else:
        tip = ""
    session.start_tips = f"桌面 {bohemia_show_array(array)}"
    return f"【天国骰子】游戏已创建。{tip}\n{session.create_info()}"


@plugin.handle(r"([1-6]+) ?(继续|结束)", ["user_id", "group_id"])
@bohemia_dice.action(place)
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
    array = session.data[array_self]

    try:
        choise_array: list[int] = [session.data[array_self][i - 1] for i in map(int, set(choise))]
    except IndexError:
        return

    pt, actN = bohemia_dice_pt(choise_array)
    if pt == 0:
        return
    session.data[pt_table_self] += pt
    tip = (
        f"你选择了 {bohemia_show_array(choise_array)}\n"
        "目标分数 4000\n"
        f"对方分数 {session.data[pt_others]}\n"
        f"自己分数 {session.data[pt_self]}\n"
        f"本轮分数 {session.data[pt_table_self]}"
    )
    if cmd == "继续":
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
                "继续...\n"
                f"桌面 {bohemia_show_array(next_array)}\n"
                "本轮失败！\n"
                f"下一个玩家：{next_user}\n"
                f"桌面 {bohemia_show_array(next2_array)}"
            )
        else:
            session.delay()
            return f"{tip}\n继续...\n桌面 {bohemia_show_array(next_array)}"
    else:
        session.data[pt_self] += session.data[pt_table_self]
        session.data[pt_table_self] = 0
        if session.data[pt_self] >= 4000:
            session.win = user_id
            return session.end(f"{tip}\n结束...\n桌面 {bohemia_show_array(array)}")
        session.data[alive_others] = 6
        session.data[array_others] = next_array = first_random_dice()
        session.nextround()
        return f"{tip}\n结束...\n下一个玩家：{next_user}\n桌面 {bohemia_show_array(next_array)}"
