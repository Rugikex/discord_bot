from __future__ import annotations
from typing import TYPE_CHECKING

from my_functions import delete_msg

if TYPE_CHECKING:
    import discord

    from classes.track import Track


class SearchResults:
    def __init__(
        self,
        tracks: list[Track],
        query: str,
        shuffle: bool,
        user: discord.User | discord.Member,
        message: discord.Message | None,
        position: int | None,
    ) -> None:
        self._tracks: list[Track] = tracks
        self._query: str = query
        self._shuffle: bool = shuffle
        self._user: discord.User | discord.Member = user
        self._message: discord.Message | None = message
        self._position: int | None = position

    @property
    def tracks(self) -> list[Track]:
        return self._tracks

    @property
    def query(self) -> str:
        return self._query

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @property
    def user(self) -> discord.User | discord.Member:
        return self._user

    @property
    def message(self) -> discord.Message | None:
        return self._message

    @message.setter
    def message(self, value: discord.Message | None) -> None:
        self._message = value

    async def delete_message(self) -> None:
        await delete_msg(self._message)
        self._message = None

    @property
    def position(self) -> int | None:
        return self._position

    def get_track(self, index: int) -> Track:
        return self._tracks[index]
