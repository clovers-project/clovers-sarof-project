from typing import Any, ClassVar, cast, Sequence
from datetime import datetime
from sqlmodel import SQLModel as BaseSQLModel, Field, Relationship
from sqlmodel import Session, create_engine, select
from sqlalchemy import Column
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON


class SQLModel(BaseSQLModel):
    @classmethod
    def select(cls):
        return select(cls)


class BaseItem:
    id: str
    name: str

    def deal(self, account: "Account", unsettled: int, session: Session):
        bank = self.bank(account, session)
        return self.bank_deal(bank, unsettled, session)

    def bank(self, account: "Account", session: Session) -> "BaseBank":
        raise NotImplementedError

    def corp_deal(self, group: "Group", unsettled: int, session: Session):
        bank = group.item(self.id, session).one_or_none() or BaseBank(item_id=self.id, bound_id=group.id)
        return self.bank_deal(bank, unsettled, session)

    @staticmethod
    def bank_deal(bank: "BaseBank", unsettled: int, session: Session):
        if unsettled < 0 and bank.n < (-unsettled):
            return bank.n
        bank.n += unsettled
        if bank.n <= 0:
            # assert bank.n == 0
            BankType = type(bank)
            if (_bank := session.get(BankType, BankType.id == bank.id)) is not None:
                session.delete(_bank)
        else:
            session.add(bank)
        session.commit()


class BaseBank(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    item_id: str = Field(index=True)
    n: int = 0
    bound_id: Any

    @classmethod
    def select_item(cls, bound_id: Any, item_id: str):
        return select(cls).where(cls.bound_id == bound_id, cls.item_id == item_id)


class Entity(SQLModel):
    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    BankType: ClassVar[type[BaseBank]]

    def cancel(self, session: Session):
        if (obj := session.get(type(self), self.id)) is None:
            return
        session.delete(obj)
        session.commit()

    def item(self, item_id: str, session: Session):
        return session.exec(self.BankType.select_item(bound_id=self.id, item_id=item_id))

    @classmethod
    def find(cls, name: str, session: Session):
        return session.exec(select(cls).where(cls.name == name)).one_or_none()


class Exchange(BaseBank, table=True):
    stock: "Stock" = Relationship(back_populates="exchange")
    bound_id: str = Field(foreign_key="stock.id", index=True)
    # relation
    user: "User" = Relationship(back_populates="exchange")
    user_id: str = Field(foreign_key="user.id", index=True)
    #  data
    quote: float = 0.0

    def deal(self, unsettled: int, session: Session):
        time_log = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        settle = min(self.n, unsettled)
        self.user.post_message(f"【{time_log}】卖出 {self.stock.name}*{settle}")
        self.n -= settle
        if self.n <= 0:
            session.delete(self)
        # 理论上用户存在库存且数量应大于等于 settle
        # 但为了健壮性这里做冗余处理
        bank = self.user.item(self.bound_id, session).one_or_none()
        if bank is not None:
            if self.stock.bank_deal(bank, -settle, session) is not None:
                session.delete(bank)
        return unsettled - settle


class Stock(BaseItem, Entity, table=True):
    BankType = Exchange
    exchange: list[Exchange] = Relationship(back_populates="stock", cascade_delete=True)
    # relation
    group: "Group" = Relationship(back_populates="stock")
    group_id: str = Field(foreign_key="group.id", index=True)
    # data
    value: int = 0
    """全群资产"""
    floating: float = 0
    """浮动资产"""
    issuance: int = 0
    """股票发行量"""
    time: datetime
    """注册时间"""
    extra: dict[str, Any] = Field(default_factory=dict, sa_column=Column(MutableDict.as_mutable(SQLiteJSON())))

    def reset_value(self, value: int):
        self.value = value
        self.floating = float(value)

    def bank(self, account: "Account", session: Session):
        return account.user.item(self.id, session).one_or_none() or UserBank(item_id=self.id, bound_id=account.user_id)

    def market(self, session: Session, limit: float = 0):
        if limit <= 0:
            return cast(Sequence[Exchange], self.item(self.id, session).all())
        else:
            query = select(Exchange).where(
                Exchange.bound_id == self.group_id,
                Exchange.item_id == self.id,
                Exchange.quote <= limit,
                Exchange.quote > 0.0,
            )
            return session.exec(query).all()

    @property
    def price(self):
        if self.issuance <= 0:
            return 0.0
        total_price = max(self.value, self.floating)
        if total_price <= 0.0:
            return 0.0
        return total_price / self.issuance


class AccountBank(BaseBank, table=True):
    account: "Account" = Relationship(back_populates="bank")
    bound_id: int = Field(foreign_key="account.id")


class Account(Entity, table=True):
    id: int | None = Field(default=None, primary_key=True)
    BankType = AccountBank
    bank: list[AccountBank] = Relationship(back_populates="account", cascade_delete=True)
    # relation
    user: "User" = Relationship(back_populates="accounts")
    user_id: str = Field(foreign_key="user.id", index=True)
    group: "Group" = Relationship(back_populates="accounts")
    group_id: str = Field(foreign_key="group.id", index=True)
    # data
    sign_in: datetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict, sa_column=Column(MutableDict.as_mutable(SQLiteJSON())))

    @property
    def nickname(self):
        return self.name or self.user.name or self.user_id


