import random
from typing import TypedDict
from ..action import place, Event
from ..core import Session as BaseSession, to_int

game = "俄罗斯轮盘"
place.info[game] = "开枪"


class SessionData(TypedDict):
    bullet: list[int]
    index: int


type Session = BaseSession[SessionData]


@place.create(game, ["俄罗斯轮盘", "装弹"])
async def _(session: Session, arg: str):
    bullet_num = to_int(arg)
    if bullet_num:
        bullet_num = random.randint(1, 6) if bullet_num < 1 or bullet_num > 6 else bullet_num
    else:
        bullet_num = 1
    bullet = [0, 0, 0, 0, 0, 0, 0]
    for i in random.sample([0, 1, 2, 3, 4, 5, 6], bullet_num):
        bullet[i] = 1
    session.data = {"bullet": bullet, "index": 0}
    session.end_tips = str(bullet)
    return f"{' '.join('咔' for _ in range(bullet_num))}，装填完毕\n第一枪的概率为：{bullet_num * 100 / 7 :.2f}%\n{session.create_info}"


@place.action(game, ["开枪"])
async def _(event: Event, session: Session):
    index = session.data["index"]
    MAG = session.data["bullet"][index:]
    user_id = event.user_id
    count = event.args_to_int() or 1
    l_MAG = len(MAG)
    if count < 0 or count > l_MAG:
        count = l_MAG
    shot_tip = f"连开{count}枪！\n" if count > 1 else ""
    if any(MAG[:count]):
        session.win = session.p1_uid if session.p2_uid == user_id else session.p2_uid
        random_tip = random.choice(["嘭！，你直接去世了", "眼前一黑，你直接穿越到了异世界...(死亡)", "终究还是你先走一步..."])
        result = f"{shot_tip}{random_tip}\n第 {index + MAG.index(1) + 1} 发子弹送走了你..."
        return session.end(result)
    else:
        session.nextround()
        session.data["index"] += count
        next_name = session.p1_nickname if session.next == session.p1_uid else session.p2_nickname
        random_tip = random.choice(
            [
                "呼呼，没有爆裂的声响，你活了下来",
                "虽然黑洞洞的枪口很恐怖，但好在没有子弹射出来，你活下来了",
                "看来运气不错，你活了下来",
            ]
        )
        return f"{shot_tip}{random_tip}\n下一枪中弹的概率：{len(session.data["bullet"]) * 100 / (l_MAG - count):.2f}%\n接下来轮到{next_name}了..."
