from __future__ import annotations
import datetime
from typing import TYPE_CHECKING

import discord
from googleapiclient.errors import HttpError
import isodate
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


async def playlist_link(
    playlist_url: str, interaction: discord.Interaction
) -> list[Track]:
    # if globals_var.client_bot.server_id_using_youtube is not None:
    #     return [None]
    # globals_var.client_bot.server_id_using_youtube = interaction.guild_id

    server: Server = globals_var.client_bot.get_server(interaction.guild_id)
    if server is None:
        return []

    ydl_opts = {"quiet": True, "extract_flat": True}

    def extract_info(playlist_url: str) -> dict:
        with YoutubeDL(ydl_opts) as ydl:
            info: dict = ydl.extract_info(playlist_url, download=False)
        return info

    info: dict = await globals_var.client_bot.loop.run_in_executor(
        None, extract_info, playlist_url
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

    # globals_var.client_bot.server_id_using_youtube = None
    await my_functions.delete_msg(server.loading_playlist_message)
    server.loading_playlist_message = None

    return tracks


# Not use
# def create_tracks(video_ids: str) -> list[Track]:
#     res: list[Track] = []
#     request = globals_var.youtube.videos().list(
#         part="snippet,contentDetails,id", id=video_ids
#     )
#     response = request.execute()

#     for item in response["items"]:
#         res.append(
#             Track(
#                 item["snippet"]["title"],
#                 isodate.parse_duration(item["contentDetails"]["duration"]),
#                 "https://www.youtube.com/watch?v=" + item["id"],
#             )
#         )

#     return res


# # Faster than playlist_link but costs twice in YouTube API units
# def playlist_link2(link: str) -> list[Track]:
#     playlist_id: str = link.split("list=", 1)[1].split("&", 1)[0]
#     request_id = globals_var.youtube.playlistItems().list(
#         part="contentDetails", maxResults=50, playlistId=playlist_id
#     )
#     res: list[Track] = []
#     while request_id is not None:
#         try:
#             response_id = request_id.execute()
#         except HttpError:
#             return []

#         video_ids = ",".join(
#             map(
#                 str, map(lambda n: n["contentDetails"]["videoId"], response_id["items"])
#             )
#         )
#         res.extend(create_tracks(video_ids))

#         request_id = globals_var.youtube.playlistItems().list_next(
#             previous_request=request_id, previous_response=response_id
#         )

#     return res
