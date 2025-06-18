from sqlmodel import func, cast, Integer, desc
from clovers_sarof.core.account import AccountBank, UserBank, Group, User, Account


def _rank_user_extra_all(key: str, limit: int):
    value = cast(func.json_extract(User.extra, f"$.{key}"), Integer)
    query = User.select().where(value.isnot(None)).order_by(value.desc()).limit(limit)

    def analyse(user: User):
        avatar_url = user.avatar_url
        name = user.name
        value: int = user.extra[key]
        return avatar_url, name, value

    return query, analyse


def _rank_user_extra_group(key: str, group_id: str, limit: int):
    value = cast(func.json_extract(User.extra, f"$.{key}"), Integer)
    query = Account.select().join(User).where(Account.group_id == group_id, value.isnot(None)).order_by(value.desc()).limit(limit)

    def analyse(account: Account):
        avatar_url = account.user.avatar_url
        name = account.nickname
        value: int = account.user.extra[key]
        return avatar_url, name, value

    return query, analyse


def rank_user_extra(key: str, group_id: str | None, limit: int):
    if group_id is None:
        return _rank_user_extra_all(key, limit)
    else:
        return _rank_user_extra_group(key, group_id, limit)


def _rank_user_bank_all(item_id: str, limit: int):
    query = UserBank.select().where(UserBank.item_id == item_id).order_by(desc(UserBank.n)).limit(limit)

    def analyse(bank: UserBank):
        avatar_url = bank.user.avatar_url
        name = bank.user.name
        value = bank.n
        return avatar_url, name, value

    return query, analyse


def _rank_user_bank_group(item_id: str, group_id: str | None, limit: int):
    query = (
        UserBank.select()
        .join(User)
        .join(Account)
        .where(UserBank.item_id == item_id, Account.group_id == group_id)
        .order_by(desc(UserBank.n))
        .limit(limit)
    )

    def analyse(bank: UserBank):
        avatar_url = bank.user.avatar_url
        name = bank.user.name
        value = bank.n
        return avatar_url, name, value

    return query, analyse


def rank_user_bank(item_id: str, group_id: str | None, limit: int):
    if group_id is None:
        return _rank_user_bank_all(item_id, limit)
    else:
        return _rank_user_bank_group(item_id, group_id, limit)


def _get_account_bank_all(item_id: str, limit: int):
    query = (
        AccountBank.select()
        .join(Account)
        .join(Group)
        .where(AccountBank.item_id == item_id)
        .order_by(desc(AccountBank.n * Group.level))
        .limit(limit)
    )

    def analyse(bank: AccountBank):
        avatar_url = bank.account.user.avatar_url
        name = bank.account.nickname
        value = bank.n * bank.account.group.level
        return avatar_url, name, value

    return query, analyse


def _get_account_bank_group(item_id: str, group_id: str | None, limit: int):
    query = (
        AccountBank.select()
        .join(Account)
        .where(AccountBank.item_id == item_id, Account.group_id == group_id)
        .order_by(desc(AccountBank.n))
        .limit(limit)
    )

    def analyse(bank: AccountBank):
        avatar_url = bank.account.user.avatar_url
        name = bank.account.nickname
        value = bank.n
        return avatar_url, name, value

    return query, analyse


def rank_account_bank(item_id: str, group_id: str | None, limit: int):
    if group_id is None:
        return _get_account_bank_all(item_id, limit)
    else:
        return _get_account_bank_group(item_id, group_id, limit)
