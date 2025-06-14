import time
import heapq
import math
import random
import asyncio
from io import BytesIO
from linecard import ImageList
from clovers import TempHandle
from clovers.logger import logger
from clovers.config import Config as CloversConfig
from clovers_apscheduler import scheduler
from clovers_sarof_core import __plugin__ as plugin, Event, Rule
from clovers_sarof_core import manager, client
from clovers_sarof_core import GOLD, STD_GOLD, REVOLUTION_MARKING
from clovers_sarof_core.account import Stock, Account, User, Group, Exchange, AccountBank, UserBank, GroupBank
from clovers_sarof_core.linecard import card_template, avatar_list, item_info, item_card, stock_card
from clovers_sarof_core.tools import format_number, to_int, download_url
from .tools import gini_coef, item_name_rule
from .config import Config


config_data = CloversConfig.environ().setdefault(__package__, {})
__config__ = Config.model_validate(config_data)
"""主配置类"""
config_data.update(__config__.model_dump())

revolt_gold = __config__.revolt_gold
revolt_gini = __config__.revolt_gini
gini_filter_gold = __config__.gini_filter_gold
revolt_cd = __config__.revolt_cd
company_public_gold = __config__.company_public_gold


@plugin.handle(["发起重置"], ["group_id"], rule=Rule.group)
async def _(event: Event):
    group_id: str = event.group_id  # type: ignore
    with manager.db.session as session:
        group = session.get(Group, group_id)
        if group is None:
            return "群组不存在。"
        banks = session.exec(
            AccountBank.select()
            .join(Account)
            .where(
                Account.group_id == group.id,
                AccountBank.item_id == GOLD.id,
                AccountBank.n > gini_filter_gold,
            )
        ).all()
        wealths = [x.n for x in banks]
        if (sum_wealths := sum(wealths)) < company_public_gold:
            return f"本群金币（{sum_wealths}）小于{company_public_gold}，未满足重置条件。"
        if (gini := gini_coef(wealths)) < revolt_gini:
            return f"当前基尼系数为{gini:f3}，未满足重置条件。"
        ranklist = heapq.nlargest(10, banks, key=lambda x: x.n)
        top = ranklist[0]
        REVOLUTION_MARKING.deal(top.account, 1, session)
        for i, bank in enumerate(ranklist):
            bank.n = int(bank.n * i / 10)
            bank.account.extra["revolution"] = False
        rate = group.level / group.level + 1
        for bank in group.bank:
            if manager.items_library[bank.item_id].domain == 1:
                bank.n = int(bank.n * rate)
        group.level += 1
        session.commit()
    return f"当前系数为：{gini:f3}，重置成功！恭喜{top.account.nickname}进入挂件榜☆！重置签到已刷新。"


@plugin.handle(["重置签到", "领取金币"], ["user_id", "group_id", "nickname", "avatar"])
async def _(event: Event):
    with manager.db.session as session:
        account = manager.account(event, session)
        if account is None:
            return "无法在当前会话创建账户。"
        if avatar_url := event.avatar:
            account.user.avatar_url = avatar_url
        if not account.extra.setdefault("revolution", True):
            return "你没有待领取的金币"
        n = random.randint(*revolt_gold)
        GOLD.deal(account, n, session)
        account.extra["revolution"] = False
        session.commit()
    return f"这是你重置后获得的金币！你获得了 {n} 金币"


