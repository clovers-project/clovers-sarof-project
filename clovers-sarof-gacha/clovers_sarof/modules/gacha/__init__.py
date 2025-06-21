import time
import random
import asyncio
from collections import Counter
from clovers import TempHandle
from clovers.config import Config as CloversConfig
from clovers_sarof.core import __plugin__ as plugin, Event, Rule
from clovers_sarof.core import manager
from clovers_sarof.core import GOLD, STD_GOLD
from clovers_sarof.core.account import Session, Item, Stock, Account, AccountBank, UserBank
from clovers_sarof.core.linecard import card_template, item_card
from clovers_sarof.core.tools import format_number
from .core import pool, usage, AIR_PACK, RED_PACKET, VIP_CARD
from .image import report_card
from .config import Config

config_data = CloversConfig.environ().setdefault(__package__, {})
__config__ = Config.model_validate(config_data)
"""主配置类"""
config_data.update(__config__.model_dump())

gacha_gold = __config__.gacha_gold
packet_gold = __config__.packet_gold
luckey_min, luckey_max = __config__.luckey_coin
ticket_price = gacha_gold * 50


@plugin.handle(
    r"^(.+)连抽?卡?|单抽",
    ["user_id", "group_id", "nickname", "to_me"],
    rule=Rule.to_me,
)
async def _(event: Event):
    count = event.args_to_int()
    if not count:
        return
    count = 200 if count > 200 else 1 if count < 1 else count
    cost_gold = count * gacha_gold
    with manager.db.session as session:
        account = manager.account(event, session)
        if account is None:
            return "无法在当前会话创建账户。"
        if (tn := GOLD.deal(account, -cost_gold, session)) is not None:
            return f"{count}连抽卡需要{cost_gold}金币，你的金币：{tn}。"
        prop_data: list[list[tuple[Item, int]]] = [[], [], []]
        report_data = {"prop_star": 0, "prop_n": 0, "air_star": 0, "air_n": 0}
        for prop, n in Counter(pool.gacha() for _ in range(count)).items():
            prop_data[prop.domain].append((prop, n))
            if prop.domain == 0:
                star_key = "air_star"
                n_key = "air_n"
            else:
                star_key = "prop_star"
                n_key = "prop_n"
                prop.deal(account, n, session)
            report_data[star_key] += prop.rare * n
            report_data[n_key] += n
        if count < 10:
            return "你获得了" + "\n".join(f"({prop.rare}☆){prop.name}:{n}个" for seg in prop_data for prop, n in seg)
        else:
            info = [report_card(account.nickname, **report_data)]
            if report_data["prop_n"] == 0:
                AIR_PACK.deal(account, 1, session)
                RED_PACKET.deal(account, 10, session)
                GOLD.deal(account, cost_gold, session)
                info.append(card_template(item_card([(AIR_PACK, 1), (GOLD, cost_gold), (RED_PACKET, 10)]), f"本次抽卡已免费"))
            air_prop, local_prop, global_prop = prop_data
            if global_prop:
                info.append(card_template(item_card(global_prop), f"全局道具"))
            if local_prop:
                info.append(card_template(item_card(local_prop), f"群内道具"))
            if air_prop:
                info.append(card_template(item_card(air_prop), f"未获取"))
        return manager.info_card(info, event.user_id)


@usage("金币")
def _(account: Account, session: Session, item: Item, count: int, extra: str):
    return f"你使用了{count}枚{item.name}。"


@usage("测试金库")
def _(account: Account, session: Session, item: Item, count: int, extra: str):
    return f"你获得了{format_number(count * 1000000000)}金币，{format_number(count * 1000000)}钻石。祝你好运！"


@usage("空气礼包")
def _(account: Account, session: Session, item: Item, count: int, extra: str):
    data = []
    for air_item in manager.items_library.values():
        if air_item.domain != 0:
            continue
        air_item.deal(account, count, session)
        data.append((air_item, count))
    return ["你获得了", manager.info_card([card_template(item_card(data), "空气礼包")], account.user_id)]


@usage("随机红包")
def _(account: Account, session: Session, item: Item, count: int, extra: str):
    gold = random.randint(*packet_gold) * count
    GOLD.deal(account, gold, session)
    return f"你获得了{gold}金币。祝你好运~"


@usage("重开券")
def _(account: Account, session: Session, item: Item, count: int, extra: str):
    account.cancel(session)
    return "你在本群的账户已重置，祝你好运~"


async def recv_red_packet(event: Event, handle: TempHandle):
    handle.finish()
    with manager.db.session as session:
        account = manager.account(event, session)
        if account is None:
            return "领取失败...未找到你的账户。"
        RED_PACKET.deal(account, 1, session)
        return f"领取成功，你已获得1个{RED_PACKET.name}"


