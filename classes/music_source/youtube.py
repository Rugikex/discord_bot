from __future__ import annotations
import asyncio
import datetime
import re
from typing import TYPE_CHECKING, Any

from discord import Color
from discord.ui import View
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .base import MusicSource
from classes.search_results import SearchResults
from classes.track import Track
from logger_setup import YDLLogger, my_logger
import my_functions

if TYPE_CHECKING:
    from classes.my_client import MyClient
    from classes.guild_player import GuildPlayer
    from collections.abc import Awaitable, Callable

    import discord


YDL_STREAM_OPTIONS: dict[str, Any] = {
    "simulate": True,
    "format": "bestaudio/best",
    "noplaylist": True,
    "logger": YDLLogger(),
    "youtube_include_dash_manifest": False,
    "ignoreerrors": True,
}

FFMPEG_OPTIONS: dict[str, str] = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 3",
    "options": "-vn -loglevel quiet",
}

YOUTUBE_PLAYLIST_REGEX: re.Pattern[str] = re.compile(
    r"^(https://)?(www\.|music\.)?(youtube\.com|youtu\.be)/"
    r"((playlist\?list=[^&]+)|(watch\?v=[^&]+&list=[^&]+))"
)

YOUTUBE_VIDEO_REGEX: re.Pattern[str] = re.compile(
    r"^(https://)?(www\.|music\.)?(youtube\.com/watch\?v=[^&]+|youtu\.be/[^?&]+)"
)

YOUTUBE_VIDEO_WITH_LIST_REGEX: re.Pattern[str] = re.compile(
    r"^(https://)?(www\.|music\.)?(youtube\.com/watch\?v=([^&\n]+)(&list=[^&\n]+)?(&index=[^&\n]+)?|youtu\.be/([^?&\n]+))"
)


def _extract_flat(url: str) -> dict[str, Any] | None:
    """Blocking (network): run it in an executor."""
    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except DownloadError as error:
        my_logger.warning("yt-dlp can't extract %s: %s", url, error)
        return None


def _extract_stream(url: str) -> dict[str, Any] | None:
    """Blocking (network): run it in an executor."""
    try:
        with YoutubeDL(YDL_STREAM_OPTIONS) as ydl:
            return ydl.extract_info(url)
    except DownloadError as error:
        my_logger.warning("yt-dlp can't get stream of %s: %s", url, error)
        return None


def _entries_to_tracks(
    info: dict[str, Any] | None, requester: discord.User | discord.Member
) -> list[Track]:
    if not info:
        return []

    tracks: list[Track] = []
    for entry in info.get("entries") or []:
        if not entry or entry.get("duration") is None:
            continue
        tracks.append(
            Track(
                entry.get("title", ""),
                datetime.timedelta(seconds=entry["duration"]),
                entry.get("url", ""),
                "youtube",
                requester,
            )
        )
    return tracks


