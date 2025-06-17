import asyncio
import httpx
from collections.abc import Iterable
from typing import overload


class NeverKeyType:
    def __hash__(self):
        raise TypeError("NeverKeyType is unhashable")

    def __bool__(self):
        return False


NEVER_KEY = NeverKeyType()


def is_samekey(key1, key2):
    return len({key1, key2}) == 1


class Library[K, V]:
    @overload
    def __init__(self, data: Iterable[tuple[K, Iterable[K], V]]) -> None: ...
    @overload
    def __init__(self) -> None: ...

    def __init__(self, data=None) -> None:
        self._key_data: dict[K, V] = {}
        self._index_key: dict[K, K] = {}
        self._key_indices: dict[K, set[K]] = {}
        if not data:  # None or empty
            return
        for key, indices, value in data:
            self.set_library(key, indices, value)

    def __repr__(self):
        return repr({key: (self._key_indices[key], value) for key, value in self._key_data.items()})

    def __getitem__(self, index: K) -> V:
        if index in self._key_data:
            return self._key_data[index]
        if index in self._index_key:
            return self._key_data[self._index_key[index]]
        raise KeyError(f"{index} is not a key or alias")

    def __setitem__(self, key: K, data: V):
        if key in self._index_key:
            raise KeyError(f"{key} is already a alias for {self._index_key[key]}")
        self._key_data[key] = data
        if key not in self._key_indices:
            self._key_indices[key] = set()

    def __delitem__(self, index: K):
        if index in self._key_data:
            del self._key_data[index]
            if indices := self._key_indices.get(index):
                for i in indices:
                    del self._index_key[i]
                del self._key_indices[index]
        elif index in self._index_key:
            self._key_indices[self._index_key[index]].remove(index)
            del self._index_key[index]
        else:
            raise KeyError(f"{index} is not a key or alias")

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

    def primary_key(self, index: K) -> K:
        return index if index in self._key_data else self._index_key.get(index, NEVER_KEY)  # type: ignore # primary_key returns only K or NEVER_KEY

    def upsert(self, key: K, data: V):
        if (_key := self.primary_key(key)) is NEVER_KEY:
            _key = key
        self[_key] = data
        return _key

    def delete(self, key: K, missing_ok=True):
        if (key := self.primary_key(key)) is NEVER_KEY:
            if missing_ok:
                return
            raise KeyError(f"{key} is not a key or alias")
        del self[key]

    def set_alias(self, index: K, alias: K):
        if is_samekey(index, alias):
            raise ValueError(f"{index} and {alias} are same key")
        if alias in self._key_data:
            raise KeyError(f"{alias} is a primary key")
        if (key := self.primary_key(index)) is NEVER_KEY:
            raise KeyError(f"{index} is not a key or alias")
        if alias in self._index_key:
            if is_samekey(key, old_key := self._index_key[alias]):
                return
            else:
                self._key_indices[old_key].remove(alias)
        self._index_key[alias] = key
        self._key_indices[key].add(alias)

    def set_library(self, key: K, indices: Iterable[K], data: V):
        indices = set(indices)
        if alias := (indices & self._key_data.keys()):
            raise KeyError(f"{alias} are primary keys")
        _key = self.upsert(key, data)
        self._key_indices[_key].update(indices)
        for alias in indices:
            if alias in self._index_key and not is_samekey(_key, old_key := self._index_key[alias]):
                self._key_indices[old_key].remove(alias)
            self._index_key[alias] = _key

    def update(self, library: "Library[K, V]"):
        for data in library:
            self.set_library(*data)

    @overload
    def get(self, index: K) -> V | None: ...
    @overload
    def get(self, index: K, default: V) -> V: ...

    def get(self, index: K, default=None):
        if (key := self.primary_key(index)) is not NEVER_KEY:
            return self[key]
        else:
            return default

    def setdefault(self, index: K, default: V):
        if (key := self.primary_key(index)) is NEVER_KEY:
            key = index
            self[key] = default
        return self[key]


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
