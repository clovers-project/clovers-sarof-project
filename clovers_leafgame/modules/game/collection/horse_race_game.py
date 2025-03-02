import asyncio
from clovers_leafgame.main import plugin, manager
from clovers_leafgame.core.clovers import Event
from clovers_leafgame.output import text_to_image, BytesIO
from ..core import Session, Game
from .action import place
from .horse_race import RaceWorld

horse_race_game = Game("赛马小游戏", "赛马加入 名字")


@plugin.handle(["赛马创建"], ["user_id", "group_id", "at"], priority=1)
@horse_race_game.create(place)
async def _(session: Session, arg: str):
    session.at = session.p1_uid
    if session.bet:
        prop, n = session.bet
        tip = f"\n> 本场奖金：{n}{prop.name}"
    else:
        tip = ""
    session.data["world"] = RaceWorld()
    return f"> 创建赛马比赛成功！{tip},\n> 输入 【赛马加入 名字】 即可加入赛马。"


@plugin.handle(["赛马加入"], ["user_id", "group_id", "nickname"])
async def _(event: Event):
    if not (session := horse_race_game.session_check(place, event.group_id)):
        return
    if session.game.name != horse_race_game.name:
        return
    user, account = manager.account(event)
    if session.bet:
        prop, n = session.bet
        if account.bank[prop.id] < n:
            return f"报名赛马需要{n}个{prop.name}（你持有的的数量{account.bank[prop.id]}）"
    world: RaceWorld = session.data["world"]
    horsename = event.single_arg()
    if not horsename:
        return "请输入你的马儿名字"
    return world.join_horse(horsename, account.user_id, account.name)


@plugin.handle(["赛马开始"], ["user_id", "group_id", "Bot_Nickname"])
async def _(event: Event):
    group_id = event.group_id
    if not (session := horse_race_game.session_check(place, group_id)):
        return
    if session.game.name != horse_race_game.name:
        return
    world = session.data["world"]
    assert isinstance(world, RaceWorld)
    if world.status == 1:
        return
    player_count = len(world.racetrack)
    if player_count < world.min_player_numbers:
        return f"开始失败！赛马开局需要最少{world.min_player_numbers}人参与"
    world.status = 1

    async def result():
        if session.bet:
            prop, n = session.bet
            for horse in world.racetrack:
                bank = prop.locate_bank(*manager.locate_account(horse.playeruid, group_id))
                bank[prop.id] -= n
            tip = f"\n> 当前奖金：{n}{prop.name}"
        else:
            tip = ""
        yield f"> 比赛开始！{tip}"
        empty_race = ["[  ]" for _ in range(world.max_player_numbers - player_count)]
        await asyncio.sleep(1)
        while world.status == 1:
            round_info = world.nextround()
            racetrack = [horse.display(world.track_length) for horse in world.racetrack]
            output = BytesIO()
            text_to_image("\n".join(racetrack + empty_race), font_size=30, width=0, bg_color="white").save(output, format="png")
            yield [round_info, output]
            await asyncio.sleep(0.5 + int(0.06 * len(round_info)))
            # 全员失败计算
            if world.is_die_all():
                session.time = 0
                yield "比赛已结束，鉴定为无马生还"
                return
            # 全员胜利计算
            if winer := [horse for horse in world.racetrack if horse.location == world.track_length - 1]:
                yield f"> 比赛结束\n> {event.Bot_Nickname}正在为您生成战报..."
                await asyncio.sleep(1)
                if session.bet:
                    winer_list = []
                    prop, n = session.bet
                    n = int(n * len(world.racetrack) / len(winer))
                    for win_horse in winer:
                        winer_list.append(f"> {win_horse.player}")
                        bank = prop.locate_bank(*manager.locate_account(horse.playeruid, group_id))
                        bank[prop.id] += n
                    bet = f"\n奖金：{n}{prop.name}"
                else:
                    winer_list = [f"> {win_horse.player}" for win_horse in winer]
                    bet = ""

                winer_list = "\n".join(winer_list)
                session.time = 0
                yield f"> 比赛已结束，胜者为：\n{winer_list}{bet}"
                return
            await asyncio.sleep(1)

    return result()
