from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from classes.track import Track
    from collections.abc import Awaitable, Callable
    import discord


class MusicSource(ABC):
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
