from __future__ import annotations
import asyncio
from datetime import timedelta
from mutagen import File, MutagenError
from pathlib import Path
from typing import TYPE_CHECKING

from discord import Color
from thefuzz import fuzz

from .base import MusicSource
from classes.track import Track
from classes.search_results import SearchResults
from classes.search_view import show_search_results
from constants import BASE_DIR
import my_functions

if TYPE_CHECKING:
    from classes.my_client import MyClient
    from classes.guild_player import GuildPlayer
    from classes.search_view import OnSelect
    import discord


MUSIC_FOLDER: Path = BASE_DIR / "music"
AUDIO_EXTENSIONS: tuple[str, ...] = (".mp3", ".wav", ".flac")


def list_local_files() -> list[Path]:
    if not MUSIC_FOLDER.is_dir():
        return []
    return [
        path
        for path in MUSIC_FOLDER.iterdir()
        if path.suffix.lower() in AUDIO_EXTENSIONS
    ]


def load_local_track(
    path: str | Path, requester: discord.User | discord.Member
) -> Track | None:
    """Blocking (reads the file): run it in an executor."""
    # A relative path (e.g. "music/intro.mp3" in the settings) starts from BASE_DIR
    path = BASE_DIR / path
    try:
        audio = File(path)
    except (MutagenError, OSError):
        return None
    if audio is None or audio.info is None:
        return None

    return Track(
        path.stem,
        timedelta(seconds=int(audio.info.length)),
        str(path),
        "local",
        requester,
    )


def load_local_tracks(
    paths: list[Path], requester: discord.User | discord.Member
) -> list[Track]:
    """Blocking (reads files): run it in an executor."""
    tracks: list[Track] = []
    for path in paths:
        track: Track | None = load_local_track(path, requester)
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
        on_select: OnSelect,
    ) -> list[Track]:
        files: list[Path] = list_local_files()
        player: GuildPlayer = interaction.client.get_player(interaction.guild_id)

        if player.search_results is not None:
            await my_functions.delete_msg(player.search_results.message)

        message = await my_functions.send_by_channel(
            interaction.channel,
            f"Searching for track related to {query}.",
            permanent=True,
        )

        matches = []
        for file in files:
            score = fuzz.WRatio(query, file.stem)
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
            searches, query, shuffle, interaction.user, message, position
        )
        player.search_results = search_results

        await show_search_results(search_results, on_select)
        return []

    async def get_stream_url(self, track: Track) -> tuple[str | None, dict[str, str]]:
        return track.link, {"options": "-vn -loglevel quiet"}
