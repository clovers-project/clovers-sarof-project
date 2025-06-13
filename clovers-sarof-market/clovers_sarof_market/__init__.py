import time
import heapq
import math
import random
from io import BytesIO
from collections import Counter
from linecard import ImageList
from clovers import TempHandle
from clovers.logger import logger
from clovers.config import Config as CloversConfig
from clovers_apscheduler import scheduler
from clovers_sarof_core import __plugin__ as plugin, Event, Rule
from clovers_sarof_core import manager
from clovers_sarof_core import GOLD, STD_GOLD, REVOLUTION_MARKING, DEBUG_MARKING
from clovers_sarof_core.account import Stock, Account, Group, AccountBank, UserBank, GroupBank
from clovers_sarof_core.linecard import (
    text_to_image,
    card_template,
    avatar_card,
    item_info,
    item_card,
    stock_card,
    candlestick,
    dist_card,
)
from clovers_sarof_core.tools import format_number, to_int
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
    stock_name, buy, limit = args
    with manager.db.session as session:
        if (stock := Stock.find(stock_name, session)) is None:
            return f"没有 {stock_name} 的注册信息"
        buy_count = min

    buy = min(stock_group.invest[stock.id], buy)
    if buy < 1:
        return "已售空，请等待结算。"
    stock_level = stock_group.level
    stock_value = sum(manager.group_wealths(stock.id, GOLD.id)) * stock_level + stock_group.bank[STD_GOLD.id]
    user, account = manager.account(event)
    group = manager.data.group(account.group_id)
    level = group.level
    account_STD_GOLD = account.bank[GOLD.id] * level
    my_STD_GOLD = user.bank[STD_GOLD.id] + account_STD_GOLD
    issuance = stock.issuance
    floating = stock.floating
    limit = limit or float("inf")
    value = 0.0
    _buy = 0
    for _ in range(buy):
        unit = max(floating, stock_value) / issuance
        if unit > limit:
            tip = f"价格超过限制（{limit}）。"
            break
        value += unit
        if value > my_STD_GOLD:
            value -= unit
            tip = f"你的金币不足（{my_STD_GOLD}）。"
            break
        floating += unit
        _buy += 1
    else:
        tip = "交易成功！"

    int_value = math.ceil(value)
    user.bank[STD_GOLD.id] -= int_value
    if (n := user.bank[STD_GOLD.id]) < 0:
        user.bank[STD_GOLD.id] = 0
        account_STD_GOLD += n
        account.bank[GOLD.id] = math.ceil(account_STD_GOLD / level)
        user.add_message(f"购买{_buy}份{stock_name}需要花费{int_value}枚标准金币，其中{-n}枚来自购买群账户，汇率（{level}）")
    user.invest[stock.id] += _buy
    stock_group.bank[GOLD.id] += math.ceil(value / stock_level)
    group.invest[stock.id] -= _buy
    stock.floating = floating
    stock.value = stock_value + int_value
    output = BytesIO()
    text_to_image(
        f"{stock.name}\n----\n数量：{_buy}\n单价：{round(value/_buy,2)}\n总计：{int_value}" + endline(tip),
        width=440,
        bg_color="white",
    ).save(output, format="png")
    return output


@plugin.handle(["出售", "卖出", "结算"], ["user_id"])
async def _(event: Event):
    if not (args := event.args_parse()):
        return
    stock_name, n, quote = args
    user = manager.data.user(event.user_id)
    stock_group = manager.group_library.get(stock_name)
    if not stock_group or not (stock := stock_group.stock):
        return f"没有 {stock_name} 的注册信息"
    stock_name = stock_group.nickname
    my_stock = min(user.invest[stock.id], n)
    user_id = user.id
    exchange = stock.exchange
    if my_stock < 1:
        if user_id in exchange:
            del exchange[user_id]
            return "交易信息已注销。"
        else:
            return "交易信息无效。"
    if user_id in exchange:
        tip = "交易信息已修改。"
    else:
        tip = "交易信息发布成功！"
    exchange[user_id] = (n, quote or 0.0)
    output = BytesIO()
    text_to_image(
        f"{stock_name}\n----\n报价：{quote or '自动出售'}\n数量：{n}" + endline(tip),
        width=440,
        bg_color="white",
    ).save(output, format="png")
    return output


@plugin.handle(["市场信息"], ["user_id"])
async def _(event: Event):
    data = [(stock, group.invest[stock.id]) for group in manager.data.group_dict.values() if (stock := group.stock)]
    if not data:
        return "市场为空"
    data.sort(key=lambda x: x[0].value, reverse=True)
    return manager.info_card([invest_card(data)], event.user_id)


