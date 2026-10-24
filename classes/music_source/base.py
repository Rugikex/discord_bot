from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

import discord

from constants import BASE_DIR

if TYPE_CHECKING:
    from classes.my_client import MyClient
    from classes.track import Track
    from collections.abc import Awaitable, Callable


ASSETS_FOLDER: Path = BASE_DIR / "assets"


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
    async def get_track(
        self, link: str, requester: discord.User | discord.Member
    ) -> Track | None:
        """Build a track (with its real title and duration) from a link."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        interaction: discord.Interaction[MyClient],
        shuffle: bool,
        position: int | None,
        create_button_select: Callable[[int, str], Awaitable[discord.ui.Button]],
    ) -> list[Track]:
        pass

    @abstractmethod
    async def get_stream_url(self, track: Track) -> tuple[str | None, dict[str, str]]:
        pass

    def create_embed(
        self, track: Track, loop_requester: str | None
    ) -> tuple[discord.Embed, discord.File]:
        """Create a discord embed and a discord file with logo."""
        file: discord.File = discord.File(ASSETS_FOLDER / self.logo, filename=self.logo)

        embed: discord.Embed = discord.Embed(
            title=track.title, url=self.get_url(track), color=self.color
        )
        embed.set_author(name="Playing", icon_url=f"attachment://{self.logo}")
        loop_str: str = (
            f"✅ made by {loop_requester}" if loop_requester is not None else "❌"
        )
        embed.description = (
            f"Duration: {track.duration}\n"
            f"Loop: {loop_str}\n"
            f"Requested by {track.requester.mention}"
        )

        return embed, file