@plugin.handle(["金币转"], ["user_id", "group_id", "nickname"])
async def _(event: Event):
    if not (args := event.args):
        return
    x, *args = args
    match x:
        case "入":
            if not (len(args) == 1 and args[0].isdigit()):
                return "请输入正确的数量"
            n = int(args[0])
            with manager.db.session as session:
                account = manager.account(event, session)
                if account is None:
                    return "无法在当前会话创建账户。"
                level = manager.db.group(account.group_id, session).level
                assert level >= 1
                n_std = n * level
                if (tn := STD_GOLD.deal(account, -n_std, session)) is not None:
                    return f"你的账户中没有足够的{STD_GOLD.name}（{tn}）。"
                GOLD.deal(account, n, session)
                session.commit()
                return f"你成功将{n_std}枚{STD_GOLD.name}兑换为{n}枚{GOLD.name}"
        case "出":
            if not (len(args) == 1 and args[0].isdigit()):
                return "请输入正确的数量"
            n = int(args[0])
            with manager.db.session as session:
                account = manager.account(event, session)
                if account is None:
                    return "无法在当前会话创建账户。"
                level = manager.db.group(account.group_id, session).level
                assert level >= 1
                n_std = n * level
                if (tn := GOLD.deal(account, -n, session)) is not None:
                    return f"你的账户中没有足够的{GOLD.name}（{tn}）。"
                STD_GOLD.deal(account, n, session)
                session.commit()
                return f"你成功将{n}枚{GOLD.name}兑换为{n_std}枚{STD_GOLD.name}"
        case "转移":
            if not (len(args) == 2 and (n := to_int(args[1]))):
                return "请输入正确的目标账户所在群及数量"
            with manager.db.session as session:
                account = manager.account(event, session)
                if account is None:
                    return "无法在当前会话创建账户。"
                group_name = args[0]
                if group := session.get(Group, group_name):
                    group_name = group.nickname
                    group_id = group.id
                    level = group.level
                elif stock := Stock.find(group_name, session):
                    group_id = stock.group_id
                    level = stock.group.level
                else:
                    return f"未找到【{group_name}】"
                target_account = session.exec(
                    Account.select().where(
                        Account.group_id == group_id,
                        Account.user_id == account.user_id,
                    )
                ).one_or_none()
                if target_account is None:
                    return f"你在{group_name}没有帐户"
                if n > 0:
                    exrate = account.group.level / level
                    if (tn := GOLD.deal(account, -n, session)) is not None:
                        return f"你的账户中没有足够的{GOLD.name}（{tn}）。"
                    receipt = int(n * exrate)
                    GOLD.deal(target_account, receipt, session)
                    session.commit()
                    return f"{account.nickname} 向 目标账户:{group_name} 发送 {n} {GOLD.name}\n汇率 {exrate:3f}\n实际收到 {receipt}"
                else:
                    exrate = level / account.group.level
                    if (tn := GOLD.deal(target_account, -n, session)) is not None:
                        return f"你的目标账户中没有足够的{GOLD.name}（{tn}）。"
                    receipt = int(n * exrate)
                    GOLD.deal(account, receipt, session)
                    session.commit()
                    return f"目标账户:{group_name} 向 {account.nickname} 发送 {n} {GOLD.name}\n汇率 {exrate:3f}\n实际收到 {receipt}"


@plugin.handle(["群金库", "群仓库"], ["user_id", "group_id", "permission"], rule=Rule.group)
async def _(event: Event):
    if not (args := event.args_parse()):
        return
    command, n = args[:2]
    if n < 0:
        return "请输入正确的数量"
    group_id: str = event.group_id  # type: ignore
    user_id = event.user_id
    if command == "查看":
        with manager.db.session as session:
            group = session.get(Group, group_id)
            if group is None:
                return "群组不存在。"
            item_data, stock_data = manager.bank_data(group.bank, session)
            imagelist: ImageList = []
            if item_data:
                if len(item_data) < 6:
                    imagelist.extend(item_info(item_data))
                else:
                    imagelist.append(card_template(item_card(item_data), "群仓库"))
            if stock_data:
                imagelist.append(card_template(stock_card(stock_data), "群投资"))
        return manager.info_card(imagelist, user_id) if imagelist else "群金库是空的"
    sign, name = command[0], command[1:]
    with manager.db.session as session:
        if (item := (manager.items_library.get(name) or Stock.find(name, session))) is None:
            return f"没有名为 {name} 的道具或股票。"
        group = session.get(Group, group_id)
        if group is None:
            return "群组不存在。"
        account = manager.db.account(user_id, group_id, session)
        if sign == "存":
            if (tn := item.deal(account, -n, session)) is not None:
                return f"你没有足够的{item.name}（{tn}）"
            item.corp_deal(group, n, session)
            return f"你在群仓库存入了{n}个{item.name}"
        elif sign == "取":
            if not Rule.group_admin(event):
                return f"你的权限不足。"
            if (tn := item.corp_deal(group, -n, session)) is not None:
                return f"群仓库没有足够的{item.name}（{tn}）"
            item.deal(account, n, session)
            return f"你在群仓库取出了{n}个{item.name}"


