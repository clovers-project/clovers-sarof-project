import random
from collections import Counter
from clovers_leafgame.main import plugin
from clovers_leafgame.clovers import Event
from clovers_leafgame.output import text_to_image, BytesIO
from ..core import Session, Game, to_int
from .action import place

buckshot_roulette = Game("恶魔轮盘", "向自己开枪|向对方开枪|使用道具")


def buckshot_roulette_random_bullet(bullet_num: int):
    """填装一半的子弹"""
    empty_bullet_num = bullet_num // 2
    real_bullet_num = bullet_num - empty_bullet_num
    bullet = [1] * real_bullet_num + [0] * empty_bullet_num
    random.shuffle(bullet)
    return bullet, real_bullet_num, empty_bullet_num


def buckshot_roulette_random_props(props_num: int):
    prop_list = ["手铐", "短锯", "放大镜", "香烟", "啤酒", "逆转器", "过期药品", "肾上腺素", "手机", "箱子"]
    return random.choices(prop_list, k=props_num)


def buckshot_roulette_status(session: Session):

    result = []
    result.append(f"玩家 {session.p1_nickname}[pixel 340]玩家 {session.p2_nickname}")
    result.append(
        f"血量 [font color=red]{session.data['HP1'] * '♥'}[pixel 340][font color=black]血量 [font color=red]{session.data['HP2'] * '♥'}"
    )
    result.append("----")
    props1 = [f"{k} {v}" for k, v in Counter(session.data["props1"]).items()]
    props2 = [f"[pixel 340]{k} {v}" for k, v in Counter(session.data["props2"]).items()]
    props = [["", ""] for _ in range(max(len(props1), len(props2)))]
    for i, x in enumerate(props1):
        props[i][0] = x
    for i, x in enumerate(props2):
        props[i][1] = x
    result.append("\n".join(x + y for x, y in props))
    output = BytesIO()
    text_to_image("\n".join(result), bg_color="white", width=660).save(output, format="png")
    return output


def buckshot_roulette_loading(session: Session):
    props_num = random.randint(1, 4)
    session.data["props1"] += buckshot_roulette_random_props(props_num)
    session.data["props1"] = session.data["props1"][:8]
    session.data["buff1"].clear()
    session.data["props2"] += buckshot_roulette_random_props(props_num)
    session.data["props2"] = session.data["props2"][:8]
    session.data["buff2"].clear()
    bullet, real_bullet_num, empty_bullet_num = buckshot_roulette_random_bullet(random.randint(2, 8))
    session.data["bullet"] = bullet
    return f"本轮装弹：\n实弹:{real_bullet_num} 空弹:{empty_bullet_num}"


@plugin.handle(["恶魔轮盘"], ["user_id", "group_id", "at"], priority=1)
@buckshot_roulette.create(place)
async def _(session: Session, arg: str):
    hp = to_int(arg)
    if hp is None or hp > 6 or hp < 3:
        hp = random.randint(3, 6)
        tip = ""
    else:
        tip = f"\n本轮对决已设置血量：{hp}"
    session.data["HP_MAX"] = hp
    session.data["HP1"] = hp
    session.data["HP2"] = hp
    session.data["buff1"] = set()
    session.data["buff2"] = set()
    session.data["props1"] = []
    session.data["props2"] = []
    if session.bet:
        prop, n = session.bet
        tip += f"\n本场下注：{n}{prop.name}/轮"
    session.start_tips = [buckshot_roulette_loading(session), buckshot_roulette_status(session)]
    return f"【恶魔轮盘】游戏已创建。{tip}\n{session.create_info()}"


@plugin.handle(["向自己开枪", "向对方开枪"], ["user_id", "group_id"])
@buckshot_roulette.action(place)
async def _(event: Event, session: Session):
    user_id = event.user_id
    bullet = session.data["bullet"]
    current_bullet = bullet[0]
    bullet = bullet[1:]
    if user_id == session.p1_uid:
        hp_self = "HP1"
        hp_others = "HP2"
        buff = "buff1"
    else:
        hp_self = "HP2"
        hp_others = "HP1"
        buff = "buff2"
    target = event.raw_command[1:3]
    hp = hp_self if target == "自己" else hp_others

    def remove_tag(buffs: set[str], tag: str):
        if tag in buffs:
            buffs.remove(tag)
            return True
        else:
            return False

    if remove_tag(session.data[buff], "短锯"):
        current_bullet *= 2
    session.data[hp] -= current_bullet
    result = []
    if current_bullet:
        result.append(f"砰的一声炸响，子弹的击中了{target}")
    else:
        result.append("扣动板机，发出清脆的敲击声...")

    if session.data[hp] <= 0:
        session.win = session.p1_uid if hp == "HP2" else session.p2_uid
        return session.end(result[0])

    if not bullet:
        result.append("最后一发子弹已打出。")
        result.append(buckshot_roulette_loading(session))
    else:
        session.data["bullet"] = bullet

    if (target == "自己" and current_bullet == 0) or remove_tag(session.data[buff], "手铐"):
        session.delay()
    else:
        session.nextround()
    next_name = session.p1_nickname if session.next == session.p1_uid else session.p2_nickname
    result.append(f"请下一位玩家：{next_name}\n{buckshot_roulette.action_tip}")
    return ["\n".join(result), buckshot_roulette_status(session)]