class YoutubeSource(MusicSource):
    color: Color = Color.red()
    logo: str = "youtube-logo.png"

    def get_url(self, track: Track) -> str | None:
        return track.link

    async def get_track(
        self, link: str, requester: discord.User | discord.Member
    ) -> Track | None:
        tracks: list[Track] = await self._single_link(link, requester)
        return tracks[0] if tracks else None

    async def search(
        self,
        query: str,
        interaction: discord.Interaction[MyClient],
        shuffle: bool,
        position: int | None,
        create_button_select: Callable[[int, str], Awaitable[discord.ui.Button]],
    ) -> list[Track]:
        message: discord.Message | None
        player: GuildPlayer = interaction.client.get_player(interaction.guild_id)
        tracks: list[Track] = []

        if YOUTUBE_PLAYLIST_REGEX.search(query) is not None:
            message = await my_functions.send_by_channel(
                interaction.channel, "Loading playlist...", permanent=True
            )
            player.loading_playlist_message = message
            tracks = await self._playlist_link(query, interaction)
        elif YOUTUBE_VIDEO_REGEX.search(query) is not None:
            message = await my_functions.send_by_channel(
                interaction.channel, "Loading track...", permanent=True
            )
            tracks = await self._single_link(query, interaction.user)
            await my_functions.delete_msg(message)
        else:
            if player.search_results is not None:
                await my_functions.delete_msg(player.search_results.message)

            message = await my_functions.send_by_channel(
                interaction.channel,
                f"Searching for track related to {query}.",
                permanent=True,
            )

            searches: list[Track] = await self._specific_search(query, interaction.user)

            if not searches:
                await my_functions.edit_message(
                    message, content=f'No track found for "{query}".', delete_after=10.0
                )
                return []

            search_results: SearchResults = SearchResults(
                searches, shuffle, interaction.user, message, position
            )
            player.search_results = search_results

            msg_content: str = "Select a track with buttons.\n\n"
            for i, track in enumerate(searches):
                msg_content += f"**{i + 1}:** {track}\n"

            view: View = View()
            for i in range(len(searches)):
                view.add_item(await create_button_select(i, query))

            await my_functions.edit_message(message, content=msg_content, view=view)
            return []

        if len(tracks) == 0 and YOUTUBE_VIDEO_WITH_LIST_REGEX.search(query) is not None:
            match: re.Match[str] | None = YOUTUBE_VIDEO_WITH_LIST_REGEX.match(query)

            await my_functions.send_by_channel(
                interaction.channel, "No playlist found, loading track..."
            )
            if match:
                video_id: str = match[4] if match[4] is not None else match[7]
                tracks = await self._single_link(
                    f"https://youtu.be/{video_id}", interaction.user
                )

        if len(tracks) == 0:
            await my_functions.send_by_channel(
                interaction.channel, f'No audio found for "{query}".'
            )
            return []

        return tracks

    async def get_stream_url(self, track: Track) -> tuple[str | None, dict[str, str]]:
        info: dict[str, Any] | None = await asyncio.to_thread(
            _extract_stream, track.link
        )

        url: str | None = None
        if info:
            # "url" is the format selected by ydl_opts["format"] (bestaudio)
            url = info.get("url")
            if url is None:
                # Formats are sorted from worst to best
                for info_format in reversed(info.get("formats") or []):
                    if info_format.get("acodec") not in (None, "none"):
                        url = info_format.get("url")
                        break
        return url, FFMPEG_OPTIONS

    async def _specific_search(
        self, query: str, requester: discord.User | discord.Member
    ) -> list[Track]:
        info: dict[str, Any] | None = await asyncio.to_thread(
            _extract_flat, f"ytsearch5:{query}"
        )
        return _entries_to_tracks(info, requester)

    async def _single_link(
        self, video_url: str, requester: discord.User | discord.Member
    ) -> list[Track]:
        info: dict[str, Any] | None = await asyncio.to_thread(_extract_flat, video_url)

        if not info or info.get("duration") is None:
            return []
        return [
            Track(
                info.get("title", ""),
                datetime.timedelta(seconds=info.get("duration", 0)),
                info.get("webpage_url", video_url),
                "youtube",
                requester,
            )
        ]

    def _normalize_youtube_url(self, url: str) -> str:
        match: re.Match[str] | None = re.search(r"[?&]list=([^&]+)", url)
        if match:
            playlist_id: str = match.group(1)
            return f"https://www.youtube.com/playlist?list={playlist_id}"
        return url

    async def _playlist_link(
        self, playlist_url: str, interaction: discord.Interaction[MyClient]
    ) -> list[Track]:
        normalized_url: str = self._normalize_youtube_url(playlist_url)

        player: GuildPlayer = interaction.client.get_player(interaction.guild_id)

        info: dict[str, Any] | None = await asyncio.to_thread(
            _extract_flat, normalized_url
        )
        tracks: list[Track] = _entries_to_tracks(info, interaction.user)

        await my_functions.delete_msg(player.loading_playlist_message)
        player.loading_playlist_message = None

        return tracks