class UserBank(BaseBank, table=True):
    user: "User" = Relationship(back_populates="bank")
    bound_id: str = Field(foreign_key="user.id")


class User(Entity, table=True):
    BankType = UserBank
    bank: list[UserBank] = Relationship(back_populates="user", cascade_delete=True)
    # relation
    accounts: list[Account] = Relationship(back_populates="user", cascade_delete=True)
    exchange: list[Exchange] = Relationship(back_populates="user", cascade_delete=True)
    # data
    avatar_url: str = ""
    connect: str = ""
    extra: dict[str, Any] = Field(default_factory=dict, sa_column=Column(MutableDict.as_mutable(SQLiteJSON())))
    mailbox: list[str] = Field(default_factory=list, sa_column=Column(SQLiteJSON()))

    def post_message(self, message: str, history: int = 30):
        self.mailbox.append(message)
        self.mailbox = self.mailbox[-history:]


class GroupBank(BaseBank, table=True):
    group: "Group" = Relationship(back_populates="bank")
    bound_id: str = Field(foreign_key="group.id")


class Group(Entity, table=True):
    BankType = GroupBank
    bank: list[GroupBank] = Relationship(back_populates="group", cascade_delete=True)
    # relation
    accounts: list[Account] = Relationship(back_populates="group", cascade_delete=True)
    stock: Stock | None = Relationship(back_populates="group", cascade_delete=True)
    # data
    avatar_url: str = ""
    level: int = 1
    extra: dict[str, Any] = Field(default_factory=dict, sa_column=Column(MutableDict.as_mutable(SQLiteJSON())))

    @property
    def nickname(self):
        return self.stock.name if self.stock is not None else self.name or self.id

    def listed(self, name: str, session: Session):
        if self.stock is not None:
            self.stock.name = name
        else:
            self.stock = Stock(
                id=f"stock:{self.id}",
                name=name,
                group_id=self.id,
                time=datetime.today(),
                issuance=20000 * self.level,
            )
        session.add(self)
        session.add(self.stock)
        session.commit()
        session.refresh(self)
        return self.stock


class DataBase:
    def __init__(self, DATABASE_URL: str) -> None:
        self.engine = create_engine(DATABASE_URL)
        SQLModel.metadata.create_all(self.engine)

    @classmethod
    def load(cls, DATABASE_URL: str):
        return cls(DATABASE_URL)

    def user(self, user_id: str, session: Session):
        user = session.get(User, user_id)
        if user is None:
            user = User(id=user_id, name="")
            session.add(user)
        return user

    def group(self, group_id: str, session: Session):
        group = session.get(Group, group_id)
        if group is None:
            group = Group(id=group_id, name="")
            session.add(group)
        return group

    def account(self, user_id: str, group_id: str, session: Session):
        query = select(Account).where(Account.user_id == user_id, Account.group_id == group_id)
        account = session.exec(query).one_or_none()
        user = self.user(user_id, session)
        group = self.group(group_id, session)
        if account is None:
            account = Account(name="", user_id=user.id, group_id=group.id)
            session.add(account)
            session.commit()
        return account

    @property
    def session(self):
        return Session(self.engine)


class Item(BaseItem):
    id: str
    """ID"""
    name: str
    """名称"""
    rare: int
    """稀有度"""
    domain: int
    """
    作用域
        0:无(空气)
        1:群内
        2:全局
    """
    timeliness: int
    """
    时效
        0:时效道具
        1:永久道具
    """
    number: int
    """编号"""
    color: str
    """颜色"""
    intro: str
    """介绍"""
    tip: str
    """提示"""

    def __init__(
        self,
        item_id: str,
        name: str,
        color: str = "black",
        intro: str = "",
        tip: str = "",
    ) -> None:
        if not item_id.startswith("item:") or not item_id[5:].isdigit():
            raise ValueError("item_id must be item:digit")
        self.name = name
        self.color = color
        self.intro = intro
        self.tip = tip
        self.id = item_id
        self.rare = int(item_id[5])
        self.domain = int(item_id[6])
        self.timeliness = int(item_id[7])
        self.number = int(item_id[8:])
        if self.domain == 2:
            self.bank = self.user_bank
        else:
            self.bank = self.account_bank

    @property
    def dict(self):

        return {"item_id": self.id, "name": self.name, "color": self.color, "intro": self.intro, "tip": self.tip}

    def deal(self, account: Account, unsettled: int, session: Session):
        bank = self.bank(account, session)
        return self.bank_deal(bank, unsettled, session)

    def bank(self, account: Account, session: Session) -> BaseBank:
        raise NotImplementedError

    def account_bank(self, account: Account, session: Session):
        account_id = account.id
        if account_id is None:
            raise ValueError("account_id is None")
        return account.item(self.id, session).one_or_none() or AccountBank(item_id=self.id, bound_id=account_id)

    def user_bank(self, account: Account, session: Session):
        return account.user.item(self.id, session).one_or_none() or UserBank(item_id=self.id, bound_id=account.user_id)