async def corp_rename(event: Event, handle: TempHandle):
    handle.finish()
    if event.message != "是":
        return "重命名已取消"
    state: tuple[str, str] = handle.state  # type: ignore
    stock_id, stock_name = state
    with manager.db.session as session:
        stock = session.get(Stock, stock_id)
        if stock is None:
            return f"{stock_id} 已被注销"
        stock.name = stock_name
        session.commit()


@plugin.handle(
    ["市场注册", "公司注册", "注册公司"],
    ["user_id", "group_id", "to_me", "permission", "group_avatar"],
    rule=[Rule.group, Rule.to_me, Rule.group_admin],
)
async def _(event: Event):
    group_id: str = event.group_id  #  type: ignore
    stock_name = event.single_arg()
    if not stock_name:
        return "请输入注册名"
    if (check := item_name_rule(stock_name)) is not None:
        return check
    if stock_name in manager.items_library:
        return f"注册名 {stock_name} 与已有物品重复"
    with manager.db.session as session:
        if Stock.find(stock_name, session) is not None:
            return f"{stock_name} 已被其他群注册"
        group = manager.db.group(group_id, session)
        if stock := group.stock:
            rule: list[Rule.Checker] = [Rule.identify(event.user_id, group_id), lambda event: event.message in "是否"]
            plugin.temp_handle(["user_id", "group_id", "permission"], rule=rule, state=(stock.id, stock_name))(corp_rename)
            return f"本群已在市场注册，注册名：{stock.name}，是否修改？【是/否】"
        if group_avatar := event.group_avatar:
            group.avatar_url = group_avatar
        session.commit()
        group_bank = session.exec(GroupBank.select_item(group.id, GOLD.id)).one_or_none()
        if group_bank is None or (n := group_bank.n) < company_public_gold:
            n = n if group_bank else 0
            return f"把注册到市场要求群金库至少有 {company_public_gold} {GOLD.name}，本群数量：{n}\n请使用指令【群仓库存{GOLD.name}】存入。"
        group_bank.n = 0
        stock_value = n * group.level
        STD_GOLD.corp_deal(group, stock_value, session)
        stock = group.listed(stock_name, session)
        stock.corp_deal(group, stock.issuance, session)
        banks = session.exec(
            AccountBank.select()
            .join(Account)
            .where(
                AccountBank.item_id == GOLD.id,
                Account.group_id == group_id,
            )
        ).all()
        stock_value += sum(bank.n for bank in banks) * group.level
        stock.reset_value(stock_value)
        session.commit()
    return f"{stock.name}发行成功，发行价格为{format_number(stock_value/ stock.issuance)}金币"


@plugin.handle(["购买", "发行购买"], ["user_id", "group_id", "nickname"])
async def _(event: Event):
    if not (args := event.args_parse()):
        return
    stock_name, buy_count, limit = args
    with manager.db.session as session:
        if (stock := Stock.find(stock_name, session)) is None:
            return f"没有 {stock_name} 的注册信息"
        account = manager.account(event, session)
        if account is None:
            return "无法在当前会话创建账户。"
        group_bank = stock.group.item(stock.id, session).one_or_none()
        if (group_bank is None or group_bank.n <= 0) and not (market := stock.market(session, limit)):
            return "没有符合要求的出售信息"
        market = sorted(market, key=lambda exchange: exchange.quote)
        level = account.group.level
        my_std_bank = STD_GOLD.bank(account, session)
        my_gold_bank = GOLD.bank(account, session)
        std_total = my_std_bank.n + my_gold_bank.n * level
        std_cost = 0
        buy_n = 0
        quote_current: float = 0
        for exchange in market:
            _buy = (std_total - std_cost) / exchange.quote
            if _buy >= exchange.n:
                buy_n += exchange.n
                quote_current = exchange.quote
                std_gold_n = int(exchange.n * quote_current)
                buy_count = exchange.deal(buy_count, session)
                bank = exchange.user.item(STD_GOLD.id, session).one_or_none() or UserBank(item_id=STD_GOLD.id, bound_id=exchange.user_id)
                bank.n += std_gold_n
                std_cost += std_gold_n
                session.add(bank)
            else:
                exchange_n = int(_buy)
                buy_n += exchange_n
                quote_current = exchange.quote
                std_gold_n = int(exchange_n * quote_current)
                exchange.deal(exchange_n, session)
                bank = exchange.user.item(STD_GOLD.id, session).one_or_none() or UserBank(item_id=STD_GOLD.id, bound_id=exchange.user_id)
                bank.n += std_gold_n
                std_cost += std_gold_n
                session.add(bank)
                break
            if buy_count <= 0:
                break
        else:
            if group_bank is not None and buy_count > 0 and (price := stock.price) > 0:
                growth_rate = 1 / stock.issuance
                for _ in range(buy_count):
                    quote_current = max(quote_current, price)
                    std_cost += quote_current
                    if std_cost > std_total:
                        std_cost -= quote_current
                        break
                    price += price * growth_rate
                    buy_n += 1
        std_cost = math.ceil(std_cost)
        tip = f"【购买:{stock_name}】使用了 {std_cost} 枚 {STD_GOLD.name}"
        if std_cost < my_std_bank.n:
            my_std_bank.n -= std_cost
            session.add(my_std_bank)
        else:
            std_cost -= my_std_bank.n
            if _bank := session.get(UserBank, STD_GOLD.id):
                session.delete(_bank)
            if std_cost > 0:
                my_gold_bank.n -= math.ceil(std_cost / level)
                session.add(my_gold_bank)
                tip += f"，其中{std_cost}枚来自购买群账户，汇率（{level}）"
        account.user.post_message(tip)
        session.commit()
    if buy_n > 0:
        card_template(
            f"{stock_name}\n----\n数量：{buy_n}\n单价：{buy_n / std_cost :2f}\n总计：{std_cost}",
            "购买信息",
            bg_color="white",
            width=440,
        ).save((output := BytesIO()), format="png")
        return output
    return "你没有足够的金币"


