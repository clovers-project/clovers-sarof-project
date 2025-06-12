import asyncio
import httpx
from collections.abc import Iterable
from typing import overload


class Library[K, V]:
    """多键字典"""

    @overload
    def __init__(self, data: Iterable[tuple[K, Iterable[K], V]]) -> None: ...
    @overload
    def __init__(self) -> None: ...

    def __init__(self, data=None) -> None:
        self._key_data: dict[K, V] = {}
        self._index_key: dict[K, K] = {}
        self._key_indices: dict[K, set[K]] = {}
        if not data:
            return
        for key, alias, value in data:
            self.set_item(key, alias, value)

    def __getitem__(self, index: K) -> V:
        return self._key_data.get(index) or self._key_data[self._index_key[index]]

    def __setitem__(self, index: K, data: V):
        key = self._index_key.get(index, index)
        self._key_data[key] = data

    def __contains__(self, key):
        return key in self._key_indices or key in self._index_key

    def __iter__(self):
        return iter((key, self._key_indices[key], value) for key, value in self._key_data.items())

    def keys(self):
        return self._key_data.keys()

    def values(self):
        return self._key_data.values()

    def items(self):
        return self._key_data.items()

    def set_item(self, key: K, indices: Iterable[K], data: V):
        if old_indices := self._key_indices.get(key):
            for i in old_indices:
                del self._index_key[i]
        self._key_data[key] = data
        indices = set(indices)
        self._key_indices[key] = indices
        for i in indices:
            self._index_key[i] = key

    def __delitem__(self, index: K):
        if index in self._key_data:
            del self._key_data[index]
            if indices := self._key_indices.get(index):
                for i in indices:
                    del self._index_key[i]
                del self._key_indices[index]
            return
        if key := self._index_key[index]:
            del self._index_key[index]
            self._key_indices[key].discard(index)
            return
        raise KeyError(index)

    def update(self, data: "Library[K, V]"):
        for key, indices, value in data:
            self.set_item(key, indices, value)

    @overload
    def get(self, index: K) -> V | None: ...
    @overload
    def get(self, index: K, default: V) -> V: ...

    def get(self, index: K, default=None):
        if key := self._index_key.get(index):
            return self._key_data[key]
        return self._key_data.get(index, default)

    def setdefault(self, index: K, default: V):
        if key := self._index_key.get(index):
            return self._key_data[key]
        return self._key_data.setdefault(index, default)


def to_int(N) -> int | None:
    try:
        return int(N)
    except ValueError:
        return {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}.get(N)


def format_number(num: int | float) -> str:
    if num < 10000:
        return "{:,}".format(round(num, 2))
    x = str(int(num))
    if 10000 <= num < 100000000:
        if (y := int(x[-4:])) > 0:
            return f"{x[:-4]}万{y}"
        return f"{x[:-4]}万"
    if 100000000 <= num < 1000000000000:
        if (y := int(x[-8:-4])) > 0:
            return f"{x[:-8]}亿{y}万"
        return f"{x[:-8]}亿"
    if 1000000000000 <= num < 1000000000000000:
        if (y := int(x[-12:-8])) > 0:
            return f"{x[:-12]}万亿{y}亿"
        return f"{x[:-12]}万亿"
    return "{:.2e}".format(num)


async def download_url(url: str, client: httpx.AsyncClient, retry: int = 3):
    for _ in range(retry):
        try:
            resp = await client.get(url, timeout=20)
            resp.raise_for_status()
            return resp.content
        except httpx.HTTPStatusError:
            await asyncio.sleep(3)
        except httpx.ConnectError:
            return
