from __future__ import annotations
import asyncio
import datetime
import re
from typing import TYPE_CHECKING, Any

from discord import Color
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .base import MusicSource
from classes.track import Track
from constants import MAX_SEARCH_RESULTS
from logger_setup import YDLLogger, my_logger

if TYPE_CHECKING:
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

    def is_link(self, query: str) -> bool:
        return (
            YOUTUBE_PLAYLIST_REGEX.search(query) is not None
            or YOUTUBE_VIDEO_REGEX.search(query) is not None
        )

    async def load(
        self, link: str, requester: discord.User | discord.Member
    ) -> list[Track]:
        if YOUTUBE_PLAYLIST_REGEX.search(link) is None:
            return await self._single_link(link, requester)

        tracks: list[Track] = await self._playlist_link(link, requester)
        if tracks:
            return tracks

        # Unreadable playlist (e.g. a mix): load only the video of the link
        match: re.Match[str] | None = YOUTUBE_VIDEO_WITH_LIST_REGEX.match(link)
        if match is None:
            return []
        video_id: str = match[4] if match[4] is not None else match[7]
        return await self._single_link(f"https://youtu.be/{video_id}", requester)

    async def search(
        self, query: str, requester: discord.User | discord.Member
    ) -> list[Track]:
        info: dict[str, Any] | None = await asyncio.to_thread(
            _extract_flat, f"ytsearch{MAX_SEARCH_RESULTS}:{query}"
        )
        return _entries_to_tracks(info, requester)

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
        self, playlist_url: str, requester: discord.User | discord.Member
    ) -> list[Track]:
        normalized_url: str = self._normalize_youtube_url(playlist_url)
        info: dict[str, Any] | None = await asyncio.to_thread(
            _extract_flat, normalized_url
        )
        return _entries_to_tracks(info, requester)
