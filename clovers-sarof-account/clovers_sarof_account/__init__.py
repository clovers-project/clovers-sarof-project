import random
from datetime import datetime
from PIL import ImageColor
from linecard import ImageList
from clovers import TempHandle
from clovers.config import Config as CloversConfig
from clovers_apscheduler import scheduler
from clovers_sarof_core import __plugin__ as plugin, Event, Rule
from clovers_sarof_core import manager, client
from clovers_sarof_core import GOLD, STD_GOLD, REVOLUTION_MARKING, DEBUG_MARKING
from clovers_sarof_core.account import Stock, Account, Group, AccountBank, UserBank
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
from clovers_sarof_core.tools import download_url, format_number
from .config import Config

config_data = CloversConfig.environ().setdefault(__package__, {})
__config__ = Config.model_validate(config_data)
"""主配置类"""
config_data.update(__config__.model_dump())

sign_gold = __config__.sign_gold
lucky_marking = __config__.lucky_marking
revolution_marking = __config__.revolution_marking
debug_marking = __config__.debug_marking


@plugin.handle(["设置背景"], ["user_id", "to_me", "image_list"], rule=Rule.to_me)
async def _(event: Event):
    user_id = event.user_id
    log = []
    if args := event.args:
        BG_type = args[0]
        with manager.db.session as session:
            user = manager.db.user(user_id, session)
            if BG_type.startswith("高斯模糊"):
                try:
                    radius = int(args[1])
                except:
                    radius = 16
                user.extra["BG_type"] = f"GAUSS:{radius}"
            elif BG_type in ("无", "透明"):
                user.extra["BG_type"] = "NONE"
            elif BG_type == "默认":
                if "BG_type" in user.extra:
                    del user.extra["BG_type"]
            else:
                try:
                    ImageColor.getcolor(BG_type, "RGB")
                    user.extra["BG_type"] = BG_type
                except ValueError:
                    BG_type = "ValueError"
            session.commit()
            log.append(f"背景蒙版类型设置为：{BG_type}")
    if url_list := event.image_list:
        if (image := await download_url(url_list[0], client)) is None:
            log.append("图片下载失败")
        else:
            manager.BG_PATH.joinpath(f"{user_id}.png").write_bytes(image)
            log.append("图片下载成功")
    if log:
        return "\n".join(log)


@plugin.handle(["删除背景"], ["user_id", "to_me"], rule=Rule.to_me)
async def _(event: Event):
    manager.BG_PATH.joinpath(f"{event.user_id}.png").unlink(True)
    return "背景图片删除成功！"


@plugin.handle(["金币签到", "轮盘签到"], ["user_id", "group_id", "nickname", "avatar"])
async def _(event: Event):
    with manager.db.session as session:
        account = manager.account(event, session)
        if account is None:
            return "无法在当前会话创建账户。"
        today = datetime.today()
        if account.sign_in and (today - account.sign_in).days == 0:
            return "你已经签过到了哦"
        if avatar := event.avatar:
            account.user.avatar_url = avatar
        n = random.randint(*sign_gold)
        account.sign_in = today
        GOLD.deal(account, n, session)
        session.commit()
    return random.choice(["祝你好运~", "可别花光了哦~"]) + f"\n你获得了 {n} {GOLD.name}"


@plugin.handle(["发红包"], ["user_id", "group_id", "at", "permission"], rule=[Rule.at, Rule.group])
async def _(event: Event):
    group_id: str = event.group_id  # type: ignore
    unsettled = event.args_to_int()
    sender_id = event.user_id
    receiver_id = event.at[0]
    if unsettled < 0:
        if event.permission < 2:
            return "你输入了负数，请不要这样做。"
        sender_id, receiver_id = receiver_id, sender_id
        unsettled = -unsettled
    with manager.db.session as session:
        return manager.transfer(GOLD, unsettled, sender_id, receiver_id, group_id, session)[1]


@plugin.handle(["送道具"], ["user_id", "group_id", "at", "permission"], rule=[Rule.at, Rule.group])
async def _(event: Event):
    group_id: str = event.group_id  # type: ignore
    if not (args := event.args_parse()):
        return
    item_name, unsettled = args[:2]
    item = manager.items_library.get(item_name)
    if not item:
        return f"没有【{item_name}】这种道具。"
    sender_id = event.user_id
    receiver_id = event.at[0]
    if unsettled < 0:
        if event.permission < 2:
            return "你输入了负数，请不要这样做。"
        sender_id, receiver_id = receiver_id, sender_id
        unsettled = -unsettled
    with manager.db.session as session:
        return manager.transfer(item, unsettled, sender_id, receiver_id, group_id, session)[1]


