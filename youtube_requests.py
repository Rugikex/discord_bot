import datetime
import os

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import isodate
import pytube
from pytube.exceptions import RegexMatchError

from class_music_item import MusicItem

load_dotenv()
youtube_key = os.getenv("YOUTUBE_KEY")
youtube = build("youtube", "v3", developerKey=youtube_key)


def create_music_item(yt_obj):
    return MusicItem("youtube", yt_obj.title, datetime.timedelta(seconds=yt_obj.length), yt_obj.watch_url)


def create_music_items(video_ids):
    res = []
    request = youtube.videos().list(
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
    for i in range(min(5, len(search.results))):
        res.append(create_music_item(search.results[i]))
    return res


def single_link(link):
    try:
        obj = pytube.YouTube(link)
    except RegexMatchError:
        return []

    return [create_music_item(obj)]


def playlist_link(link):
    urls = []
    # pytube.Playlist(link).video_urls returns pytube.helpers.DeferredGeneratorList that don't support slicing
    urls.extend(pytube.Playlist(link).video_urls)
    res = []
    while urls:
        video_ids = list(map(lambda n: n.split("https://www.youtube.com/watch?v=", 1)[1], urls[:50]))
        res.extend(create_music_items(video_ids))
        urls = urls[50:]

    return res


# Faster than playlist_link but costs twice in YouTube API units
def playlist_link2(link):
    playlist_id = link.split("list=", 1)[1].split("&index=", 1)[0]
    request_id = youtube.playlistItems().list(
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

        request_id = youtube.playlistItems().list_next(previous_request=request_id, previous_response=response_id)

    return res