@plugin.handle(["使用道具"], ["user_id", "group_id"])
@buckshot_roulette.action(place)
async def _(event: Event, session: Session):
    prop_key = event.single_arg()
    prop_tips = {
        "手铐": "对方一回合无法行动",
        "短锯": "本发子弹伤害翻倍",
        "放大镜": "查看本发子弹",
        "香烟": "增加1点血量",
        "啤酒": "退一发子弹",
        "逆转器": "转换当前枪膛里面的子弹真假",
        "过期药品": "50%的概率回两滴血，剩下的概率扣一滴血",
        "肾上腺素": "偷取对方的道具并立即使用",
        "手机": "查看接下来第n发子弹真假",
        "箱子": "每人抽取一件道具",
    }
    if not prop_key or prop_key not in prop_tips:
        return
    session.delay()

    def use(session: Session, prop_key: str):

        if session.next == session.p1_uid:
            self_key = "1"
            others_key = "2"
        else:
            self_key = "2"
            others_key = "1"
        props = f"props{self_key}"
        if prop_key not in session.data[props]:
            return f"你未持有道具【{prop_key}】"
        session.data[props].remove(prop_key)
        tips = "效果：" + prop_tips[prop_key]

        match prop_key:
            case "手铐" | "短锯":
                session.data[f"buff{self_key}"].add(prop_key)
            case "放大镜":
                tips += f"\n本发是：{'空弹' if session.data['bullet'][0] == 0 else '实弹'}"
            case "香烟":
                hp = f"HP{self_key}"
                session.data[hp] += 1
                session.data[hp] = min(session.data[hp], session.data["HP_MAX"])
                tips += f"\n你的血量：{session.data[hp]}"
            case "啤酒":
                tips += f"\n你退掉了一发：{'空弹' if session.data['bullet'][0] == 0 else '实弹'}"
                session.data["bullet"] = session.data["bullet"][1:]
                if not session.data["bullet"]:
                    return [f"最后一发子弹已被退出。\n{tips}\n{buckshot_roulette_loading(session)}", buckshot_roulette_status(session)]
            case "逆转器":
                session.data["bullet"][0] = 1 - session.data["bullet"][0]
            case "过期药品":
                hp = f"HP{self_key}"
                if random.randint(0, 1) == 0:
                    tips += "\n你减少了1滴血"
                    session.data[hp] -= 1
                    if session.data[hp] <= 0:
                        session.win = getattr(session, f"p{others_key}_uid")
                        return session.end(tips)
                else:
                    tips += "\n你增加了2滴血"
                    session.data[hp] += 2
                    session.data[hp] = min(session.data[hp], session.data["HP_MAX"])
            case "肾上腺素":
                if len(event.args) < 2:
                    return tips + "\n使用失败，你未指定对方的道具"
                inner_prop_key = event.args[1]
                if inner_prop_key == prop_key:
                    return tips + "\n使用失败，目标不能是肾上腺素"
                others_props = f"props{others_key}"
                if inner_prop_key not in session.data[others_props]:
                    return tips + f"\n使用失败，对方未持有道具{inner_prop_key}"
                session.data[others_props].remove(inner_prop_key)
                session.data[props].append(inner_prop_key)
                return use(session, inner_prop_key)
            case "手机":
                bullet = session.data["bullet"]
                sum_bullet = len(bullet)
                sum_real_bullet = sum(bullet)
                sum_empty_bullet = sum_bullet - sum_real_bullet
                random_index = random.randint(1, sum_bullet)
                tips += f"\n弹仓内还有{sum_real_bullet}发实弹,{sum_empty_bullet}发空弹\n接下来第{random_index}发是：{'空弹' if bullet[random_index-1] == 0 else '实弹'}"
            case "箱子":
                prop1, prop2 = buckshot_roulette_random_props(2)
                session.data[props].append(prop1)
                session.data[props] = session.data[props][:8]
                others_props = f"props{others_key}"
                session.data[others_props].append(prop2)
                session.data[others_props] = session.data[others_props][:8]
                tips += f"\n你获得了{prop1}\n对方获得了{prop2}"
            case _:
                assert False, "玩家持有无法使用的道具"
        return tips

    return use(session, prop_key)