@plugin.handle(r"(.+)查询$", ["user_id", "group_id", "nickname"])
async def _(event: Event):
    item = manager.items_library.get(event.args[0])
    if not item:
        return
    with manager.db.session as session:
        account = manager.account(event, session)
        if account is None:
            return "无法在当前会话创建账户。"
        return f"你还有 {item.bank(account, session).n} 个{item.name}"


@plugin.handle(["我的信息", "我的资料卡"], ["user_id", "group_id", "nickname"])
async def _(event: Event):
    with manager.db.session as session:
        account = manager.account(event, session)
        if account is None:
            return "无法在当前会话创建账户。"
        marking_lines = [lucky_marking]
        if REVOLUTION_MARKING.bank(account, session).n > 0:
            marking_lines.append(revolution_marking)
        if DEBUG_MARKING.bank(account, session).n > 0:
            marking_lines.append(debug_marking)
        user = account.user
        avatar_url = user.avatar_url
        nickname = account.nickname
        dist_lines = []
        dist: list[tuple[int, str]] = [((sum_std_n := STD_GOLD.bank(account, session).n), "个人账户")]
        for _account in user.accounts:
            _group = _account.group
            std_n = GOLD.bank(_account, session).n * _group.level
            if std_n > 0:
                dist.append((std_n, _group.nickname))
            sum_std_n += std_n
        dist_lines.append(f"[font color=#FFCC33]金币 {format_number(sum_std_n)}")
        if stock_data := manager.stock_data(user.bank, session):
            stock_value = format_number(manager.stock_value(stock_data, session))
        else:
            stock_value = "0"
        dist_lines.append(f"[font color=#0066CC]股票 {stock_value}")
        for marking_item in manager.marking_library.values():
            if (n := marking_item.bank(account, session).n) > 0:
                dist_lines.append(f"[font color={marking_item.color}]Lv.{min(n, 99)}[pixel 160]{marking_item.tip}")
        message_lines = []
        if account.sign_in is None:
            message_lines.append(f"[font color=red]未注册")
        elif (delta_days := (datetime.today() - account.sign_in).days) == 0:
            message_lines.append("[font color=green]今日已签到")
        else:
            message_lines.append(f"[font color=red]连续{delta_days}天 未签到")
        if user.mailbox:
            message_lines.extend(user.mailbox)
            user.mailbox = []
            session.commit()
    imagelist: ImageList = []
    imagelist.append(avatar_card(await download_url(avatar_url, client), nickname, marking_lines))
    imagelist.append(text_to_image("\n".join(dist_lines), 40, canvas=dist_card(dist) if dist else None))
    if stock_data:
        imagelist.append(card_template(stock_card(stock_data), "股票信息"))
    imagelist.append(card_template("\n".join(message_lines), "Message", font_size=30, autowrap=True))
    return manager.info_card(imagelist, event.user_id)


@plugin.handle(["我的道具"], ["user_id", "group_id", "nickname"])
async def _(event: Event):
    with manager.db.session as session:
        account = manager.account(event, session)
        if account is None:
            return "无法在当前会话创建账户。"
        bank = account.bank + account.user.bank
        if not bank:
            return "您的仓库空空如也。"
        item_data = manager.item_data(bank)
    if len(item_data) < 10 or event.single_arg() in ("信息", "介绍", "详情"):
        imagelist = item_info(item_data)
    else:
        imagelist = [card_template(item_card(item_data), "道具仓库")]
    return manager.info_card(imagelist, event.user_id)


@plugin.handle(["股票查询", "投资查询"], ["user_id", "group_id", "nickname"])
async def _(event: Event):
    with manager.db.session as session:
        account = manager.account(event, session)
        if account is None:
            return "无法在当前会话创建账户。"
        stock_data = manager.stock_data(account.user.bank, session)
    if stock_data:
        return manager.info_card([card_template(stock_card(stock_data), f"股票信息:{account.name}")], event.user_id)
    else:
        return "您的仓库空空如也。"