@usage("幸运硬币", 1)
def _(account: Account, session: Session, item: Item, count: int, extra: str):
    info = []
    bet_item = manager.items_library.get(extra.strip(), GOLD)
    if count < luckey_min:
        count = luckey_min
    elif count > luckey_max:
        info.append(f"不要过于依赖幸运哦!\n已将数量调整为{luckey_max}个")
        count = luckey_max
    bank = bet_item.bank(account, session)
    if random.randint(0, 1) == 0:
        if bank.n == 0:
            RED_PACKET.deal(account, 1, session)
            info.append(f"结果是正面！\n但你未持有{bet_item.name}...\n送你1个『{RED_PACKET.name}』，祝你好运~")
        else:
            session.add(bank)
            if bank.n < count:
                count = bank.n
                info.append(f"你没有足够数量的{bet_item.name}...\n已将数量调整为持有个数（{count}）")
            bank.n += count
            info.append(f"结果是正面！\n恭喜你获得了{count}个{bet_item.name}")
    else:
        if bank.n == 0:
            info.append(f"结果是反面...\n但你未持有{bet_item.name}...\n逃过一劫了呢，祝你好运~")
        elif bank.n < count:
            count = bank.n
            bank.n = 0
            info.append(f"结果是反面...\n你没有足够数量的{bet_item.name}...\n全部拿出来吧！（{count}）")
        else:
            bank.n -= count
            info.append(f"结果是反面...\n你你失去了{count}个{bet_item.name}...")
            if random.randint(0, 1) == 0:
                user_id = account.user_id
                group_id = account.group_id
                rule: list[Rule.Checker] = [Rule.identify(user_id, group_id), lambda event: event.message == "领取红包"]
                plugin.temp_handle(["user_id", "group_id", "nickname"], rule=rule)(recv_red_packet)
    session.commit()
    return "\n".join(info)


@usage("道具兑换券", 0)
def _(account: Account, session: Session, item: Item, count: int, extra: str):
    if extra:
        item_name = extra.strip()
        if (item_t := manager.items_library.get(item_name)) is None:
            return f"不存在道具【{item_name}】"
        if item_t.rare < 3:
            return f"无法兑换【{item_t.name}】"
    else:
        item_t = item
    # 购买道具兑换券，价格 50抽
    ticket_bank = item.bank(account, session)
    tips = []
    if count > ticket_bank.n:
        cost = ticket_price * (count - ticket_bank.n)
        tips.append(f"你的{item.name}数量不足,将使用{cost}{GOLD.name}购买（单价：{ticket_bank}）。")
        if VIP_CARD.bank(account, session).n > 0:
            discount = int(cost * 0.2)
            tips.append(f"【{VIP_CARD.name}】20%off （-{discount}）")
            cost -= discount
        if tn := GOLD.deal(account, -cost, session):
            tips.append(f"金币不足。你还有{tn}枚金币。（需要：{cost}）")
            return "\n".join(tips)
        ticket_bank.n = 0
    else:
        cost = None
        ticket_bank.n -= count
    session.add(ticket_bank)
    item_t.deal(account, count, session)
    tips.append(f"你获得了{count}个【{item_t.name}】！")
    return "\n".join(tips)


# @usage("绯红迷雾之书", 1)
# def _(account: Account, session: Session, item: Item, count: int, extra: str):
#     folders = {f.name: f for f in manager.backup_path.iterdir() if f.is_dir()}
#     user_id = account.user_id
#     group_id = account.group_id
#     rule: list[Rule.Checker] = [Rule.identify(user_id, group_id), lambda event: event.message in folders]
#     plugin.temp_handle(["user_id", "group_id"], rule=rule, state=folders)(choise_date)
#     return "请输入你要回档的日期:\n" + "\n".join(folders.keys())


# async def choise_date(event: Event, handle: TempHandle):
#     handle.finish()
#     folders: dict[str, Path] = handle.state  # type: ignore
#     folder = folders[event.message]
#     files = {f.stem.split()[1].replace("-", ":"): f for f in folder.iterdir() if f.is_file()}
#     user_id = event.user_id
#     group_id = event.group_id
#     assert user_id and group_id
#     rule: list[Rule.Checker] = [Rule.identify(user_id, group_id), lambda event: event.message in files]
#     plugin.temp_handle(["user_id", "group_id"], rule=rule, state=files)(choise_time)
#     return "请输入你要回档的时间:\n" + "\n".join(files.keys())


# async def choise_time(event: Event, handle: TempHandle):
#     handle.finish()
#     files: dict[str, Path] = handle.state  # type: ignore
#     file = files[event.message]
#     raise NotImplementedError("无法实现数据库回档")


@usage("恶魔轮盘", 1)
def _(account: Account, session: Session, item: Item, count: int, extra: str):
    user_id = account.user_id
    group_id = account.group_id
    rule: list[Rule.Checker] = [Rule.identify(user_id, group_id), lambda event: event.message in ("开枪", "取消")]
    plugin.temp_handle(["user_id", "group_id"], rule=rule, state=(account.id, item.id))(devil_shoot)
    return "你手中的左轮枪已经装好了子弹，请开枪，或者取消。"


