from collections.abc import Callable
from clovers.core.plugin import Event as CloversEvent, Plugin
from clovers.utils.tools import to_int


class Event:
    def __init__(self, event: CloversEvent):
        self.event: CloversEvent = event

    @property
    def raw_command(self):
        return self.event.raw_command

    @property
    def args(self):
        return self.event.args

    @property
    def user_id(self) -> str:
        return self.event.kwargs["user_id"]

    @property
    def group_id(self) -> str:
        return self.event.kwargs["group_id"]

    @property
    def nickname(self) -> str:
        return self.event.kwargs["nickname"]

    @property
    def permission(self) -> int:
        return self.event.kwargs["permission"]

    @property
    def to_me(self) -> bool:
        return self.event.kwargs["to_me"]

    @property
    def at(self) -> list[str]:
        return self.event.kwargs["at"]

    def is_private(self) -> bool:
        return self.group_id is None

    @property
    def avatar(self) -> str | None:
        return self.event.kwargs["avatar"]

    @property
    def image_list(self) -> list[str]:
        return self.event.kwargs["image_list"]

    @property
    def group_avatar(self) -> str | None:
        return self.event.kwargs["group_avatar"]

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

    async def send_group_message(self, group_id: str, result):
        func = self.event.kwargs.get("send_group_message")
        if not func:
            return
        try:
            await func(group_id=group_id, result=result)
        except Exception as e:
            print(e)


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
    def locate(user_id: str, group_id: str):
        def decorator(func):
            async def wrapper(event: Event, finish: Plugin.Finish):
                if event.user_id == user_id and event.group_id == group_id:
                    return
                return await func(event, finish)

            return wrapper

        return decorator