@plugin.handle(["群资料卡"], ["user_id", "group_id", "nickname", "group_avatar"])
async def _(event: Event):
    """
    群资料卡
    """
    group_name = event.single_arg()
    with manager.db.session as session:
        if group_name:
            if (stock := Stock.find(group_name, session)) is not None:
                group = stock.group
            elif (group := session.get(Group, group_name) or Group.find(group_name, session)) is None:
                return f"未找到【{group_name}】"
        else:
            group_id = event.group_id
            if not group_id:
                return "请输入群名或群号"
            group = manager.db.group(group_id, session)
        if (avatar_url := event.group_avatar) is not None:
            group.avatar_url = avatar_url
            session.add(group)
            session.commit()
        else:
            avatar_url = group.avatar_url
        group_name = group.nickname
        lines = [
            f"{stock.time.strftime('%Y年%m月%d日')if (stock :=group.stock) else '未发行'}",
            f"等级 {group.level}",
            f"成员 {len(group.accounts)}",
        ]
        banks = session.exec(
            AccountBank.select()
            .join(Account)
            .where(
                Account.group_id == group.id,
                AccountBank.item_id == REVOLUTION_MARKING.id,
                AccountBank.n > 0,
            )
        ).all()
        revolution_ranklist = "\n".join(f"{bank.account.nickname}[right]{bank.n}次" for bank in banks) if banks else None
        candlestick_record = record if (stock := group.stock) and (record := stock.extra.get("record")) else None
        item_data, stock_data = manager.bank_data(group.bank, session)

    imagelist: ImageList = []
    imagelist.append(avatar_card(await download_url(avatar_url, client) if avatar_url else None, group_name, lines))
    if revolution_ranklist is not None:
        imagelist.append(card_template(revolution_ranklist, "路灯挂件榜"))
    if candlestick_record is not None:
        imagelist.append(candlestick((9.5, 3), 12, candlestick_record))
    if item_data:
        imagelist.append(card_template(item_card(item_data), "群仓库"))
    if stock_data:
        imagelist.append(card_template(stock_card(stock_data), "群投资"))
    return manager.info_card(imagelist, event.user_id)


# 超管指令
@plugin.handle(["获取"], ["user_id", "group_id", "nickname", "permission"], rule=Rule.superuser)
async def _(event: Event):
    if not (args := event.args_parse()):
        return
    name, N = args[:2]
    item = manager.items_library.get(name)
    if not item:
        return f"没有【{name}】这种道具。"
    with manager.db.session as session:
        account = manager.account(event, session)
        if account is None:
            return "无法在当前会话创建账户。"
        if (n := item.deal(account, N, session)) is None:
            session.commit()
            return f"你获得了{N}个【{item.name}】！"
        return f"获取失败，你的【{item.name}】（{n}）数量不足。"


async def cancel_confirm(event: Event, handle: TempHandle):
    handle.finish()
    with manager.db.session as session:
        account = session.get(Account, handle.state)
        assert account is not None
        nickname = account.nickname
        account.cancel(session)
    return f"冻结完成,目标账户【{nickname}】已注销。"


@plugin.handle(["注销账户"], ["user_id", "group_id", "permission", "at"], rule=[Rule.superuser, Rule.at])
async def _(event: Event):
    if (group_id := event.group_id) is None:
        return
    user_id = event.user_id
    with manager.db.session as session:
        account = session.exec(Account.select().where(Account.user_id == user_id, Account.group_id == group_id)).one_or_none()
        if account is None:
            return "目标账户不存在。"
        account_id = account.id
    confirm_code = "".join(str(random.randint(0, 9)) for _ in range(4))
    confirm_rule: list[Rule.Checker] = [Rule.identify(user_id, group_id), lambda event: event.message == confirm_code]
    plugin.temp_handle(["user_id", "group_id", "permission"], rule=confirm_rule, state=account_id)(cancel_confirm)
    return f"您即将注销 {account.name}({account.user_id})，请输入{confirm_code}来确认。"


def new_day():
    manager.clean_backup(604800)
    with manager.db.session as session:
        banks: list[UserBank | AccountBank] = []
        banks.extend(session.exec(UserBank.select().where(UserBank.item_id.startswith("item:"))).all())
        banks.extend(session.exec(AccountBank.select().where(AccountBank.item_id.startswith("item:"))).all())
        for bank in banks:
            if (item := manager.items_library.get(bank.item_id)) is None:
                session.delete(item)
                continue
            if item.timeliness == 0:
                bank.n -= 1
                if bank.n <= 0:
                    session.delete(item)
                    continue
        session.commit()


scheduler.add_job(new_day, trigger="cron", hour=0, misfire_grace_time=120)
scheduler.add_job(manager.backup, trigger="cron", hour="*/4", misfire_grace_time=120)
