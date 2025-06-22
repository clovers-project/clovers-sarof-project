"""+++++++++++++++++
————————————————————
    ᕱ⑅ᕱ。 ᴍᴏʀɴɪɴɢ
   (｡•ᴗ-)_
————————————————————
+++++++++++++++++"""

import json
import shutil
from io import BytesIO
from pathlib import Path
from datetime import datetime
from collections.abc import Sequence
from PIL import ImageFilter, Image
from PIL.Image import Image as IMG
from linecard import info_splicing, ImageList, CanvasEffectHandler
from ._clovers import Event
from .account import Session, DataBase, Group, Account, AccountBank, BaseBank, Stock, Item
from .tools import Library


def canvas_effect(canvas: IMG, image: IMG, padding: int, x: int, y: int):
    box = (padding, y, x + padding - 4, y + image.size[1] - 4)
    region = canvas.crop(box)
    colorBG = Image.new("RGBA", (x, image.size[1]), "#0000000F")
    canvas.paste(colorBG, (padding + 4, y + 4), mask=colorBG)
    canvas.paste(region, box)
    box = (padding + 4, y + 4, x + padding - 4, y + image.size[1] - 4)
    region = canvas.crop(box)
    colorBG = Image.new("RGBA", (x, image.size[1]), "#00000022")
    canvas.paste(colorBG, (padding, y), mask=colorBG)
    canvas.paste(region, box)
    colorBG = Image.new("RGBA", (region.width, region.height), "#FFFFFF22")
    region.paste(colorBG, mask=colorBG)
    canvas.paste(region, box)
    box = (padding, y, x + padding, y + image.size[1])
    region = canvas.crop(box).filter(ImageFilter.BLUR).filter(ImageFilter.GaussianBlur(radius=8))
    canvas.paste(region, box)
    canvas.paste(image, (padding, y), mask=image)


class Manager:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path) if isinstance(path, str) else path
        self.BG_PATH = self.path / "BG_image"
        self.BG_PATH.mkdir(exist_ok=True, parents=True)
        self.backup_path = self.path / "backup"
        self.backup_path.mkdir(exist_ok=True, parents=True)
        self.sqlite_db = self.path.joinpath("clovers_game_collection.db")
        self.db = DataBase(f"sqlite:///{self.sqlite_db.as_posix()}")
        self.items_library = Library[str, Item]()
        for k, v in json.loads(Path(__file__).parent.joinpath("props_library.json").read_text(encoding="utf_8")).items():
            item = Item(f"item:{k}", **v)
            self.items_library.set_library(item.id, {item.name}, item)
        self.marking_library = Library[str, Item]()

    def backup(self):
        date_today, now_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S").split()
        backup_today = self.backup_path / date_today
        if not backup_today.exists():
            backup_today.mkdir(mode=755)
        file = backup_today / f"clovers_game_collection {now_time}.db"
        shutil.copy2(self.sqlite_db, file)

    def clean_backup(self, delta: int | float):
        folders = [f for f in self.backup_path.iterdir() if f.is_dir()]
        info = []
        timestamp = datetime.now().timestamp()
        for folder in folders:
            if timestamp - folder.stat().st_birthtime > delta:
                shutil.rmtree(folder)
                info.append(f"备份 {folder} 已删除！")
        return "\n".join(info)

    def info_card(self, info: ImageList, user_id: str, BG_type: str | CanvasEffectHandler = canvas_effect):
        BG_PATH = self.BG_PATH / f"{user_id}.png"
        if not BG_PATH.exists():
            BG_PATH = self.BG_PATH / "default.png"
        output = BytesIO()
        info_splicing(info, BG_PATH, spacing=10, BG_type=BG_type).save(output, format="png")
        return output

    def account(self, event: Event, session: Session):
        user_id = event.user_id
        user = self.db.user(user_id, session)
        group_id = event.group_id or user.connect
        if not group_id:
            return None
        account = self.db.account(user_id, group_id, session)
        nickname = event.nickname
        if event.nickname:
            account.name = nickname
            if event.is_private() or not user.name:
                user.name = nickname
                session.add(user)
            session.add(account)
            session.commit()
            session.refresh(account)
        return account

    def transfer(
        self,
        item: Item,
        unsettled: int,
        sender_id: str,
        receiver_id: str,
        group_id: str,
        session: Session,
        force: bool = False,
    ) -> tuple[bool, str]:
        if unsettled < 1:
            return False, f"数量不能小于1。"
        sender_account = self.db.account(sender_id, group_id, session)
        sender_name = sender_account.name or sender_account.user.name or sender_account.user_id
        if (n := item.deal(sender_account, -unsettled, session)) is not None:
            if force:
                unsettled = n
                item.deal(sender_account, -unsettled, session)
            else:
                return False, f"数量不足。\n——{sender_name}还有{n}个{item.name}。"
        receiver_account = self.db.account(receiver_id, group_id, session)
        item.deal(receiver_account, unsettled, session)
        receiver_name = receiver_account.name or receiver_account.user.name or receiver_account.user_id
        return True, f"{sender_name} 向 {receiver_name} 赠送了{unsettled}个{item.name}"

    def group_wealths(self, group: Group, item_id: str, session: Session) -> list[int]:
        """
        群内总资产
        """
        wealths: list[int] = []
        item = self.items_library[item_id]
        if item.domain == 1:
            group_id = group.id
            query = AccountBank.select().join(Account).where(AccountBank.item_id == item_id, Account.group_id == group_id)
            wealths.extend(b.n for b in session.exec(query).all())
        group_bank = group.item(item_id, session).first()
        if group_bank is not None:
            wealths.append(group_bank.n)
        return wealths

    def stock_data(self, invest: Sequence[BaseBank], session: Session):
        banks = {bank.item_id: bank.n for bank in invest if bank.item_id.startswith("stock:")}
        stocks = session.exec(Stock.select().where(Stock.id.in_(banks.keys()))).all()  # type: ignore
        return [(stock, banks.get(stock.id, 0)) for stock in stocks]

    def stock_value(self, stock_data: list[tuple[Stock, int]], session: Session):
        value = sum(stock.value * n / issuance for stock, n in stock_data if (issuance := stock.issuance) > 0)
        return int(value)

    def item_data(self, bank: Sequence[BaseBank]):
        items: list[tuple[Item, int]] = []
        for b in bank:
            if (item_id := b.item_id).startswith("item:"):
                n = b.n
                if n > 0 and (item := self.items_library.get(item_id)):
                    items.append((item, n))
        return items

    def bank_data(self, bank: Sequence[BaseBank], session: Session):
        items: list[tuple[Item, int]] = []
        banks: dict[str, int] = {}
        for b in bank:
            item_id = b.item_id
            n = b.n
            if item_id.startswith("item:"):
                if n > 0 and (item := self.items_library.get(item_id)):
                    items.append((item, n))
            elif item_id.startswith("stock:"):
                banks[item_id] = n
            else:
                pass
        stocks = session.exec(Stock.select().where(Stock.id.in_(banks.keys()))).all()  # type: ignore
        return items, [(stock, banks.get(stock.id, 0)) for stock in stocks]

    @staticmethod
    def find_group(name: str, session: Session):
        group = session.get(Group, name)
        if group is not None:
            return group
        stock = Stock.find(name, session)
        if stock is not None:
            return stock.group
