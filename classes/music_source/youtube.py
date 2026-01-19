from __future__ import annotations
import datetime
import re
from typing import TYPE_CHECKING

from discord import Color
from discord.ui import View
from yt_dlp import YoutubeDL

from .base import MusicSource
from classes.search_results import SearchResults
from classes.track import Track
import config
import my_functions

if TYPE_CHECKING:
    from classes.server import Server
    from collections.abc import Awaitable, Callable

    import discord


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


class YoutubeSource(MusicSource):
    color: Color = Color.red()
    logo: str = "youtube-logo.png"

    def get_url(self, track: Track) -> str | None:
        return track.link

    async def search(
        self,
        query: str,
        interaction: discord.Interaction,
        shuffle: bool,
        position: int | None,
        create_button_select: Callable[[int, str], Awaitable[discord.ui.Button]],
    ) -> list[Track]:
        message: discord.Message | None
        server: Server = config.client_bot.get_server(interaction.guild_id)
        tracks: list[Track] = []

        if YOUTUBE_PLAYLIST_REGEX.search(query) is not None:
            message = await my_functions.send_by_channel(
                interaction.channel, "Loading playlist...", permanent=True
            )
            server.loading_playlist_message = message
            tracks = await self._playlist_link(query, interaction)
        elif YOUTUBE_VIDEO_REGEX.search(query) is not None:
            message = await my_functions.send_by_channel(
                interaction.channel, "Loading track...", permanent=True
            )
            tracks = await self._single_link(query, interaction.user)
            await my_functions.delete_msg(message)
        else:
            if server.search_results is not None:
                await my_functions.delete_msg(server.search_results.message)

            message = await my_functions.send_by_channel(
                interaction.channel,
                f"Searching for track related to {query}.",
                permanent=True,
            )

            searches: list[Track] = self._specific_search(query, interaction.user)

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
        with YoutubeDL(config.ydl_opts) as ydl:
            info: dict = await config.client_bot.loop.run_in_executor(
                None, ydl.extract_info, track.link
            )

        url: str | None = None
        if info:
            for info_format in info["formats"]:
                if "asr" not in info_format:
                    continue
                url = info_format["url"]
                break
        return url, FFMPEG_OPTIONS

    def _specific_search(
        self, query: str, requester: discord.User | discord.Member
    ) -> list[Track]:
        ydl_opts: dict = {
            "quiet": True,
            "extract_flat": True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            search_url: str = f"ytsearch5:{query}"
            info: dict = ydl.extract_info(search_url, download=False)

        tracks: list[Track] = []
        for entry in info.get("entries", []):
            if entry.get("duration") is None:
                continue
            tracks.append(
                Track(
                    entry.get("title", ""),
                    datetime.timedelta(seconds=entry.get("duration", 0)),
                    entry.get("url", ""),
                    "youtube",
                    requester,
                )
            )

        return tracks

    async def _single_link(
        self, video_url: str, requester: discord.User | discord.Member
    ) -> list[Track]:
        ydl_opts = {"quiet": True, "extract_flat": True}

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        if info.get("duration") is None:
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
        self, playlist_url: str, interaction: discord.Interaction
    ) -> list[Track]:
        normalized_url: str = self._normalize_youtube_url(playlist_url)

        server: Server = config.client_bot.get_server(interaction.guild_id)
        if server is None:
            return []

        ydl_opts = {"quiet": True, "extract_flat": True}

        def extract_info(url: str) -> dict:
            with YoutubeDL(ydl_opts) as ydl:
                info: dict = ydl.extract_info(url, download=False)
            return info

        info: dict = await config.client_bot.loop.run_in_executor(
            None, extract_info, normalized_url
        )

        tracks: list[Track] = []
        for entry in info.get("entries", []):
            if entry.get("duration") is None:
                continue
            track = Track(
                entry.get("title", ""),
                datetime.timedelta(seconds=entry.get("duration", 0)),
                entry.get("url", ""),
                "youtube",
                interaction.user,
            )
            tracks.append(track)

        await my_functions.delete_msg(server.loading_playlist_message)
        server.loading_playlist_message = None

        return tracks
