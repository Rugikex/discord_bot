from __future__ import annotations
import asyncio
from datetime import timedelta
from mutagen import File, MutagenError
import os
from typing import TYPE_CHECKING

from discord import Color
from discord.ui import View
from thefuzz import fuzz

from .base import MusicSource
from classes.track import Track
from classes.search_results import SearchResults
import my_functions

if TYPE_CHECKING:
    from classes.my_client import MyClient
    from classes.server import Server
    from collections.abc import Awaitable, Callable
    import discord


MUSIC_FOLDER: str = "music"
AUDIO_EXTENSIONS: tuple[str, ...] = (".mp3", ".wav", ".flac")


def list_local_files() -> list[str]:
    if not os.path.isdir(MUSIC_FOLDER):
        return []
    return [f for f in os.listdir(MUSIC_FOLDER) if f.lower().endswith(AUDIO_EXTENSIONS)]


def load_local_track(
    path: str, requester: discord.User | discord.Member
) -> Track | None:
    """Blocking (reads the file): run it in an executor."""
    try:
        audio = File(path)
    except (MutagenError, OSError):
        return None
    if audio is None or audio.info is None:
        return None

    return Track(
        os.path.splitext(os.path.basename(path))[0],
        timedelta(seconds=int(audio.info.length)),
        path,
        "local",
        requester,
    )


def load_local_tracks(
    file_names: list[str], requester: discord.User | discord.Member
) -> list[Track]:
    """Blocking (reads files): run it in an executor."""
    tracks: list[Track] = []
    for file_name in file_names:
        track: Track | None = load_local_track(f"{MUSIC_FOLDER}/{file_name}", requester)
        if track is not None:
            tracks.append(track)
    return tracks


class LocalSource(MusicSource):
    color: Color = Color.from_str("#1F3F68")
    logo: str = "server-logo.png"

    def get_url(self, track: Track) -> str | None:
        return None

    async def get_track(
        self, link: str, requester: discord.User | discord.Member
    ) -> Track | None:
        return await asyncio.to_thread(load_local_track, link, requester)

    async def search(
        self,
        query: str,
        interaction: discord.Interaction[MyClient],
        shuffle: bool,
        position: int | None,
        create_button_select: Callable[[int, str], Awaitable[discord.ui.Button]],
    ) -> list[Track]:
        files: list[str] = list_local_files()
        server: Server = interaction.client.get_server(interaction.guild_id)

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

        searches: list[Track] = await asyncio.to_thread(
            load_local_tracks, matches, interaction.user
        )
        if not searches:
            await my_functions.edit_message(
                message, content=f'No track found for "{query}".', delete_after=10.0
            )
            return []

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