async def devil_shoot(event: Event, handle: TempHandle):
    handle.finish()
    message = event.message
    if message == "取消":
        return f"你取消了恶魔轮盘"

    async def result():
        bullet_lst = [0, 0, 0, 0, 0, 0]
        for i in random.sample([0, 1, 2, 3, 4, 5], random.randint(0, 6)):
            bullet_lst[i] = 1
        if bullet_lst[0] == 1:
            yield "砰！一团火从枪口喷出，你从这个世界上消失了。"
            with manager.db.session as session:
                user = manager.db.user(event.user_id, session)
                user.cancel(session)
        else:
            yield "咔！你活了下来..."
            with manager.db.session as session:
                counter = Counter[str]()
                for bank in session.exec(UserBank.select().where(UserBank.bound_id == event.user_id)):
                    item_id = bank.item_id
                    if item_id.startswith("item:"):
                        counter[item_id] += bank.n * 10
                    elif item_id.startswith("stock:"):
                        stock = session.get(Stock, bank.item_id)
                        if stock is None:
                            session.delete(stock)
                        else:
                            valuation = int(stock.price * bank.n * 10)
                            counter[STD_GOLD.id] += valuation
                for bank in session.exec(
                    AccountBank.select()
                    .join(Account)
                    .where(
                        Account.user_id == event.user_id,
                        AccountBank.item_id.startswith("item:"),
                    )
                ):
                    counter[bank.item_id] += bank.n * 10
                account_id: int
                item_id: str
                account_id, item_id = handle.state  # type: ignore
                counter[item_id] = 1
                account = session.get(Account, account_id)
                if account is None:
                    return
                data: list[tuple[Item, int]] = []
                for item_id, n in counter.items():
                    item = manager.items_library.get(item_id)
                    if item is None:
                        continue
                    item.deal(account, n, session)
                    data.append((item, n))
                session.commit()
            data.sort(key=lambda x: x[0].rare)
            yield ["这是你获得的道具", manager.info_card([card_template(item_card(data), "10倍奖励")], event.user_id)]
            await asyncio.sleep(0.5)
        yield f"装弹列表：{" ".join(str(x) for x in bullet_lst)}"

    return result()


@usage("无名木箱", 0)
@usage("开锁器", 0)
def _(account: Account, session: Session, item: Item, count: int, extra: str):
    item_case = manager.items_library["无名木箱"]
    if (case_bank := item_case.bank(account, session)).n < 1:
        return "你未持有无名木箱"
    item_key = manager.items_library["开锁器"]
    if (key_bank := item_key.bank(account, session)).n < 1:
        return "你未持有开锁器"
    if count == 1:
        count = 4
    elif count > 6 or count < 4:
        return "只支持4-6位密码"
    case_bank.n -= 1
    key_bank.n -= 1
    session.add(case_bank)
    session.add(key_bank)
    session.commit()
    rule: Rule.Checker = lambda e: e.user_id == account.user_id
    code = [random.randint(0, 9) for _ in range(count)]
    plugin.temp_handle(["user_id", "group_id", "nickname"], timeout=180, rule=rule, state=(account.id, code, []))(unlock_case)
    return (
        "请在180秒内输入正确的密码！你有10次输入密码的机会，超时或机会用完或导致失败。输入【取消】则会停止解锁。\n"
        f"请输入{count}位密码：{'|'.join('❓'*count)}"
    )


async def unlock_case(event: Event, handle: TempHandle):
    """✅❌🟠🟢❓"""
    account_id: int
    code: list[int]
    log: list[str]
    account_id, code, log = handle.state  # type: ignore
    with manager.db.session as session:
        account = manager.account(event, session)
        if account is None or account.id != account_id:
            return
    if event.message == "取消":
        handle.finish()
        return "取消解锁！"
    inputs_code = event.message[: len(code)]
    if not inputs_code.isdigit():
        return "请输入数字！"
    _pv = 0
    _v = 0
    _w = 0
    show_code = []
    flag = True
    for i, c in enumerate(inputs_code):
        n = int(c)
        if n == code[i]:
            _pv += 1
            show_code.append(f"{i+1}✅")
        elif n in code:
            _v += 1
            show_code.append(f"{i+1}🟠")
            flag = False
        else:
            _w += 1
            show_code.append(f"{i+1}❌")
            flag = False
    if flag:
        times = len(code) - 3
        match random.randint(0, 9):
            case 0:
                item = manager.items_library["恶魔轮盘"]
                n = times
                tip = "神秘的箱子被打开，散发着邪恶的气息，将周围的一切都染上了一层不祥的阴影..."
            case _:
                item = manager.items_library["初级元素"]
                n = random.randint(5, 10) * times
                tip = "神秘的箱子被打开，里面散发着彩色的微光..."

        with manager.db.session as session:
            account = manager.account(event, session)
            assert account is not None
            item.deal(account, n, session)
        handle.finish()
        return f"密码为:{inputs_code} 输入正确！\n{tip}\n你获得了{n}个{item.name}。"
    else:
        log.append("|".join(show_code))
        msg = [f"第{i}次输入:{c}" for i, c in enumerate(log, start=1)]
        msg.append(f"{_pv}个数字正确，{_v}个数字正确但位置不对，{_w}个数字错误。")
        msg.append(f"剩余时间：{int(handle.expiration - time.time())}秒")
        if len(log) >= 10:
            handle.finish()
            msg.append("密码破解失败。")
        return "\n".join(msg)
