from __future__ import annotations
import datetime
from typing import TYPE_CHECKING

import discord
from googleapiclient.errors import HttpError
import isodate
import pytubefix
import pytubefix.exceptions

from classes.track import Track
import globals_var
import my_functions

if TYPE_CHECKING:
    from classes.server import Server


def create_track(yt_obj: pytubefix.YouTube) -> Track:
    title: str = yt_obj.title
    duration: datetime.timedelta | None = None
    try:
        duration = datetime.timedelta(seconds=yt_obj.length)
    except TypeError:
        pass
    url: str = yt_obj.watch_url
    return Track(title, duration, url)


def create_tracks(video_ids: str) -> list[Track]:
    res: list[Track] = []
    request = globals_var.youtube.videos().list(
        part="snippet,contentDetails,id", id=video_ids
    )
    response = request.execute()

    for item in response["items"]:
        res.append(
            Track(
                item["snippet"]["title"],
                isodate.parse_duration(item["contentDetails"]["duration"]),
                "https://www.youtube.com/watch?v=" + item["id"],
            )
        )

    return res


def specific_search(context: str) -> list[Track]:
    search: pytubefix.Search = pytubefix.Search(context)
    res: list[Track] = []
    results: list[pytubefix.YouTube] = search.videos
    for i in range(min(5, len(results))):
        res.append(create_track(results[i]))
    return res


async def single_link(link: str) -> list[Track]:
    try:
        obj: pytubefix.YouTube = await globals_var.client_bot.loop.run_in_executor(
            None, pytubefix.YouTube, link
        )
    except pytubefix.exceptions.RegexMatchError:
        return []

    return [create_track(obj)]


async def playlist_link(
    interaction: discord.Interaction, link: str
) -> list[Track] | list[None] | None:
    if globals_var.client_bot.server_id_using_youtube is not None:
        return [None]

    globals_var.client_bot.server_id_using_youtube = interaction.guild_id
    urls = []
    playlist: pytubefix.Playlist = await globals_var.client_bot.loop.run_in_executor(
        None, pytubefix.Playlist, link
    )
    pytubefix_urls: pytubefix.helpers.DeferredGeneratorList = playlist.video_urls
    # pytubefix.helpers.DeferredGeneratorList don't support slicing we need to convert it to a list
    await globals_var.client_bot.loop.run_in_executor(None, urls.extend, pytubefix_urls)
    numbers_new_tracks: int = len(urls)
    res: list[Track] = []
    server: Server = globals_var.client_bot.get_server(interaction.guild_id)
    message: discord.Message = server.loading_playlist_message
    while urls:
        voice_client: discord.VoiceClient = discord.utils.get(
            globals_var.client_bot.voice_clients, guild=interaction.guild
        )
        if voice_client is None:
            return None
        message = await my_functions.edit_message(
            message, content=f"Loading playlist: {len(res)}/{numbers_new_tracks}."
        )
        video_ids = list(
            map(lambda n: n.split("https://www.youtube.com/watch?v=", 1)[1], urls[:50])
        )
        res.extend(
            await globals_var.client_bot.loop.run_in_executor(
                None, create_tracks, video_ids
            )
        )
        urls = urls[50:]
    globals_var.client_bot.server_id_using_youtube = None
    message = await my_functions.edit_message(
        message, content=f"Loading playlist: {len(res)}/{numbers_new_tracks}."
    )
    await my_functions.delete_msg(message)
    server.loading_playlist_message = None
    return res


# Not use
# Faster than playlist_link but costs twice in YouTube API units
def playlist_link2(link: str) -> list[Track]:
    playlist_id: str = link.split("list=", 1)[1].split("&", 1)[0]
    request_id = globals_var.youtube.playlistItems().list(
        part="contentDetails", maxResults=50, playlistId=playlist_id
    )
    res: list[Track] = []
    while request_id is not None:
        try:
            response_id = request_id.execute()
        except HttpError:
            return []

        video_ids = ",".join(
            map(
                str, map(lambda n: n["contentDetails"]["videoId"], response_id["items"])
            )
        )
        res.extend(create_tracks(video_ids))

        request_id = globals_var.youtube.playlistItems().list_next(
            previous_request=request_id, previous_response=response_id
        )

    return res
