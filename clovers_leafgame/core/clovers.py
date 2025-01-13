from io import BytesIO
from collections.abc import Callable, AsyncGenerator
from clovers import Event as CloversEvent, Result
from clovers_utils.tools import to_int


def build_result(result):
    if isinstance(result, str):
        return Result("text", result)
    if isinstance(result, BytesIO):
        return Result("image", result)
    if isinstance(result, list):
        return Result("list", [build_result(seg) for seg in result])
    if isinstance(result, AsyncGenerator):

        async def output():
            async for x in result:
                yield build_result(x)

        return Result("segmented", output())
    return result


class Event:
    def __init__(self, event: CloversEvent):
        self.event: CloversEvent = event

    @property
    def raw_command(self):
        return self.event.raw_command

    @property
    def args(self):
        return self.event.args

    async def send_group_message(self, group_id: str, result):
        return await self.event.call("group_message", {"group_id": group_id, "data": build_result(result)})

    async def send_private_message(self, user_id: str, result):
        return await self.event.call("private_message", {"user_id": user_id, "data": build_result(result)})

    @property
    def Bot_Nickname(self):
        return self.event.properties["Bot_Nickname"]

    @property
    def user_id(self) -> str:
        return self.event.properties["user_id"]

    @property
    def group_id(self) -> str:
        return self.event.properties["group_id"]

    @property
    def nickname(self) -> str:
        return self.event.properties["nickname"].replace("\n", "").replace(" ", "")

    @property
    def permission(self) -> int:
        return self.event.properties["permission"]

    @property
    def to_me(self) -> bool:
        return self.event.properties["to_me"]

    @property
    def at(self) -> list[str]:
        return self.event.properties["at"]

    def is_private(self) -> bool:
        return self.group_id is None

    @property
    def avatar(self) -> str | None:
        return self.event.properties["avatar"]

    @property
    def image_list(self) -> list[str]:
        return self.event.properties["image_list"]

    @property
    def group_avatar(self) -> str | None:
        return self.event.properties["group_avatar"]

    def args_to_int(self):
        if args := self.args:
            n = to_int(args[0]) or 0
        else:
            n = 0
        return n

    def args_parse(self) -> tuple[str, int, float] | None:
        args = self.args
        if not args:
            return
        l = len(args)
        if l == 1:
            return args[0], 1, 0
        name = args[0]
        n = args[1]
        if number := to_int(n):
            n = number
        elif number := to_int(name):
            name = n
            n = number
        else:
            n = 1
        f = 0
        if l > 2:
            try:
                f = float(args[2])
            except:
                pass
        return name, n, f

    def single_arg(self):
        if args := self.args:
            return args[0]


class Rule:
    @staticmethod
    def superuser(event: Event):
        return event.permission > 2

    @staticmethod
    def group_owner(event: Event):
        return event.permission > 1

    @staticmethod
    def group_admin(event: Event):
        return event.permission > 0

    @staticmethod
    def to_me(event: Event):
        return event.to_me

    @staticmethod
    def at(event: Event):
        return bool(event.at)

    @staticmethod
    def locate(user_id: str, group_id: str) -> Callable[[Event], bool]:
        return lambda e: e.user_id == user_id and e.group_id == group_id