@plugin.handle(["出售", "卖出", "结算"], ["user_id"])
async def _(event: Event):
    if not (args := event.args_parse()):
        return
    stock_name, n, quote = args
    with manager.db.session as session:
        if (stock := Stock.find(stock_name, session)) is None:
            return f"没有 {stock_name} 的注册信息"
        account = manager.account(event, session)
        if account is None:
            return "无法在当前会话创建账户。"
        query = Exchange.select_item(stock.id, stock.id).join(User).where(User.id == account.user_id)
        exchange = session.exec(query).one_or_none()
        if n <= 0:
            if exchange is None:
                return "没有交易信息。"
            else:
                session.delete(exchange)
                return "交易信息已注销。"
        if exchange is None:
            exchange = Exchange(
                item_id=stock.id,
                bound_id=stock.id,
                user_id=account.user_id,
                n=n,
                quote=quote,
            )
            session.add(exchange)
            tip = "交易信息发布成功！"
        else:
            exchange.n = n
            exchange.quote = quote
            tip = "交易信息已修改。"
        session.commit()
    card_template(
        f"{stock_name}\n----\n报价：{quote or '自动出售'}\n数量：{n}",
        tip,
        bg_color="white",
        width=440,
    ).save((output := BytesIO()), format="png")
    return output


@plugin.handle(["市场信息"], ["user_id"])
async def _(event: Event):
    if stock_name := event.message:
        with manager.db.session as session:
            if (stock := Stock.find(stock_name, session)) is None:
                return f"没有 {stock_name} 的注册信息"
            exchanges = stock.market(session)
            exchanges = heapq.nsmallest(20, exchanges, key=lambda x: x.quote)
            avatar_urls, infos = zip(*((e.user.avatar_url, f"报价：{e.quote}[pixel 580]数量：{e.n}") for e in exchanges))
        avatars = await asyncio.gather(*(download_url(avatar, client) for avatar in avatar_urls))
        imagelist = avatar_list(zip(avatars, infos))
    else:
        with manager.db.session as session:
            all_stocks = session.exec(Stock.select()).all()
            data = [(stock, bank.n) for stock in all_stocks if (bank := stock.group.item(stock.id, session).one_or_none())]
        if not data:
            return "市场为空"
        data.sort(key=lambda x: x[0].value, reverse=True)
        imagelist = [card_template(stock_card(data), "市场信息")]
    return manager.info_card(imagelist, event.user_id)


