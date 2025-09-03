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
        shuffle: bool,
        user: discord.Member,
        message: discord.Message | None,
        position: int | None,
    ) -> None:
        self._tracks: list[Track] = tracks
        self._shuffle: bool = shuffle
        self._user: discord.Member = user
        self._message: discord.Message = message
        self._position: int = position

    @property
    def tracks(self) -> list[Track]:
        return self._tracks

    @tracks.setter
    def tracks(self, value: list[Track]) -> None:
        self._tracks = value

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @property
    def user(self) -> discord.Member:
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
