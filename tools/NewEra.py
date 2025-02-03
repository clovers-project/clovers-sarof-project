from collections import Counter
from clovers_leafgame.main import manager
from clovers_leafgame.item import STD_GOLD


def NewEra():
    user_dict = manager.data.user_dict
    group_dict = manager.data.group_dict
    account_dict = manager.data.account_dict
    props_library = manager.props_library
    # 检查 user_dict
    for user_id, user in user_dict.items():
        user.id = user_id
        user.avatar_url = f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"
        # 删除股票
        user.invest.clear()
        # 删除道具
        user.bank = Counter({k: min(v, 20000) for k, v in user.bank.items() if v > 0 and k in props_library})
        for group_id, accounts_id in user.accounts_map.items():
            account = account_dict[accounts_id]
            account.user_id = user_id
            account.group_id = group_id
            # 删除道具
            account.bank = Counter({k: min(v, 20000) for k, v in account.bank.items() if v > 0 and k in props_library})
            group_dict[group_id].accounts_map[user_id] = accounts_id
        if "BG_type" in user.extra:
            del user.extra["BG_type"]
    # 检查 group_dict
    for group_id, group in group_dict.items():
        # 删除股票
        group.invest.clear()
        # 删除道具
        group.bank = Counter({k: min(v, 20000) for k, v in group.bank.items() if v > 0 and k in props_library})
        # 修正公司等级
        group.level = sum(group.extra.setdefault("revolution_achieve", {}).values()) + 1
        stock = group.stock
        if not stock:
            continue
        # 修正股票库存
        stock.id = group_id
        issuance = 20000 * group.level
        stock.issuance = issuance
        group.invest[group_id] = issuance
        group.bank[STD_GOLD.id] = issuance


NewEra()
