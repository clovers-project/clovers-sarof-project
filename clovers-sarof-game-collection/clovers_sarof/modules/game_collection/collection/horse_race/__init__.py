import asyncio
from io import BytesIO
from clovers.config import Config as CloversConfig
from clovers_sarof.core.linecard import text_to_image
from clovers_sarof.core import manager
from ...action import place, Event, Rule
from ...core import Session
from .core import RaceWorld
from .config import Config

config_data = CloversConfig.environ().setdefault(__package__, {})
__config__ = Config.model_validate(config_data)
"""主配置类"""
config_data.update(__config__.model_dump())

track_length = __config__.setting_track_length
base_move_range = __config__.base_move_range
random_move_min, random_move_max = __config__.random_move_range
random_move_range = int(random_move_min * track_length), int(random_move_max * track_length)
range_of_player_numbers = __config__.range_of_player_numbers
event_randvalue = __config__.event_randvalue
kwargs = {
    "track_length": track_length,
    "base_move_range": base_move_range,
    "random_move_range": random_move_range,
    "range_of_player_numbers": range_of_player_numbers,
    "event_randvalue": event_randvalue,
}

game = "赛马小游戏"
place.info[game] = "赛马加入 名字"


@place.create(game, ["赛马创建"])
async def _(session: Session, arg: str):
    session.at = session.p1_uid
    if session.bet:
        prop, n = session.bet
        tip = f"\n> 本场奖金：{n}{prop.name}"
    else:
        tip = ""
    session.data["world"] = RaceWorld(**kwargs)
    return f"> 创建赛马比赛成功！{tip},\n> 输入 【赛马加入 名字】 即可加入赛马。"


@place.plugin.handle(["赛马加入"], ["user_id", "group_id", "nickname"], rule=Rule.group)
async def _(event: Event):
    group_id: str = event.group_id  # type: ignore
    session = place.session(group_id)
    if session is None:
        return
    if session.game != game:
        return
    horsename = event.single_arg()
    if not horsename:
        return "请输入你的马儿名字"
    if session.bet:
        item, n = session.bet
        with manager.db.session as sql_session:
            account = manager.account(event, sql_session)
            assert account is not None
            if (bn := item.bank(account, sql_session).n) < n:
                return f"报名赛马需要{n}个{item.name}（你持有的的数量{bn}）"
    world: RaceWorld = session.data["world"]
    return world.join_horse(horsename, account.user_id, account.name)


@place.plugin.handle(["赛马开始"], ["user_id", "group_id"])
async def _(event: Event):
    group_id: str = event.group_id  # type: ignore
    session = place.session(group_id)
    if session is None:
        return
    if session.game != game:
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
            item, n = session.bet
            with manager.db.session as sql_session:
                for horse in world.racetrack:
                    player = manager.db.account(horse.playeruid, group_id, sql_session)
                    bank = item.bank(player, sql_session)
                    if bank.n >= n:
                        bank.n -= n
                    else:
                        bank.n = 0  # 金额不足的 bot 免费提供补齐。此处为特性（
            yield f"> 比赛开始！\n> 当前奖金：{n}{item.name}"
        else:
            yield f"> 比赛开始！"
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
            if winner := [horse for horse in world.racetrack if horse.location == world.track_length - 1]:
                yield f"> 比赛结束\n> 正在为您生成战报..."
                await asyncio.sleep(1)
                if session.bet:
                    winner_list = []
                    item, n = session.bet
                    n = int(n * len(world.racetrack) / len(winner))
                    with manager.db.session as sql_session:
                        for win_horse in winner:
                            winner_list.append(f"> {win_horse.player}")
                            player = manager.db.account(win_horse.playeruid, group_id, sql_session)
                            item.deal(player, n, sql_session)
                    bet = f"\n奖金：{n}{item.name}"
                else:
                    winner_list = [f"> {win_horse.player}" for win_horse in winner]
                    bet = ""
                winer_list = "\n".join(winner_list)
                session.time = 0
                yield f"> 比赛已结束，胜者为：\n{winer_list}{bet}"
                return
            await asyncio.sleep(1)

    return result()
