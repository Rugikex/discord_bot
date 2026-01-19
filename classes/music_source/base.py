from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from classes.track import Track
    from collections.abc import Awaitable, Callable
    import discord


class MusicSource(ABC):

    @property
    @abstractmethod
    def color(self) -> discord.Color: ...

    @property
    @abstractmethod
    def logo(self) -> str: ...

    @abstractmethod
    def get_url(self, track: Track) -> str | None:
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        interaction: discord.Interaction,
        shuffle: bool,
        position: int | None,
        create_button_select: Callable[[int, str], Awaitable[discord.ui.Button]],
    ) -> list[Track]:
        pass

    @abstractmethod
    async def get_stream_url(self, track: Track) -> tuple[str | None, dict[str, str]]:
        pass