@plugin.handle(["继承公司账户", "继承群账户"], ["user_id", "permission"], rule=Rule.superuser)
async def _(event: Event):
    args = event.args
    if len(args) != 3:
        return
    arrow = args[1]
    if arrow == "->":
        deceased = args[0]
        heir = args[2]
    elif arrow == "<-":
        heir = args[0]
        deceased = args[2]
    else:
        return "请输入:被继承群 -> 继承群"
    deceased_group = manager.group_library.get(deceased)
    if not deceased_group:
        return f"被继承群:{deceased} 不存在"
    heir_group = manager.group_library.get(heir)
    if not heir_group:
        return f"继承群:{heir} 不存在"
    if deceased_group is heir_group:
        return "无法继承自身"
    ExRate = deceased_group.level / heir_group.level
    # 继承群金库
    invest_group = Counter(deceased_group.invest)
    heir_group.invest = Counter(heir_group.invest) + invest_group
    bank_group = Counter({k: int(v * ExRate) if manager.props_library[k].domain == 1 else v for k, v in deceased_group.bank.items()})
    heir_group.bank = Counter(heir_group.bank) + bank_group
    # 继承群员账户
    all_bank_private = Counter()
    for deceased_user_id, deceased_account_id in deceased_group.accounts_map.items():
        deceased_account = manager.data.account_dict[deceased_account_id]
        bank = Counter({k: int(v * ExRate) for k, v in deceased_account.bank.items()})
        if deceased_user_id in heir_group.accounts_map:
            all_bank_private += bank
            heir_account_id = heir_group.accounts_map[deceased_user_id]
            heir_account = manager.data.account_dict[heir_account_id]
            heir_account.bank = Counter(heir_account.bank) + bank
        else:
            bank_group += bank
            heir_group.bank = Counter(heir_group.bank) + bank
    del manager.group_library[deceased_group.id]
    manager.data.cancel_group(deceased_group.id)
    info = []
    info.append(invest_card(manager.invest_data(invest_group), "群投资继承"))
    info.append(prop_card(manager.props_data(bank_group), "群金库继承"))
    info.append(prop_card(manager.props_data(all_bank_private), "个人总继承"))
    return manager.info_card(info, event.user_id)


@plugin.handle(["刷新市场"], ["permission"], rule=Rule.superuser)
@scheduler.scheduled_job("cron", minute="*/5", misfire_grace_time=120)
async def _(*arg, **kwargs):
    def stock_update(group: Group):
        stock = group.stock
        if not stock:
            logger.info(f"{group.id} 更新失败")
            return
        level = group.level
        # 资产更新
        wealths = manager.group_wealths(group.id, GOLD.id)
        stock_value = stock.value = sum(wealths) * level + group.bank[STD_GOLD.id]
        floating = stock.floating
        if not floating or math.isnan(floating):
            stock.floating = float(stock_value)
            logger.info(f"{stock.name} 已初始化")
            return
        # 股票价格变化：趋势性影响（正态分布），随机性影响（平均分布），向债务价值回归
        floating += floating * random.gauss(0, 0.03)
        floating += stock_value * random.uniform(-0.1, 0.1)
        floating += (stock_value - floating) * 0.05
        # 股票浮动收入
        group.bank[GOLD.id] = int(wealths[-1] * floating / stock.floating)
        # 结算交易市场上的股票
        issuance = stock.issuance
        std_value = 0
        now_time = time.time()
        clock = time.strftime("%H:%M", time.localtime(now_time))
        for user_id, exchange in stock.exchange.items():
            user = manager.data.user(user_id)
            n, quote = exchange
            value = 0.0
            settle = 0
            if quote:
                for _ in range(n):
                    unit = floating / issuance
                    if unit < quote:
                        break
                    value += quote
                    floating -= quote
                    settle += 1
            else:
                for _ in range(n):
                    unit = max(floating / issuance, 0.0)
                    value += unit
                    floating -= unit
                settle = n
            if settle == 0:
                continue
            elif settle < n:
                stock.exchange[user_id] = (n - settle, quote)
            else:
                stock.exchange[user_id] = (0, 0)
            user.invest[stock.id] -= settle
            group.invest[stock.id] += settle
            int_value = int(value)
            user.bank[STD_GOLD.id] += int_value
            user.message.append(
                f"【交易市场 {clock}】收入{int_value}标准金币。\n{stock.name}已出售{settle}/{n}，报价{quote or format_number(value/settle)}。"
            )
            std_value += value
        group.bank[GOLD.id] -= int(std_value / level)
        stock.exchange = {user_id: exchange for user_id, exchange in stock.exchange.items() if exchange[0] > 0}
        # 更新浮动价格
        stock.floating = floating
        # 记录价格历史
        if not (stock_record := group.extra.get("stock_record")):
            stock_record = [(0.0, 0.0) for _ in range(720)]
        stock_record.append((now_time, floating / issuance))
        stock_record = stock_record[-720:]
        group.extra["stock_record"] = stock_record
        logger.info(f"{stock.name} 更新成功！")

    groups = (group for group in manager.data.group_dict.values() if group.stock and group.stock.issuance)
    for group in groups:
        stock_update(group)


@plugin.handle(["市场浮动重置"], ["permission"], rule=Rule.superuser)
async def _(event: Event):
    groups = (group for group in manager.data.group_dict.values() if group.stock and group.stock.issuance)
    for group in groups:
        stock = group.stock
        if not stock:
            continue
        wealths = manager.group_wealths(group.id, GOLD.id)
        stock_value = stock.value = sum(wealths) * group.level + group.bank[STD_GOLD.id]
        stock.floating = stock.value = stock_value
    return "重置成功！"
