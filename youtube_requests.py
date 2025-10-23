from __future__ import annotations
import datetime
import re
from typing import TYPE_CHECKING

import discord
from yt_dlp import YoutubeDL

from classes.track import Track
import globals_var
import my_functions

if TYPE_CHECKING:
    from classes.server import Server


def specific_search(
    query: str, requester: discord.User | discord.Member
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
                requester,
            )
        )

    return tracks


async def single_link(
    video_url: str, requester: discord.User | discord.Member
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
            requester,
        )
    ]

def normalize_youtube_url(url: str) -> str:
    match: re.Match[str] | None = re.search(r"[?&]list=([^&]+)", url)
    if match:
        playlist_id: str = match.group(1)
        return f"https://www.youtube.com/playlist?list={playlist_id}"
    return url

async def playlist_link(
    playlist_url: str, interaction: discord.Interaction
) -> list[Track]:
    normalized_url: str = normalize_youtube_url(playlist_url)

    server: Server = globals_var.client_bot.get_server(interaction.guild_id)
    if server is None:
        return []

    ydl_opts = {"quiet": True, "extract_flat": True}

    def extract_info(url: str) -> dict:
        with YoutubeDL(ydl_opts) as ydl:
            info: dict = ydl.extract_info(url, download=False)
        return info

    info: dict = await globals_var.client_bot.loop.run_in_executor(
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
            interaction.user,
        )
        tracks.append(track)

    await my_functions.delete_msg(server.loading_playlist_message)
    server.loading_playlist_message = None

    return tracks
