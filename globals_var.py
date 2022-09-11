import os
import datetime

import discord
from dotenv import load_dotenv
from googleapiclient.discovery import build

from custom_classes import MusicItem

load_dotenv()

discord_key = os.getenv("DISCORD_KEY")
client_bot = discord.Client(intents=discord.Intents.all())
tree = discord.app_commands.CommandTree(client_bot)

youtube_key = os.getenv("YOUTUBE_KEY")
youtube = build("youtube", "v3", developerKey=youtube_key)

wololo = MusicItem("youtube", "Welcome", datetime.timedelta(seconds=2), "https://www.youtube.com/watch?v=hSU0Z3_466s")

"""
Store by guild id
Contains:
    'music': music currently playing,
    'message': message that display which music is currently playing,
    'audio': audio currently playing
"""
current_music = {}

"""
Store by guild id
Contains:
    'searches': list of 1 to 5 MusicItem about the last search terms
    'shuffle': boolean to know if the music must be shuffled
    'user': user who requested the song
    'message': message that shows searches
"""
specifics_searches = {}

"""
Store by guild id
Contains a list of MusicItem(s)
"""
queues_musics = {}
queues_message = {}

reactions_song = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
reactions_queue = ["⬆️", "⬇️"]


def initialize():
    global current_music, specifics_searches, queues_musics, queues_message,\
        reactions_song, reactions_queue, client_bot, youtube, tree
