import typing
from sqlmodel import func, cast, Integer, desc, select, Column
from clovers_sarof.core.account import AccountBank, UserBank, Group, User, Account, Session


def _rank_user_extra_all(key: str, limit: int, session: Session):
    value = cast(func.json_extract(User.extra, f"$.{key}"), Integer)
    query = select(User.avatar_url, User.name, value).where(value.isnot(None)).order_by(value.desc()).limit(limit)
    return session.exec(query).all()


def _rank_user_extra_group(key: str, group_id: str, limit: int, session: Session):
    value = cast(func.json_extract(User.extra, f"$.{key}"), Integer)
    query = (
        select(User.avatar_url, Account.name, value)
        .join(User, typing.cast(Column, Account.user_id) == User.id)  # FROM Account
        .where(Account.group_id == group_id, value.isnot(None))
        .order_by(value.desc())
        .limit(limit)
    )
    return session.exec(query).all()


def rank_user_extra(key: str, group_id: str | None, limit: int, session: Session):
    if group_id is None:
        return _rank_user_extra_all(key, limit, session)
    else:
        return _rank_user_extra_group(key, group_id, limit, session)


def _rank_user_bank_all(item_id: str, limit: int, session: Session):
    query = (
        select(User.avatar_url, User.name, UserBank.n)
        .join(User)  # FROM UserBank
        .where(UserBank.item_id == item_id)
        .order_by(desc(UserBank.n))
        .limit(limit)
    )
    return session.exec(query).all()


def _rank_user_bank_group(item_id: str, group_id: str | None, limit: int, session: Session):
    query = (
        select(User.avatar_url, Account.name, UserBank.n)
        .join(User, typing.cast(Column, UserBank.bound_id) == User.id)  # FROM UserBank
        .join(Account, typing.cast(Column, User.id) == Account.user_id)
        .where(UserBank.item_id == item_id, Account.group_id == group_id)
        .order_by(desc(UserBank.n))
        .limit(limit)
    )

    return session.exec(query).all()


def rank_user_bank(item_id: str, group_id: str | None, limit: int, session: Session):
    if group_id is None:
        return _rank_user_bank_all(item_id, limit, session)
    else:
        return _rank_user_bank_group(item_id, group_id, limit, session)


def _get_account_bank_all(item_id: str, limit: int, session: Session):
    query = (
        select(User.avatar_url, User.name, func.sum(AccountBank.n * Group.level).label("total_value"))
        .join(Account, typing.cast(Column, AccountBank.bound_id) == Account.id)  # FROM AccountBank
        .join(User, typing.cast(Column, Account.user_id) == User.id)
        .join(Group, typing.cast(Column, Account.group_id) == Group.id)
        .where(AccountBank.item_id == item_id)
        .group_by(User.id, User.avatar_url, User.name)
        .order_by(desc("total_value"))
        .limit(limit)
    )
    return session.exec(query).all()


def _get_account_bank_group(item_id: str, group_id: str | None, limit: int, session: Session):
    query = (
        select(User.avatar_url, Account.name, AccountBank.n)
        .join(Account, typing.cast(Column, AccountBank.bound_id) == Account.id)  # FROM AccountBank
        .join(User, typing.cast(Column, Account.user_id) == User.id)
        .where(AccountBank.item_id == item_id, Account.group_id == group_id)
        .order_by(desc(AccountBank.n))
        .limit(limit)
    )
    return session.exec(query).all()


def rank_account_bank(item_id: str, group_id: str | None, limit: int, session: Session):
    if group_id is None:
        return _get_account_bank_all(item_id, limit, session)
    else:
        return _get_account_bank_group(item_id, group_id, limit, session)