@plugin.handle(["继承公司账户", "继承群账户"], ["user_id", "permission"], rule=Rule.superuser)
async def _(event: Event):
    args = event.args
    if len(args) != 3:
        return
    arrow = args[1]
    if arrow == "->":
        deceased_name = args[0]
        heir_name = args[2]
    elif arrow == "<-":
        heir_name = args[0]
        deceased_name = args[2]
    else:
        return "请输入:被继承群 -> 继承群"

    with manager.db.session as session:
        if (deceased_group := manager.find_group(deceased_name, session)) is None:
            return f"被继承群:{deceased_name} 不存在"
        if (heir_group := manager.find_group(heir_name, session)) is None:
            return f"被继承群:{deceased_name} 不存在"
        if deceased_group is heir_group:
            return "无法继承自身"
        heir_group_id = heir_group.id
        item_data, stock_data = manager.bank_data(deceased_group.bank, session)
        ExRate = deceased_group.level / heir_group.level
        imagelist = []
        if item_data:
            imagelist.append(card_template(item_card(item_data), "继承群仓库"))
            for item, n in item_data:
                heir_bank = session.exec(GroupBank.select_item(heir_group_id, item.id)).one_or_none()
                if heir_bank is None:
                    heir_bank = GroupBank(bound_id=heir_group_id, item_id=item.id)
                    session.add(heir_bank)
                heir_bank.n += int(ExRate * n) if item.domain == 1 else n
        if stock_data:
            imagelist.append(card_template(stock_card(stock_data), "继承群投资"))
            for item, n in stock_data:
                heir_bank = session.exec(GroupBank.select_item(heir_group_id, item.id)).one_or_none()
                if heir_bank is None:
                    heir_bank = GroupBank(bound_id=heir_group_id, item_id=item.id)
                    session.add(heir_bank)
                heir_bank.n += n
        deceased_group.cancel(session)
        session.commit()
    if imagelist:
        return manager.info_card(imagelist, event.user_id)
    else:
        return f"{deceased_name}已成功注销！但无任何可继承物品。"


def stock_update():
    with manager.db.session as session:
        stocks = session.exec(Stock.select()).all()
        for stock in stocks:
            wealths = manager.group_wealths(stock.group_id, GOLD.id, session)
            level = stock.group.level
            stock_value = sum(wealths) * level
            std_bank = session.exec(GroupBank.select_item(stock.group_id, STD_GOLD.id)).one_or_none()
            if std_bank:
                stock_value += std_bank.n
            stock.value = stock_value
            floating = stock.floating
            if math.isnan(floating):
                stock.floating = float(stock_value)
                logger.info(f"{stock.name} 已初始化")
                continue
            # 股票价格变化：趋势性影响（正态分布），随机性影响（平均分布），向债务价值回归
            floating += floating * random.gauss(0, 0.03)
            floating += stock_value * random.uniform(-0.1, 0.1)
            floating += (stock_value - floating) * 0.05
            # 结算交易市场上的股票
            issuance = stock.issuance
            for exchange in sorted(stock.exchange, key=lambda x: x.quote):
                value = 0.0
                settle = 0
                user = exchange.user
                if (quote := exchange.quote) > 0:
                    for _ in range(exchange.n):
                        unit = floating / issuance
                        if unit < quote:
                            exchange.n -= settle
                            break
                        value += quote
                        floating -= quote
                        settle += 1
                else:
                    settle = exchange.n
                    for _ in range(exchange.n):
                        unit = max(floating / issuance, 0.0)
                        value += unit
                        floating -= unit
                if settle == 0:
                    continue
                exchange.deal(settle, session)
                bank = user.item(stock.id, session).one_or_none()
                value = int(value)
                bank = user.item(STD_GOLD.id, session).one_or_none()
                if bank is None:
                    bank = UserBank(bound_id=user.id, item_id=STD_GOLD.id, n=value)
                    session.add(bank)
                else:
                    bank.n += value
                stock.floating = floating
            # 记录价格历史
            now_time = time.time()
            if not (record := stock.extra.get("record")):
                record = [(0.0, 0.0) for _ in range(720)]
            record.append((now_time, floating / issuance))
            record = record[-720:]
            stock.extra["stock_record"] = record
            logger.info(f"{stock.name} 更新成功！")


scheduler.add_job(stock_update, trigger="cron", minute="*/5", misfire_grace_time=120)


@plugin.handle(["刷新市场"], ["permission"], rule=Rule.superuser)
async def _(event: Event):
    stock_update()
