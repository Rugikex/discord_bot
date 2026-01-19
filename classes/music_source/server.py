from __future__ import annotations
from datetime import timedelta
from mutagen import File
import os
from typing import TYPE_CHECKING

from discord import Color
from discord.ui import View
from thefuzz import fuzz

from .base import MusicSource
from classes.track import Track
from classes.search_results import SearchResults
import config
import my_functions


if TYPE_CHECKING:
    from classes.server import Server
    from collections.abc import Awaitable, Callable
    import discord


class ServerSource(MusicSource):
    color: Color = Color.from_str("#1F3F68")
    logo: str = "server-logo.png"

    def get_url(self, track: Track) -> str | None:
        return None

    async def search(
        self,
        query: str,
        interaction: discord.Interaction,
        shuffle: bool,
        position: int | None,
        create_button_select: Callable[[int, str], Awaitable[discord.ui.Button]],
    ) -> list[Track]:
        files = [
            f for f in os.listdir("music") if f.endswith((".mp3", ".wav", ".flac"))
        ]
        server: Server = config.client_bot.get_server(interaction.guild_id)

        if server.search_results is not None:
            await my_functions.delete_msg(server.search_results.message)

        message = await my_functions.send_by_channel(
            interaction.channel,
            f"Searching for track related to {query}.",
            permanent=True,
        )

        matches = []
        for file in files:
            score = fuzz.WRatio(query, os.path.splitext(file)[0])
            if score >= 50:
                matches.append({"file": file, "score": score})

        if not matches:
            await my_functions.edit_message(
                message, content=f'No track found for "{query}".', delete_after=10.0
            )
            return []

        matches.sort(key=lambda x: x["score"], reverse=True)
        matches = [match["file"] for match in matches]
        matches = matches[:5]

        searches: list[Track] = []
        match: str
        for match in matches:
            track = Track(
                match,
                timedelta(seconds=int(File(f"music/{match}").info.length)),
                f"music/{match}",
                "server",
                interaction.user,
            )
            searches.append(track)

        search_results: SearchResults = SearchResults(
            searches, shuffle, interaction.user, message, position
        )
        server.search_results = search_results

        msg_content: str = "Select a track with buttons.\n\n"
        for i, track in enumerate(searches):
            msg_content += f"**{i + 1}:** {track}\n"

        view: View = View()
        for i in range(len(searches)):
            view.add_item(await create_button_select(i, query))

        await my_functions.edit_message(message, content=msg_content, view=view)
        return []

    async def get_stream_url(self, track: Track) -> tuple[str | None, dict[str, str]]:
        return track.link, {"options": "-vn -loglevel quiet"}
