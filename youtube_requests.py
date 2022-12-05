import datetime

import discord
from googleapiclient.errors import HttpError
import isodate
import pytube
import pytube.exceptions

import globals_var
import my_functions
from custom_classes import MusicItem


def create_music_item(yt_obj):
    return MusicItem("youtube", yt_obj.title, datetime.timedelta(seconds=yt_obj.length), yt_obj.watch_url)


def create_music_items(video_ids):
    res = []
    request = globals_var.youtube.videos().list(
        part="snippet,contentDetails,id",
        id=video_ids
    )
    response = request.execute()

    for item in response['items']:
        res.append(MusicItem("youtube",
                             item['snippet']['title'],
                             isodate.parse_duration(item['contentDetails']['duration']),
                             "https://www.youtube.com/watch?v=" + item['id']))

    return res


def specific_search(context):
    search = pytube.Search(context)
    res = []
    results = search.results
    for i in range(min(5, len(results))):
        res.append(create_music_item(results[i]))
    return res


def single_link(link):
    try:
        obj = pytube.YouTube(link)
    except pytube.exceptions.RegexMatchError:
        return []

    return [create_music_item(obj)]


async def waiting_queue():
    return


async def playlist_link(interaction: discord.Interaction, link):
    if len(globals_var.queue_request_youtube) == 0:
        urls = []
        # pytube.Playlist(link).video_urls returns pytube.helpers.DeferredGeneratorList that don't support slicing
        playlist = await globals_var.client_bot.loop.run_in_executor(None, pytube.Playlist, link)
        pytube_urls = playlist.video_urls
        await globals_var.client_bot.loop.run_in_executor(None, urls.extend, pytube_urls)
        numbers_new_musics = len(urls)
        res = []
        while urls:
            await my_functions.edit(interaction, content=f"Loading playlist: {len(res)}/{numbers_new_musics}.")
            video_ids = list(map(lambda n: n.split("https://www.youtube.com/watch?v=", 1)[1], urls[:50]))
            res.extend(await globals_var.client_bot.loop.run_in_executor(None, create_music_items, video_ids))
            urls = urls[50:]

        await my_functions.edit(interaction, content=f"Loading playlist: {len(res)}/{numbers_new_musics}.")
        return res


# Not use
# Faster than playlist_link but costs twice in YouTube API units
def playlist_link2(link):
    playlist_id = link.split("list=", 1)[1].split("&", 1)[0]
    request_id = globals_var.youtube.playlistItems().list(
        part="contentDetails",
        maxResults=50,
        playlistId=playlist_id
    )
    res = []
    while request_id is not None:
        try:
            response_id = request_id.execute()
        except HttpError:
            return []

        video_ids = ','.join(map(str, map(lambda n: n['contentDetails']['videoId'], response_id['items'])))
        res.extend(create_music_items(video_ids))

        request_id = globals_var.youtube.playlistItems()\
            .list_next(previous_request=request_id, previous_response=response_id)

    return res
