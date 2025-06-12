from typing import Any, Protocol
from collections.abc import AsyncGenerator
from clovers import EventProtocol, Event as BaseEvent, Result, Plugin
from .tools import to_int
from io import BytesIO


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


class PropertiesProtocol(Protocol):
    Bot_Nickname: str
    user_id: str
    group_id: str | None
    nickname: str
    avatar: str
    group_avatar: str | None
    to_me: bool
    permission: int
    at: list[str]
    image_list: list[str]


def create_plugin() -> Plugin:
    plugin = Plugin(build_event=Event, build_result=build_result)
    plugin.set_protocol("properties", PropertiesProtocol)
    return plugin


class Event(PropertiesProtocol, EventProtocol):
    def __init__(self, event: BaseEvent):
        self.event: BaseEvent = event

    def __getattr__(self, name: str) -> Any:
        return getattr(self.event, name)

    async def send_group_message(self, group_id: str, result):
        return await self.event.call("group_message", {"group_id": group_id, "data": build_result(result)})

    async def send_private_message(self, user_id: str, result):
        return await self.event.call("private_message", {"user_id": user_id, "data": build_result(result)})

    def is_private(self) -> bool:
        return self.group_id is None

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
    type Checker = Plugin.Rule.Checker[Event]
    superuser: Checker = lambda event: event.permission > 2
    group_owner: Checker = lambda event: event.permission > 1
    group_admin: Checker = lambda event: event.permission > 0
    to_me: Checker = lambda event: event.to_me
    at: Checker = lambda event: bool(event.at)
    private: Checker = lambda event: event.is_private()
    group: Checker = lambda event: not event.is_private()

    @staticmethod
    def identify(user_id: str, group_id: str) -> Checker:
        return lambda e: e.user_id == user_id and e.group_id == group_id
